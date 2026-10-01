import os
from uuid import uuid4
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for, flash, current_app
from routes.auth import role_required, login_required
from services.database_service import get_staff_subjects, get_subject_details, get_student_details, get_all_students
from services.correction_service import get_staff_queries, update_query_status_to_review, resolve_mark_correction_query, get_query_details
from services.cache_service import api_cache
from db import fetch_all, fetch_one, execute

staff_bp = Blueprint('staff', __name__, url_prefix='/staff')

ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.ppt', '.pptx'}

@staff_bp.route('/dashboard')
@login_required('staff')
def dashboard():
    staff_id = session.get('staff_id')
    # Fetch assigned subjects for the upload dropdown
    subjects = fetch_all("SELECT * FROM subjects WHERE staff_id = %s ORDER BY subject_name ASC", (staff_id,))
    # Fetch notes previously uploaded by this staff member
    notes = fetch_all("""
        SELECT n.id, n.subject_id, n.staff_id, n.title, n.filename, n.stored_path, n.uploaded_at,
               sub.subject_name, sub.subject_code
        FROM notes n
        JOIN subjects sub ON n.subject_id = sub.subjectid
        WHERE n.staff_id = %s
        ORDER BY n.uploaded_at DESC
    """, (staff_id,))
    return render_template('staff/dashboard.html', subjects=subjects, notes=notes)

@staff_bp.route('/notes/upload', methods=['POST'])
@login_required('staff')
def upload_note():
    staff_id = session.get('staff_id')
    if not staff_id:
        flash("Unauthorized: Staff session not found.", "danger")
        return redirect(url_for('staff.dashboard'))

    subject_id = request.form.get('subject_id')
    title = request.form.get('title', '').strip()

    if not subject_id or not title:
        flash("Please provide a note title and select an assigned subject.", "warning")
        return redirect(url_for('staff.dashboard'))

    # Verify subject belongs to this staff member
    subject = fetch_one("SELECT * FROM subjects WHERE subjectid = %s AND staff_id = %s", (subject_id, staff_id))
    if not subject:
        flash("Unauthorized subject selection: This subject is not assigned to you.", "danger")
        return redirect(url_for('staff.dashboard'))

    if 'file' not in request.files:
        flash("No file was selected for upload.", "warning")
        return redirect(url_for('staff.dashboard'))

    file = request.files['file']
    if not file or not file.filename or file.filename.strip() == '':
        flash("Please choose a file to upload.", "warning")
        return redirect(url_for('staff.dashboard'))

    original_name = file.filename
    _, ext = os.path.splitext(original_name)
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        flash(f"Invalid file extension '{ext}'. Only .pdf, .doc, .docx, .ppt, and .pptx are allowed.", "danger")
        return redirect(url_for('staff.dashboard'))

    # Store with uuid and secure_filename to avoid collision and traversal
    safe_name = secure_filename(original_name) or f"note{ext}"
    stored_filename = f"{uuid4().hex}_{safe_name}"

    upload_dir = current_app.config.get('NOTES_UPLOAD_DIR') or os.path.join(current_app.root_path, 'uploads', 'notes')
    os.makedirs(upload_dir, exist_ok=True)
    stored_path = os.path.join(upload_dir, stored_filename)

    try:
        file.save(stored_path)
    except Exception as e:
        flash(f"Failed to save file to server: {str(e)}", "danger")
        return redirect(url_for('staff.dashboard'))

    try:
        execute("""
            INSERT INTO notes (subject_id, staff_id, title, filename, stored_path)
            VALUES (%s, %s, %s, %s, %s)
        """, (subject_id, staff_id, title, original_name, stored_filename))
        flash("Subject note uploaded successfully!", "success")
    except Exception as e:
        if os.path.exists(stored_path):
            try:
                os.remove(stored_path)
            except Exception:
                pass
        flash(f"Database error while saving note: {str(e)}", "danger")

    return redirect(url_for('staff.dashboard'))

@staff_bp.route('/notes/delete/<int:note_id>', methods=['POST'])
@login_required('staff')
def delete_note(note_id):
    staff_id = session.get('staff_id')
    if not staff_id:
        flash("Unauthorized: Staff session not found.", "danger")
        return redirect(url_for('staff.dashboard'))

    # Ensure only rows where staff_id matches the logged-in staff can be deleted
    note = fetch_one("SELECT * FROM notes WHERE id = %s AND staff_id = %s", (note_id, staff_id))
    if not note:
        flash("Subject note not found or you do not have permission to delete it.", "danger")
        return redirect(url_for('staff.dashboard'))

    # Remove the file from disk
    upload_dir = current_app.config.get('NOTES_UPLOAD_DIR') or os.path.join(current_app.root_path, 'uploads', 'notes')
    file_path = os.path.join(upload_dir, os.path.basename(note['stored_path']))
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Warning: could not delete file from disk {file_path}: {e}")

    # Remove record from database
    try:
        execute("DELETE FROM notes WHERE id = %s AND staff_id = %s", (note_id, staff_id))
        flash("Subject note deleted successfully.", "success")
    except Exception as e:
        flash(f"Database error while deleting note: {str(e)}", "danger")

    return redirect(url_for('staff.dashboard'))


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
    refresh = request.args.get('refresh') in ('1', 'true', 'yes')
    cache_key = f"staff_dash_{staff_id}"
    if not refresh:
        cached = api_cache.get(cache_key)
        if cached is not None:
            return jsonify(cached)

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

    result = {
        'assigned_subjects_count': len(assigned_subjects),
        'total_students': total_students,
        'average_marks': avg_marks,
        'average_attendance': avg_att,
        'pass_percentage': avg_pass,
        'fail_percentage': avg_fail,
        'subjects': assigned_subjects,
        'subject_analytics': subject_analytics_list
    }
    api_cache.set(cache_key, result, ttl=30)
    return jsonify(result)

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

    # Fast direct SQL filtering in a single query
    staff_students = get_all_students(subject_ids=assigned_sub_ids)
    return jsonify(staff_students)

