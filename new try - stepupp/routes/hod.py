import os
from datetime import datetime
from uuid import uuid4
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for, flash, current_app, Response
from routes.auth import role_required, login_required
from db import fetch_all, fetch_one, execute
from services.analytics import calculate_department_analytics
from services.database_service import get_all_students, get_student_details, get_all_subjects
from services.correction_service import get_hod_queries, get_hod_summary_stats, get_all_audit_logs, resolve_mark_correction_query, get_query_details
<<<<<<< HEAD
from services.cache_service import api_cache
from services.erp_service import (
    erp_get_students, erp_get_student_by_id, erp_create_student, erp_update_student, erp_delete_student,
    erp_get_all_staff, erp_create_staff, erp_update_staff, erp_delete_staff,
    erp_get_all_subjects, erp_create_subject, erp_update_subject, erp_delete_subject,
    erp_get_attendance, erp_add_attendance, erp_update_attendance, erp_delete_attendance, erp_export_attendance_csv,
    erp_get_marks, erp_add_mark, erp_update_mark, erp_delete_mark, erp_get_marks_reports,
    erp_get_timetable, erp_add_timetable_slot, erp_update_timetable_slot, erp_delete_timetable_slot
)

def get_current_user_meta():
    return {
        'user_id': session.get('user_id'),
        'user_name': session.get('display_name', 'HOD - IT Department'),
        'user_role': session.get('role', 'hod')
    }
=======
from services.erp_service import (
    get_students_paginated, add_student, update_student, delete_student,
    get_staff_detailed, add_staff, update_staff, delete_staff,
    get_subjects_detailed, add_subject, update_subject, delete_subject,
    get_attendance_records, add_attendance, update_attendance, delete_attendance,
    get_marks_records, add_mark, update_mark, delete_mark,
    get_timetable_grid, add_timetable_entry, delete_timetable_entry
)
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1

hod_bp = Blueprint('hod', __name__, url_prefix='/hod')

ALLOWED_GALLERY_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}

@hod_bp.route('/dashboard')
@role_required('hod')
def dashboard():
    gallery_items = fetch_all("SELECT * FROM gallery ORDER BY uploaded_at DESC")
    return render_template('hod/dashboard.html', gallery_items=gallery_items)

@hod_bp.route('/edit-details')
@role_required('hod', 'admin')
def edit_details_page():
    return render_template('hod/edit_details.html')

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
@role_required('hod', 'admin')
def staff_page():
    return render_template('hod/staff.html')

@hod_bp.route('/subjects')
@role_required('hod', 'admin')
def subjects_page():
    return render_template('hod/subjects.html')

@hod_bp.route('/timetable')
@role_required('hod', 'admin')
def timetable_page():
    return render_template('hod/timetable.html')

@hod_bp.route('/analytics')
@role_required('hod', 'admin')
def analytics_page():
    return render_template('hod/analytics.html')

@hod_bp.route('/reports')
@role_required('hod', 'admin')
def reports_page():
    return render_template('hod/reports.html')

@hod_bp.route('/csv-upload')
@role_required('hod', 'admin')
def csv_upload_page():
    return render_template('hod/csv_upload.html')

<<<<<<< HEAD
# =========================================================================
# ERP REST API ENDPOINTS
# =========================================================================

@hod_bp.route('/api/analytics')
@role_required('hod', 'admin')
def api_hod_analytics():
    refresh = request.args.get('refresh') in ('1', 'true', 'yes')
    data = calculate_department_analytics(force_refresh=refresh)
    return jsonify(data)

# --- 1. Student Management APIs ---
@hod_bp.route('/api/students', methods=['GET', 'POST'])
@role_required('hod', 'admin')
def api_hod_students():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form.to_dict()
        try:
            res = erp_create_student(data, get_current_user_meta())
            api_cache.invalidate('students')
            return jsonify({'success': True, 'data': res}), 201
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 400
        except Exception as e:
            return jsonify({'error': f'Failed to create student: {str(e)}'}), 500

    # GET
=======
@hod_bp.route('/subjects')
@role_required('hod')
def subjects_page():
    return render_template('hod/subjects.html')

