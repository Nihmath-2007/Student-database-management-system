import os
import sys
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config.database import execute_query

def validate_and_parse_csv(filepath):
    """
    Reads an uploaded CSV, validates rows, detects missing/duplicate/invalid data,
    and returns a preview dictionary with row-level validation status.
    """
    if not os.path.exists(filepath):
        return {'success': False, 'errors': ['Uploaded CSV file not found.']}

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        return {'success': False, 'errors': [f'Failed to parse CSV file: {str(e)}']}

    # Normalize column names to lowercase stripped
    df.columns = [str(col).strip().lower() for col in df.columns]

    col_mapping = {}
    
    # Register number
    for c in ['register_no', 'regno', 'reg_no', 'register number', 'studentid']:
        if c in df.columns:
            col_mapping['register_no'] = c
            break

    # Student Name
    for c in ['student_name', 'name', 'student name']:
        if c in df.columns:
            col_mapping['student_name'] = c
            break

    # Subject
    for c in ['subject', 'subject_name', 'subject_code']:
        if c in df.columns:
            col_mapping['subject'] = c
            break

    # Marks
    for c in ['marks', 'marks_obtained', 'mark', 'score']:
        if c in df.columns:
            col_mapping['marks'] = c
            break

    # Attendance
    for c in ['attendance', 'attendance_percentage', 'att_pct', 'attendance_pct']:
        if c in df.columns:
            col_mapping['attendance'] = c
            break

    missing_cols = []
    for req in ['register_no', 'subject', 'marks']:
        if req not in col_mapping:
            missing_cols.append(req)

    if missing_cols:
        return {
            'success': False,
            'errors': [f"Missing required columns in CSV: {', '.join(missing_cols)}. Expected columns like 'register_no', 'subject', 'marks', 'attendance'."]
        }

    # Fetch existing students and subjects from Railway MySQL
    db_students = {str(s['regno']).strip(): s['studentid'] for s in execute_query("SELECT studentid, regno FROM students", fetchall=True) or []}
    db_subjects = execute_query("SELECT subjectid, subject_code, subject_name FROM subjects", fetchall=True) or []
    
    subject_lookup = {}
    for sub in db_subjects:
        subject_lookup[str(sub['subject_code']).lower()] = sub['subjectid']
        subject_lookup[str(sub['subject_name']).lower()] = sub['subjectid']

    row_previews = []
    errors = []
    valid_rows = []
    seen_keys = set()

    for idx, row in df.iterrows():
        row_num = idx + 1
        row_errors = []
        
        regno = str(row.get(col_mapping['register_no'], '')).strip()
        sub_input = str(row.get(col_mapping['subject'], '')).strip()
        marks_input = row.get(col_mapping['marks'], None)
        att_input = row.get(col_mapping.get('attendance', ''), None)
        name_input = str(row.get(col_mapping.get('student_name', ''), '')).strip()

        # Validate Register Number
        if not regno or regno.lower() == 'nan':
            row_errors.append(f"Row {row_num}: Missing register number.")
        elif regno not in db_students:
            row_errors.append(f"Row {row_num}: Register number '{regno}' not found in students database.")

        # Validate Subject
        subject_id = None
        if not sub_input or sub_input.lower() == 'nan':
            row_errors.append(f"Row {row_num}: Missing subject.")
        else:
            subject_id = subject_lookup.get(sub_input.lower())
            if not subject_id:
                row_errors.append(f"Row {row_num}: Subject '{sub_input}' not recognized.")

        # Validate Marks
        marks_val = None
        try:
            marks_val = float(marks_input)
            if marks_val < 0 or marks_val > 100:
                row_errors.append(f"Row {row_num}: Invalid marks '{marks_val}'. Must be between 0 and 100.")
        except (ValueError, TypeError):
            row_errors.append(f"Row {row_num}: Non-numeric marks '{marks_input}'.")

        # Validate Attendance
        att_val = None
        if att_input is not None and str(att_input).lower() != 'nan':
            try:
                att_val = float(att_input)
                if att_val < 0 or att_val > 100:
                    row_errors.append(f"Row {row_num}: Invalid attendance '{att_val}%'. Must be between 0 and 100.")
            except (ValueError, TypeError):
                row_errors.append(f"Row {row_num}: Non-numeric attendance '{att_input}'.")

        # Duplicate check
        key = (regno, sub_input.lower())
        if key in seen_keys:
            row_errors.append(f"Row {row_num}: Duplicate record for student '{regno}' and subject '{sub_input}'.")
        else:
            seen_keys.add(key)

        is_valid = len(row_errors) == 0
        if is_valid:
            valid_rows.append({
                'student_id': db_students[regno],
                'subject_id': subject_id,
                'marks': marks_val,
                'max_marks': 100.0,
                'attendance': att_val,
                'regno': regno
            })
        else:
            errors.extend(row_errors)

        row_previews.append({
            'row_num': row_num,
            'regno': regno,
            'name': name_input,
            'subject': sub_input,
            'marks': marks_input,
            'attendance': att_input,
            'is_valid': is_valid,
            'errors': row_errors
        })

    return {
        'success': True,
        'total_rows': len(df),
        'valid_count': len(valid_rows),
        'invalid_count': len(df) - len(valid_rows),
        'errors': errors,
        'previews': row_previews,
        'valid_data': valid_rows
    }

from services.analytics import invalidate_analytics_cache

def process_csv_import(valid_data):
    """
    Inserts or updates internal_marks and attendance records safely matching the actual database schema.
    """
    inserted_marks = 0
    
    for row in valid_data:
        student_id = row['student_id']
        subject_id = row['subject_id']
        marks = row['marks']
        max_marks = row.get('max_marks', 100.0)
        att_val = row.get('attendance')

        # Update or insert internal_marks
        existing = execute_query(
            "SELECT id FROM internal_marks WHERE student_id = %s AND subject_id = %s AND test_number = 1",
            (student_id, subject_id),
            fetchone=True
        )

        if existing:
            execute_query(
                "UPDATE internal_marks SET marks_obtained = %s, max_marks = %s WHERE id = %s",
                (marks, max_marks, existing['id']),
                commit=True
            )
        else:
            execute_query(
                "INSERT INTO internal_marks (student_id, subject_id, test_number, marks_obtained, max_marks) VALUES (%s, %s, 1, %s, %s)",
                (student_id, subject_id, marks, max_marks),
                commit=True
            )
        inserted_marks += 1

        # Update attendance if provided
        if att_val is not None:
            try:
                target_pct = float(att_val)
                att_records = execute_query(
                    "SELECT id FROM attendance WHERE student_id = %s ORDER BY date ASC",
                    (student_id,),
                    fetchall=True
                ) or []
                
                if att_records:
                    total_days = len(att_records)
                    present_count = int(round((target_pct / 100.0) * total_days))
                    for idx, rec in enumerate(att_records):
                        status = 'Present' if idx < present_count else 'Absent'
                        execute_query(
                            "UPDATE attendance SET status = %s WHERE id = %s",
                            (status, rec['id']),
                            commit=True
                        )
            except Exception as att_err:
                print(f"Warning: Failed to update attendance for student {student_id}: {att_err}")

    # Invalidate cached analytics so changes appear immediately
    invalidate_analytics_cache()

    return {
        'success': True,
        'imported_records': inserted_marks
    }
