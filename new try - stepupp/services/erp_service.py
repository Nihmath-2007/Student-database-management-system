"""
ERP Service for College Management System
Provides production-grade CRUD, audit logging, filtering, and reporting
for Students, Staff, Subjects, Attendance, Internal Marks, and Timetable.
"""
import io
import csv
import json
from datetime import datetime, date
from werkzeug.security import generate_password_hash
from db import fetch_all, fetch_one, execute

def log_erp_audit(table_name, record_id, action, field_name=None, old_val=None, new_val=None, user_meta=None, notes=None):
    """Logs action into audit_log table for accountability."""
    try:
        user_meta = user_meta or {}
        user_id = user_meta.get('user_id')
        user_name = user_meta.get('user_name', 'HOD - IT Department')
        user_role = user_meta.get('user_role', 'hod')

        old_str = json.dumps(old_val, default=str) if isinstance(old_val, (dict, list)) else (str(old_val) if old_val is not None else None)
        new_str = json.dumps(new_val, default=str) if isinstance(new_val, (dict, list)) else (str(new_val) if new_val is not None else None)

        execute("""
            INSERT INTO audit_log (table_name, record_id, action, field_name, old_value, new_value, changed_by_user_id, changed_by_name, changed_by_role, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (table_name, int(record_id or 0), action, field_name, old_str, new_str, user_id, user_name, user_role, notes))
    except Exception as e:
        print(f"Warning: Failed to log audit record: {e}")


# =========================================================================
# 1. STUDENT MANAGEMENT MODULE (Full CRUD)
# =========================================================================

def erp_get_students(search=None, department=None, year=None, status=None, page=1, per_page=20):
    """
    Fetches students with KPI aggregations, filtering, search, and pagination.
    """
    query = """
    SELECT 
        s.studentid, s.regno, s.name, s.department, s.year, s.section, s.email, s.phone,
        COALESCE(att.att_pct, 0.0) as attendance_percentage,
        COALESCE(att.total_days, 0) as total_days,
        COALESCE(att.present_days, 0) as present_days,
        COALESCE(marks.avg_marks, 0.0) as avg_marks,
        COALESCE(marks.passed_count, 0) as passed_subjects,
        COALESCE(marks.failed_count, 0) as failed_subjects
    FROM students s
    LEFT JOIN (
        SELECT 
            student_id,
            COUNT(*) as total_days,
            SUM(CASE WHEN LOWER(status) = 'present' THEN 1 ELSE 0 END) as present_days,
            ROUND((SUM(CASE WHEN LOWER(status) = 'present' THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(*), 0)) * 100.0, 1) as att_pct
        FROM attendance
        GROUP BY student_id
    ) att ON s.studentid = att.student_id
    LEFT JOIN (
        SELECT 
            student_id,
            ROUND(AVG(marks_obtained), 1) as avg_marks,
            SUM(CASE WHEN (marks_obtained / NULLIF(max_marks, 0)) * 100 >= 50 THEN 1 ELSE 0 END) as passed_count,
            SUM(CASE WHEN (marks_obtained / NULLIF(max_marks, 0)) * 100 < 50 THEN 1 ELSE 0 END) as failed_count
        FROM internal_marks
        GROUP BY student_id
    ) marks ON s.studentid = marks.student_id
    WHERE 1=1
    """
    params = []

    if search:
        s_term = f"%{search.strip()}%"
        query += " AND (s.name LIKE %s OR s.regno LIKE %s OR s.email LIKE %s)"
        params.extend([s_term, s_term, s_term])

    if department and department != 'All':
        query += " AND s.department = %s"
        params.append(department)

    if year and year != 'All':
        query += " AND s.year = %s"
        params.append(year)

    # Order
    query += " ORDER BY s.regno ASC"

    all_rows = fetch_all(query, tuple(params)) or []

    # Tag status
    processed = []
    for s in all_rows:
        att = float(s['attendance_percentage'] or 0.0)
        avg = float(s['avg_marks'] or 0.0)
        if att < 75.0 or avg < 50.0:
            s['status'] = 'At Risk'
            s['at_risk'] = True
        else:
            s['status'] = 'Normal'
            s['at_risk'] = False

        if status == 'At Risk' and not s['at_risk']:
            continue
        if status == 'Normal' and s['at_risk']:
            continue

        processed.append(s)

    total_records = len(processed)
    
    # In-memory sorting for rank if requested
    if status == 'Top Rank':
        processed.sort(key=lambda x: float(x.get('avg_marks') or 0), reverse=True)
    elif status == 'Bottom Rank':
        processed.sort(key=lambda x: float(x.get('avg_marks') or 0))

    # Pagination
    if per_page and per_page > 0:
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_students = processed[start_idx:end_idx]
    else:
        paginated_students = processed

    total_pages = (total_records + per_page - 1) // per_page if per_page else 1

    return {
        'students': paginated_students,
        'total': total_records,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages
    }

def erp_get_student_by_id(student_id):
    """Fetches full profile, attendance, and internal marks for a single student."""
    stu = fetch_one("SELECT * FROM students WHERE studentid = %s", (student_id,))
    if not stu:
        return None

    # Attendance summary
    att_summary = fetch_one("""
        SELECT 
            COUNT(*) as total_days,
            SUM(CASE WHEN LOWER(status) = 'present' THEN 1 ELSE 0 END) as present_days,
            ROUND((SUM(CASE WHEN LOWER(status) = 'present' THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(*), 0)) * 100.0, 1) as att_pct
        FROM attendance
        WHERE student_id = %s
    """, (student_id,)) or {'total_days': 0, 'present_days': 0, 'att_pct': 0.0}

    # Subject-wise marks
    marks = fetch_all("""
        SELECT m.id, m.test_number, m.marks_obtained, m.max_marks,
               sub.subject_code, sub.subject_name, sub.semester,
               ROUND((m.marks_obtained / NULLIF(m.max_marks, 0)) * 100, 1) as percentage
        FROM internal_marks m
        JOIN subjects sub ON m.subject_id = sub.subjectid
        WHERE m.student_id = %s
        ORDER BY sub.subject_code, m.test_number
    """, (student_id,)) or []

    return {
        'profile': stu,
        'attendance': att_summary,
        'marks': marks
    }

def erp_create_student(data, user_meta=None):
    """
    Creates a new student, generates user login account, and logs audit record.
    """
    regno = str(data.get('regno', '')).strip()
    name = str(data.get('name', '')).strip()
    department = str(data.get('department', 'Information Technology')).strip()
    year = str(data.get('year', 'Third year')).strip()
    section = str(data.get('section', 'A')).strip()
    email = str(data.get('email', '')).strip()
    phone = str(data.get('phone', '')).strip() or None

    if not regno or not name:
        raise ValueError("Register Number and Full Name are mandatory fields.")

    # Check unique regno
    existing = fetch_one("SELECT studentid FROM students WHERE regno = %s", (regno,))
    if existing:
        raise ValueError(f"Student with Register Number '{regno}' already exists.")

    # Determine next studentid
    max_id_row = fetch_one("SELECT MAX(studentid) as m FROM students")
    next_id = (max_id_row['m'] or 0) + 1 if max_id_row else 1

    execute("""
        INSERT INTO students (studentid, regno, name, department, year, section, email, phone)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (next_id, regno, name, department, year, section, email, phone))

    # Create student portal login account (Default password = student123)
    try:
        user_exists = fetch_one("SELECT id FROM users WHERE username = %s", (regno,))
        if not user_exists:
            pwd_hash = generate_password_hash('student123')
            execute("""
                INSERT INTO users (username, password_hash, role, student_id)
                VALUES (%s, %s, 'student', %s)
            """, (regno, pwd_hash, next_id))
    except Exception as ue:
        print(f"Notice: User account creation warning: {ue}")

    log_erp_audit(
        table_name='students',
        record_id=next_id,
        action='INSERT',
        field_name='all',
        new_val={'regno': regno, 'name': name, 'department': department, 'year': year, 'section': section, 'email': email, 'phone': phone},
        user_meta=user_meta,
        notes=f"Added new student {name} ({regno})"
    )

    return {'studentid': next_id, 'regno': regno, 'name': name, 'message': 'Student created successfully.'}

