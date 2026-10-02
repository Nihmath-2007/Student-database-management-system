import time
import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template, flash
from config.database import execute_query
from services.database_service import get_user_by_username

auth_bp = Blueprint('auth', __name__)

def verify_password(stored_hash: str, candidate_password: str) -> bool:
    """
    Verifies passwords using bcrypt or werkzeug hashes securely.
    """
    if not stored_hash or not candidate_password:
        return False
    try:
        # Check if stored hash is bcrypt
        if stored_hash.startswith('$2b$') or stored_hash.startswith('$2a$') or stored_hash.startswith('$2y$'):
            import bcrypt
            return bcrypt.checkpw(candidate_password.encode('utf-8'), stored_hash.encode('utf-8'))
        
        # Fallback to werkzeug security
        from werkzeug.security import check_password_hash
        return check_password_hash(stored_hash, candidate_password)
    except Exception as e:
        print(f"Password verification warning: {e}")
        return False

def login_required(*args):
    """
    Flexible Authentication & Role Authorization Decorator.
    Supports usage as:
      @login_required                -> requires any authenticated user
      @login_required("staff")       -> requires authenticated staff member
      @login_required("student", "admin") -> requires student or admin role
    """
    if len(args) == 1 and callable(args[0]):
        f = args[0]
        @wraps(f)
        def decorated_function(*f_args, **f_kwargs):
            if 'user_id' not in session:
                if request.path.startswith('/api/') or request.is_json or request.headers.get('Accept') == 'application/json':
                    return jsonify({'error': 'Unauthorized. Please login.', 'authenticated': False}), 401
                return redirect(url_for('auth.login', next=request.path))
            return f(*f_args, **f_kwargs)
        return decorated_function
    else:
        roles = list(args)
        # Admins have full access to HOD endpoints
        if 'hod' in roles and 'admin' not in roles:
            roles.append('admin')

        def decorator(f):
            @wraps(f)
            def decorated_function(*f_args, **f_kwargs):
                if 'user_id' not in session:
                    if request.path.startswith('/api/') or request.is_json or request.headers.get('Accept') == 'application/json':
                        return jsonify({'error': 'Unauthorized. Please login.', 'authenticated': False}), 401
                    return redirect(url_for('auth.login', next=request.path))
                
                user_role = session.get('role')
                if roles and user_role not in roles:
                    if request.path.startswith('/api/') or request.is_json or request.headers.get('Accept') == 'application/json':
                        return jsonify({'error': 'Forbidden. Access restricted.', 'role': user_role}), 403
                    return render_template('unauthorized.html', role=user_role), 403
                return f(*f_args, **f_kwargs)
            return decorated_function
        return decorator

def role_required(*roles):
    return login_required(*roles)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        # If user is already authenticated, direct to appropriate dashboard
        if 'user_id' in session:
            role = session.get('role')
            if role in ('admin', 'hod'):
                return redirect(url_for('hod.dashboard'))
            elif role == 'staff':
                return redirect(url_for('staff.dashboard'))
            elif role == 'student':
                return redirect(url_for('student.dashboard'))
                
        timeout_msg = None
        if request.args.get('timeout'):
            timeout_msg = "Your session has expired due to 15 minutes of inactivity. Please log in again."
            
        return render_template('login.html', error=timeout_msg)

    # Handle POST
    data = request.get_json() if request.is_json else request.form
    username_input = str(data.get('username', '')).strip()
    password_input = str(data.get('password', '')).strip()

    # Rule 3: Show "Invalid roll number or password" on failure; do not distinguish
    invalid_cred_msg = "Invalid roll number or password"

    if not username_input or not password_input:
        if request.is_json:
            return jsonify({'error': invalid_cred_msg}), 401
        return render_template('login.html', error=invalid_cred_msg)

    # 1. Lookup user by roll number, student name, or admin username
    user = get_user_by_username(username_input)
    if not user:
        if request.is_json:
            return jsonify({'error': invalid_cred_msg}), 401
        return render_template('login.html', error=invalid_cred_msg)

    # 2. Check Account Lockout (5 wrong attempts -> 5 minutes lock)
    now = datetime.datetime.now()
    locked_until = user.get('locked_until')
    if locked_until:
        if isinstance(locked_until, str):
            try:
                locked_until = datetime.datetime.fromisoformat(locked_until)
            except Exception:
                pass
        
        if isinstance(locked_until, datetime.datetime) and locked_until > now:
            remaining_seconds = int((locked_until - now).total_seconds())
            remaining_minutes = max(1, (remaining_seconds + 59) // 60)
            lock_msg = f"Account is temporarily locked due to 5 consecutive failed login attempts. Please try again after {remaining_minutes} minute(s)."
            if request.is_json:
                return jsonify({'error': lock_msg, 'locked': True, 'remaining_minutes': remaining_minutes}), 429
            return render_template('login.html', error=lock_msg)
        else:
            # Lockout expired, reset failed counter
            execute_query("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = %s", (user['id'],), commit=True)
            user['failed_attempts'] = 0

    # 3. Validate password against hashed password
    if not verify_password(user['password_hash'], password_input):
        current_attempts = int(user.get('failed_attempts') or 0) + 1
        if current_attempts >= 5:
            lock_deadline = now + datetime.timedelta(minutes=5)
            execute_query(
                "UPDATE users SET failed_attempts = %s, locked_until = %s WHERE id = %s",
                (current_attempts, lock_deadline, user['id']),
                commit=True
            )
            lock_msg = "Account is temporarily locked due to 5 consecutive failed login attempts. Please try again after 5 minutes."
            if request.is_json:
                return jsonify({'error': lock_msg, 'locked': True}), 429
            return render_template('login.html', error=lock_msg)
        else:
            execute_query(
                "UPDATE users SET failed_attempts = %s WHERE id = %s",
                (current_attempts, user['id']),
                commit=True
            )
            if request.is_json:
                return jsonify({'error': invalid_cred_msg}), 401
            return render_template('login.html', error=invalid_cred_msg)

    # 4. Successful login: reset failed attempts & lockout
    execute_query("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = %s", (user['id'],), commit=True)

    # 5. Initialize secure session
    session.clear()
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    session['student_id'] = user['student_id']
    session['staff_id'] = user['staff_id']
    session['display_name'] = user['student_name'] or user['staff_name'] or ('Administrator' if user['role'] in ('admin', 'hod') else user['username'])
    session['last_activity'] = time.time()
    session.permanent = True

    # Role-based redirection
    if user['role'] in ('admin', 'hod'):
        redirect_url = url_for('hod.dashboard')
    elif user['role'] == 'staff':
        redirect_url = url_for('staff.dashboard')
    elif user['role'] == 'student':
        redirect_url = url_for('student.dashboard')
    else:
        redirect_url = url_for('index')

    if request.is_json:
        return jsonify({
            'message': 'Login successful',
            'role': user['role'],
            'redirect_url': redirect_url
        })
    return redirect(redirect_url)

@auth_bp.route('/logout')
def logout():
    session.clear()
    timeout = request.args.get('timeout')
    if timeout:
        return redirect(url_for('auth.login', timeout=1))
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/me')
@login_required
def get_current_user():
    # Security requirement: NEVER return password_hash or DOB in API responses
    return jsonify({
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'role': session.get('role'),
        'display_name': session.get('display_name'),
        'student_id': session.get('student_id'),
        'staff_id': session.get('staff_id')
    })
