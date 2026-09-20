import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config.database import execute_query

def get_user_by_username(username):
    query = """
    SELECT u.*, s.name as student_name, st.name as staff_name 
    FROM users u
    LEFT JOIN students s ON u.student_id = s.studentid
    LEFT JOIN staff st ON u.staff_id = st.staffid
    WHERE u.username = %s
    """
    return execute_query(query, (username,), fetchone=True)

def get_all_students(year_filter=None, semester_filter=None, subject_filter=None, search=None, subject_ids=None):
    """
    Fetches list of students with calculated attendance %, average marks %, and at-risk status.
    Uses fast SQL aggregations matching the accurate attendance and internal_marks schemas.
    """
    query = """
    SELECT 
        s.studentid, s.regno, s.name, s.department, s.year, s.email,
        0.0 as CGPA,
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
    
    if year_filter and year_filter != 'All':
        query += " AND s.year = %s"
        params.append(year_filter)
        
    if search:
        query += " AND (s.name LIKE %s OR s.regno LIKE %s)"
        params.append(f"%{search}%")
        params.append(f"%{search}%")
        
    if subject_filter and subject_filter != 'All':
        query += " AND s.studentid IN (SELECT DISTINCT student_id FROM internal_marks WHERE subject_id = %s)"
        params.append(subject_filter)

    if subject_ids:
        placeholders = ','.join(['%s'] * len(subject_ids))
        query += f" AND s.studentid IN (SELECT DISTINCT student_id FROM internal_marks WHERE subject_id IN ({placeholders}))"
        params.extend(subject_ids)

    query += " ORDER BY s.regno ASC"
    
    students = execute_query(query, tuple(params), fetchall=True) or []
    
    # Calculate At-Risk Status (Attendance < 75% OR Avg Marks < 50)
    for student in students:
        att_pct = float(student['attendance_percentage'] or 0.0)
        avg_m = float(student['avg_marks'] or 0.0)
        if att_pct < 75.0 or avg_m < 50.0:
            student['at_risk'] = True
            student['status'] = 'At Risk'
        else:
            student['at_risk'] = False
            student['status'] = 'Normal'
            
    return students

def get_student_details(student_id):
    """
    Returns full profile and subject-wise metrics for a single student.
    """
    student_query = "SELECT * FROM students WHERE studentid = %s"
    student = execute_query(student_query, (student_id,), fetchone=True)
    if not student:
        return None

    # Attendance overall
    att_query = """
    SELECT 
        COUNT(*) as total_days,
        SUM(CASE WHEN LOWER(status) = 'present' THEN 1 ELSE 0 END) as present_days,
        SUM(CASE WHEN LOWER(status) = 'absent' THEN 1 ELSE 0 END) as absent_days,
        ROUND((SUM(CASE WHEN LOWER(status) = 'present' THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(*), 0)) * 100.0, 1) as attendance_percentage
    FROM attendance WHERE student_id = %s
    """
    att = execute_query(att_query, (student_id,), fetchone=True) or {}
    
    # Subject-wise marks & test trend
    marks_query = """
    SELECT 
        m.id, m.subject_id, m.test_number, m.marks_obtained, m.max_marks,
        sub.subject_code, sub.subject_name, sub.semester,
        st.name as staff_name
    FROM internal_marks m
    JOIN subjects sub ON m.subject_id = sub.subjectid
    LEFT JOIN staff st ON sub.staff_id = st.staffid
    WHERE m.student_id = %s
    ORDER BY sub.subject_name, m.test_number
    """
    marks_rows = execute_query(marks_query, (student_id,), fetchall=True) or []

    # Aggregate marks by subject
    subjects_summary = {}
    test_trend = {}
    
    for row in marks_rows:
        sub_name = row['subject_name']
        test_num = f"Test {row['test_number']}"
        marks_obt = float(row['marks_obtained'] or 0.0)
        max_m = float(row['max_marks'] or 100.0)
        score_pct = round((marks_obt / max_m) * 100.0, 1) if max_m > 0 else 0.0
        
        if sub_name not in subjects_summary:
            subjects_summary[sub_name] = {
                'subject_id': row['subject_id'],
                'subject_code': row['subject_code'],
                'subject_name': sub_name,
                'semester': row['semester'],
                'staff_name': row['staff_name'],
                'marks_obtained': marks_obt,
                'max_marks': max_m,
                'percentage': score_pct,
                'status': 'Pass' if score_pct >= 50 else 'Fail'
            }
        else:
            subjects_summary[sub_name]['marks_obtained'] = (subjects_summary[sub_name]['marks_obtained'] + marks_obt) / 2.0
            subjects_summary[sub_name]['percentage'] = round((subjects_summary[sub_name]['marks_obtained'] / max_m) * 100.0, 1)
            subjects_summary[sub_name]['status'] = 'Pass' if subjects_summary[sub_name]['percentage'] >= 50 else 'Fail'
            
        if test_num not in test_trend:
            test_trend[test_num] = []
        test_trend[test_num].append(score_pct)

    # Subject attendance set to overall student attendance percentage
    subject_list = list(subjects_summary.values())
    overall_att_pct = float(att.get('attendance_percentage', 0.0) or 0.0)
    
    for sub in subject_list:
        sub['attendance_pct'] = overall_att_pct

    marks_list = [s['percentage'] for s in subject_list]
    passed_count = sum(1 for s in subject_list if s['status'] == 'Pass')
    failed_count = sum(1 for s in subject_list if s['status'] == 'Fail')
    
    test_trend_avg = {k: round(sum(v)/len(v), 1) for k, v in test_trend.items() if len(v) > 0}

    return {
        'profile': student,
        'attendance': att,
        'subjects': subject_list,
        'passed_subjects': passed_count,
        'failed_subjects': failed_count,
        'overall_average': round(sum(marks_list)/len(marks_list), 1) if marks_list else 0.0,
        'highest_mark': max(marks_list) if marks_list else 0.0,
        'lowest_mark': min(marks_list) if marks_list else 0.0,
        'test_trend': test_trend_avg
    }

def get_all_subjects():
    query = """
    SELECT sub.*, st.name as staff_name 
    FROM subjects sub
    LEFT JOIN staff st ON sub.staff_id = st.staffid
    ORDER BY sub.semester, sub.subject_name
    """
    return execute_query(query, fetchall=True) or []

def get_staff_subjects(staff_id):
    query = """
    SELECT sub.*, st.name as staff_name
    FROM subjects sub
    JOIN staff st ON sub.staff_id = st.staffid
    WHERE sub.staff_id = %s
    """
    return execute_query(query, (staff_id,), fetchall=True) or []

def get_subject_details(subject_id):
    query = """
    SELECT sub.*, st.name as staff_name
    FROM subjects sub
    LEFT JOIN staff st ON sub.staff_id = st.staffid
    WHERE sub.subjectid = %s
    """
    subject = execute_query(query, (subject_id,), fetchone=True)
    if not subject:
        return None

    marks_query = """
    SELECT 
        s.studentid, s.regno, s.name,
        m.marks_obtained, m.max_marks, m.test_number,
        ROUND((m.marks_obtained / NULLIF(m.max_marks, 0)) * 100.0, 1) as percentage,
        COALESCE(att.att_pct, 85.0) as attendance_pct
    FROM internal_marks m
    JOIN students s ON m.student_id = s.studentid
    LEFT JOIN (
        SELECT student_id, ROUND((SUM(CASE WHEN LOWER(status) = 'present' THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(*), 0)) * 100.0, 1) as att_pct
        FROM attendance
        GROUP BY student_id
    ) att ON s.studentid = att.student_id
    WHERE m.subject_id = %s
    ORDER BY s.regno
    """
    students_marks = execute_query(marks_query, (subject_id,), fetchall=True) or []
    
    total_students = len(students_marks)
    marks_list = [float(s['percentage'] or 0.0) for s in students_marks]
    att_list = [float(s['attendance_pct'] or 0.0) for s in students_marks]
    
    avg_marks = round(sum(marks_list)/total_students, 1) if total_students > 0 else 0.0
    avg_att = round(sum(att_list)/total_students, 1) if total_students > 0 else 0.0
    
    passed_count = sum(1 for m in marks_list if m >= 50.0)
    failed_count = total_students - passed_count
    pass_pct = round((passed_count / total_students) * 100.0, 1) if total_students > 0 else 0.0
    fail_pct = round(100.0 - pass_pct, 1)

    return {
        'subject': subject,
        'total_students': total_students,
        'average_marks': avg_marks,
        'average_attendance': avg_att,
        'pass_percentage': pass_pct,
        'fail_percentage': fail_pct,
        'passed_count': passed_count,
        'failed_count': failed_count,
        'student_marks': students_marks
    }
