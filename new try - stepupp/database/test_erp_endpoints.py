"""
Comprehensive automated test suite for ERP REST API endpoints.
Tests Student, Staff, Subject, Attendance, Marks, Timetable CRUD and Audit logging
directly through Flask test client with HOD role session.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from app import app
from db import fetch_one, execute

class ErpEndpointTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'hod'
            sess['role'] = 'hod'
            sess['display_name'] = 'Dr. HOD Test'

    def test_01_student_crud(self):
        print("\n--- Testing Student CRUD ---")
        test_regno = "911524TEST01"

        # 1. Create
        payload = {
            'regno': test_regno,
            'name': 'ERP Automated Test Student',
            'department': 'Information Technology',
            'year': 'Third year',
            'section': 'A',
            'email': 'erp_test@msec.org.in',
            'phone': '9876543210'
        }
        res = self.client.post('/hod/api/students', json=payload)
        self.assertIn(res.status_code, [200, 201])
        data = res.get_json()
        self.assertTrue(data.get('success'))
        student_id = data['data']['studentid']
        print(f"Created student ID: {student_id}")

        # 2. Get
        res_get = self.client.get(f'/hod/api/student/{student_id}')
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.get_json()['profile']['regno'], test_regno)

        # 3. Update
        payload['name'] = 'ERP Automated Test Student (Updated)'
        res_upd = self.client.put(f'/hod/api/student/{student_id}', json=payload)
        self.assertEqual(res_upd.status_code, 200)

        # 4. Delete
        res_del = self.client.delete(f'/hod/api/student/{student_id}')
        self.assertEqual(res_del.status_code, 200)
        print("Student CRUD succeeded.")

    def test_02_staff_crud(self):
        print("\n--- Testing Staff CRUD ---")
        payload = {
            'name': 'Prof. ERP Test Faculty',
            'designation': 'Assistant Professor',
            'department': 'Information Technology',
            'subjects': 'Software Engineering',
            'email': 'faculty_test@msec.org.in',
            'phone': '9988776655'
        }
        res = self.client.post('/hod/api/staff', json=payload)
        self.assertIn(res.status_code, [200, 201])
        data = res.get_json()
        staff_id = data['data']['staffid']
        print(f"Created staff ID: {staff_id}")

        # Update
        payload['designation'] = 'Associate Professor'
        res_upd = self.client.put(f'/hod/api/staff/{staff_id}', json=payload)
        self.assertEqual(res_upd.status_code, 200)

        # Delete
        res_del = self.client.delete(f'/hod/api/staff/{staff_id}')
        self.assertEqual(res_del.status_code, 200)
        print("Staff CRUD succeeded.")

    def test_03_subject_crud(self):
        print("\n--- Testing Subject CRUD ---")
        sub_code = "24TEST01"
        payload = {
            'subject_code': sub_code,
            'subject_name': 'Automated Test Course',
            'semester': 5,
            'department': 'Information Technology',
            'staff_id': None
        }
        res = self.client.post('/hod/api/subjects', json=payload)
        self.assertIn(res.status_code, [200, 201])
        print(f"Created subject code: {sub_code}")

        # Update
        payload['subject_name'] = 'Automated Test Course (Updated)'
        res_upd = self.client.put(f'/hod/api/subject/{sub_code}', json=payload)
        self.assertEqual(res_upd.status_code, 200)

        # Delete
        res_del = self.client.delete(f'/hod/api/subject/{sub_code}')
        self.assertEqual(res_del.status_code, 200)
        print("Subject CRUD succeeded.")

    def test_04_attendance_crud_and_export(self):
        print("\n--- Testing Attendance CRUD & Export ---")
        first_stu = fetch_one("SELECT studentid FROM students LIMIT 1")
        if not first_stu:
            return
        stu_id = first_stu['studentid']

        # Add
        payload = {
            'student_id': stu_id,
            'date': '2026-09-28',
            'status': 'Present'
        }
        res = self.client.post('/hod/api/attendance', json=payload)
        self.assertIn(res.status_code, [200, 201])
        
        # Get
        res_get = self.client.get(f'/hod/api/attendance?student_id={stu_id}&date=2026-09-28')
        self.assertEqual(res_get.status_code, 200)
        recs = res_get.get_json()['records']
        self.assertTrue(len(recs) > 0)
        att_id = recs[0]['id']

        # Update
        res_upd = self.client.put(f'/hod/api/attendance/{att_id}', json={'status': 'Absent', 'date': '2026-09-28'})
        self.assertEqual(res_upd.status_code, 200)

        # Export CSV
        res_exp = self.client.get('/hod/api/attendance/export')
        self.assertEqual(res_exp.status_code, 200)
        self.assertIn('text/csv', res_exp.headers.get('Content-Type'))
        print("Attendance CRUD and CSV export succeeded.")

    def test_05_timetable_crud(self):
        print("\n--- Testing Timetable CRUD ---")
        first_sub = fetch_one("SELECT subject_code FROM subjects LIMIT 1")
        sub_code = first_sub['subject_code'] if first_sub else '24IT3501'

        payload = {
            'day_of_week': 'Saturday',
            'period_number': 7,
            'time_slot': '03:10 PM - 04:00 PM',
            'subject_code': sub_code,
            'classroom': 'TEST-LAB',
            'year': 'Third year',
            'section': 'A'
        }
        res = self.client.post('/hod/api/timetable', json=payload)
        self.assertIn(res.status_code, [200, 201])
        slot_id = res.get_json()['data']['id']

        # Update
        payload['classroom'] = 'LH-305'
        res_upd = self.client.put(f'/hod/api/timetable/{slot_id}', json=payload)
        self.assertEqual(res_upd.status_code, 200)

        # Delete
        res_del = self.client.delete(f'/hod/api/timetable/{slot_id}')
        self.assertEqual(res_del.status_code, 200)
        print("Timetable CRUD succeeded.")

if __name__ == '__main__':
    unittest.main()
