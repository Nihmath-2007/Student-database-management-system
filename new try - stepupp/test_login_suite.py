import os
import sys
import time
import unittest
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from config.database import execute_query

class TestStudentAuthSystem(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        # Reset failed attempts and lockout for test accounts
        execute_query("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE username IN ('911524205030', '911524205001', 'admin')", commit=True)

    def test_01_successful_login_with_roll_number(self):
        """Rule 1 & 2: Login with Roll Number and DOB password."""
        res = self.client.post('/login', data={
            'username': '911524205030',
            'password': '03032007'
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/student/dashboard', res.headers.get('Location', ''))

    def test_02_successful_login_with_student_name(self):
        """Rule 1: Login with Student Name (case-insensitive) and DOB password."""
        res = self.client.post('/login', data={
            'username': 'MOHAMED NIHMATHULLAH S',
            'password': '03032007'
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/student/dashboard', res.headers.get('Location', ''))

    def test_03_invalid_password_returns_generic_error(self):
        """Rule 3: Show 'Invalid roll number or password' and do NOT disclose which was wrong."""
        res = self.client.post('/login', data={
            'username': '911524205030',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Invalid roll number or password', res.data)
        # Must NOT leak which one was incorrect
        self.assertNotIn(b'password is incorrect', res.data.lower())
        self.assertNotIn(b'user not found', res.data.lower())

    def test_04_nonexistent_roll_returns_same_generic_error(self):
        """Rule 3: Nonexistent roll returns exact same error."""
        res = self.client.post('/login', data={
            'username': '999999999999',
            'password': '01012000'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Invalid roll number or password', res.data)

    def test_05_account_lockout_after_5_wrong_attempts(self):
        """Rule 5: After 5 wrong attempts, lock that account for 5 minutes."""
        test_roll = '911524205001'
        # 4 wrong attempts
        for _ in range(4):
            res = self.client.post('/login', data={'username': test_roll, 'password': 'bad'}, follow_redirects=True)
            self.assertIn(b'Invalid roll number or password', res.data)

        # 5th wrong attempt triggers lockout
        res5 = self.client.post('/login', data={'username': test_roll, 'password': 'bad'}, follow_redirects=True)
        self.assertIn(b'Account is temporarily locked', res5.data)

        # 6th attempt (even with correct password) remains blocked while locked
        res6 = self.client.post('/login', data={'username': test_roll, 'password': '07082007'}, follow_redirects=True)
        self.assertIn(b'Account is temporarily locked', res6.data)

        # Cleanup lock
        execute_query("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE username = %s", (test_roll,), commit=True)

    def test_06_unauthenticated_requests_blocked(self):
        """Rule 4: Block every page and API route unless user is logged in."""
        # HTML Page: Redirects to login
        res_page = self.client.get('/student/dashboard', follow_redirects=False)
        self.assertEqual(res_page.status_code, 302)
        self.assertIn('/login', res_page.headers.get('Location', ''))

        # API Route: Server rejects with HTTP 401
        res_api = self.client.get('/student/api/dashboard')
        self.assertEqual(res_api.status_code, 401)
        self.assertIn('Unauthorized', res_api.get_json().get('error', ''))

    def test_07_student_can_only_see_own_record(self):
        """Rule 7: Logged-in student can see only their own record; admin sees all."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 29
            sess['username'] = '911524205030'
            sess['role'] = 'student'
            sess['student_id'] = 29
            sess['display_name'] = 'MOHAMED NIHMATHULLAH S'
            sess['last_activity'] = time.time()

        # Student CAN access own dashboard API
        res_stud = self.client.get('/student/api/dashboard')
        self.assertEqual(res_stud.status_code, 200)
        stud_data = res_stud.get_json()
        self.assertEqual(stud_data['profile']['studentid'], 29)
        # Security: DOB and password must NOT be in student profile response
        self.assertNotIn('dob', stud_data['profile'])
        self.assertNotIn('password', stud_data['profile'])
        self.assertNotIn('password_hash', stud_data['profile'])

        # Student CANNOT access admin student list (Blocked with 403)
        res_admin_api = self.client.get('/hod/api/students')
        self.assertEqual(res_admin_api.status_code, 403)

    def test_08_admin_can_access_all_students(self):
        """Rule 7: Admin account can see all students."""
        res = self.client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/hod/dashboard', res.headers.get('Location', ''))

    def test_09_inactivity_timeout_forces_logout(self):
        """Rule 6: Log users out after 15 minutes of inactivity."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 29
            sess['username'] = '911524205030'
            sess['role'] = 'student'
            sess['student_id'] = 29
            # Set last activity to 16 minutes ago
            sess['last_activity'] = time.time() - (16 * 60)

        # Access should be rejected due to inactivity timeout
        res = self.client.get('/student/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers.get('Location', ''))
        self.assertIn('timeout=1', res.headers.get('Location', ''))

    def test_10_logout_clears_session(self):
        """Rule 6: Logout button clears session."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 29
            sess['username'] = '911524205030'
            sess['role'] = 'student'
            sess['last_activity'] = time.time()

        res = self.client.get('/logout', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers.get('Location', ''))

        # Check session is cleared
        with self.client.session_transaction() as sess:
            self.assertNotIn('user_id', sess)

if __name__ == '__main__':
    unittest.main()
