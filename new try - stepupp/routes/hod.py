from flask import Blueprint, render_template, jsonify, request, session
from routes.auth import role_required
from services.analytics import calculate_department_analytics
from services.database_service import get_all_students, get_student_details, get_all_subjects

hod_bp = Blueprint('hod', __name__, url_prefix='/hod')

@hod_bp.route('/dashboard')
@role_required('hod')
def dashboard():
    return render_template('hod/dashboard.html')

@hod_bp.route('/students')
@role_required('hod')
def students_page():
    return render_template('hod/students.html')

@hod_bp.route('/student/<int:student_id>')
@role_required('hod')
def student_detail_page(student_id):
    return render_template('hod/student_detail.html', student_id=student_id)

@hod_bp.route('/attendance')
@role_required('hod')
def attendance_analytics_page():
    return render_template('hod/attendance.html')

@hod_bp.route('/marks')
@role_required('hod')
def marks_analytics_page():
    return render_template('hod/marks.html')

@hod_bp.route('/staff')
@role_required('hod')
def staff_page():
    return render_template('hod/staff.html')

@hod_bp.route('/analytics')
@role_required('hod')
def analytics_page():
    return render_template('hod/analytics.html')

@hod_bp.route('/reports')
@role_required('hod')
def reports_page():
    return render_template('hod/reports.html')

@hod_bp.route('/csv-upload')
@role_required('hod')
def csv_upload_page():
    return render_template('hod/csv_upload.html')

# API Endpoints
@hod_bp.route('/api/analytics')
@role_required('hod')
def api_hod_analytics():
    data = calculate_department_analytics()
    return jsonify(data)

@hod_bp.route('/api/students')
@role_required('hod')
def api_hod_students():
    year = request.args.get('year')
    subject = request.args.get('subject')
    search = request.args.get('search')
    
    students = get_all_students(year_filter=year, subject_filter=subject, search=search)
    return jsonify(students)

@hod_bp.route('/api/student/<int:student_id>')
@role_required('hod')
def api_hod_student_detail(student_id):
    data = get_student_details(student_id)
    if not data:
        return jsonify({'error': 'Student not found.'}), 404
    return jsonify(data)

@hod_bp.route('/api/subjects')
@role_required('hod')
def api_hod_subjects():
    subjects = get_all_subjects()
    return jsonify(subjects)
