from functools import wraps
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from werkzeug.security import check_password_hash
from services.database_service import get_user_by_username

auth_bp = Blueprint('auth', __name__)

def login_required(*args):
    """
    Flexible Authentication & Role Authorization Decorator.
    Supports usage as:
      @login_required                -> requires any authenticated user
      @login_required("staff")       -> requires authenticated staff member
      @login_required("student", "staff") -> requires student or staff role
    """
    if len(args) == 1 and callable(args[0]):
        f = args[0]
        @wraps(f)
        def decorated_function(*f_args, **f_kwargs):
            if 'user_id' not in session:
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Unauthorized. Please login.'}), 401
                return redirect(url_for('auth.login'))
            return f(*f_args, **f_kwargs)
        return decorated_function
    else:
        roles = args
        def decorator(f):
            @wraps(f)
            def decorated_function(*f_args, **f_kwargs):
                if 'user_id' not in session:
                    if request.path.startswith('/api/'):
                        return jsonify({'error': 'Unauthorized. Please login.'}), 401
                    return redirect(url_for('auth.login'))
                user_role = session.get('role')
                if roles and user_role not in roles:
                    if request.path.startswith('/api/'):
                        return jsonify({'error': 'Forbidden. Access restricted.'}), 403
                    return render_template('unauthorized.html', role=user_role), 403
                return f(*f_args, **f_kwargs)
            return decorated_function
        return decorator

def role_required(*roles):
    return login_required(*roles)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if 'user_id' in session:
            role = session.get('role')
            if role == 'hod':
                return redirect(url_for('hod.dashboard'))
            elif role == 'staff':
                return redirect(url_for('staff.dashboard'))
            elif role == 'student':
                return redirect(url_for('student.dashboard'))
        return render_template('login.html')

    data = request.get_json() if request.is_json else request.form
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', '')).strip()

    if not username or not password:
        if request.is_json:
            return jsonify({'error': 'Username and password are required.'}), 400
        return render_template('login.html', error='Username and password are required.')

    user = get_user_by_username(username)
    if not user or not check_password_hash(user['password_hash'], password):
        if request.is_json:
            return jsonify({'error': 'Invalid username or password credentials.'}), 401
        return render_template('login.html', error='Invalid username or password credentials.')

    # Set Session
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    session['student_id'] = user['student_id']
    session['staff_id'] = user['staff_id']
    session['display_name'] = user['student_name'] or user['staff_name'] or 'HOD - IT Department'

    redirect_url = '/hod/dashboard'
    if user['role'] == 'staff':
        redirect_url = '/staff/dashboard'
    elif user['role'] == 'student':
        redirect_url = '/student/dashboard'

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
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/me')
@login_required
def get_current_user():
    return jsonify({
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'role': session.get('role'),
        'display_name': session.get('display_name'),
        'student_id': session.get('student_id'),
        'staff_id': session.get('staff_id')
    })