def erp_update_student(student_id, data, user_meta=None):
    """
    Updates student profile, updates login username if regno changed, and logs audit.
    """
    curr = fetch_one("SELECT * FROM students WHERE studentid = %s", (student_id,))
    if not curr:
        raise ValueError("Student record not found.")

    regno = str(data.get('regno', curr['regno'])).strip()
    name = str(data.get('name', curr['name'])).strip()
    department = str(data.get('department', curr['department'])).strip()
    year = str(data.get('year', curr['year'])).strip()
    section = str(data.get('section', curr.get('section', 'A'))).strip()
    email = str(data.get('email', curr['email'])).strip()
    phone = str(data.get('phone', curr.get('phone') or '')).strip() or None

    if not regno or not name:
        raise ValueError("Register Number and Full Name are mandatory fields.")

    # Check regno clash with another student
    clash = fetch_one("SELECT studentid FROM students WHERE regno = %s AND studentid != %s", (regno, student_id))
    if clash:
        raise ValueError(f"Register Number '{regno}' is already assigned to another student.")

    execute("""
        UPDATE students
        SET regno = %s, name = %s, department = %s, year = %s, section = %s, email = %s, phone = %s
        WHERE studentid = %s
    """, (regno, name, department, year, section, email, phone, student_id))

    # Update associated user account username if regno changed
    if curr['regno'] != regno:
        try:
            execute("UPDATE users SET username = %s WHERE student_id = %s", (regno, student_id))
        except Exception as ue:
            print(f"Notice: Failed to update username: {ue}")

    log_erp_audit(
        table_name='students',
        record_id=student_id,
        action='UPDATE',
        field_name='profile',
        old_val=curr,
        new_val={'regno': regno, 'name': name, 'department': department, 'year': year, 'section': section, 'email': email, 'phone': phone},
        user_meta=user_meta,
        notes=f"Updated student profile for {name} ({regno})"
    )

    return {'studentid': student_id, 'message': 'Student updated successfully.'}

def erp_delete_student(student_id, user_meta=None):
    """
    Safely deletes student, removing child references in attendance, internal_marks,
    mark_correction_requests, and users table.
    """
    curr = fetch_one("SELECT * FROM students WHERE studentid = %s", (student_id,))
    if not curr:
        raise ValueError("Student not found.")

    # 1. Delete associated correction requests
    try:
        execute("DELETE FROM mark_correction_requests WHERE student_id = %s", (student_id,))
    except Exception:
        pass

    # 2. Delete attendance
    try:
        execute("DELETE FROM attendance WHERE student_id = %s", (student_id,))
    except Exception:
        pass

    # 3. Delete internal marks
    try:
        execute("DELETE FROM internal_marks WHERE student_id = %s", (student_id,))
    except Exception:
        pass

    # 4. Delete user login
    try:
        execute("DELETE FROM users WHERE student_id = %s", (student_id,))
    except Exception:
        pass

    # 5. Delete student record
    execute("DELETE FROM students WHERE studentid = %s", (student_id,))

    log_erp_audit(
        table_name='students',
        record_id=student_id,
        action='DELETE',
        old_val=curr,
        user_meta=user_meta,
        notes=f"Deleted student {curr.get('name')} ({curr.get('regno')})"
    )

    return {'message': f"Student {curr.get('name')} deleted successfully."}


