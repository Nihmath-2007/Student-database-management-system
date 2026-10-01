import os
from uuid import uuid4
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for, flash, current_app, Response
from routes.auth import role_required, login_required
from db import fetch_all, fetch_one, execute
from services.analytics import calculate_department_analytics
from services.database_service import get_all_students, get_student_details, get_all_subjects
from services.correction_service import get_hod_queries, get_hod_summary_stats, get_all_audit_logs, resolve_mark_correction_query, get_query_details
from services.erp_service import (
    get_students_paginated, add_student, update_student, delete_student,
    get_staff_detailed, add_staff, update_staff, delete_staff,
    get_subjects_detailed, add_subject, update_subject, delete_subject,
    get_attendance_records, add_attendance, update_attendance, delete_attendance,
    get_marks_records, add_mark, update_mark, delete_mark,
    get_timetable_grid, add_timetable_entry, delete_timetable_entry
)

hod_bp = Blueprint('hod', __name__, url_prefix='/hod')

ALLOWED_GALLERY_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}

@hod_bp.route('/dashboard')
@role_required('hod')
def dashboard():
    gallery_items = fetch_all("SELECT * FROM gallery ORDER BY uploaded_at DESC")
    return render_template('hod/dashboard.html', gallery_items=gallery_items)

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
    year = request.args.get('year')
    subject = request.args.get('subject')

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

@hod_bp.route('/api/student/<int:student_id>')
@role_required('hod')
def api_hod_student_detail(student_id):
    data = get_student_details(student_id)
    if not data:
        return jsonify({'error': 'Student not found.'}), 404
    return jsonify(data)

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
def api_hod_subjects():
    subjects = get_all_subjects()
    return jsonify(subjects)

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
    return render_template('hod/queries.html')


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
