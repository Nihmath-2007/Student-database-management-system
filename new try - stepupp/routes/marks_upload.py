import os
import re
from uuid import uuid4
from werkzeug.utils import secure_filename
from flask import (
    Blueprint, render_template, request, jsonify, session,
    redirect, url_for, flash, current_app, send_file
)
from routes.auth import login_required
from config.database import get_db_connection, fetch_all, fetch_one
from services.marks_extractor import extract_marks_from_file
from services.marks_matcher import match_extracted_rows_to_students
from services.marks_excel_service import update_marks_data_file, get_marks_data_filepaths
from services.cache_service import api_cache

marks_bp = Blueprint('marks_upload', __name__, url_prefix='/marks')

ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit


def _get_upload_dir():
    """Returns absolute path to safe uploads directory."""
    upload_dir = os.path.join(current_app.root_path, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def _validate_file_content(file_bytes, ext):
    """
    Validates file headers/magic bytes to prevent disguised or corrupt uploads.
    """
    if len(file_bytes) > MAX_FILE_SIZE:
        return False, "File size exceeds the 10 MB limit."

    if ext == '.pdf':
        if not file_bytes.startswith(b'%PDF'):
            return False, "Invalid PDF file content."
    elif ext in ('.jpg', '.jpeg'):
        if not (file_bytes.startswith(b'\xff\xd8\xff') or b'JFIF' in file_bytes[:32] or b'Exif' in file_bytes[:32]):
            return False, "Invalid JPEG image content."
    elif ext == '.png':
        if not file_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            return False, "Invalid PNG image content."

    return True, None


@marks_bp.route('/upload', methods=['GET'])
@login_required('staff', 'hod')
def upload_page():
    """
    Renders the marks upload form.
    Only Staff and HOD/Admin can access this page. Students receive 403 Forbidden.
    Dropdown populates:
    - For Staff: their assigned subjects
    - For HOD/Admin: all subjects
    """
    role = session.get('role')
    staff_id = session.get('staff_id')

    if role == 'staff' and staff_id:
        subjects = fetch_all(
            "SELECT * FROM subjects WHERE staff_id = %s ORDER BY semester ASC, subject_name ASC",
            (staff_id,)
        ) or []
    else:
        # HOD or Admin: full departmental subjects
        subjects = fetch_all(
            "SELECT sub.*, st.name as staff_name FROM subjects sub LEFT JOIN staff st ON sub.staff_id = st.staffid ORDER BY sub.semester ASC, sub.subject_name ASC"
        ) or []

    # Fetch recent upload history from upload_log
    recent_uploads = fetch_all("""
        SELECT ul.id, ul.uploaded_by, ul.subject_id, ul.test_number,
               ul.filename, ul.rows_saved, ul.uploaded_at,
               sub.subject_name, sub.subject_code
        FROM upload_log ul
        LEFT JOIN subjects sub ON ul.subject_id = sub.subjectid
        ORDER BY ul.uploaded_at DESC
        LIMIT 10
    """) or []

    from services.marks_extractor import _find_tesseract_cmd
    tesseract_ready = bool(_find_tesseract_cmd())
    vision_ready = bool(os.getenv('GEMINI_API_KEY') or os.getenv('VISION_API_KEY'))

    return render_template(
        'marks/upload.html',
        subjects=subjects,
        recent_uploads=recent_uploads,
        tesseract_ready=tesseract_ready,
        vision_ready=vision_ready
    )
 


@marks_bp.route('/extract', methods=['POST'])
@login_required('staff', 'hod')
def extract_marks():
    """
    Handles uploaded marks sheet file:
    1. Validates subject, test number, max marks, and file.
    2. Enforces 10 MB limit and verifies server-side file type and content.
    3. Saves original file safely in /uploads with UUID-based unique filename.
    4. Runs extraction (pdfplumber table extraction or OCR with OpenCV pre-processing).
    5. Matches extracted identifiers/names to database students in the subject's semester.
    6. Renders the interactive Review Screen.
    """
    role = session.get('role')
    staff_id = session.get('staff_id')

    subject_id = request.form.get('subject_id')
    test_number = request.form.get('test_number')
    max_marks = request.form.get('max_marks', '100')

    # Basic validations
    if not subject_id or not test_number:
        flash("Please select a Subject and specify the Test Number.", "danger")
        return redirect(url_for('marks_upload.upload_page'))

    try:
        subject_id = int(subject_id)
        test_number = int(test_number)
        max_marks = float(max_marks)
        if max_marks <= 0:
            raise ValueError
    except ValueError:
        flash("Invalid test number or max marks value. Max marks must be a positive number.", "danger")
        return redirect(url_for('marks_upload.upload_page'))

    # Security check: if staff, verify subject is assigned to them
    if role == 'staff' and staff_id:
        assigned = fetch_one("SELECT * FROM subjects WHERE subjectid = %s AND staff_id = %s", (subject_id, staff_id))
        if not assigned:
            flash("Unauthorized: You can only upload marks for subjects assigned to you.", "danger")
            return redirect(url_for('marks_upload.upload_page'))

    # Check file in request
    if 'file' not in request.files:
        flash("No file was selected for upload.", "warning")
        return redirect(url_for('marks_upload.upload_page'))

    file = request.files['file']
    if not file or not file.filename or file.filename.strip() == '':
        flash("Please choose a valid file to upload.", "warning")
        return redirect(url_for('marks_upload.upload_page'))

    original_filename = file.filename
    _, ext = os.path.splitext(original_filename)
    ext = ext.lower()

    if ext not in ALLOWED_EXTENSIONS:
        flash(f"Invalid file type '{ext}'. Only JPG, JPEG, PNG, and PDF files are allowed.", "danger")
        return redirect(url_for('marks_upload.upload_page'))

    # Read bytes and validate file size & magic bytes
    file_bytes = file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        flash("Upload failed: File size exceeds the maximum limit of 10 MB.", "danger")
        return redirect(url_for('marks_upload.upload_page'))

    is_valid, err_msg = _validate_file_content(file_bytes, ext)
    if not is_valid:
        flash(f"Security verification failed: {err_msg}", "danger")
        return redirect(url_for('marks_upload.upload_page'))

    # Save original upload in /uploads with safe unique filename
    safe_base = secure_filename(original_filename) or f"marks_upload{ext}"
    unique_filename = f"{uuid4().hex}_{safe_base}"
    upload_dir = _get_upload_dir()
    stored_path = os.path.join(upload_dir, unique_filename)

    with open(stored_path, 'wb') as f:
        f.write(file_bytes)

    # Run modular extraction
    try:
        raw_records = extract_marks_from_file(stored_path, unique_filename)
    except Exception as e:
        flash(f"Extraction error: {str(e)}", "danger")
        return redirect(url_for('marks_upload.upload_page'))

    if not raw_records:
        flash(
            "Could not detect any student mark rows from the uploaded file. "
            "Please ensure the file contains legible text or tables and try again.",
            "warning"
        )
        return redirect(url_for('marks_upload.upload_page'))

    # Run database matching against eligible students in this subject's semester
    matched_data = match_extracted_rows_to_students(raw_records, subject_id, threshold=90.0)
    matched_rows = matched_data['results']
    eligible_students = matched_data['eligible_students']

    # Fetch subject details for display
    subject = fetch_one("SELECT * FROM subjects WHERE subjectid = %s", (subject_id,))

    # Match summary statistics
    matched_count = sum(1 for r in matched_rows if r['status'] == 'Matched')
    review_count = sum(1 for r in matched_rows if r['status'] == 'Needs Review')
    not_found_count = sum(1 for r in matched_rows if r['status'] == 'Not Found')

    return render_template(
        'marks/review.html',
        subject=subject,
        subject_id=subject_id,
        test_number=test_number,
        max_marks=max_marks,
        stored_filename=unique_filename,
        original_filename=original_filename,
        rows=matched_rows,
        eligible_students=eligible_students,
        matched_count=matched_count,
        review_count=review_count,
        not_found_count=not_found_count
    )


@marks_bp.route('/save', methods=['POST'])
@login_required('staff', 'hod')
def save_marks():
    """
    Saves confirmed marks to the database and updates data file:
    1. Validates all rows: marks must be numeric and within [0, Max Marks], or marked Absent.
    2. Rejects invalid marks and shows clear error.
    3. Performs INSERT ... ON DUPLICATE KEY UPDATE in internal_marks inside ONE transaction.
    4. Logs the upload event into upload_log table inside the same transaction.
    5. Rolls back everything if any row fails.
    6. Updates marks_data.xlsx without duplicates.
    7. Clears relevant caches.
    """
    data = request.get_json() if request.is_json else request.form

    try:
        subject_id = int(data.get('subject_id'))
        test_number = int(data.get('test_number'))
        max_marks = float(data.get('max_marks'))
        filename = str(data.get('filename', 'manual_upload'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Invalid subject, test number or max marks parameters.'}), 400

    # Parse rows list
    import json
    rows = data.get('rows')
    if isinstance(rows, str):
        try:
            rows = json.loads(rows)
        except Exception:
            return jsonify({'success': False, 'error': 'Invalid rows payload format.'}), 400

    if not rows or not isinstance(rows, list):
        return jsonify({'success': False, 'error': 'No mark rows were submitted for saving.'}), 400

    # Server-side validation of every row
    validated_rows = []
    excel_records = []

    subject = fetch_one("SELECT * FROM subjects WHERE subjectid = %s", (subject_id,))
    subject_name = subject['subject_name'] if subject else f"Subject {subject_id}"

    # Pre-fetch eligible student names & regnos for validation
    eligible_students = fetch_all("SELECT studentid, regno, name FROM students")
    student_map = {s['studentid']: s for s in eligible_students}

    for idx, r in enumerate(rows):
        student_id_val = r.get('student_id')
        if not student_id_val:
            return jsonify({
                'success': False,
                'error': f"Row {idx + 1}: No student selected. Please map or remove unmatched rows before saving."
            }), 400

        try:
            student_id = int(student_id_val)
        except ValueError:
            return jsonify({'success': False, 'error': f"Row {idx + 1}: Invalid student ID."}), 400

        if student_id not in student_map:
            return jsonify({'success': False, 'error': f"Row {idx + 1}: Student with ID {student_id} not found."}), 400

        student_info = student_map[student_id]
        mark_input = str(r.get('mark', '')).strip()
        is_absent = r.get('is_absent', False) or mark_input.upper() in ('AB', 'A', '-', 'ABSENT', 'ABS', 'NULL', 'NONE', '')

        marks_obtained = None
        if not is_absent:
            # Must be a valid non-negative number <= max_marks
            try:
                marks_obtained = float(mark_input)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f"Row {idx + 1} ({student_info['name']}): Mark '{mark_input}' is not a valid number."
                }), 400

            if marks_obtained < 0:
                return jsonify({
                    'success': False,
                    'error': f"Row {idx + 1} ({student_info['name']}): Mark cannot be negative ({marks_obtained})."
                }), 400

            if marks_obtained > max_marks:
                return jsonify({
                    'success': False,
                    'error': f"Row {idx + 1} ({student_info['name']}): Mark {marks_obtained} exceeds Max Marks ({max_marks})."
                }), 400

        validated_rows.append({
            'student_id': student_id,
            'marks_obtained': marks_obtained,
            'is_absent': is_absent
        })

        excel_records.append({
            'regno': student_info['regno'],
            'student_name': student_info['name'],
            'subject_name': subject_name,
            'test_number': test_number,
            'marks_obtained': marks_obtained,
            'max_marks': max_marks,
            'is_absent': is_absent
        })

    # =========================================================================
    # TRANSACTIONAL DATABASE WRITE
    # =========================================================================
    conn, db_type = get_db_connection()
    cursor = None
    rows_saved = 0
    uploaded_by = session.get('display_name') or session.get('username') or str(session.get('user_id') or 'Staff')

    try:
        # Disable autocommit to ensure atomic transaction
        if hasattr(conn, 'autocommit'):
            conn.autocommit = False
        elif hasattr(conn, '_raw_conn') and hasattr(conn._raw_conn, 'autocommit'):
            conn._raw_conn.autocommit = False

        cursor = conn.cursor()

        if db_type == 'mysql':
            upsert_query = """
            INSERT INTO internal_marks (student_id, subject_id, test_number, marks_obtained, max_marks)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                marks_obtained = VALUES(marks_obtained),
                max_marks = VALUES(max_marks)
            """
        else:
            # SQLite fallback syntax
            upsert_query = """
            INSERT INTO internal_marks (student_id, subject_id, test_number, marks_obtained, max_marks)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(student_id, subject_id, test_number) DO UPDATE SET
                marks_obtained = excluded.marks_obtained,
                max_marks = excluded.max_marks
            """

        for vr in validated_rows:
            cursor.execute(
                upsert_query,
                (vr['student_id'], subject_id, test_number, vr['marks_obtained'], max_marks)
            )
            rows_saved += 1

        # Record upload in upload_log table within the same transaction
        if db_type == 'mysql':
            log_query = """
            INSERT INTO upload_log (uploaded_by, subject_id, test_number, filename, rows_saved, uploaded_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """
        else:
            log_query = """
            INSERT INTO upload_log (uploaded_by, subject_id, test_number, filename, rows_saved, uploaded_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """

        cursor.execute(log_query, (uploaded_by, subject_id, test_number, filename, rows_saved))

        # Commit everything as a single transaction
        conn.commit()

    except Exception as db_err:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"Error saving marks inside transaction: {db_err}")
        return jsonify({
            'success': False,
            'error': f"Database transaction failed and was rolled back: {str(db_err)}"
        }), 500

    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass

    # =========================================================================
    # UPDATE DATA FILE (marks_data.xlsx) WITHOUT DUPLICATES
    # =========================================================================
    try:
        update_marks_data_file(excel_records)
    except Exception as xl_err:
        print(f"Notice: Failed to update marks_data.xlsx: {xl_err}")

    # =========================================================================
    # CACHE INVALIDATION
    # =========================================================================
    try:
        api_cache.delete(f"subject_details_{subject_id}")
        api_cache.delete("student_att_map")
        for vr in validated_rows:
            api_cache.delete(f"student_details_{vr['student_id']}")
    except Exception:
        pass

    success_msg = f"Successfully confirmed and saved {rows_saved} student marks for Test {test_number}!"
    flash(success_msg, "success")

    return jsonify({
        'success': True,
        'rows_saved': rows_saved,
        'message': success_msg,
        'redirect_url': url_for('marks_upload.upload_page')
    })


@marks_bp.route('/download-data-file')
@login_required('staff', 'hod')
def download_data_file():
    """
    Allows Staff and HOD to download the synchronized marks_data.xlsx file.
    """
    primary_path, _ = get_marks_data_filepaths()
    if not os.path.isfile(primary_path):
        from services.marks_excel_service import regenerate_full_marks_data_file
        regenerate_full_marks_data_file()

    return send_file(
        primary_path,
        as_attachment=True,
        download_name='marks_data.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