# =========================================================================
# 2. STAFF MANAGEMENT MODULE (Full CRUD)
# =========================================================================

def erp_get_all_staff(search=None, department=None):
    """
    Returns full staff directory including assigned subjects and contact info.
    """
    query = """
    SELECT 
        st.staffid, st.name, st.subjects, st.department, st.email, st.phone, st.designation,
        COUNT(DISTINCT sub.subject_code) as total_assigned_subjects,
        GROUP_CONCAT(DISTINCT CONCAT(sub.subject_code, ' - ', sub.subject_name) SEPARATOR ', ') as detailed_subjects
    FROM staff st
    LEFT JOIN subjects sub ON st.staffid = sub.staff_id
    WHERE 1=1
    """
    params = []

    if search:
        s_term = f"%{search.strip()}%"
        query += " AND (st.name LIKE %s OR st.subjects LIKE %s OR st.email LIKE %s)"
        params.extend([s_term, s_term, s_term])

    if department and department != 'All':
        query += " AND st.department = %s"
        params.append(department)

    query += " GROUP BY st.staffid, st.name, st.subjects, st.department, st.email, st.phone, st.designation ORDER BY st.staffid ASC"

    return fetch_all(query, tuple(params)) or []

def erp_create_staff(data, user_meta=None):
    """
    Creates a new staff member, user account (staff123), and assigns subjects.
    """
    name = str(data.get('name', '')).strip()
    subjects = str(data.get('subjects', '')).strip()
    department = str(data.get('department', 'Information Technology')).strip()
    email = str(data.get('email', '')).strip() or None
    phone = str(data.get('phone', '')).strip() or None
    designation = str(data.get('designation', 'Assistant Professor')).strip()

    if not name:
        raise ValueError("Faculty name is required.")

    max_id_row = fetch_one("SELECT MAX(staffid) as m FROM staff")
    next_id = (max_id_row['m'] or 0) + 1 if max_id_row else 1

    execute("""
        INSERT INTO staff (staffid, name, subjects, department, email, phone, designation)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (next_id, name, subjects, department, email, phone, designation))

    # Create faculty user login (e.g. staff<id> or username from email)
    username = f"staff{next_id}"
    try:
        user_exists = fetch_one("SELECT id FROM users WHERE username = %s", (username,))
        if not user_exists:
            pwd_hash = generate_password_hash('staff123')
            execute("""
                INSERT INTO users (username, password_hash, role, staff_id)
                VALUES (%s, %s, 'staff', %s)
            """, (username, pwd_hash, next_id))
    except Exception as ue:
        print(f"Notice: User account creation for staff warning: {ue}")

    log_erp_audit(
        table_name='staff',
        record_id=next_id,
        action='INSERT',
        new_val={'name': name, 'subjects': subjects, 'department': department, 'email': email, 'phone': phone, 'designation': designation},
        user_meta=user_meta,
        notes=f"Added faculty member {name} (Staff ID: {next_id})"
    )

    return {'staffid': next_id, 'name': name, 'username': username, 'message': 'Faculty created successfully.'}

def erp_update_staff(staff_id, data, user_meta=None):
    """Updates staff record and syncs subject assignments."""
    curr = fetch_one("SELECT * FROM staff WHERE staffid = %s", (staff_id,))
    if not curr:
        raise ValueError("Staff member not found.")

    name = str(data.get('name', curr['name'])).strip()
    subjects = str(data.get('subjects', curr['subjects'] or '')).strip()
    department = str(data.get('department', curr.get('department') or 'Information Technology')).strip()
    email = str(data.get('email', curr.get('email') or '')).strip() or None
    phone = str(data.get('phone', curr.get('phone') or '')).strip() or None
    designation = str(data.get('designation', curr.get('designation') or 'Assistant Professor')).strip()

    if not name:
        raise ValueError("Faculty name is required.")

    execute("""
        UPDATE staff
        SET name = %s, subjects = %s, department = %s, email = %s, phone = %s, designation = %s
        WHERE staffid = %s
    """, (name, subjects, department, email, phone, designation, staff_id))

    log_erp_audit(
        table_name='staff',
        record_id=staff_id,
        action='UPDATE',
        old_val=curr,
        new_val={'name': name, 'subjects': subjects, 'department': department, 'email': email, 'phone': phone, 'designation': designation},
        user_meta=user_meta,
        notes=f"Updated faculty member {name}"
    )

    return {'staffid': staff_id, 'message': 'Faculty member updated successfully.'}

def erp_delete_staff(staff_id, user_meta=None):
    """Deletes staff member, reassigns subjects to NULL, and removes login."""
    curr = fetch_one("SELECT * FROM staff WHERE staffid = %s", (staff_id,))
    if not curr:
        raise ValueError("Staff member not found.")

    # 1. Unassign subjects
    try:
        execute("UPDATE subjects SET staff_id = NULL WHERE staff_id = %s", (staff_id,))
    except Exception:
        pass

    # 2. Timetable slots nullify staff
    try:
        execute("UPDATE timetable SET staff_id = NULL WHERE staff_id = %s", (staff_id,))
    except Exception:
        pass

    # 3. Delete user account
    try:
        execute("DELETE FROM users WHERE staff_id = %s", (staff_id,))
    except Exception:
        pass

    # 4. Delete staff record
    execute("DELETE FROM staff WHERE staffid = %s", (staff_id,))

    log_erp_audit(
        table_name='staff',
        record_id=staff_id,
        action='DELETE',
        old_val=curr,
        user_meta=user_meta,
        notes=f"Deleted faculty member {curr.get('name')}"
    )

    return {'message': f"Faculty member {curr.get('name')} deleted successfully."}


# =========================================================================
# 3. SUBJECT MANAGEMENT MODULE (Full CRUD)
# =========================================================================

def erp_get_all_subjects(department=None, semester=None, search=None):
    """Returns all subjects mapped with faculty information and student enrollment count."""
    query = """
    SELECT 
        sub.subject_code, sub.subject_name, sub.semester, sub.staff_id, sub.subjectid, sub.department,
        st.name as faculty_name,
        COUNT(DISTINCT m.student_id) as enrolled_students_count,
        ROUND(AVG(m.marks_obtained), 1) as avg_score
    FROM subjects sub
    LEFT JOIN staff st ON sub.staff_id = st.staffid
    LEFT JOIN internal_marks m ON sub.subjectid = m.subject_id
    WHERE 1=1
    """
    params = []

    if search:
        s_term = f"%{search.strip()}%"
        query += " AND (sub.subject_code LIKE %s OR sub.subject_name LIKE %s OR st.name LIKE %s)"
        params.extend([s_term, s_term, s_term])

    if department and department != 'All':
        query += " AND sub.department = %s"
        params.append(department)

    if semester and semester != 'All':
        query += " AND sub.semester = %s"
        params.append(int(semester))

    query += " GROUP BY sub.subject_code, sub.subject_name, sub.semester, sub.staff_id, sub.subjectid, sub.department, st.name ORDER BY sub.semester ASC, sub.subject_code ASC"

    return fetch_all(query, tuple(params)) or []

def erp_create_subject(data, user_meta=None):
    """Creates a new subject, associates faculty, and logs audit."""
    code = str(data.get('subject_code', '')).strip().upper()
    name = str(data.get('subject_name', '')).strip()
    semester = int(data.get('semester', 5))
    staff_id = data.get('staff_id')
    department = str(data.get('department', 'Information Technology')).strip()

    staff_id = int(staff_id) if staff_id and str(staff_id).isdigit() else None

    if not code or not name:
        raise ValueError("Subject Code and Subject Name are required.")

    # Check duplicate code
    exists = fetch_one("SELECT subject_code FROM subjects WHERE subject_code = %s", (code,))
    if exists:
        raise ValueError(f"Subject with code '{code}' already exists.")

    # Next subjectid integer
    max_id_row = fetch_one("SELECT MAX(subjectid) as m FROM subjects")
    next_id = (max_id_row['m'] or 0) + 1 if max_id_row else 1

    execute("""
        INSERT INTO subjects (subject_code, subject_name, semester, staff_id, subjectid, department)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (code, name, semester, staff_id, next_id, department))

    log_erp_audit(
        table_name='subjects',
        record_id=next_id,
        action='INSERT',
        new_val={'subject_code': code, 'subject_name': name, 'semester': semester, 'staff_id': staff_id, 'department': department},
        user_meta=user_meta,
        notes=f"Created subject {code} - {name}"
    )

    return {'subject_code': code, 'subjectid': next_id, 'message': 'Subject added successfully.'}