@hod_bp.route('/timetable')
@role_required('hod')
def timetable_page():
    return render_template('hod/timetable.html')

# ==============================================================================
# HOD ERP REST API ENDPOINTS
# ==============================================================================

# --- Student Management Endpoints ---
@hod_bp.route('/api/students', methods=['GET'])
@role_required('hod')
def api_hod_students():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 15))
    search = request.args.get('search')
    department = request.args.get('department')
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
    year = request.args.get('year')
    department = request.args.get('department')
    subject = request.args.get('subject')
<<<<<<< HEAD
    search = request.args.get('search')
    status = request.args.get('status')
    page = request.args.get('page')
    per_page = request.args.get('per_page')
    paginate = request.args.get('paginate') in ('1', 'true', 'yes') or page is not None
    simple = request.args.get('simple') in ('1', 'true', 'yes')
    refresh = request.args.get('refresh') in ('1', 'true', 'yes')
=======

    # If requested without pagination params, maintain backward compatibility
    if not request.args.get('page'):
        students = get_all_students(year_filter=year, subject_filter=subject, search=search)
        return jsonify(students)

    result = get_students_paginated(search=search, department=department, year=year, page=page, limit=limit)
    return jsonify(result)

@hod_bp.route('/api/students', methods=['POST'])
@role_required('hod')
def api_hod_add_student():
    data = request.get_json() if request.is_json else request.form
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        res = add_student(data, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Student added successfully!', 'student': res}), 201
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to create student: {str(e)}'}), 500

@hod_bp.route('/api/students/<int:student_id>', methods=['PUT', 'POST'])
@role_required('hod')
def api_hod_update_student(student_id):
    data = request.get_json() if request.is_json else request.form
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        res = update_student(student_id, data, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Student updated successfully!', 'student': res})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to update student: {str(e)}'}), 500

@hod_bp.route('/api/students/<int:student_id>', methods=['DELETE'])
@role_required('hod')
def api_hod_delete_student(student_id):
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        delete_student(student_id, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Student removed successfully!'})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to delete student: {str(e)}'}), 500
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1

    cache_key = f"students_{simple}_{paginate}_{page}_{per_page}_{year}_{department}_{subject}_{search}_{status}"
    if not refresh:
        cached = api_cache.get(cache_key)
        if cached is not None:
            return jsonify(cached)

    if simple:
        # Fast student list query directly on students table without heavy cross-table joins
        query = "SELECT studentid, regno, name, department, year, section, email, phone FROM students WHERE 1=1"
        params = []
        if department and department != 'All':
            query += " AND (department = %s OR department = %s)"
            dept_map = {'Information Technology': 'IT', 'IT': 'Information Technology', 'Computer Science': 'CSE', 'CSE': 'Computer Science', 'Artificial Intelligence': 'AI', 'AI': 'Artificial Intelligence'}
            params.extend([department, dept_map.get(department, department)])
        if year and year != 'All':
            query += " AND year = %s"
            params.append(year)
        if search:
            query += " AND (name LIKE %s OR regno LIKE %s OR email LIKE %s)"
            s_term = f"%{search.strip()}%"
            params.extend([s_term, s_term, s_term])
        query += " ORDER BY regno ASC"
        students = fetch_all(query, tuple(params)) or []
        for s in students:
            s['status'] = 'Active'
            s['at_risk'] = False
        api_cache.set(cache_key, students, ttl=60)
        return jsonify(students)

    if paginate:
        p = int(page or 1)
        pp = int(per_page or 20)
        res = erp_get_students(search=search, department=department, year=year, status=status, page=p, per_page=pp)
        api_cache.set(cache_key, res, ttl=45)
        return jsonify(res)
    else:
        # Backward-compatible list for analytics pages
        students = get_all_students(year_filter=year, subject_filter=subject, search=search)
        api_cache.set(cache_key, students, ttl=45)
        return jsonify(students)

