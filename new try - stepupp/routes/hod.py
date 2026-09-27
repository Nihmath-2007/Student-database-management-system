import os
from uuid import uuid4
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for, flash, current_app
from routes.auth import role_required, login_required
from db import fetch_all, fetch_one, execute
from services.analytics import calculate_department_analytics
from services.database_service import get_all_students, get_student_details, get_all_subjects
from services.correction_service import get_hod_queries, get_hod_summary_stats, get_all_audit_logs, resolve_mark_correction_query, get_query_details

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