def erp_update_subject(subject_code, data, user_meta=None):
    """Updates subject information and assigned faculty."""
    curr = fetch_one("SELECT * FROM subjects WHERE subject_code = %s", (subject_code,))
    if not curr:
        raise ValueError("Subject not found.")

    new_code = str(data.get('subject_code', curr['subject_code'])).strip().upper()
    name = str(data.get('subject_name', curr['subject_name'])).strip()
    semester = int(data.get('semester', curr['semester']))
    staff_id = data.get('staff_id')
    department = str(data.get('department', curr.get('department') or 'Information Technology')).strip()

    staff_id = int(staff_id) if staff_id and str(staff_id).isdigit() else None

    if not new_code or not name:
        raise ValueError("Subject Code and Subject Name are required.")

    if new_code != subject_code:
        dup = fetch_one("SELECT subject_code FROM subjects WHERE subject_code = %s", (new_code,))
        if dup:
            raise ValueError(f"Subject code '{new_code}' is already taken.")

    execute("""
        UPDATE subjects
        SET subject_code = %s, subject_name = %s, semester = %s, staff_id = %s, department = %s
        WHERE subject_code = %s
    """, (new_code, name, semester, staff_id, department, subject_code))

    log_erp_audit(
        table_name='subjects',
        record_id=curr.get('subjectid') or 0,
        action='UPDATE',
        old_val=curr,
        new_val={'subject_code': new_code, 'subject_name': name, 'semester': semester, 'staff_id': staff_id, 'department': department},
        user_meta=user_meta,
        notes=f"Updated subject {new_code} - {name}"
    )

    return {'subject_code': new_code, 'message': 'Subject updated successfully.'}

def erp_delete_subject(subject_code, user_meta=None):
    """Deletes subject, handling dependent records."""
    curr = fetch_one("SELECT * FROM subjects WHERE subject_code = %s", (subject_code,))
    if not curr:
        raise ValueError("Subject not found.")

    sub_id = curr.get('subjectid')

    # Remove references in timetable
    try:
        execute("DELETE FROM timetable WHERE subject_code = %s", (subject_code,))
    except Exception:
        pass

    # Remove references in notes
    try:
        if sub_id:
            execute("DELETE FROM notes WHERE subject_id = %s", (sub_id,))
    except Exception:
        pass

    # Remove references in marks
    try:
        if sub_id:
            execute("DELETE FROM internal_marks WHERE subject_id = %s", (sub_id,))
    except Exception:
        pass

    execute("DELETE FROM subjects WHERE subject_code = %s", (subject_code,))

    log_erp_audit(
        table_name='subjects',
        record_id=sub_id or 0,
        action='DELETE',
        old_val=curr,
        user_meta=user_meta,
        notes=f"Deleted subject {curr.get('subject_code')} - {curr.get('subject_name')}"
    )

    return {'message': f"Subject {subject_code} deleted successfully."}


