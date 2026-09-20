import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config.database import execute_query

# In-memory analytics cache (TTL: 60 seconds)
_analytics_cache = {
    'data': None,
    'expires_at': 0.0
}

def invalidate_analytics_cache():
    """Flushes the cached analytics so the next request recomputes fresh metrics."""
    global _analytics_cache
    _analytics_cache['data'] = None
    _analytics_cache['expires_at'] = 0.0

def calculate_department_analytics(force_refresh=False):
    """
    Computes complete Information Technology Department academic & attendance analytics.
    Uses ultra-fast SQL aggregations and an in-memory cache for sub-millisecond response times.
    """
    global _analytics_cache
    now = time.time()
    if not force_refresh and _analytics_cache['data'] is not None and now < _analytics_cache['expires_at']:
        return _analytics_cache['data']

    # 1. Total counts
    student_count_row = execute_query("SELECT COUNT(*) as cnt FROM students", fetchone=True) or {}
    total_students = student_count_row.get('cnt', 0)

    staff_count_row = execute_query("SELECT COUNT(*) as cnt FROM staff", fetchone=True) or {}
    total_staff = staff_count_row.get('cnt', 0)

    subject_count_row = execute_query("SELECT COUNT(*) as cnt FROM subjects", fetchone=True) or {}
    total_subjects = subject_count_row.get('cnt', 0)

    if total_students == 0:
        return {}

    # 2. Student summary with attendance & marks
    student_query = """
    SELECT 
        s.studentid, s.regno, s.name, s.department, s.year, s.email,
        COALESCE(att.attendance_percentage, 0.0) as attendance_pct,
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
            ROUND((SUM(CASE WHEN LOWER(status) = 'present' THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(*), 0)) * 100.0, 1) as attendance_percentage
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
    """
    students = execute_query(student_query, fetchall=True) or []

    # Student classifications
    below_75 = 0
    between_75_85 = 0
    above_85 = 0
    at_risk_list = []

    total_att_sum = 0.0
    total_marks_sum = 0.0
    passed_students_count = 0

    for s in students:
        att = float(s['attendance_pct'] or 0.0)
        avg_m = float(s['avg_marks'] or 0.0)
        total_att_sum += att
        total_marks_sum += avg_m

        if att < 75.0:
            below_75 += 1
        elif att <= 85.0:
            between_75_85 += 1
        else:
            above_85 += 1

        is_at_risk = (att < 75.0 or avg_m < 50.0)
        s['is_at_risk'] = is_at_risk
        if is_at_risk:
            at_risk_list.append(s)
        if avg_m >= 50.0:
            passed_students_count += 1

    above_75 = total_students - below_75
    avg_dept_attendance = round(total_att_sum / total_students, 1) if total_students else 0.0
    avg_dept_marks = round(total_marks_sum / total_students, 1) if total_students else 0.0
    overall_pass_pct = round((passed_students_count / total_students) * 100.0, 1) if total_students else 0.0

    # Sort top performers & at-risk
    top_students = sorted(students, key=lambda x: float(x['avg_marks'] or 0), reverse=True)[:5]
    at_risk_sorted = sorted(at_risk_list, key=lambda x: float(x['avg_marks'] or 0))[:10]

    # 3. Subject-wise performance
    sub_query = """
    SELECT 
        s.subjectid as subject_id, s.subject_name, s.subject_code, s.semester, 
        ROUND(AVG((m.marks_obtained / NULLIF(m.max_marks, 0))*100.0), 1) as avg_marks,
        ROUND((SUM(CASE WHEN (m.marks_obtained / NULLIF(m.max_marks, 0))*100.0 >= 50 THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(*), 0))*100.0, 1) as pass_percentage
    FROM internal_marks m 
    JOIN subjects s ON m.subject_id = s.subjectid 
    GROUP BY s.subjectid
    """
    subject_analytics = execute_query(sub_query, fetchall=True) or []

    # 4. Semester-wise performance
    sem_query = """
    SELECT 
        s.semester, 
        ROUND(AVG((m.marks_obtained / NULLIF(m.max_marks, 0))*100.0), 1) as avg_marks,
        ROUND((SUM(CASE WHEN (m.marks_obtained / NULLIF(m.max_marks, 0))*100.0 >= 50 THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(*), 0))*100.0, 1) as pass_percentage
    FROM internal_marks m 
    JOIN subjects s ON m.subject_id = s.subjectid 
    GROUP BY s.semester
    """
    semester_analytics = execute_query(sem_query, fetchall=True) or []

    # 5. Dynamic Insights
    insights = []
    if subject_analytics:
        lowest_sub = min(subject_analytics, key=lambda x: float(x['avg_marks'] or 0))
        highest_sub = max(subject_analytics, key=lambda x: float(x['avg_marks'] or 0))
        insights.append(f"📊 <strong>{lowest_sub['subject_name']}</strong> has the lowest average performance ({lowest_sub['avg_marks']}%).")
        insights.append(f"🏆 <strong>{highest_sub['subject_name']}</strong> achieved the highest average marks ({highest_sub['avg_marks']}%).")

    if below_75 > 0:
        insights.append(f"⚠️ <strong>{below_75} students</strong> currently have attendance below 75% cutoff threshold.")

    if len(at_risk_list) > 0:
        insights.append(f"🚨 <strong>{len(at_risk_list)} students</strong> are classified as 'At Risk' and need academic intervention.")
    else:
        insights.append("✅ All students are performing above the minimum risk criteria.")

    insights.append(f"📈 Department Overall Pass Percentage stands at <strong>{overall_pass_pct}%</strong> across {total_students} enrolled students.")

    result = {
        'kpis': {
            'total_students': total_students,
            'total_staff': total_staff,
            'total_subjects': total_subjects,
            'avg_attendance': avg_dept_attendance,
            'avg_marks': avg_dept_marks,
            'below_75_attendance': int(below_75),
            'between_75_85_attendance': int(between_75_85),
            'above_85_attendance': int(above_85),
            'above_75_attendance': int(above_75),
            'at_risk_students': len(at_risk_list),
            'overall_pass_percentage': float(overall_pass_pct)
        },
        'attendance_distribution': {
            'below_75': int(below_75),
            'between_75_85': int(between_75_85),
            'above_85': int(above_85)
        },
        'subject_analytics': subject_analytics,
        'semester_analytics': semester_analytics,
        'top_students': top_students,
        'at_risk_list': at_risk_sorted,
        'insights': insights
    }

    # Store in memory cache for 60 seconds
    _analytics_cache['data'] = result
    _analytics_cache['expires_at'] = now + 60.0

    return result
