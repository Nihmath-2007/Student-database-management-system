"""
<<<<<<< HEAD
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
=======
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
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
        params.append(department)

    if year and year != 'All':
        query += " AND s.year = %s"
<<<<<<< HEAD
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
=======
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
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
    existing = fetch_one("SELECT studentid FROM students WHERE regno = %s", (regno,))
    if existing:
        raise ValueError(f"Student with Register Number '{regno}' already exists.")

    # Determine next studentid
<<<<<<< HEAD
    max_id_row = fetch_one("SELECT MAX(studentid) as m FROM students")
    next_id = (max_id_row['m'] or 0) + 1 if max_id_row else 1
=======
    max_id_res = fetch_one("SELECT MAX(studentid) as max_id FROM students")
    new_id = (max_id_res['max_id'] or 0) + 1 if max_id_res else 1
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1

    execute("""
        INSERT INTO students (studentid, regno, name, department, year, section, email, phone)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
<<<<<<< HEAD
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
=======
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
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
        SET regno = %s, name = %s, department = %s, year = %s, section = %s, email = %s, phone = %s
        WHERE studentid = %s
    """, (regno, name, department, year, section, email, phone, student_id))

<<<<<<< HEAD
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
=======
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
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
    try:
        execute("DELETE FROM mark_correction_requests WHERE student_id = %s", (student_id,))
    except Exception:
        pass

<<<<<<< HEAD
    # 2. Delete attendance
    try:
        execute("DELETE FROM attendance WHERE student_id = %s", (student_id,))
    except Exception:
        pass

    # 3. Delete internal marks
=======
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
    try:
        execute("DELETE FROM internal_marks WHERE student_id = %s", (student_id,))
    except Exception:
        pass

<<<<<<< HEAD
    # 4. Delete user login
=======
    try:
        execute("DELETE FROM attendance WHERE student_id = %s", (student_id,))
    except Exception:
        pass

>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
    try:
        execute("DELETE FROM users WHERE student_id = %s", (student_id,))
    except Exception:
        pass

<<<<<<< HEAD
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
=======
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
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1

    if not name:
        raise ValueError("Faculty name is required.")

<<<<<<< HEAD
    max_id_row = fetch_one("SELECT MAX(staffid) as m FROM staff")
    next_id = (max_id_row['m'] or 0) + 1 if max_id_row else 1
=======
    max_id_res = fetch_one("SELECT MAX(staffid) as max_id FROM staff")
    new_id = (max_id_res['max_id'] or 0) + 1 if max_id_res else 1
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1

    execute("""
        INSERT INTO staff (staffid, name, subjects, department, email, phone, designation)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
<<<<<<< HEAD
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
=======
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
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
    try:
        execute("UPDATE timetable SET staff_id = NULL WHERE staff_id = %s", (staff_id,))
    except Exception:
        pass
<<<<<<< HEAD

    # 3. Delete user account
=======
    # Remove user login
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
    try:
        execute("DELETE FROM users WHERE staff_id = %s", (staff_id,))
    except Exception:
        pass

<<<<<<< HEAD
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
=======
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
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1

    if semester and semester != 'All':
        query += " AND sub.semester = %s"
        params.append(int(semester))

<<<<<<< HEAD
    query += " GROUP BY sub.subject_code, sub.subject_name, sub.semester, sub.staff_id, sub.subjectid, sub.department, st.name ORDER BY sub.semester ASC, sub.subject_code ASC"

    return fetch_all(query, tuple(params)) or []

def erp_create_subject(data, user_meta=None):
    """Creates a new subject, associates faculty, and logs audit."""
=======
    if department and department != 'All':
        query += " AND (sub.department = %s OR sub.department IS NULL)"
        params.append(department)

    query += " ORDER BY sub.semester ASC, sub.subject_code ASC"
    return fetch_all(query, tuple(params)) or []


def add_subject(data, actor_name="HOD", actor_id=None):
    """Creates a new subject and maps semester & faculty."""
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
    code = str(data.get('subject_code', '')).strip().upper()
    name = str(data.get('subject_name', '')).strip()
    semester = int(data.get('semester', 5))
    staff_id = data.get('staff_id')
    department = str(data.get('department', 'Information Technology')).strip()

<<<<<<< HEAD
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
=======
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
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1

    execute("""
        INSERT INTO subjects (subject_code, subject_name, semester, staff_id, subjectid, department)
        VALUES (%s, %s, %s, %s, %s, %s)
<<<<<<< HEAD
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
=======
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

>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
    try:
        execute("DELETE FROM timetable WHERE subject_code = %s", (subject_code,))
    except Exception:
        pass

<<<<<<< HEAD
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
=======
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
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
    """
    params = []

    if student_id:
        query += " AND m.student_id = %s"
<<<<<<< HEAD
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
=======
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
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
        WHERE student_id = %s AND subject_id = %s AND test_number = %s
    """, (student_id, subject_id, test_number))

    if existing:
<<<<<<< HEAD
        execute("""
            UPDATE internal_marks
=======
        # Update existing
        execute("""
            UPDATE internal_marks 
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
            SET marks_obtained = %s, max_marks = %s
            WHERE id = %s
        """, (marks_obtained, max_marks, existing['id']))
        mark_id = existing['id']
<<<<<<< HEAD
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
=======
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
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1

    if marks_obtained < 0 or marks_obtained > max_marks:
        raise ValueError(f"Marks obtained must be between 0 and {max_marks}.")

    execute("""
<<<<<<< HEAD
        UPDATE internal_marks
=======
        UPDATE internal_marks 
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
        SET marks_obtained = %s, max_marks = %s, test_number = %s
        WHERE id = %s
    """, (marks_obtained, max_marks, test_number, mark_id))

<<<<<<< HEAD
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
=======
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
>>>>>>> 64facb2054844e04b8271f84d38f7e0146e7f6f1