# =========================================================================
# 4. ATTENDANCE MANAGEMENT MODULE (CRUD, Filters, CSV Export)
# =========================================================================

def erp_get_attendance(date_filter=None, subject_id=None, student_id=None, status_filter=None, search=None, page=1, per_page=30):
    """Fetches attendance records with rich filters, student details, and pagination."""
    query = """
    SELECT 
        att.id, att.student_id, att.date, att.status, att.subject_id,
        s.regno, s.name as student_name, s.department, s.year, s.section,
        sub.subject_code, sub.subject_name
    FROM attendance att
    JOIN students s ON att.student_id = s.studentid
    LEFT JOIN subjects sub ON att.subject_id = sub.subjectid
    WHERE 1=1
    """
    params = []

    if date_filter:
        query += " AND att.date = %s"
        params.append(date_filter)

    if subject_id and subject_id != 'All':
        query += " AND att.subject_id = %s"
        params.append(int(subject_id))

    if student_id:
        query += " AND att.student_id = %s"
        params.append(int(student_id))

    if status_filter and status_filter != 'All':
        query += " AND LOWER(att.status) = LOWER(%s)"
        params.append(status_filter)

    if search:
        s_term = f"%{search.strip()}%"
        query += " AND (s.name LIKE %s OR s.regno LIKE %s)"
        params.extend([s_term, s_term])

    query += " ORDER BY att.date DESC, s.regno ASC"

    # Count total
    count_query = f"SELECT COUNT(*) as cnt FROM ({query}) as t"
    total_row = fetch_one(count_query, tuple(params))
    total_records = total_row['cnt'] if total_row else 0

    # Limit / Offset
    if per_page and per_page > 0:
        offset = (page - 1) * per_page
        query += f" LIMIT {int(per_page)} OFFSET {int(offset)}"

    records = fetch_all(query, tuple(params)) or []

    # Format date string for JSON
    for r in records:
        if isinstance(r.get('date'), (date, datetime)):
            r['date_str'] = r['date'].strftime('%Y-%m-%d')
        else:
            r['date_str'] = str(r.get('date', ''))

    total_pages = (total_records + per_page - 1) // per_page if per_page else 1

    return {
        'records': records,
        'total': total_records,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages
    }

def erp_add_attendance(data, user_meta=None):
    """
    Adds or updates attendance record for a student on a specific date.
    Supports single mark or bulk marks.
    """
    records = data.get('records') if isinstance(data.get('records'), list) else [data]
    added_count = 0
    updated_count = 0

    for item in records:
        student_id = item.get('student_id')
        att_date = item.get('date') or datetime.now().strftime('%Y-%m-%d')
        status = str(item.get('status', 'Present')).capitalize()
        subject_id = item.get('subject_id')
        subject_id = int(subject_id) if subject_id and str(subject_id).isdigit() else None

        if not student_id or not att_date:
            continue

        if status not in ('Present', 'Absent'):
            status = 'Present'

        # Check existing unique (student_id, date)
        existing = fetch_one("SELECT id, status FROM attendance WHERE student_id = %s AND date = %s", (student_id, att_date))
        if existing:
            execute("""
                UPDATE attendance
                SET status = %s, subject_id = COALESCE(%s, subject_id)
                WHERE id = %s
            """, (status, subject_id, existing['id']))
            updated_count += 1
            log_erp_audit(
                table_name='attendance',
                record_id=existing['id'],
                action='UPDATE',
                old_val={'status': existing['status']},
                new_val={'status': status, 'date': att_date, 'subject_id': subject_id},
                user_meta=user_meta,
                notes=f"Updated attendance for student ID {student_id} on {att_date}"
            )
        else:
            new_id = execute("""
                INSERT INTO attendance (student_id, date, status, subject_id)
                VALUES (%s, %s, %s, %s)
            """, (student_id, att_date, status, subject_id))
            added_count += 1
            log_erp_audit(
                table_name='attendance',
                record_id=new_id or 0,
                action='INSERT',
                new_val={'student_id': student_id, 'date': att_date, 'status': status, 'subject_id': subject_id},
                user_meta=user_meta,
                notes=f"Marked attendance for student ID {student_id} on {att_date}: {status}"
            )

    return {'added': added_count, 'updated': updated_count, 'message': f"Saved {added_count + updated_count} attendance records."}

def erp_update_attendance(att_id, data, user_meta=None):
    """Updates a single attendance record."""
    curr = fetch_one("SELECT * FROM attendance WHERE id = %s", (att_id,))
    if not curr:
        raise ValueError("Attendance record not found.")

    status = str(data.get('status', curr['status'])).capitalize()
    att_date = data.get('date') or curr['date']
    subject_id = data.get('subject_id', curr.get('subject_id'))
    subject_id = int(subject_id) if subject_id and str(subject_id).isdigit() else None

    if status not in ('Present', 'Absent'):
        status = 'Present'

    execute("""
        UPDATE attendance
        SET status = %s, date = %s, subject_id = %s
        WHERE id = %s
    """, (status, att_date, subject_id, att_id))

    log_erp_audit(
        table_name='attendance',
        record_id=att_id,
        action='UPDATE',
        old_val=curr,
        new_val={'status': status, 'date': str(att_date), 'subject_id': subject_id},
        user_meta=user_meta,
        notes=f"Updated attendance record #{att_id}"
    )

    return {'id': att_id, 'message': 'Attendance updated successfully.'}

def erp_delete_attendance(att_id, user_meta=None):
    """Deletes an attendance record."""
    curr = fetch_one("SELECT * FROM attendance WHERE id = %s", (att_id,))
    if not curr:
        raise ValueError("Attendance record not found.")

    execute("DELETE FROM attendance WHERE id = %s", (att_id,))

    log_erp_audit(
        table_name='attendance',
        record_id=att_id,
        action='DELETE',
        old_val=curr,
        user_meta=user_meta,
        notes=f"Deleted attendance record #{att_id}"
    )

    return {'message': 'Attendance record deleted successfully.'}