@hod_bp.route('/api/student/<int:student_id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
@role_required('hod', 'admin')
def api_hod_student_detail(student_id):
    if request.method == 'DELETE':
        try:
            res = erp_delete_student(student_id, get_current_user_meta())
            api_cache.invalidate('students')
            return jsonify({'success': True, 'data': res})
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 404
        except Exception as e:
            return jsonify({'error': f'Failed to delete student: {str(e)}'}), 500

    if request.method in ('PUT', 'PATCH'):
        data = request.get_json() if request.is_json else request.form.to_dict()
        try:
            res = erp_update_student(student_id, data, get_current_user_meta())
            api_cache.invalidate('students')
            return jsonify({'success': True, 'data': res})
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 400
        except Exception as e:
            return jsonify({'error': f'Failed to update student: {str(e)}'}), 500

    # GET
    data = erp_get_student_by_id(student_id)
    if not data:
        return jsonify({'error': 'Student not found.'}), 404
    return jsonify(data)

<<<<<<< HEAD

# --- 2. Staff Management APIs ---
@hod_bp.route('/api/staff', methods=['GET', 'POST'])
@role_required('hod', 'admin')
def api_hod_staff():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form.to_dict()
        try:
            res = erp_create_staff(data, get_current_user_meta())
            api_cache.invalidate('staff')
            return jsonify({'success': True, 'data': res}), 201
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 400
        except Exception as e:
            return jsonify({'error': f'Failed to create staff: {str(e)}'}), 500

    search = request.args.get('search')
    department = request.args.get('department')
    refresh = request.args.get('refresh') in ('1', 'true', 'yes')
    cache_key = f"staff_{search}_{department}"
    if not refresh:
        cached = api_cache.get(cache_key)
        if cached is not None:
            return jsonify(cached)

    staff_members = erp_get_all_staff(search=search, department=department)
    res = {'staff': staff_members}
    api_cache.set(cache_key, res, ttl=60)
    return jsonify(res)

@hod_bp.route('/api/staff/<int:staff_id>', methods=['PUT', 'PATCH', 'DELETE'])
@role_required('hod', 'admin')
def api_hod_staff_detail(staff_id):
    if request.method == 'DELETE':
        try:
            res = erp_delete_staff(staff_id, get_current_user_meta())
            api_cache.invalidate('staff')
            return jsonify({'success': True, 'data': res})
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 404
        except Exception as e:
            return jsonify({'error': f'Failed to delete faculty member: {str(e)}'}), 500

    data = request.get_json() if request.is_json else request.form.to_dict()
    try:
        res = erp_update_staff(staff_id, data, get_current_user_meta())
        api_cache.invalidate('staff')
        return jsonify({'success': True, 'data': res})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to update faculty member: {str(e)}'}), 500


# --- 3. Subject Management APIs ---
@hod_bp.route('/api/subjects', methods=['GET', 'POST'])
@role_required('hod', 'admin')
=======
# --- Staff Management Endpoints ---
@hod_bp.route('/api/staff', methods=['GET'])
@role_required('hod')
def api_hod_get_staff():
    search = request.args.get('search')
    department = request.args.get('department')
    staff_members = get_staff_detailed(search=search, department=department)
    return jsonify(staff_members)

@hod_bp.route('/api/staff', methods=['POST'])
@role_required('hod')
def api_hod_add_staff():
    data = request.get_json() if request.is_json else request.form
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        res = add_staff(data, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Faculty member added successfully!', 'staff': res}), 201
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to add staff: {str(e)}'}), 500

@hod_bp.route('/api/staff/<int:staff_id>', methods=['PUT', 'POST'])
@role_required('hod')
def api_hod_update_staff(staff_id):
    data = request.get_json() if request.is_json else request.form
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        res = update_staff(staff_id, data, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Faculty updated successfully!', 'staff': res})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to update staff: {str(e)}'}), 500

@hod_bp.route('/api/staff/<int:staff_id>', methods=['DELETE'])
@role_required('hod')
def api_hod_delete_staff(staff_id):
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        delete_staff(staff_id, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Faculty removed successfully!'})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to delete staff: {str(e)}'}), 500

