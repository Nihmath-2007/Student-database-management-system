from flask import Blueprint, render_template, jsonify, request, session
from routes.auth import role_required
from services.database_service import get_staff_subjects, get_subject_details, get_student_details, get_all_students

staff_bp = Blueprint('staff', __name__, url_prefix='/staff')

@staff_bp.route('/dashboard')
@role_required('staff')
def dashboard():
    return render_template('staff/dashboard.html')

@staff_bp.route('/subject-analytics')
@role_required('staff')
def subject_analytics_page():
    return render_template('staff/subject_analytics.html')

@staff_bp.route('/students')
@role_required('staff')
def students_page():
    return render_template('staff/students.html')

@staff_bp.route('/student/<int:student_id>')
@role_required('staff')
def student_detail_page(student_id):
    return render_template('staff/student_detail.html', student_id=student_id)

@staff_bp.route('/attendance')
@role_required('staff')
def attendance_page():
    return render_template('staff/attendance.html')

@staff_bp.route('/marks')
@role_required('staff')
def marks_page():
    return render_template('staff/marks.html')

@staff_bp.route('/csv-upload')
@role_required('staff')
def csv_upload_page():
    return render_template('staff/csv_upload.html')

# API Endpoints
@staff_bp.route('/api/subjects')
@role_required('staff')
def api_staff_subjects():
    staff_id = session.get('staff_id')
    subjects = get_staff_subjects(staff_id)
    return jsonify(subjects)

@staff_bp.route('/api/dashboard')
@role_required('staff')
def api_staff_dashboard():
    staff_id = session.get('staff_id')
    assigned_subjects = get_staff_subjects(staff_id)
    
    total_students_set = set()
    subject_analytics_list = []
    
    for sub in assigned_subjects:
        details = get_subject_details(sub['subjectid'])
        if details:
            subject_analytics_list.append(details)
            for m in details['student_marks']:
                total_students_set.add(m['studentid'])

    total_students = len(total_students_set)
    avg_marks = round(sum(s['average_marks'] for s in subject_analytics_list)/len(subject_analytics_list), 1) if subject_analytics_list else 0
    avg_att = round(sum(s['average_attendance'] for s in subject_analytics_list)/len(subject_analytics_list), 1) if subject_analytics_list else 0
    
    avg_pass = round(sum(s['pass_percentage'] for s in subject_analytics_list)/len(subject_analytics_list), 1) if subject_analytics_list else 0
    avg_fail = round(100.0 - avg_pass, 1)

    return jsonify({
        'assigned_subjects_count': len(assigned_subjects),
        'total_students': total_students,
        'average_marks': avg_marks,
        'average_attendance': avg_att,
        'pass_percentage': avg_pass,
        'fail_percentage': avg_fail,
        'subjects': assigned_subjects,
        'subject_analytics': subject_analytics_list
    })

@staff_bp.route('/api/subject/<int:subject_id>')
@role_required('staff')
def api_staff_subject_detail(subject_id):
    staff_id = session.get('staff_id')
    # RBAC check: ensure subject belongs to staff
    assigned_subjects = get_staff_subjects(staff_id)
    allowed_ids = [s['subjectid'] for s in assigned_subjects]
    
    if subject_id not in allowed_ids:
        return jsonify({'error': 'Unauthorized. Subject not assigned to you.'}), 403

    details = get_subject_details(subject_id)
    if not details:
        return jsonify({'error': 'Subject details not found.'}), 404
        
    return jsonify(details)

@staff_bp.route('/api/students')
@role_required('staff')
def api_staff_students():
    staff_id = session.get('staff_id')
    assigned_subjects = get_staff_subjects(staff_id)
    assigned_sub_ids = [s['subjectid'] for s in assigned_subjects]

    if not assigned_sub_ids:
        return jsonify([])

    # Filter all students to those taking assigned subjects
    all_students = get_all_students()
    staff_students = []
    
    for student in all_students:
        s_details = get_student_details(student['studentid'])
        if s_details:
            # Check if student takes any of staff's subjects
            sub_ids = [s.get('subject_id') for s in s_details['subjects'] if s.get('subject_id') in assigned_sub_ids]
            if sub_ids or len(assigned_sub_ids) > 0:
                staff_students.append(student)

    return jsonify(staff_students)

@staff_bp.route('/api/student/<int:student_id>')
@role_required('staff')
def api_staff_student_detail(student_id):
    data = get_student_details(student_id)
    if not data:
        return jsonify({'error': 'Student not found.'}), 404
    return jsonify(data)