def erp_export_attendance_csv(date_filter=None, subject_id=None, search=None):
    """Generates CSV stream for attendance export."""
    res = erp_get_attendance(date_filter=date_filter, subject_id=subject_id, search=search, page=1, per_page=10000)
    records = res.get('records', [])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Record ID', 'Register Number', 'Student Name', 'Department', 'Year', 'Section', 'Date', 'Subject', 'Attendance Status'])

    for r in records:
        sub_str = f"{r.get('subject_code') or ''} - {r.get('subject_name') or ''}".strip(' -')
        writer.writerow([
            r.get('id'),
            r.get('regno'),
            r.get('student_name'),
            r.get('department'),
            r.get('year'),
            r.get('section'),
            r.get('date_str'),
            sub_str or 'General Session',
            r.get('status')
        ])

    return output.getvalue()


# =========================================================================
# 5. INTERNAL MARKS MODULE (Full CRUD & Reports)
# =========================================================================

def erp_get_marks(student_id=None, subject_id=None, test_number=None, search=None, page=1, per_page=30):
    """Fetches internal marks with student and subject details, filters, and pagination."""
    query = """
    SELECT 
        m.id, m.student_id, m.subject_id, m.test_number, m.marks_obtained, m.max_marks,
        ROUND((m.marks_obtained / NULLIF(m.max_marks, 0)) * 100, 1) as percentage,
        s.regno, s.name as student_name, s.department, s.year, s.section,
        sub.subject_code, sub.subject_name, sub.semester
    FROM internal_marks m
    JOIN students s ON m.student_id = s.studentid
    LEFT JOIN subjects sub ON m.subject_id = sub.subjectid
    WHERE 1=1
    """
    params = []

    if student_id:
        query += " AND m.student_id = %s"
        params.append(int(student_id))

    if subject_id and subject_id != 'All':
        query += " AND m.subject_id = %s"
        params.append(int(subject_id))

    if test_number and test_number != 'All':
        query += " AND m.test_number = %s"
        params.append(int(test_number))

    if search:
        s_term = f"%{search.strip()}%"
        query += " AND (s.name LIKE %s OR s.regno LIKE %s OR sub.subject_name LIKE %s)"
        params.extend([s_term, s_term, s_term])

    query += " ORDER BY s.regno ASC, sub.subject_code ASC, m.test_number ASC"

    count_query = f"SELECT COUNT(*) as cnt FROM ({query}) as t"
    total_row = fetch_one(count_query, tuple(params))
    total_records = total_row['cnt'] if total_row else 0

    if per_page and per_page > 0:
        offset = (page - 1) * per_page
        query += f" LIMIT {int(per_page)} OFFSET {int(offset)}"

    records = fetch_all(query, tuple(params)) or []

    for r in records:
        pct = float(r.get('percentage') or 0.0)
        r['result'] = 'Pass' if pct >= 50.0 else 'Fail'

    total_pages = (total_records + per_page - 1) // per_page if per_page else 1

    return {
        'marks': records,
        'total': total_records,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages
    }

def erp_add_mark(data, user_meta=None):
    """Adds a new internal mark entry with validation and audit logging."""
    student_id = int(data.get('student_id'))
    subject_id = int(data.get('subject_id'))
    test_number = int(data.get('test_number', 1))
    marks_obtained = float(data.get('marks_obtained', 0))
    max_marks = float(data.get('max_marks', 100))

    if marks_obtained < 0 or marks_obtained > max_marks:
        raise ValueError(f"Marks obtained must be between 0 and {max_marks}.")

    # Check existing mark for same student, subject, test
    existing = fetch_one("""
        SELECT id FROM internal_marks
        WHERE student_id = %s AND subject_id = %s AND test_number = %s
    """, (student_id, subject_id, test_number))

    if existing:
        execute("""
            UPDATE internal_marks
            SET marks_obtained = %s, max_marks = %s
            WHERE id = %s
        """, (marks_obtained, max_marks, existing['id']))
        mark_id = existing['id']
        action = 'UPDATE'
    else:
        mark_id = execute("""
            INSERT INTO internal_marks (student_id, subject_id, test_number, marks_obtained, max_marks)
            VALUES (%s, %s, %s, %s, %s)
        """, (student_id, subject_id, test_number, marks_obtained, max_marks))
        action = 'INSERT'

    log_erp_audit(
        table_name='internal_marks',
        record_id=mark_id,
        action=action,
        new_val={'student_id': student_id, 'subject_id': subject_id, 'test_number': test_number, 'marks_obtained': marks_obtained, 'max_marks': max_marks},
        user_meta=user_meta,
        notes=f"Internal Mark recorded for student {student_id}, Subject {subject_id}, Test {test_number}: {marks_obtained}/{max_marks}"
    )

    return {'id': mark_id, 'message': 'Internal mark recorded successfully.'}

def erp_update_mark(mark_id, data, user_meta=None):
    """Updates an existing internal mark record."""
    curr = fetch_one("SELECT * FROM internal_marks WHERE id = %s", (mark_id,))
    if not curr:
        raise ValueError("Mark record not found.")

    marks_obtained = float(data.get('marks_obtained', curr['marks_obtained']))
    max_marks = float(data.get('max_marks', curr['max_marks']))
    test_number = int(data.get('test_number', curr['test_number']))

    if marks_obtained < 0 or marks_obtained > max_marks:
        raise ValueError(f"Marks obtained must be between 0 and {max_marks}.")

    execute("""
        UPDATE internal_marks
        SET marks_obtained = %s, max_marks = %s, test_number = %s
        WHERE id = %s
    """, (marks_obtained, max_marks, test_number, mark_id))

    log_erp_audit(
        table_name='internal_marks',
        record_id=mark_id,
        action='UPDATE',
        old_val=curr,
        new_val={'marks_obtained': marks_obtained, 'max_marks': max_marks, 'test_number': test_number},
        user_meta=user_meta,
        notes=f"Updated mark ID #{mark_id} to {marks_obtained}/{max_marks}"
    )

    return {'id': mark_id, 'message': 'Internal mark updated successfully.'}

