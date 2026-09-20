from flask import Blueprint, render_template, jsonify, session
from routes.auth import role_required
from services.database_service import get_student_details

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/dashboard')
@role_required('student')
def dashboard():
    return render_template('student/dashboard.html')

@student_bp.route('/marks')
@role_required('student')
def marks_page():
    return render_template('student/marks.html')

@student_bp.route('/attendance')
@role_required('student')
def attendance_page():
    return render_template('student/attendance.html')

@student_bp.route('/calculator')
@role_required('student')
def calculator_page():
    return render_template('student/calculator.html')

@student_bp.route('/performance')
@role_required('student')
def performance_page():
    return render_template('student/performance.html')

@student_bp.route('/profile')
@role_required('student')
def profile_page():
    student_id = session.get('student_id', 1)
    return render_template('student/profile.html', student_id=student_id)

# API Endpoint
@student_bp.route('/api/dashboard')
@role_required('student')
def api_student_dashboard():
    student_id = session.get('student_id')
    if not student_id:
        return jsonify({'error': 'Student ID not bound to user session.'}), 400

    details = get_student_details(student_id)
    if not details:
        return jsonify({'error': 'Student records not found.'}), 404

    # Determine best subject and lowest performing subject
    subjects = details.get('subjects', [])
    best_subject = None
    lowest_subject = None
    
    if subjects:
        best_subject = max(subjects, key=lambda s: s['percentage'])['subject_name']
        lowest_subject = min(subjects, key=lambda s: s['percentage'])['subject_name']

    details['best_subject'] = best_subject or 'N/A'
    details['lowest_subject'] = lowest_subject or 'N/A'

    return jsonify(details)