@staff_bp.route('/api/student/<int:student_id>')
@role_required('staff')
def api_staff_student_detail(student_id):
    data = get_student_details(student_id)
    if not data:
        return jsonify({'error': 'Student not found.'}), 404
    return jsonify(data)


# Mark Correction Request Workflow Endpoints
@staff_bp.route('/queries')
@role_required('staff')
def queries_page():
    return render_template('staff/queries.html')


@staff_bp.route('/api/queries')
@role_required('staff')
def api_staff_queries():
    staff_id = session.get('staff_id')
    if not staff_id:
        return jsonify({'error': 'Staff session not found.'}), 400

    status_filter = request.args.get('status', 'all')
    cache_key = f"staff_queries_{staff_id}_{status_filter}"
    cached = api_cache.get(cache_key)
    if cached is not None:
        return jsonify(cached)

    # Fetch once, compute stats and filter in memory to eliminate duplicate network query
    all_queries = get_staff_queries(staff_id, status_filter='all')
    if status_filter == 'all':
        queries = all_queries
    elif status_filter == 'pending':
        queries = [q for q in all_queries if q['status'] in ('Raised', 'Under Review')]
    elif status_filter == 'overdue':
        queries = [q for q in all_queries if q.get('is_overdue')]
    else:
        queries = [q for q in all_queries if q['status'] == status_filter]

    pending_count = sum(1 for q in all_queries if q['status'] in ('Raised', 'Under Review'))
    overdue_count = sum(1 for q in all_queries if q.get('is_overdue'))
    approved_count = sum(1 for q in all_queries if q['status'] == 'Approved')
    rejected_count = sum(1 for q in all_queries if q['status'] == 'Rejected')

    res = {
        'queries': queries,
        'stats': {
            'total': len(all_queries),
            'pending': pending_count,
            'overdue': overdue_count,
            'approved': approved_count,
            'rejected': rejected_count
        }
    }
    api_cache.set(cache_key, res, ttl=20)
    return jsonify(res)


@staff_bp.route('/api/query/<int:query_id>/review', methods=['POST'])
@role_required('staff')
def api_staff_query_review(query_id):
    staff_id = session.get('staff_id')
    user_id = session.get('user_id')
    user_name = session.get('display_name') or session.get('username')

    try:
        update_query_status_to_review(
            request_id=query_id,
            user_id=user_id,
            user_name=user_name,
            user_role='staff',
            staff_id=staff_id
        )
        api_cache.invalidate('staff_queries')
        api_cache.invalidate('hod_queries')
        return jsonify({
            'success': True,
            'message': f'Request #{query_id} is now Under Review. Answer script verification initiated.'
        })
    except (ValueError, PermissionError) as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to update review status: {str(e)}'}), 500


@staff_bp.route('/api/query/<int:query_id>/resolve', methods=['POST'])
@role_required('staff')
def api_staff_query_resolve(query_id):
    staff_id = session.get('staff_id')
    user_id = session.get('user_id')
    user_name = session.get('display_name') or session.get('username')

    data = request.get_json() if request.is_json else request.form
    action = data.get('action')  # 'approve' or 'reject'
    remarks = data.get('remarks')
    new_mark = data.get('new_mark')

    if not action or action.lower() not in ('approve', 'reject'):
        return jsonify({'error': "Action must be 'approve' or 'reject'."}), 400

    try:
        result = resolve_mark_correction_query(
            request_id=query_id,
            action_type=action,
            user_id=user_id,
            user_name=user_name,
            user_role='staff',
            staff_id=staff_id,
            remarks=remarks,
            new_mark=new_mark
        )
        api_cache.invalidate('staff_queries')
        api_cache.invalidate('hod_queries')
        api_cache.invalidate('marks')
        api_cache.invalidate('all_stud')
        api_cache.invalidate('student_details')
        api_cache.invalidate('subject_details')
        invalidate_analytics_cache()
        return jsonify({
            'success': True,
            'result': result,
            'message': result.get('message', 'Request resolved successfully.')
        })
    except (ValueError, PermissionError) as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to resolve request: {str(e)}'}), 500