def erp_delete_mark(mark_id, user_meta=None):
    """Deletes an internal mark record."""
    curr = fetch_one("SELECT * FROM internal_marks WHERE id = %s", (mark_id,))
    if not curr:
        raise ValueError("Mark record not found.")

    execute("DELETE FROM internal_marks WHERE id = %s", (mark_id,))

    log_erp_audit(
        table_name='internal_marks',
        record_id=mark_id,
        action='DELETE',
        old_val=curr,
        user_meta=user_meta,
        notes=f"Deleted internal mark ID #{mark_id}"
    )

    return {'message': 'Mark record deleted successfully.'}

def erp_get_marks_reports(report_type='student', student_id=None, subject_id=None, semester=None):
    """
    Generates Student Report, Subject Report, or Semester Report data.
    """
    if report_type == 'student':
        if not student_id:
            # All students summary
            return fetch_all("""
                SELECT 
                    s.studentid, s.regno, s.name, s.department, s.year,
                    ROUND(AVG(m.marks_obtained), 1) as avg_marks,
                    COUNT(m.id) as total_tests_taken,
                    SUM(CASE WHEN (m.marks_obtained / NULLIF(m.max_marks, 0)) * 100 >= 50 THEN 1 ELSE 0 END) as passed_tests,
                    SUM(CASE WHEN (m.marks_obtained / NULLIF(m.max_marks, 0)) * 100 < 50 THEN 1 ELSE 0 END) as failed_tests
                FROM students s
                LEFT JOIN internal_marks m ON s.studentid = m.student_id
                GROUP BY s.studentid, s.regno, s.name, s.department, s.year
                ORDER BY avg_marks DESC
            """)
        else:
            return erp_get_student_by_id(student_id)

    elif report_type == 'subject':
        query = """
            SELECT 
                sub.subjectid, sub.subject_code, sub.subject_name, sub.semester,
                COUNT(m.id) as total_tests_evaluated,
                ROUND(AVG(m.marks_obtained), 1) as avg_score,
                ROUND(MAX(m.marks_obtained), 1) as highest_score,
                ROUND(MIN(m.marks_obtained), 1) as lowest_score,
                ROUND((SUM(CASE WHEN (m.marks_obtained / NULLIF(m.max_marks, 0)) * 100 >= 50 THEN 1 ELSE 0 END) / NULLIF(COUNT(m.id), 0)) * 100, 1) as pass_percentage
            FROM subjects sub
            LEFT JOIN internal_marks m ON sub.subjectid = m.subject_id
            WHERE 1=1
        """
        params = []
        if subject_id and subject_id != 'All':
            query += " AND sub.subjectid = %s"
            params.append(int(subject_id))
        query += " GROUP BY sub.subjectid, sub.subject_code, sub.subject_name, sub.semester ORDER BY sub.semester, sub.subject_code"
        return fetch_all(query, tuple(params))

    elif report_type == 'semester':
        query = """
            SELECT 
                sub.semester,
                COUNT(DISTINCT sub.subject_code) as total_subjects,
                COUNT(DISTINCT m.student_id) as enrolled_students,
                ROUND(AVG(m.marks_obtained), 1) as avg_marks,
                ROUND((SUM(CASE WHEN (m.marks_obtained / NULLIF(m.max_marks, 0)) * 100 >= 50 THEN 1 ELSE 0 END) / NULLIF(COUNT(m.id), 0)) * 100, 1) as pass_rate
            FROM subjects sub
            LEFT JOIN internal_marks m ON sub.subjectid = m.subject_id
            GROUP BY sub.semester
            ORDER BY sub.semester ASC
        """
        return fetch_all(query)

    return []


# =========================================================================
# 6. TIMETABLE MANAGEMENT MODULE (Full CRUD)
# =========================================================================

DEFAULT_PERIOD_SLOTS = [
    (1, '09:00 AM - 09:50 AM'),
    (2, '09:50 AM - 10:40 AM'),
    (3, '11:00 AM - 11:50 AM'),
    (4, '11:50 AM - 12:40 PM'),
    (5, '01:30 PM - 02:20 PM'),
    (6, '02:20 PM - 03:10 PM'),
    (7, '03:10 PM - 04:00 PM'),
]

DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

