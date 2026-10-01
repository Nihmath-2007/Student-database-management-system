from flask import Blueprint, render_template, jsonify, session, request
from routes.auth import role_required, login_required
from services.database_service import get_student_details
from services.correction_service import get_student_marks_with_query_status, get_student_queries, raise_mark_correction_query
from services.cache_service import api_cache
from db import fetch_all

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/dashboard')
@role_required('student')
def dashboard():
    # Fetch all notes grouped by subject with caching
    notes = api_cache.get('all_notes')
    if notes is None:
        notes = fetch_all("""
            SELECT n.id, n.subject_id, n.title, n.filename, n.uploaded_at,
                   sub.subject_name, sub.subject_code,
                   COALESCE(st.name, 'Faculty') as staff_name
            FROM notes n
            JOIN subjects sub ON n.subject_id = sub.subjectid
            LEFT JOIN staff st ON n.staff_id = st.staffid
            ORDER BY sub.subject_name ASC, n.uploaded_at DESC
        """) or []
        api_cache.set('all_notes', notes, ttl=60)

    grouped_notes = {}
    for note in (notes or []):
        s_name = note['subject_name']
        if s_name not in grouped_notes:
            grouped_notes[s_name] = []
        grouped_notes[s_name].append(note)

    return render_template('student/dashboard.html', notes=notes, grouped_notes=grouped_notes)


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


@student_bp.route('/queries')
@role_required('student')
def queries_page():
    return render_template('student/queries.html')


@student_bp.route('/api/marks-with-queries')
@role_required('student')
def api_student_marks_with_queries():
    student_id = session.get('student_id')
    if not student_id:
        return jsonify({'error': 'Student session not found.'}), 400
    cache_key = f"stud_mq_{student_id}"
    cached = api_cache.get(cache_key)
    if cached is not None:
        return jsonify({'marks': cached})
    marks = get_student_marks_with_query_status(student_id)
    api_cache.set(cache_key, marks, ttl=30)
    return jsonify({'marks': marks})


@student_bp.route('/api/queries')
@role_required('student')
def api_student_queries():
    student_id = session.get('student_id')
    if not student_id:
        return jsonify({'error': 'Student session not found.'}), 400
    cache_key = f"stud_queries_{student_id}"
    cached = api_cache.get(cache_key)
    if cached is not None:
        return jsonify({'queries': cached})
    queries = get_student_queries(student_id)
    api_cache.set(cache_key, queries, ttl=30)
    return jsonify({'queries': queries})


@student_bp.route('/api/queries/raise', methods=['POST'])
@role_required('student')
def api_student_raise_query():
    student_id = session.get('student_id')
    user_id = session.get('user_id')
    user_name = session.get('display_name') or session.get('username')

    if not student_id:
        return jsonify({'error': 'Unauthorized. Student session not found.'}), 401

    data = request.get_json() if request.is_json else request.form
    mark_id = data.get('mark_id')
    reason = data.get('reason')
    student_note = data.get('student_note')
    expected_mark = data.get('expected_mark')

    if not mark_id:
        return jsonify({'error': 'Mark ID is required.'}), 400

    try:
        from services.correction_service import raise_mark_correction_query
        query_id = raise_mark_correction_query(
            student_id=student_id,
            mark_id=int(mark_id),
            reason=reason,
            student_note=student_note,
            expected_mark=expected_mark,
            user_id=user_id,
            user_name=user_name
        )
        api_cache.delete(f"stud_mq_{student_id}")
        api_cache.delete(f"stud_queries_{student_id}")
        api_cache.invalidate('staff_queries')
        api_cache.invalidate('hod_queries')
        return jsonify({
            'success': True,
            'message': 'Mark correction query submitted successfully. Assigned faculty will review.',
            'query_id': query_id
        })
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to submit query: {str(e)}'}), 500
