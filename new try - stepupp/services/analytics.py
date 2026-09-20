import os
import sys
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config.database import execute_query

def calculate_department_analytics():
    """
    Computes complete Information Technology Department academic & attendance analytics using Pandas.
    """
    # 1. Fetch Students
    students_query = "SELECT studentid, regno, name, department, year, email FROM students"
    students_df = pd.DataFrame(execute_query(students_query, fetchall=True) or [])
    
    # 2. Fetch Staff
    staff_query = "SELECT staffid, name, subjects FROM staff"
    staff_df = pd.DataFrame(execute_query(staff_query, fetchall=True) or [])

    # 3. Fetch Subjects
    subjects_query = "SELECT subject_code, subject_name, semester, staff_id, subjectid FROM subjects"
    subjects_df = pd.DataFrame(execute_query(subjects_query, fetchall=True) or [])

    # 4. Fetch Attendance
    att_query = "SELECT id, student_id, present, absent FROM attendance"
    att_df = pd.DataFrame(execute_query(att_query, fetchall=True) or [])

    # 5. Fetch Marks
    marks_query = "SELECT id, student_id, subject_id, test_number, marks_obtained, max_marks FROM internal_marks"
    marks_df = pd.DataFrame(execute_query(marks_query, fetchall=True) or [])

    if students_df.empty:
        return {}

    # Total counts
    total_students = len(students_df)
    total_staff = len(staff_df)
    total_subjects = len(subjects_df)

    # Attendance Aggregations
    if not att_df.empty:
        att_df['total_days'] = att_df['present'] + att_df['absent']
        att_df['present_days'] = att_df['present']
        att_df['attendance_pct'] = np.where(att_df['total_days'] > 0, (att_df['present_days'] / att_df['total_days']) * 100.0, 0.0)
        att_agg = att_df[['student_id', 'total_days', 'present_days', 'attendance_pct']]
    else:
        att_agg = pd.DataFrame(columns=['student_id', 'total_days', 'present_days', 'attendance_pct'])

    # Marks Aggregations
    if not marks_df.empty:
        marks_df['marks_obtained'] = pd.to_numeric(marks_df['marks_obtained'], errors='coerce').fillna(0.0)
        marks_df['max_marks'] = pd.to_numeric(marks_df['max_marks'], errors='coerce').replace(0, np.nan).fillna(100.0)
        marks_df['pct'] = (marks_df['marks_obtained'] / marks_df['max_marks']) * 100.0
        
        marks_agg = marks_df.groupby('student_id').agg(
            avg_marks=('pct', 'mean'),
            passed_subjects=('pct', lambda x: (x >= 50.0).sum()),
            failed_subjects=('pct', lambda x: (x < 50.0).sum())
        ).reset_index()
    else:
        marks_agg = pd.DataFrame(columns=['student_id', 'avg_marks', 'passed_subjects', 'failed_subjects'])

    # Merge student summary
    merged_df = students_df.merge(att_agg, left_on='studentid', right_on='student_id', how='left')
    merged_df = merged_df.merge(marks_agg, on='student_id', how='left')
    
    merged_df['attendance_pct'] = merged_df['attendance_pct'].fillna(0.0).round(1)
    merged_df['avg_marks'] = merged_df['avg_marks'].fillna(0.0).round(1)
    
    # Classify At-Risk (Attendance < 75% or Avg Marks < 50%)
    merged_df['is_at_risk'] = (merged_df['attendance_pct'] < 75.0) | (merged_df['avg_marks'] < 50.0)

    # Attendance breakdown categories
    below_75 = (merged_df['attendance_pct'] < 75.0).sum()
    between_75_85 = ((merged_df['attendance_pct'] >= 75.0) & (merged_df['attendance_pct'] <= 85.0)).sum()
    above_85 = (merged_df['attendance_pct'] > 85.0).sum()
    above_75 = total_students - below_75

    avg_dept_attendance = round(float(merged_df['attendance_pct'].mean()), 1) if total_students > 0 else 0.0
    avg_dept_marks = round(float(merged_df['avg_marks'].mean()), 1) if total_students > 0 else 0.0

    at_risk_count = int(merged_df['is_at_risk'].sum())
    passed_students = (merged_df['avg_marks'] >= 50.0).sum()
    overall_pass_pct = round((passed_students / total_students) * 100.0, 1) if total_students > 0 else 0.0

    # Subject-wise Performance Metrics
    subject_analytics = []
    if not marks_df.empty and not subjects_df.empty:
        sub_merged = marks_df.merge(subjects_df, left_on='subject_id', right_on='subjectid', how='inner')
        sub_summary = sub_merged.groupby(['subjectid', 'subject_name', 'subject_code', 'semester']).agg(
            avg_score=('pct', 'mean'),
            pass_rate=('pct', lambda x: ((x >= 50.0).sum() / len(x)) * 100.0),
            total_evals=('pct', 'count')
        ).reset_index()

        for _, row in sub_summary.iterrows():
            subject_analytics.append({
                'subject_id': int(row['subjectid']),
                'subject_code': row['subject_code'],
                'subject_name': row['subject_name'],
                'semester': int(row['semester']),
                'avg_marks': round(float(row['avg_score']), 1),
                'pass_percentage': round(float(row['pass_rate']), 1)
            })

    # Year / Semester-wise performance
    semester_analytics = []
    if not marks_df.empty and not subjects_df.empty:
        sem_merged = marks_df.merge(subjects_df, left_on='subject_id', right_on='subjectid', how='inner')
        sem_summary = sem_merged.groupby('semester').agg(
            avg_marks=('pct', 'mean'),
            pass_pct=('pct', lambda x: ((x >= 50.0).sum() / len(x)) * 100.0)
        ).reset_index()

        for _, row in sem_summary.iterrows():
            semester_analytics.append({
                'semester': int(row['semester']),
                'avg_marks': round(float(row['avg_marks']), 1),
                'pass_percentage': round(float(row['pass_pct']), 1)
            })

    # Top performing students
    top_students = merged_df.sort_values(by='avg_marks', ascending=False).head(5).to_dict(orient='records')
    # At-risk students list
    at_risk_students = merged_df[merged_df['is_at_risk']].sort_values(by='avg_marks', ascending=True).head(10).to_dict(orient='records')

    # Dynamic Insights Generation
    insights = []
    if subject_analytics:
        lowest_sub = min(subject_analytics, key=lambda x: x['avg_marks'])
        highest_sub = max(subject_analytics, key=lambda x: x['avg_marks'])
        insights.append(f"📊 <strong>{lowest_sub['subject_name']}</strong> has the lowest average performance ({lowest_sub['avg_marks']}%).")
        insights.append(f"🏆 <strong>{highest_sub['subject_name']}</strong> achieved the highest average marks ({highest_sub['avg_marks']}%).")

    if below_75 > 0:
        insights.append(f"⚠️ <strong>{below_75} students</strong> currently have attendance below 75% cutoff threshold.")

    if at_risk_count > 0:
        insights.append(f"🚨 <strong>{at_risk_count} students</strong> are classified as 'At Risk' and need academic intervention.")
    else:
        insights.append("✅ All students are performing above the minimum risk criteria.")

    insights.append(f"📈 Department Overall Pass Percentage stands at <strong>{overall_pass_pct}%</strong> across {total_students} enrolled students.")

    return {
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
            'at_risk_students': at_risk_count,
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
        'at_risk_list': at_risk_students,
        'insights': insights
    }