def erp_seed_default_timetable():
    """Seeds a realistic default timetable for Third Year IT Department if empty."""
    cnt = fetch_one("SELECT COUNT(*) as c FROM timetable")
    if cnt and cnt['c'] > 0:
        return

    subjects = fetch_all("SELECT subject_code, staff_id FROM subjects ORDER BY subject_code")
    if not subjects:
        return

    classrooms = ['LH-201', 'LH-202', 'IT Lab 1', 'IoT Lab']
    import random

    entries = []
    sub_idx = 0
    for day in DAYS_OF_WEEK:
        for p_num, t_slot in DEFAULT_PERIOD_SLOTS:
            sub = subjects[sub_idx % len(subjects)]
            room = classrooms[(p_num + sub_idx) % len(classrooms)]
            entries.append((day, p_num, t_slot, sub['subject_code'], sub['staff_id'], room, 'Third year', 'A'))
            sub_idx += 1

    for e in entries:
        try:
            execute("""
                INSERT INTO timetable (day_of_week, period_number, time_slot, subject_code, staff_id, classroom, year, section)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, e)
        except Exception as ex:
            print(f"Notice: Timetable seed item warning: {ex}")

def erp_get_timetable(year='Third year', section='A', day=None):
    """
    Fetches timetable grouped by day or for a specific day.
    Auto-seeds if table is completely empty.
    """
    erp_seed_default_timetable()

    query = """
    SELECT 
        t.id, t.day_of_week, t.period_number, t.time_slot, t.subject_code, t.staff_id, t.classroom, t.year, t.section,
        sub.subject_name, sub.semester,
        st.name as faculty_name
    FROM timetable t
    JOIN subjects sub ON t.subject_code = sub.subject_code
    LEFT JOIN staff st ON t.staff_id = st.staffid
    WHERE 1=1
    """
    params = []

    if year and year != 'All':
        query += " AND t.year = %s"
        params.append(year)

    if section and section != 'All':
        query += " AND t.section = %s"
        params.append(section)

    if day and day != 'All':
        query += " AND t.day_of_week = %s"
        params.append(day)

    query += " ORDER BY FIELD(t.day_of_week, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'), t.period_number ASC"

    rows = fetch_all(query, tuple(params)) or []

    # Organize into day-wise dict
    grouped = {d: [] for d in DAYS_OF_WEEK}
    for r in rows:
        d = r.get('day_of_week')
        if d in grouped:
            grouped[d].append(r)

    return {
        'all_slots': rows,
        'grouped_by_day': grouped,
        'days': DAYS_OF_WEEK,
        'periods': DEFAULT_PERIOD_SLOTS
    }

def erp_add_timetable_slot(data, user_meta=None):
    """Adds a new timetable slot."""
    day = str(data.get('day_of_week', 'Monday')).capitalize()
    period_number = int(data.get('period_number', 1))
    time_slot = str(data.get('time_slot', '')).strip()
    subject_code = str(data.get('subject_code', '')).strip()
    staff_id = data.get('staff_id')
    classroom = str(data.get('classroom', 'LH-201')).strip()
    year = str(data.get('year', 'Third year')).strip()
    section = str(data.get('section', 'A')).strip()

    staff_id = int(staff_id) if staff_id and str(staff_id).isdigit() else None

    if not time_slot:
        # Default lookup
        for p, ts in DEFAULT_PERIOD_SLOTS:
            if p == period_number:
                time_slot = ts
                break
        time_slot = time_slot or f"Period {period_number}"

    if not subject_code:
        raise ValueError("Subject is required.")

    # If staff_id not provided, lookup default staff from subjects table
    if not staff_id:
        sub = fetch_one("SELECT staff_id FROM subjects WHERE subject_code = %s", (subject_code,))
        if sub:
            staff_id = sub.get('staff_id')

    slot_id = execute("""
        INSERT INTO timetable (day_of_week, period_number, time_slot, subject_code, staff_id, classroom, year, section)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (day, period_number, time_slot, subject_code, staff_id, classroom, year, section))

    log_erp_audit(
        table_name='timetable',
        record_id=slot_id,
        action='INSERT',
        new_val={'day': day, 'period': period_number, 'subject': subject_code, 'staff': staff_id, 'room': classroom},
        user_meta=user_meta,
        notes=f"Added timetable slot for {day} Period {period_number}: {subject_code} in {classroom}"
    )

    return {'id': slot_id, 'message': 'Timetable slot created successfully.'}

def erp_update_timetable_slot(slot_id, data, user_meta=None):
    """Updates an existing timetable slot."""
    curr = fetch_one("SELECT * FROM timetable WHERE id = %s", (slot_id,))
    if not curr:
        raise ValueError("Timetable slot not found.")

    day = str(data.get('day_of_week', curr['day_of_week'])).capitalize()
    period_number = int(data.get('period_number', curr['period_number']))
    time_slot = str(data.get('time_slot', curr['time_slot'])).strip()
    subject_code = str(data.get('subject_code', curr['subject_code'])).strip()
    staff_id = data.get('staff_id', curr['staff_id'])
    classroom = str(data.get('classroom', curr['classroom'])).strip()
    year = str(data.get('year', curr['year'])).strip()
    section = str(data.get('section', curr['section'])).strip()

    staff_id = int(staff_id) if staff_id and str(staff_id).isdigit() else None

    execute("""
        UPDATE timetable
        SET day_of_week = %s, period_number = %s, time_slot = %s, subject_code = %s, staff_id = %s, classroom = %s, year = %s, section = %s
        WHERE id = %s
    """, (day, period_number, time_slot, subject_code, staff_id, classroom, year, section, slot_id))

    log_erp_audit(
        table_name='timetable',
        record_id=slot_id,
        action='UPDATE',
        old_val=curr,
        new_val={'day': day, 'period': period_number, 'subject': subject_code, 'staff': staff_id, 'room': classroom},
        user_meta=user_meta,
        notes=f"Updated timetable slot #{slot_id}"
    )

    return {'id': slot_id, 'message': 'Timetable slot updated successfully.'}

def erp_delete_timetable_slot(slot_id, user_meta=None):
    """Deletes a timetable slot."""
    curr = fetch_one("SELECT * FROM timetable WHERE id = %s", (slot_id,))
    if not curr:
        raise ValueError("Timetable slot not found.")

    execute("DELETE FROM timetable WHERE id = %s", (slot_id,))

    log_erp_audit(
        table_name='timetable',
        record_id=slot_id,
        action='DELETE',
        old_val=curr,
        user_meta=user_meta,
        notes=f"Deleted timetable slot #{slot_id}"
    )

    return {'message': 'Timetable slot deleted successfully.'}
