"""
ERP Service Layer
Provides robust, production-ready CRUD operations for Students, Staff, Subjects, Attendance, Internal Marks, and Timetable.
Directly communicates with the live MySQL database via parameterized queries.
Includes comprehensive validation, exception handling, and audit logging.
"""

from db import fetch_all, fetch_one, execute
from datetime import datetime


def log_erp_audit(table_name, record_id, action, old_value=None, new_value=None, user_id=None, user_name="HOD", user_role="hod", notes=None):
    """Logs database operations to the audit_log table for security and tracking."""
    try:
        execute("""
            INSERT INTO audit_log (table_name, record_id, action, old_value, new_value, changed_by_user_id, changed_by_name, changed_by_role, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (table_name, record_id, action, str(old_value) if old_value else None, str(new_value) if new_value else None, user_id, user_name, user_role, notes))
    except Exception as e:
        print(f"Warning: Failed to log audit event: {e}")


# ==============================================================================
# 1. STUDENT MANAGEMENT CRUD
# ==============================================================================

def get_students_paginated(search=None, department=None, year=None, page=1, limit=15):
    """Fetches students with search, filters, and pagination."""
    query = """
        SELECT 
            s.studentid, s.regno, s.name, s.department, s.year, s.email,
            COALESCE(s.section, 'A') as section,
            COALESCE(s.phone, '') as phone,
            COALESCE(att.att_pct, 0.0) as attendance_percentage,
            COALESCE(marks.avg_marks, 0.0) as avg_marks,
            COALESCE(marks.passed_count, 0) as passed_subjects,
            COALESCE(marks.failed_count, 0) as failed_subjects
        FROM students s
        LEFT JOIN (
            SELECT 
                student_id,
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
    count_query = "SELECT COUNT(*) as total FROM students s WHERE 1=1"
    params = []

    if search:
        search_term = f"%{search.strip()}%"
        clause = " AND (s.name LIKE %s OR s.regno LIKE %s OR s.email LIKE %s)"
        query += clause
        count_query += clause
        params.extend([search_term, search_term, search_term])

    if department and department != 'All':
        query += " AND s.department = %s"
        count_query += " AND s.department = %s"
        params.append(department)

    if year and year != 'All':
        query += " AND s.year = %s"
        count_query += " AND s.year = %s"
        params.append(year)

    total_res = fetch_one(count_query, tuple(params))
    total_count = total_res['total'] if total_res else 0

    query += " ORDER BY s.studentid ASC LIMIT %s OFFSET %s"
    offset = max(0, (page - 1) * limit)
    p_params = list(params) + [limit, offset]

    students = fetch_all(query, tuple(p_params)) or []

    # Assign risk and ranking
    for s in students:
        att = float(s.get('attendance_percentage') or 0.0)
        avg_m = float(s.get('avg_marks') or 0.0)
        s['is_at_risk'] = (att < 75.0 or avg_m < 50.0)
        s['academic_standing'] = 'At Risk' if s['is_at_risk'] else ('Distinction' if avg_m >= 75.0 else 'Normal')

    return {
        'students': students,
        'total': total_count,
        'page': page,
        'limit': limit,
        'total_pages': (total_count + limit - 1) // limit if limit > 0 else 1
    }


def add_student(data, actor_name="HOD", actor_id=None):
    """Creates a new student record and automatic login credentials."""
    regno = str(data.get('regno', '')).strip()
    name = str(data.get('name', '')).strip().upper()
    department = str(data.get('department', 'IT')).strip()
    year = str(data.get('year', 'Third year')).strip()
    section = str(data.get('section', 'A')).strip().upper()
    email = str(data.get('email', '')).strip().lower()
    phone = str(data.get('phone', '')).strip()

    if not regno:
        raise ValueError("Register Number is required.")
    if not name:
        raise ValueError("Student Name is required.")

    # Check for duplicate register number
    existing = fetch_one("SELECT studentid FROM students WHERE regno = %s", (regno,))
    if existing:
        raise ValueError(f"Student with Register Number '{regno}' already exists.")

    # Determine next studentid
    max_id_res = fetch_one("SELECT MAX(studentid) as max_id FROM students")
    new_id = (max_id_res['max_id'] or 0) + 1 if max_id_res else 1

    execute("""
        INSERT INTO students (studentid, regno, name, department, year, section, email, phone)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (new_id, regno, name, department, year, section, email, phone))

    # Create user account for student portal login (default password is student123 or regno)
    from werkzeug.security import generate_password_hash
    pwd_hash = generate_password_hash("student123")
    try:
        user_exists = fetch_one("SELECT id FROM users WHERE username = %s", (regno,))
        if not user_exists:
            execute("""
                INSERT INTO users (username, password_hash, role, student_id)
                VALUES (%s, %s, 'student', %s)
            """, (regno, pwd_hash, new_id))
    except Exception as e:
        print(f"Notice: User creation note: {e}")

    log_erp_audit('students', new_id, 'CREATE', new_value=f"{regno} - {name}", user_id=actor_id, user_name=actor_name)
    return {'studentid': new_id, 'regno': regno, 'name': name}


def update_student(student_id, data, actor_name="HOD", actor_id=None):
    """Updates an existing student profile."""
    student = fetch_one("SELECT * FROM students WHERE studentid = %s", (student_id,))
    if not student:
        raise ValueError("Student record not found.")

    regno = str(data.get('regno', student['regno'])).strip()
    name = str(data.get('name', student['name'])).strip().upper()
    department = str(data.get('department', student['department'])).strip()
    year = str(data.get('year', student['year'])).strip()
    section = str(data.get('section', student.get('section', 'A') or 'A')).strip().upper()
    email = str(data.get('email', student['email'])).strip().lower()
    phone = str(data.get('phone', student.get('phone', '') or '')).strip()

    if not regno:
        raise ValueError("Register Number cannot be empty.")
    if not name:
        raise ValueError("Name cannot be empty.")

    # Check unique regno if changed
    if regno != student['regno']:
        dup = fetch_one("SELECT studentid FROM students WHERE regno = %s AND studentid != %s", (regno, student_id))
        if dup:
            raise ValueError(f"Register Number '{regno}' is already in use by another student.")

    execute("""
        UPDATE students 
        SET regno = %s, name = %s, department = %s, year = %s, section = %s, email = %s, phone = %s
        WHERE studentid = %s
    """, (regno, name, department, year, section, email, phone, student_id))

    # Keep users table username in sync
    if regno != student['regno']:
        try:
            execute("UPDATE users SET username = %s WHERE student_id = %s", (regno, student_id))
        except Exception:
            pass

    log_erp_audit('students', student_id, 'UPDATE', old_value=str(student), new_value=f"{regno} - {name}", user_id=actor_id, user_name=actor_name)
    return {'studentid': student_id, 'regno': regno, 'name': name}


def delete_student(student_id, actor_name="HOD", actor_id=None):
    """Deletes a student and cleans up related records."""
    student = fetch_one("SELECT * FROM students WHERE studentid = %s", (student_id,))
    if not student:
        raise ValueError("Student record not found or already deleted.")

    # Clean dependent records safely
    try:
        execute("DELETE FROM mark_correction_requests WHERE student_id = %s", (student_id,))
    except Exception:
        pass

    try:
        execute("DELETE FROM internal_marks WHERE student_id = %s", (student_id,))
    except Exception:
        pass

    try:
        execute("DELETE FROM attendance WHERE student_id = %s", (student_id,))
    except Exception:
        pass

    try:
        execute("DELETE FROM users WHERE student_id = %s", (student_id,))
    except Exception:
        pass

    execute("DELETE FROM students WHERE studentid = %s", (student_id,))
    log_erp_audit('students', student_id, 'DELETE', old_value=f"{student['regno']} - {student['name']}", user_id=actor_id, user_name=actor_name)
    return True


# ==============================================================================
# 2. STAFF MANAGEMENT CRUD
# ==============================================================================

def get_staff_detailed(search=None, department=None):
    """Fetches all faculty members with assigned subjects and teaching statistics."""
    query = """
        SELECT 
            st.staffid, st.name, 
            COALESCE(st.department, 'Information Technology') as department,
            COALESCE(st.email, '') as email,
            COALESCE(st.phone, '') as phone,
            COALESCE(st.designation, 'Assistant Professor') as designation,
            COALESCE(st.subjects, '') as subjects,
            sub.subject_code,
            sub.subject_name
        FROM staff st
        LEFT JOIN subjects sub ON st.staffid = sub.staff_id
        WHERE 1=1
    """
    params = []
    if search:
        search_term = f"%{search.strip()}%"
        query += " AND (st.name LIKE %s OR st.email LIKE %s OR st.subjects LIKE %s)"
        params.extend([search_term, search_term, search_term])

    if department and department != 'All':
        query += " AND (st.department = %s OR st.department IS NULL)"
        params.append(department)

    query += " ORDER BY st.staffid ASC"
    rows = fetch_all(query, tuple(params)) or []

    # Consolidate multiple subject mappings if any
    staff_map = {}
    for r in rows:
        sid = r['staffid']
        if sid not in staff_map:
            staff_map[sid] = {
                'staffid': sid,
                'name': r['name'],
                'department': r['department'],
                'email': r['email'],
                'phone': r['phone'],
                'designation': r['designation'],
                'subjects': r['subjects'] or r['subject_name'] or 'None Assigned',
                'assigned_subjects': []
            }
        if r['subject_code'] and r['subject_name']:
            staff_map[sid]['assigned_subjects'].append({
                'code': r['subject_code'],
                'name': r['subject_name']
            })

    return list(staff_map.values())


def add_staff(data, actor_name="HOD", actor_id=None):
    """Creates a new faculty member."""
    name = str(data.get('name', '')).strip().upper()
    department = str(data.get('department', 'Information Technology')).strip()
    designation = str(data.get('designation', 'Assistant Professor')).strip()
    email = str(data.get('email', '')).strip().lower()
    phone = str(data.get('phone', '')).strip()
    subject_assigned = str(data.get('subjects', '')).strip()

    if not name:
        raise ValueError("Faculty name is required.")

    max_id_res = fetch_one("SELECT MAX(staffid) as max_id FROM staff")
    new_id = (max_id_res['max_id'] or 0) + 1 if max_id_res else 1

    execute("""
        INSERT INTO staff (staffid, name, subjects, department, email, phone, designation)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (new_id, name, subject_assigned, department, email, phone, designation))

    # Also map subject in subjects table if specified
    subject_code = data.get('subject_code')
    if subject_code:
        execute("UPDATE subjects SET staff_id = %s WHERE subject_code = %s", (new_id, subject_code))

    # Create faculty user login
    from werkzeug.security import generate_password_hash
    username = f"staff{new_id}"
    try:
        execute("""
            INSERT INTO users (username, password_hash, role, staff_id)
            VALUES (%s, %s, 'staff', %s)
        """, (username, generate_password_hash("staff123"), new_id))
    except Exception:
        pass

    log_erp_audit('staff', new_id, 'CREATE', new_value=name, user_id=actor_id, user_name=actor_name)
    return {'staffid': new_id, 'name': name, 'username': username}


def update_staff(staff_id, data, actor_name="HOD", actor_id=None):
    """Updates faculty details and subject assignments."""
    staff = fetch_one("SELECT * FROM staff WHERE staffid = %s", (staff_id,))
    if not staff:
        raise ValueError("Faculty record not found.")

    name = str(data.get('name', staff['name'])).strip().upper()
    department = str(data.get('department', staff.get('department') or 'Information Technology')).strip()
    designation = str(data.get('designation', staff.get('designation') or 'Assistant Professor')).strip()
    email = str(data.get('email', staff.get('email') or '')).strip().lower()
    phone = str(data.get('phone', staff.get('phone') or '')).strip()
    subject_assigned = str(data.get('subjects', staff.get('subjects') or '')).strip()

    execute("""
        UPDATE staff 
        SET name = %s, department = %s, designation = %s, email = %s, phone = %s, subjects = %s
        WHERE staffid = %s
    """, (name, department, designation, email, phone, subject_assigned, staff_id))

    # Subject re-mapping if subject_code provided
    subject_code = data.get('subject_code')
    if subject_code:
        # Clear previous mapping for this subject if reassigning
        execute("UPDATE subjects SET staff_id = %s WHERE subject_code = %s", (staff_id, subject_code))

    log_erp_audit('staff', staff_id, 'UPDATE', old_value=staff['name'], new_value=name, user_id=actor_id, user_name=actor_name)
    return {'staffid': staff_id, 'name': name}


def delete_staff(staff_id, actor_name="HOD", actor_id=None):
    """Deletes a faculty member and unlinks assigned subjects."""
    staff = fetch_one("SELECT * FROM staff WHERE staffid = %s", (staff_id,))
    if not staff:
        raise ValueError("Faculty record not found.")

    # Unlink subjects
    execute("UPDATE subjects SET staff_id = NULL WHERE staff_id = %s", (staff_id,))
    # Unlink timetable
    try:
        execute("UPDATE timetable SET staff_id = NULL WHERE staff_id = %s", (staff_id,))
    except Exception:
        pass
    # Remove user login
    try:
        execute("DELETE FROM users WHERE staff_id = %s", (staff_id,))
    except Exception:
        pass

    execute("DELETE FROM staff WHERE staffid = %s", (staff_id,))
    log_erp_audit('staff', staff_id, 'DELETE', old_value=staff['name'], user_id=actor_id, user_name=actor_name)
    return True


# ==============================================================================
# 3. SUBJECT MANAGEMENT CRUD
# ==============================================================================

def get_subjects_detailed(search=None, semester=None, department=None):
    """Lists all subjects with assigned faculty details."""
    query = """
        SELECT 
            sub.subject_code, sub.subject_name, sub.semester, sub.staff_id, sub.subjectid,
            COALESCE(sub.department, 'Information Technology') as department,
            st.name as staff_name,
            COALESCE(st.designation, 'Faculty') as staff_designation
        FROM subjects sub
        LEFT JOIN staff st ON sub.staff_id = st.staffid
        WHERE 1=1
    """
    params = []
    if search:
        search_term = f"%{search.strip()}%"
        query += " AND (sub.subject_name LIKE %s OR sub.subject_code LIKE %s OR st.name LIKE %s)"
        params.extend([search_term, search_term, search_term])

    if semester and semester != 'All':
        query += " AND sub.semester = %s"
        params.append(int(semester))

    if department and department != 'All':
        query += " AND (sub.department = %s OR sub.department IS NULL)"
        params.append(department)

    query += " ORDER BY sub.semester ASC, sub.subject_code ASC"
    return fetch_all(query, tuple(params)) or []


def add_subject(data, actor_name="HOD", actor_id=None):
    """Creates a new subject and maps semester & faculty."""
    code = str(data.get('subject_code', '')).strip().upper()
    name = str(data.get('subject_name', '')).strip()
    semester = int(data.get('semester', 5))
    staff_id = data.get('staff_id')
    department = str(data.get('department', 'Information Technology')).strip()

    if not code:
        raise ValueError("Subject Code is required (e.g. 24IT3501).")
    if not name:
        raise ValueError("Subject Name is required.")

    # Check duplicate code
    existing = fetch_one("SELECT subject_code FROM subjects WHERE subject_code = %s", (code,))
    if existing:
        raise ValueError(f"Subject code '{code}' already exists.")

    max_id_res = fetch_one("SELECT MAX(subjectid) as max_id FROM subjects")
    new_subid = (max_id_res['max_id'] or 0) + 1 if max_id_res else 1

    staff_id = int(staff_id) if staff_id and str(staff_id).isdigit() else None

    execute("""
        INSERT INTO subjects (subject_code, subject_name, semester, staff_id, subjectid, department)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (code, name, semester, staff_id, new_subid, department))

    log_erp_audit('subjects', new_subid, 'CREATE', new_value=f"{code} - {name}", user_id=actor_id, user_name=actor_name)
    return {'subject_code': code, 'subject_name': name, 'subjectid': new_subid}


def update_subject(subject_code, data, actor_name="HOD", actor_id=None):
    """Updates subject details and assigned faculty."""
    sub = fetch_one("SELECT * FROM subjects WHERE subject_code = %s", (subject_code,))
    if not sub:
        raise ValueError("Subject record not found.")

    name = str(data.get('subject_name', sub['subject_name'])).strip()
    semester = int(data.get('semester', sub['semester']))
    department = str(data.get('department', sub.get('department') or 'Information Technology')).strip()
    staff_id = data.get('staff_id')
    staff_id = int(staff_id) if staff_id and str(staff_id).isdigit() else None

    execute("""
        UPDATE subjects
        SET subject_name = %s, semester = %s, department = %s, staff_id = %s
        WHERE subject_code = %s
    """, (name, semester, department, staff_id, subject_code))

    log_erp_audit('subjects', sub['subjectid'], 'UPDATE', old_value=sub['subject_name'], new_value=name, user_id=actor_id, user_name=actor_name)
    return {'subject_code': subject_code, 'subject_name': name}


def delete_subject(subject_code, actor_name="HOD", actor_id=None):
    """Deletes a subject record."""
    sub = fetch_one("SELECT * FROM subjects WHERE subject_code = %s", (subject_code,))
    if not sub:
        raise ValueError("Subject record not found.")

    sub_id = sub['subjectid']

    # Clean references
    try:
        execute("DELETE FROM mark_correction_requests WHERE subject_id = %s", (sub_id,))
    except Exception:
        pass

    try:
        execute("DELETE FROM internal_marks WHERE subject_id = %s", (sub_id,))
    except Exception:
        pass

    try:
        execute("DELETE FROM timetable WHERE subject_code = %s", (subject_code,))
    except Exception:
        pass

    execute("DELETE FROM subjects WHERE subject_code = %s", (subject_code,))
    log_erp_audit('subjects', sub_id, 'DELETE', old_value=f"{subject_code} - {sub['subject_name']}", user_id=actor_id, user_name=actor_name)
    return True


# ==============================================================================
# 4. ATTENDANCE MANAGEMENT CRUD
# ==============================================================================

def get_attendance_records(date=None, student_id=None, subject_id=None, status=None, search=None, page=1, limit=50):
    """Fetches attendance records with date, student, and subject filters."""
    query = """
        SELECT 
            a.id, a.student_id, a.date, a.status,
            s.regno, s.name as student_name, s.department, s.year,
            sub.subject_code, sub.subject_name
        FROM attendance a
        JOIN students s ON a.student_id = s.studentid
        LEFT JOIN subjects sub ON a.subject_id = sub.subjectid
        WHERE 1=1
    """
    count_query = """
        SELECT COUNT(*) as total
        FROM attendance a
        JOIN students s ON a.student_id = s.studentid
        WHERE 1=1
    """
    params = []

    if date:
        query += " AND a.date = %s"
        count_query += " AND a.date = %s"
        params.append(str(date))

    if student_id:
        query += " AND a.student_id = %s"
        count_query += " AND a.student_id = %s"
        params.append(int(student_id))

    if status and status != 'All':
        query += " AND a.status = %s"
        count_query += " AND a.status = %s"
        params.append(status)

    if search:
        search_term = f"%{search.strip()}%"
        clause = " AND (s.name LIKE %s OR s.regno LIKE %s)"
        query += clause
        count_query += clause
        params.extend([search_term, search_term])

    total_res = fetch_one(count_query, tuple(params))
    total_count = total_res['total'] if total_res else 0

    query += " ORDER BY a.date DESC, s.regno ASC LIMIT %s OFFSET %s"
    offset = max(0, (page - 1) * limit)
    p_params = list(params) + [limit, offset]

    records = fetch_all(query, tuple(p_params)) or []
    # Format date strings for JSON
    for r in records:
        if isinstance(r.get('date'), datetime) or hasattr(r.get('date'), 'strftime'):
            r['date'] = r['date'].strftime('%Y-%m-%d')

    return {
        'records': records,
        'total': total_count,
        'page': page,
        'limit': limit,
        'total_pages': (total_count + limit - 1) // limit if limit > 0 else 1
    }


def add_attendance(data, actor_name="HOD", actor_id=None):
    """Marks attendance for a student on a specific date (inserts or updates)."""
    student_id = data.get('student_id')
    date_val = str(data.get('date', datetime.today().strftime('%Y-%m-%d'))).strip()
    status_val = str(data.get('status', 'Present')).capitalize()
    subject_id = data.get('subject_id')

    if not student_id:
        raise ValueError("Student ID is required.")
    if status_val not in ('Present', 'Absent'):
        raise ValueError("Status must be 'Present' or 'Absent'.")

    subject_id = int(subject_id) if subject_id and str(subject_id).isdigit() else None

    # Use INSERT ... ON DUPLICATE KEY UPDATE to support re-marking or new marking
    execute("""
        INSERT INTO attendance (student_id, date, status, subject_id)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE status = VALUES(status), subject_id = VALUES(subject_id)
    """, (int(student_id), date_val, status_val, subject_id))

    return {'success': True, 'student_id': student_id, 'date': date_val, 'status': status_val}


def update_attendance(attendance_id, data, actor_name="HOD", actor_id=None):
    """Updates an attendance entry."""
    att = fetch_one("SELECT * FROM attendance WHERE id = %s", (attendance_id,))
    if not att:
        raise ValueError("Attendance entry not found.")

    status_val = str(data.get('status', att['status'])).capitalize()
    date_val = str(data.get('date', att['date']))
    if status_val not in ('Present', 'Absent'):
        raise ValueError("Status must be 'Present' or 'Absent'.")

    execute("""
        UPDATE attendance SET status = %s, date = %s WHERE id = %s
    """, (status_val, date_val, attendance_id))

    log_erp_audit('attendance', attendance_id, 'UPDATE', old_value=att['status'], new_value=status_val, user_id=actor_id, user_name=actor_name)
    return {'id': attendance_id, 'status': status_val}


def delete_attendance(attendance_id, actor_name="HOD", actor_id=None):
    """Deletes an attendance entry."""
    execute("DELETE FROM attendance WHERE id = %s", (attendance_id,))
    log_erp_audit('attendance', attendance_id, 'DELETE', user_id=actor_id, user_name=actor_name)
    return True


# ==============================================================================
# 5. INTERNAL MARKS MANAGEMENT CRUD
# ==============================================================================

def get_marks_records(student_id=None, subject_id=None, test_number=None, search=None, page=1, limit=50):
    """Fetches internal marks with subject and student joins."""
    query = """
        SELECT 
            m.id, m.student_id, m.subject_id, m.test_number, m.marks_obtained, m.max_marks,
            ROUND((m.marks_obtained / NULLIF(m.max_marks, 0)) * 100.0, 1) as percentage,
            CASE WHEN (m.marks_obtained / NULLIF(m.max_marks, 0)) * 100.0 >= 50.0 THEN 'Pass' ELSE 'Fail' END as status,
            s.regno, s.name as student_name, s.department, s.year,
            sub.subject_code, sub.subject_name
        FROM internal_marks m
        JOIN students s ON m.student_id = s.studentid
        JOIN subjects sub ON m.subject_id = sub.subjectid
        WHERE 1=1
    """
    count_query = """
        SELECT COUNT(*) as total
        FROM internal_marks m
        JOIN students s ON m.student_id = s.studentid
        JOIN subjects sub ON m.subject_id = sub.subjectid
        WHERE 1=1
    """
    params = []

    if student_id:
        query += " AND m.student_id = %s"
        count_query += " AND m.student_id = %s"
        params.append(int(student_id))

    if subject_id:
        query += " AND m.subject_id = %s"
        count_query += " AND m.subject_id = %s"
        params.append(int(subject_id))

    if test_number and str(test_number) != 'All':
        query += " AND m.test_number = %s"
        count_query += " AND m.test_number = %s"
        params.append(int(test_number))

    if search:
        search_term = f"%{search.strip()}%"
        clause = " AND (s.name LIKE %s OR s.regno LIKE %s OR sub.subject_name LIKE %s)"
        query += clause
        count_query += clause
        params.extend([search_term, search_term, search_term])

    total_res = fetch_one(count_query, tuple(params))
    total_count = total_res['total'] if total_res else 0

    query += " ORDER BY sub.subject_name ASC, s.regno ASC, m.test_number ASC LIMIT %s OFFSET %s"
    offset = max(0, (page - 1) * limit)
    p_params = list(params) + [limit, offset]

    records = fetch_all(query, tuple(p_params)) or []
    return {
        'records': records,
        'total': total_count,
        'page': page,
        'limit': limit,
        'total_pages': (total_count + limit - 1) // limit if limit > 0 else 1
    }


def add_mark(data, actor_name="HOD", actor_id=None):
    """Enters internal assessment mark for a student."""
    student_id = int(data.get('student_id', 0))
    subject_id = int(data.get('subject_id', 0))
    test_number = int(data.get('test_number', 1))
    marks_obtained = float(data.get('marks_obtained', 0.0))
    max_marks = float(data.get('max_marks', 100.0))

    if student_id <= 0:
        raise ValueError("Please select a student.")
    if subject_id <= 0:
        raise ValueError("Please select a subject.")
    if marks_obtained < 0 or marks_obtained > max_marks:
        raise ValueError(f"Marks obtained must be between 0 and {max_marks}.")

    # Check if mark entry already exists for this student, subject, and test
    existing = fetch_one("""
        SELECT id FROM internal_marks 
        WHERE student_id = %s AND subject_id = %s AND test_number = %s
    """, (student_id, subject_id, test_number))

    if existing:
        # Update existing
        execute("""
            UPDATE internal_marks 
            SET marks_obtained = %s, max_marks = %s
            WHERE id = %s
        """, (marks_obtained, max_marks, existing['id']))
        mark_id = existing['id']
    else:
        execute("""
            INSERT INTO internal_marks (student_id, subject_id, test_number, marks_obtained, max_marks)
            VALUES (%s, %s, %s, %s, %s)
        """, (student_id, subject_id, test_number, marks_obtained, max_marks))
        new_rec = fetch_one("SELECT LAST_INSERT_ID() as last_id")
        mark_id = new_rec['last_id'] if new_rec else 1

    log_erp_audit('internal_marks', mark_id, 'CREATE_OR_UPDATE', new_value=f"{marks_obtained}/{max_marks}", user_id=actor_id, user_name=actor_name)
    return {'id': mark_id, 'marks_obtained': marks_obtained, 'max_marks': max_marks}


def update_mark(mark_id, data, actor_name="HOD", actor_id=None):
    """Updates marks entry."""
    mark = fetch_one("SELECT * FROM internal_marks WHERE id = %s", (mark_id,))
    if not mark:
        raise ValueError("Mark record not found.")

    marks_obtained = float(data.get('marks_obtained', mark['marks_obtained']))
    max_marks = float(data.get('max_marks', mark['max_marks']))
    test_number = int(data.get('test_number', mark['test_number']))

    if marks_obtained < 0 or marks_obtained > max_marks:
        raise ValueError(f"Marks obtained must be between 0 and {max_marks}.")

    execute("""
        UPDATE internal_marks 
        SET marks_obtained = %s, max_marks = %s, test_number = %s
        WHERE id = %s
    """, (marks_obtained, max_marks, test_number, mark_id))

    log_erp_audit('internal_marks', mark_id, 'UPDATE', old_value=str(mark['marks_obtained']), new_value=str(marks_obtained), user_id=actor_id, user_name=actor_name)
    return {'id': mark_id, 'marks_obtained': marks_obtained, 'max_marks': max_marks}


def delete_mark(mark_id, actor_name="HOD", actor_id=None):
    """Deletes an internal marks entry."""
    execute("DELETE FROM internal_marks WHERE id = %s", (mark_id,))
    log_erp_audit('internal_marks', mark_id, 'DELETE', user_id=actor_id, user_name=actor_name)
    return True


# ==============================================================================
# 6. TIMETABLE MANAGEMENT CRUD
# ==============================================================================

DAYS_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

def get_timetable_grid(year="Third year", section="A"):
    """Fetches the complete weekly timetable matrix for the selected year and section."""
    query = """
        SELECT 
            t.id, t.day_of_week, t.period_number, t.time_slot, t.subject_code, t.staff_id, 
            t.classroom, t.year, t.section,
            sub.subject_name,
            st.name as staff_name
        FROM timetable t
        LEFT JOIN subjects sub ON t.subject_code = sub.subject_code
        LEFT JOIN staff st ON t.staff_id = st.staffid
        WHERE t.year = %s AND (t.section = %s OR t.section IS NULL)
        ORDER BY FIELD(t.day_of_week, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'), t.period_number ASC
    """
    rows = fetch_all(query, (year, section)) or []

    # Default time slots
    default_slots = {
        1: '09:00 - 09:50 AM',
        2: '09:50 - 10:40 AM',
        3: '11:00 - 11:50 AM',
        4: '11:50 - 12:40 PM',
        5: '01:30 - 02:20 PM',
        6: '02:20 - 03:10 PM',
        7: '03:10 - 04:00 PM'
    }

    grid = {day: {p: None for p in range(1, 8)} for day in DAYS_ORDER}

    for r in rows:
        d = r['day_of_week']
        p = r['period_number']
        if d in grid and p in grid[d]:
            grid[d][p] = {
                'id': r['id'],
                'subject_code': r['subject_code'],
                'subject_name': r['subject_name'] or r['subject_code'],
                'staff_name': r['staff_name'] or 'Faculty',
                'classroom': r['classroom'] or 'Lab / Hall',
                'time_slot': r['time_slot'] or default_slots.get(p, '')
            }

    return {'grid': grid, 'days': DAYS_ORDER, 'periods': list(range(1, 8)), 'slots': default_slots}


def add_timetable_entry(data, actor_name="HOD", actor_id=None):
    """Adds a new scheduled period to the timetable."""
    day = str(data.get('day_of_week', 'Monday')).capitalize()
    period = int(data.get('period_number', 1))
    time_slot = str(data.get('time_slot', '')).strip()
    subject_code = str(data.get('subject_code', '')).strip().upper()
    staff_id = data.get('staff_id')
    classroom = str(data.get('classroom', 'LH-201')).strip()
    year = str(data.get('year', 'Third year')).strip()
    section = str(data.get('section', 'A')).strip().upper()

    if day not in DAYS_ORDER:
        raise ValueError("Invalid day of week.")
    if period < 1 or period > 8:
        raise ValueError("Period number must be between 1 and 8.")
    if not subject_code:
        raise ValueError("Subject Code is required.")

    staff_id = int(staff_id) if staff_id and str(staff_id).isdigit() else None

    # Check conflict
    conflict = fetch_one("""
        SELECT id FROM timetable 
        WHERE day_of_week = %s AND period_number = %s AND year = %s AND section = %s
    """, (day, period, year, section))

    if conflict:
        # Overwrite/update existing slot
        execute("""
            UPDATE timetable 
            SET subject_code = %s, staff_id = %s, classroom = %s, time_slot = %s
            WHERE id = %s
        """, (subject_code, staff_id, classroom, time_slot, conflict['id']))
        entry_id = conflict['id']
    else:
        execute("""
            INSERT INTO timetable (day_of_week, period_number, time_slot, subject_code, staff_id, classroom, year, section)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (day, period, time_slot, subject_code, staff_id, classroom, year, section))
        new_res = fetch_one("SELECT LAST_INSERT_ID() as last_id")
        entry_id = new_res['last_id'] if new_res else 1

    log_erp_audit('timetable', entry_id, 'CREATE_OR_UPDATE', new_value=f"{day} P{period} {subject_code}", user_id=actor_id, user_name=actor_name)
    return {'id': entry_id, 'day_of_week': day, 'period_number': period}


def delete_timetable_entry(entry_id, actor_name="HOD", actor_id=None):
    """Deletes a timetable schedule entry."""
    execute("DELETE FROM timetable WHERE id = %s", (entry_id,))
    log_erp_audit('timetable', entry_id, 'DELETE', user_id=actor_id, user_name=actor_name)
    return True