# --- Subject Management Endpoints ---
@hod_bp.route('/api/subjects', methods=['GET'])
@role_required('hod')
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
def api_hod_subjects():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form.to_dict()
        try:
            res = erp_create_subject(data, get_current_user_meta())
            api_cache.invalidate('subjects')
            return jsonify({'success': True, 'data': res}), 201
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 400
        except Exception as e:
            return jsonify({'error': f'Failed to create subject: {str(e)}'}), 500

    detailed = request.args.get('detailed') in ('1', 'true', 'yes')
    search = request.args.get('search')
    department = request.args.get('department')
    semester = request.args.get('semester')
    refresh = request.args.get('refresh') in ('1', 'true', 'yes')
    cache_key = f"subjects_{detailed}_{department}_{semester}_{search}"
    if not refresh:
        cached = api_cache.get(cache_key)
        if cached is not None:
            return jsonify(cached)

    if detailed:
        subjects = erp_get_all_subjects(department=department, semester=semester, search=search)
        res = {'subjects': subjects}
        api_cache.set(cache_key, res, ttl=60)
        return jsonify(res)
    else:
        # Standard list for dropdowns
        subjects = get_all_subjects()
        api_cache.set(cache_key, subjects, ttl=60)
        return jsonify(subjects)

@hod_bp.route('/api/subject/<subject_code>', methods=['PUT', 'PATCH', 'DELETE'])
@role_required('hod', 'admin')
def api_hod_subject_detail(subject_code):
    if request.method == 'DELETE':
        try:
            res = erp_delete_subject(subject_code, get_current_user_meta())
            api_cache.invalidate('subjects')
            return jsonify({'success': True, 'data': res})
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 404
        except Exception as e:
            return jsonify({'error': f'Failed to delete subject: {str(e)}'}), 500

    data = request.get_json() if request.is_json else request.form.to_dict()
    try:
        res = erp_update_subject(subject_code, data, get_current_user_meta())
        api_cache.invalidate('subjects')
        return jsonify({'success': True, 'data': res})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to update subject: {str(e)}'}), 500


# --- 4. Attendance Management APIs ---
@hod_bp.route('/api/attendance', methods=['GET', 'POST'])
@role_required('hod', 'admin')
def api_hod_attendance():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form.to_dict()
        try:
            res = erp_add_attendance(data, get_current_user_meta())
            api_cache.invalidate('att')
            return jsonify({'success': True, 'data': res}), 201
        except Exception as e:
            return jsonify({'error': f'Failed to record attendance: {str(e)}'}), 500

    date_filter = request.args.get('date')
    subject_id = request.args.get('subject_id')
    student_id = request.args.get('student_id')
    status_filter = request.args.get('status')
    search = request.args.get('search')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 25))
    refresh = request.args.get('refresh') in ('1', 'true', 'yes')

    cache_key = f"att_{date_filter}_{subject_id}_{student_id}_{status_filter}_{search}_{page}_{per_page}"
    if not refresh:
        cached = api_cache.get(cache_key)
        if cached is not None:
            return jsonify(cached)

    res = erp_get_attendance(
        date_filter=date_filter,
        subject_id=subject_id,
        student_id=student_id,
        status_filter=status_filter,
        search=search,
        page=page,
        per_page=per_page
    )
    api_cache.set(cache_key, res, ttl=60)
    return jsonify(res)

@hod_bp.route('/api/attendance/<int:att_id>', methods=['PUT', 'PATCH', 'DELETE'])
@role_required('hod', 'admin')
def api_hod_attendance_detail(att_id):
    if request.method == 'DELETE':
        try:
            res = erp_delete_attendance(att_id, get_current_user_meta())
            api_cache.invalidate('att')
            return jsonify({'success': True, 'data': res})
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 404
        except Exception as e:
            return jsonify({'error': f'Failed to delete attendance record: {str(e)}'}), 500

    data = request.get_json() if request.is_json else request.form.to_dict()
    try:
        res = erp_update_attendance(att_id, data, get_current_user_meta())
        api_cache.invalidate('att')
        return jsonify({'success': True, 'data': res})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to update attendance record: {str(e)}'}), 500

@hod_bp.route('/api/attendance/export')
@role_required('hod', 'admin')
def api_hod_attendance_export():
    date_filter = request.args.get('date')
    subject_id = request.args.get('subject_id')
    search = request.args.get('search')

    csv_data = erp_export_attendance_csv(date_filter=date_filter, subject_id=subject_id, search=search)
    filename = f"attendance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )


# --- 5. Internal Marks Management APIs ---
@hod_bp.route('/api/marks', methods=['GET', 'POST'])
@role_required('hod', 'admin')
def api_hod_marks():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form.to_dict()
        try:
            res = erp_add_mark(data, get_current_user_meta())
            api_cache.invalidate('marks')
            return jsonify({'success': True, 'data': res}), 201
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 400
        except Exception as e:
            return jsonify({'error': f'Failed to record mark: {str(e)}'}), 500

    student_id = request.args.get('student_id')
    subject_id = request.args.get('subject_id')
    test_number = request.args.get('test_number')
    search = request.args.get('search')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 25))
    refresh = request.args.get('refresh') in ('1', 'true', 'yes')

    cache_key = f"marks_{student_id}_{subject_id}_{test_number}_{search}_{page}_{per_page}"
    if not refresh:
        cached = api_cache.get(cache_key)
        if cached is not None:
            return jsonify(cached)

    res = erp_get_marks(
        student_id=student_id,
        subject_id=subject_id,
        test_number=test_number,
        search=search,
        page=page,
        per_page=per_page
    )
    api_cache.set(cache_key, res, ttl=60)
    return jsonify(res)

@hod_bp.route('/api/marks/<int:mark_id>', methods=['PUT', 'PATCH', 'DELETE'])
@role_required('hod', 'admin')
def api_hod_mark_detail(mark_id):
    if request.method == 'DELETE':
        try:
            res = erp_delete_mark(mark_id, get_current_user_meta())
            api_cache.invalidate('marks')
            return jsonify({'success': True, 'data': res})
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 404
        except Exception as e:
            return jsonify({'error': f'Failed to delete mark: {str(e)}'}), 500

    data = request.get_json() if request.is_json else request.form.to_dict()
    try:
        res = erp_update_mark(mark_id, data, get_current_user_meta())
        api_cache.invalidate('marks')
        return jsonify({'success': True, 'data': res})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to update mark: {str(e)}'}), 500

@hod_bp.route('/api/marks/reports')
@role_required('hod', 'admin')
def api_hod_marks_reports():
    report_type = request.args.get('type', 'student')
    student_id = request.args.get('student_id')
    subject_id = request.args.get('subject_id')
    semester = request.args.get('semester')
    refresh = request.args.get('refresh') in ('1', 'true', 'yes')

    cache_key = f"mreports_{report_type}_{student_id}_{subject_id}_{semester}"
    if not refresh:
        cached = api_cache.get(cache_key)
        if cached is not None:
            return jsonify({'report': cached})

    data = erp_get_marks_reports(
        report_type=report_type,
        student_id=student_id,
        subject_id=subject_id,
        semester=semester
    )
    api_cache.set(cache_key, data, ttl=60)
    return jsonify({'report': data})


# --- 6. Timetable Management APIs ---
@hod_bp.route('/api/timetable', methods=['GET', 'POST'])
@role_required('hod', 'admin')
def api_hod_timetable():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form.to_dict()
        try:
            res = erp_add_timetable_slot(data, get_current_user_meta())
            api_cache.invalidate('tt')
            return jsonify({'success': True, 'data': res}), 201
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 400
        except Exception as e:
            return jsonify({'error': f'Failed to add timetable slot: {str(e)}'}), 500

    year = request.args.get('year', 'Third year')
    section = request.args.get('section', 'A')
    day = request.args.get('day')
    refresh = request.args.get('refresh') in ('1', 'true', 'yes')

    cache_key = f"tt_{year}_{section}_{day}"
    if not refresh:
        cached = api_cache.get(cache_key)
        if cached is not None:
            return jsonify(cached)

    data = erp_get_timetable(year=year, section=section, day=day)
    api_cache.set(cache_key, data, ttl=120)
    return jsonify(data)

@hod_bp.route('/api/timetable/<int:slot_id>', methods=['PUT', 'PATCH', 'DELETE'])
@role_required('hod', 'admin')
def api_hod_timetable_detail(slot_id):
    if request.method == 'DELETE':
        try:
            res = erp_delete_timetable_slot(slot_id, get_current_user_meta())
            api_cache.invalidate('tt')
            return jsonify({'success': True, 'data': res})
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 404
        except Exception as e:
            return jsonify({'error': f'Failed to delete timetable slot: {str(e)}'}), 500

    data = request.get_json() if request.is_json else request.form.to_dict()
    try:
        res = erp_update_timetable_slot(slot_id, data, get_current_user_meta())
        api_cache.invalidate('tt')
        return jsonify({'success': True, 'data': res})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to update timetable slot: {str(e)}'}), 500



@hod_bp.route('/api/subjects/all', methods=['GET'])
@role_required('hod')
def api_hod_subjects_all():
    search = request.args.get('search')
    semester = request.args.get('semester')
    department = request.args.get('department')
    subjects = get_subjects_detailed(search=search, semester=semester, department=department)
    return jsonify(subjects)

@hod_bp.route('/api/subjects', methods=['POST'])
@role_required('hod')
def api_hod_add_subject():
    data = request.get_json() if request.is_json else request.form
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        res = add_subject(data, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Subject created successfully!', 'subject': res}), 201
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to create subject: {str(e)}'}), 500

@hod_bp.route('/api/subjects/<subject_code>', methods=['PUT', 'POST'])
@role_required('hod')
def api_hod_update_subject(subject_code):
    data = request.get_json() if request.is_json else request.form
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        res = update_subject(subject_code, data, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Subject updated successfully!', 'subject': res})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to update subject: {str(e)}'}), 500

@hod_bp.route('/api/subjects/<subject_code>', methods=['DELETE'])
@role_required('hod')
def api_hod_delete_subject(subject_code):
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        delete_subject(subject_code, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Subject deleted successfully!'})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to delete subject: {str(e)}'}), 500

# --- Attendance Management Endpoints ---
@hod_bp.route('/api/attendance/records', methods=['GET'])
@role_required('hod')
def api_hod_attendance_records():
    date = request.args.get('date')
    student_id = request.args.get('student_id')
    subject_id = request.args.get('subject_id')
    status = request.args.get('status')
    search = request.args.get('search')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))
    result = get_attendance_records(date=date, student_id=student_id, subject_id=subject_id, status=status, search=search, page=page, limit=limit)
    return jsonify(result)

@hod_bp.route('/api/attendance', methods=['POST'])
@role_required('hod')
def api_hod_add_attendance():
    data = request.get_json() if request.is_json else request.form
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        res = add_attendance(data, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Attendance marked successfully!', 'record': res})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to mark attendance: {str(e)}'}), 500

@hod_bp.route('/api/attendance/<int:attendance_id>', methods=['PUT', 'POST'])
@role_required('hod')
def api_hod_update_attendance(attendance_id):
    data = request.get_json() if request.is_json else request.form
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        res = update_attendance(attendance_id, data, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Attendance updated successfully!', 'record': res})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to update attendance: {str(e)}'}), 500

@hod_bp.route('/api/attendance/<int:attendance_id>', methods=['DELETE'])
@role_required('hod')
def api_hod_delete_attendance(attendance_id):
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        delete_attendance(attendance_id, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Attendance entry removed!'})
    except Exception as e:
        return jsonify({'error': f'Failed to delete attendance: {str(e)}'}), 500

@hod_bp.route('/api/attendance/export', methods=['GET'])
@role_required('hod')
def api_hod_attendance_export():
    import csv
    import io
    date = request.args.get('date')
    student_id = request.args.get('student_id')
    status = request.args.get('status')
    search = request.args.get('search')
    data = get_attendance_records(date=date, student_id=student_id, status=status, search=search, page=1, limit=5000)
    records = data.get('records', [])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Record ID', 'Register Number', 'Student Name', 'Department', 'Year', 'Date', 'Status', 'Subject'])
    for r in records:
        writer.writerow([r['id'], r['regno'], r['student_name'], r['department'], r['year'], r['date'], r['status'], r.get('subject_name') or 'General'])

    output.seek(0)
    filename = f"attendance_export_{datetime.today().strftime('%Y%m%d')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

# --- Internal Marks Management Endpoints ---
@hod_bp.route('/api/marks/records', methods=['GET'])
@role_required('hod')
def api_hod_marks_records():
    student_id = request.args.get('student_id')
    subject_id = request.args.get('subject_id')
    test_number = request.args.get('test_number')
    search = request.args.get('search')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))
    result = get_marks_records(student_id=student_id, subject_id=subject_id, test_number=test_number, search=search, page=page, limit=limit)
    return jsonify(result)

@hod_bp.route('/api/marks', methods=['POST'])
@role_required('hod')
def api_hod_add_mark():
    data = request.get_json() if request.is_json else request.form
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        res = add_mark(data, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Internal mark saved successfully!', 'mark': res}), 201
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to save marks: {str(e)}'}), 500

@hod_bp.route('/api/marks/<int:mark_id>', methods=['PUT', 'POST'])
@role_required('hod')
def api_hod_update_mark(mark_id):
    data = request.get_json() if request.is_json else request.form
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        res = update_mark(mark_id, data, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Marks updated successfully!', 'mark': res})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to update marks: {str(e)}'}), 500

@hod_bp.route('/api/marks/<int:mark_id>', methods=['DELETE'])
@role_required('hod')
def api_hod_delete_mark(mark_id):
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        delete_mark(mark_id, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Internal mark record deleted!'})
    except Exception as e:
        return jsonify({'error': f'Failed to delete mark: {str(e)}'}), 500

# --- Timetable Management Endpoints ---
@hod_bp.route('/api/timetable', methods=['GET'])
@role_required('hod')
def api_hod_get_timetable():
    year = request.args.get('year', 'Third year')
    section = request.args.get('section', 'A')
    grid_data = get_timetable_grid(year=year, section=section)
    return jsonify(grid_data)

@hod_bp.route('/api/timetable', methods=['POST'])
@role_required('hod')
def api_hod_add_timetable():
    data = request.get_json() if request.is_json else request.form
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        res = add_timetable_entry(data, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Timetable entry assigned successfully!', 'entry': res})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to schedule timetable: {str(e)}'}), 500

@hod_bp.route('/api/timetable/<int:entry_id>', methods=['DELETE'])
@role_required('hod')
def api_hod_delete_timetable(entry_id):
    actor_name = session.get('display_name') or 'HOD'
    actor_id = session.get('user_id')
    try:
        delete_timetable_entry(entry_id, actor_name=actor_name, actor_id=actor_id)
        return jsonify({'success': True, 'message': 'Timetable period removed!'})
    except Exception as e:
        return jsonify({'error': f'Failed to delete timetable entry: {str(e)}'}), 500

# Gallery Management Endpoints
@hod_bp.route('/gallery/upload', methods=['POST'])
@login_required('hod')
def gallery_upload():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip() or None
    event_date = request.form.get('event_date', '').strip() or None

    if not title:
        flash("Photo title is required.", "warning")
        return redirect(url_for('hod.dashboard'))

    if 'file' not in request.files:
        flash("No file was selected for upload.", "warning")
        return redirect(url_for('hod.dashboard'))

    file = request.files['file']
    if not file or not file.filename or file.filename.strip() == '':
        flash("Please choose an image file to upload.", "warning")
        return redirect(url_for('hod.dashboard'))

    original_name = file.filename
    _, ext = os.path.splitext(original_name)
    ext = ext.lower()
    if ext not in ALLOWED_GALLERY_EXTENSIONS:
        flash(f"Invalid file extension '{ext}'. Only .jpg, .jpeg, .png, and .webp images are allowed.", "danger")
        return redirect(url_for('hod.dashboard'))

    # Cap upload size at 8MB
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 8 * 1024 * 1024:
        flash("Upload failed: File size exceeds the 8MB limit. Please upload a smaller image.", "danger")
        return redirect(url_for('hod.dashboard'))

    safe_name = secure_filename(original_name) or f"photo{ext}"
    stored_filename = f"{uuid4().hex}_{safe_name}"

    upload_dir = current_app.config.get('GALLERY_UPLOAD_DIR') or os.path.join(current_app.root_path, 'static', 'uploads', 'gallery')
    os.makedirs(upload_dir, exist_ok=True)
    stored_path = os.path.join(upload_dir, stored_filename)

    try:
        file.save(stored_path)
    except Exception as e:
        flash(f"Failed to save image to server storage: {str(e)}", "danger")
        return redirect(url_for('hod.dashboard'))

    image_path = f"uploads/gallery/{stored_filename}"
    uploaded_by = session.get('display_name') or 'HOD'

    try:
        execute("""
            INSERT INTO gallery (title, description, event_date, image_path, uploaded_by)
            VALUES (%s, %s, %s, %s, %s)
        """, (title, description, event_date, image_path, uploaded_by))
        flash("Event photo uploaded successfully to gallery!", "success")
    except Exception as e:
        if os.path.exists(stored_path):
            try:
                os.remove(stored_path)
            except Exception:
                pass
        flash(f"Database error while saving photo: {str(e)}", "danger")

    return redirect(url_for('hod.dashboard'))


@hod_bp.route('/gallery/delete/<int:photo_id>', methods=['POST'])
@login_required('hod')
def gallery_delete(photo_id):
    photo = fetch_one("SELECT * FROM gallery WHERE id = %s", (photo_id,))
    if not photo:
        flash("Photo record not found or already deleted.", "warning")
        return redirect(url_for('hod.dashboard'))

    upload_dir = current_app.config.get('GALLERY_UPLOAD_DIR') or os.path.join(current_app.root_path, 'static', 'uploads', 'gallery')
    file_path = os.path.join(upload_dir, os.path.basename(photo['image_path']))
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Warning: could not delete gallery image from disk {file_path}: {e}")

    try:
        execute("DELETE FROM gallery WHERE id = %s", (photo_id,))
        flash("Photo removed successfully from gallery.", "success")
    except Exception as e:
        flash(f"Failed to delete photo from database: {str(e)}", "danger")

    return redirect(url_for('hod.dashboard'))


# Mark Correction Request Workflow & Audit Oversight Endpoints
@hod_bp.route('/queries')
@role_required('hod')
def queries_page():
    return redirect(url_for('hod.edit_details_page'))


@hod_bp.route('/api/queries/summary')
@role_required('hod')
def api_hod_queries_summary():
    stats = get_hod_summary_stats()
    return jsonify(stats)


@hod_bp.route('/api/queries')
@role_required('hod')
def api_hod_queries():
    status_filter = request.args.get('status', 'all')
    staff_id = request.args.get('staff_id', 'all')
    subject_id = request.args.get('subject_id', 'all')
    overdue_only = request.args.get('overdue') in ('1', 'true', 'yes')
    search = request.args.get('search')

    queries = get_hod_queries(
        status_filter=status_filter,
        staff_id=staff_id,
        subject_id=subject_id,
        overdue_only=overdue_only,
        search=search
    )
    return jsonify({'queries': queries})


@hod_bp.route('/api/audit-logs')
@role_required('hod')
def api_hod_audit_logs():
    table_filter = request.args.get('table', 'all')
    search = request.args.get('search')
    limit = int(request.args.get('limit', 150))

    logs = get_all_audit_logs(limit=limit, table_filter=table_filter, search=search)
    return jsonify({'logs': logs})


@hod_bp.route('/api/query/<int:query_id>/resolve', methods=['POST'])
@role_required('hod')
def api_hod_query_resolve(query_id):
    """Allows HOD departmental oversight intervention if an escalation or override is warranted."""
    user_id = session.get('user_id')
    user_name = session.get('display_name') or 'HOD - IT Department'

    data = request.get_json() if request.is_json else request.form
    action = data.get('action')
    remarks = data.get('remarks')
    new_mark = data.get('new_mark')

    if not action or action.lower() not in ('approve', 'reject'):
        return jsonify({'error': "Action must be 'approve' or 'reject'."}), 400

    try:
        result = resolve_mark_correction_query(
            request_id=query_id,
            action_type=action,
            user_id=user_id,
            user_name=f"{user_name} (HOD Override)",
            user_role='hod',
            staff_id=None,
            remarks=remarks,
            new_mark=new_mark
        )
        return jsonify({
            'success': True,
            'result': result,
            'message': result.get('message', 'Request resolved via HOD oversight.')
        })
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to resolve request: {str(e)}'}), 500
