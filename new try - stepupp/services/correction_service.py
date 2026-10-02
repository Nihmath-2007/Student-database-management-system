import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config.database import get_db_connection, execute_query, fetch_all, fetch_one, execute

# SLA Threshold in hours for a query to be flagged as "Open Too Long"
SLA_OVERDUE_HOURS = 48


def init_correction_tables():
    """
    Ensures 'mark_correction_requests' and 'audit_log' tables exist in either SQLite or MySQL.
    """
    conn, engine = get_db_connection()
    try:
        cursor = conn.cursor()
        if engine == 'mysql':
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS mark_correction_requests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                mark_id INT NOT NULL,
                student_id INT NOT NULL,
                subject_id INT NOT NULL,
                staff_id INT NOT NULL,
                test_number INT NOT NULL DEFAULT 1,
                current_mark DECIMAL(5,2) NOT NULL,
                max_marks DECIMAL(5,2) NOT NULL DEFAULT 100.00,
                expected_mark DECIMAL(5,2) NULL,
                reason VARCHAR(100) NOT NULL,
                student_note TEXT NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'Raised',
                staff_remarks TEXT NULL,
                approved_mark DECIMAL(5,2) NULL,
                reviewed_by INT NULL,
                reviewed_by_name VARCHAR(100) NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                resolved_at DATETIME NULL,
                INDEX idx_mcr_student (student_id),
                INDEX idx_mcr_staff (staff_id),
                INDEX idx_mcr_status (status),
                INDEX idx_mcr_mark (mark_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                table_name VARCHAR(60) NOT NULL,
                record_id INT NOT NULL,
                action VARCHAR(50) NOT NULL,
                field_name VARCHAR(60) NULL,
                old_value TEXT NULL,
                new_value TEXT NULL,
                changed_by_user_id INT NULL,
                changed_by_name VARCHAR(100) NOT NULL,
                changed_by_role VARCHAR(30) NOT NULL,
                changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                notes TEXT NULL,
                INDEX idx_audit_table_rec (table_name, record_id),
                INDEX idx_audit_changed_at (changed_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            conn.commit()
        else:
            # SQLite Table Definitions
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS mark_correction_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mark_id INT NOT NULL,
                student_id INT NOT NULL,
                subject_id INT NOT NULL,
                staff_id INT NOT NULL,
                test_number INT NOT NULL DEFAULT 1,
                current_mark REAL NOT NULL,
                max_marks REAL NOT NULL DEFAULT 100.0,
                expected_mark REAL NULL,
                reason VARCHAR(100) NOT NULL,
                student_note TEXT NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'Raised',
                staff_remarks TEXT NULL,
                approved_mark REAL NULL,
                reviewed_by INT NULL,
                reviewed_by_name VARCHAR(100) NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME NULL
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name VARCHAR(60) NOT NULL,
                record_id INT NOT NULL,
                action VARCHAR(50) NOT NULL,
                field_name VARCHAR(60) NULL,
                old_value TEXT NULL,
                new_value TEXT NULL,
                changed_by_user_id INT NULL,
                changed_by_name VARCHAR(100) NOT NULL,
                changed_by_role VARCHAR(30) NOT NULL,
                changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                notes TEXT NULL
            );
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mcr_student ON mark_correction_requests(student_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mcr_staff ON mark_correction_requests(staff_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mcr_status ON mark_correction_requests(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mcr_mark ON mark_correction_requests(mark_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_table_rec ON audit_log(table_name, record_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_changed_at ON audit_log(changed_at);")
            conn.commit()

        cursor.close()
        try:
            conn.close()
        except Exception:
            pass
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        print(f"Notice: init_correction_tables: {e}")


def seed_sample_correction_data():
    """
    Seeds realistic demonstration correction requests and audit logs if mark_correction_requests is empty.
    Creates:
    1. An overdue 'Raised' query (> 48h SLA breach) for HOD tracking.
    2. An active 'Under Review' query for staff verification.
    3. A resolved 'Approved' query showing mark update and audit trail.
    """
    try:
        cnt_row = fetch_one("SELECT COUNT(*) as cnt FROM mark_correction_requests")
        if cnt_row and cnt_row['cnt'] > 0:
            return

        from datetime import timedelta
        now = datetime.now()
        t_overdue = (now - timedelta(hours=54)).strftime('%Y-%m-%d %H:%M:%S')
        t_review = (now - timedelta(hours=22)).strftime('%Y-%m-%d %H:%M:%S')
        t_review_action = (now - timedelta(hours=20)).strftime('%Y-%m-%d %H:%M:%S')
        t_approved_create = (now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
        t_approved_resolve = (now - timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S')

        # Query 1: Overdue Raised request (Student 1, Mark 186, Subject 6, Staff 6)
        q1_id = execute("""
            INSERT INTO mark_correction_requests (
                mark_id, student_id, subject_id, staff_id, test_number,
                current_mark, max_marks, expected_mark, reason, student_note,
                status, created_at, updated_at
            ) VALUES (186, 1, 6, 6, 1, 49.0, 100.0, 55.0, 'Totaling Error',
                      'Total marks in Part B Question 12 were computed as 4 instead of 10. Actual total comes to 55.',
                      'Raised', %s, %s)
        """, (t_overdue, t_overdue))

        execute("""
            INSERT INTO audit_log (
                table_name, record_id, action, field_name, old_value, new_value,
                changed_by_user_id, changed_by_name, changed_by_role, changed_at, notes
            ) VALUES ('mark_correction_requests', %s, 'QUERY_RAISED', 'status', NULL, 'Raised',
                      8, 'ABIRAMI M (911524205001)', 'student', %s, 'Correction query submitted by student. SLA target: 48h.')
        """, (q1_id, t_overdue))

        # Query 2: Under Review request (Student 2, Mark 3, Subject 2, Staff 2)
        q2_id = execute("""
            INSERT INTO mark_correction_requests (
                mark_id, student_id, subject_id, staff_id, test_number,
                current_mark, max_marks, expected_mark, reason, student_note,
                status, reviewed_by, reviewed_by_name, created_at, updated_at
            ) VALUES (3, 2, 2, 2, 1, 80.0, 100.0, 86.0, 'Unmarked Question / Answer Not Evaluated',
                      'Question 14(b) (Derivation of Bayes Theorem) was answered on page 8 but omitted during valuation.',
                      'Under Review', 3, 'Staff - Data Science', %s, %s)
        """, (t_review, t_review_action))

        execute("""
            INSERT INTO audit_log (
                table_name, record_id, action, field_name, old_value, new_value,
                changed_by_user_id, changed_by_name, changed_by_role, changed_at, notes
            ) VALUES ('mark_correction_requests', %s, 'QUERY_RAISED', 'status', NULL, 'Raised',
                      9, 'AJAY S (911524205002)', 'student', %s, 'Student flagged unmarked answer sheet question.')
        """, (q2_id, t_review))

        execute("""
            INSERT INTO audit_log (
                table_name, record_id, action, field_name, old_value, new_value,
                changed_by_user_id, changed_by_name, changed_by_role, changed_at, notes
            ) VALUES ('mark_correction_requests', %s, 'STATUS_CHANGE', 'status', 'Raised', 'Under Review',
                      3, 'Staff - Data Science', 'staff', %s, 'Faculty retrieved physical booklet for re-verification.')
        """, (q2_id, t_review_action))

        # Query 3: Approved request (Student 3, Mark 4, Subject 2, Staff 2)
        q3_id = execute("""
            INSERT INTO mark_correction_requests (
                mark_id, student_id, subject_id, staff_id, test_number,
                current_mark, max_marks, expected_mark, approved_mark, reason, student_note,
                staff_remarks, status, reviewed_by, reviewed_by_name, created_at, updated_at, resolved_at
            ) VALUES (4, 3, 2, 2, 1, 78.0, 100.0, 86.0, 86.0, 'Incorrect Entry / Typo',
                      'Answer script front page total reflects 86/100, but portal displayed 78/100.',
                      'Verified with physical answer script from Exam Cell. Typo in portal entry confirmed and rectified.',
                      'Approved', 3, 'Staff - Data Science', %s, %s, %s)
        """, (t_approved_create, t_approved_resolve, t_approved_resolve))

        execute("""
            INSERT INTO audit_log (
                table_name, record_id, action, field_name, old_value, new_value,
                changed_by_user_id, changed_by_name, changed_by_role, changed_at, notes
            ) VALUES ('mark_correction_requests', %s, 'QUERY_RAISED', 'status', NULL, 'Raised',
                      10, 'AKASH M (911524205003)', 'student', %s, 'Student requested score entry audit.')
        """, (q3_id, t_approved_create))

        execute("""
            INSERT INTO audit_log (
                table_name, record_id, action, field_name, old_value, new_value,
                changed_by_user_id, changed_by_name, changed_by_role, changed_at, notes
            ) VALUES ('internal_marks', 4, 'MARK_CORRECTION', 'marks_obtained', '78.0', '86.0',
                      3, 'Staff - Data Science', 'staff', %s, 'Automatic mark adjustment executed upon faculty approval.')
        """, (t_approved_resolve,))

        execute("""
            INSERT INTO audit_log (
                table_name, record_id, action, field_name, old_value, new_value,
                changed_by_user_id, changed_by_name, changed_by_role, changed_at, notes
            ) VALUES ('mark_correction_requests', %s, 'QUERY_APPROVED', 'status', 'Under Review', 'Approved',
                      3, 'Staff - Data Science', 'staff', %s, 'Query successfully resolved. Mark automatically updated in system.')
        """, (q3_id, t_approved_resolve))

        print("Seeded demonstration mark correction requests and audit logs.")
    except Exception as e:
        print(f"Notice: seed_sample_correction_data: {e}")


def log_audit(table_name, record_id, action, field_name, old_value, new_value, user_id, user_name, user_role, notes=None):
    """
    Writes an immutable record to the audit_log table.
    Captures: table, record, old value, new value, who (name, role, user_id), and when (CURRENT_TIMESTAMP).
    """
    query = """
    INSERT INTO audit_log (table_name, record_id, action, field_name, old_value, new_value, changed_by_user_id, changed_by_name, changed_by_role, notes)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    execute(query, (
        table_name,
        record_id,
        action,
        field_name,
        str(old_value) if old_value is not None else None,
        str(new_value) if new_value is not None else None,
        user_id,
        user_name or 'System User',
        user_role or 'system',
        notes
    ))


def parse_datetime(val):
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    val_str = str(val).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(val_str, fmt)
        except ValueError:
            continue
    return None


def calculate_age_info(created_at_val, status):
    """
    Calculates hours and days open, formatted date, and SLA overdue flag (> 48 hours for pending queries).
    """
    dt = parse_datetime(created_at_val)
    if not dt:
        return {
            'formatted_date': str(created_at_val or 'N/A'),
            'hours_open': 0,
            'days_open': 0,
            'is_overdue': False,
            'time_badge_class': 'badge-light',
            'time_text': 'Recent'
        }

    now = datetime.now()
    diff = now - dt
    total_hours = max(0, int(diff.total_seconds() // 3600))
    total_days = max(0, int(diff.days))

    # Overdue if still pending (Raised or Under Review) and exceeded SLA threshold
    is_pending = status in ('Raised', 'Under Review')
    is_overdue = is_pending and (total_hours >= SLA_OVERDUE_HOURS)

    if total_hours < 1:
        time_text = "Just now"
    elif total_hours < 24:
        time_text = f"{total_hours}h ago"
    elif total_days == 1:
        time_text = "1 day ago"
    else:
        time_text = f"{total_days} days ago"

    if is_overdue:
        time_badge_class = "badge-sla-breach"
    elif is_pending and total_hours >= 24:
        time_badge_class = "badge-sla-warning"
    else:
        time_badge_class = "badge-sla-normal"

    return {
        'formatted_date': dt.strftime('%b %d, %Y %I:%M %p'),
        'date_only': dt.strftime('%b %d, %Y'),
        'hours_open': total_hours,
        'days_open': total_days,
        'is_overdue': is_overdue,
        'time_badge_class': time_badge_class,
        'time_text': time_text
    }


def raise_mark_correction_query(student_id, mark_id, reason, student_note, expected_mark=None, user_id=None, user_name=None):
    """
    Creates a new mark correction request initiated by a student.
    Validates ownership, checks for existing open queries, links to the subject's assigned staff,
    inserts the request, and logs the action to audit_log.
    """
    # 1. Fetch the mark record and verify student ownership
    mark_row = fetch_one("""
        SELECT m.id, m.student_id, m.subject_id, m.test_number, m.marks_obtained, m.max_marks,
               s.staff_id, s.subject_name, s.subject_code,
               st.name as staff_name
        FROM internal_marks m
        JOIN subjects s ON m.subject_id = s.subjectid
        LEFT JOIN staff st ON s.staff_id = st.staffid
        WHERE m.id = %s AND m.student_id = %s
    """, (mark_id, student_id))

    if not mark_row:
        raise ValueError("Invalid mark selection or mark does not belong to your account.")

    # 2. Check if there's already an active (Raised or Under Review) query for this mark
    existing_open = fetch_one("""
        SELECT id, status FROM mark_correction_requests
        WHERE mark_id = %s AND status IN ('Raised', 'Under Review')
    """, (mark_id,))
    if existing_open:
        raise ValueError(f"A query is already {existing_open['status']} for this mark (Request #{existing_open['id']}). Please wait for faculty review.")

    # 3. Validation on reason and note
    reason = (reason or '').strip()
    if not reason:
        raise ValueError("Please select a valid reason for the mark query.")

    student_note = (student_note or '').strip()
    if not student_note or len(student_note) < 5:
        raise ValueError("Please provide an explanatory note describing the mark issue (at least 5 characters).")

    # Clean expected_mark if provided
    exp_mark_val = None
    if expected_mark is not None and str(expected_mark).strip() != '':
        try:
            exp_mark_val = float(expected_mark)
            if exp_mark_val < 0 or exp_mark_val > float(mark_row['max_marks']):
                raise ValueError(f"Expected mark must be between 0 and {mark_row['max_marks']}.")
        except ValueError as ve:
            raise ValueError(f"Invalid expected mark value: {ve}")

    staff_id = mark_row['staff_id']
    if not staff_id:
        # Fallback if unassigned: default to staffid 1
        staff_id = 1

    current_mark = float(mark_row['marks_obtained'] or 0.0)
    max_marks = float(mark_row['max_marks'] or 100.0)
    test_number = int(mark_row['test_number'] or 1)

    # 4. Insert into mark_correction_requests
    query = """
    INSERT INTO mark_correction_requests (
        mark_id, student_id, subject_id, staff_id, test_number,
        current_mark, max_marks, expected_mark, reason, student_note, status
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Raised')
    """
    request_id = execute(query, (
        mark_id,
        student_id,
        mark_row['subject_id'],
        staff_id,
        test_number,
        current_mark,
        max_marks,
        exp_mark_val,
        reason,
        student_note
    ))

    # 5. Write to audit_log
    log_audit(
        table_name='mark_correction_requests',
        record_id=request_id,
        action='QUERY_RAISED',
        field_name='status',
        old_value=None,
        new_value='Raised',
        user_id=user_id,
        user_name=user_name or f"Student #{student_id}",
        user_role='student',
        notes=f"Query raised for {mark_row['subject_code']} Test {test_number}. Reason: {reason}. Note: {student_note}"
    )

    return request_id


def update_query_status_to_review(request_id, user_id, user_name, user_role, staff_id=None):
    """
    Transitions query status from 'Raised' to 'Under Review'.
    Ensures staff is authorized for this subject's query (or HOD).
    Logs the status transition in audit_log.
    """
    req = fetch_one("SELECT * FROM mark_correction_requests WHERE id = %s", (request_id,))
    if not req:
        raise ValueError(f"Mark correction request #{request_id} not found.")

    if req['status'] != 'Raised':
        raise ValueError(f"Request is currently '{req['status']}' and cannot be moved to 'Under Review'.")

    # Authorization check for staff
    if user_role == 'staff' and staff_id:
        if req['staff_id'] != staff_id:
            raise PermissionError("You are not authorized to review queries for subjects not assigned to you.")

    # Update status
    execute("""
        UPDATE mark_correction_requests
        SET status = 'Under Review',
            reviewed_by = %s,
            reviewed_by_name = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (user_id, user_name, request_id))

    # Log in audit_log
    log_audit(
        table_name='mark_correction_requests',
        record_id=request_id,
        action='STATUS_CHANGE',
        field_name='status',
        old_value='Raised',
        new_value='Under Review',
        user_id=user_id,
        user_name=user_name,
        user_role=user_role,
        notes="Faculty commenced verification and answer script review."
    )

    return True


def resolve_mark_correction_query(request_id, action_type, user_id, user_name, user_role, staff_id=None, remarks=None, new_mark=None):
    """
    Resolves a mark correction query:
    - If action_type == 'reject': Requires a non-empty remark ("rejecting requires a remark").
      Updates status to 'Rejected', records remark, and logs to audit_log.
    - If action_type == 'approve': Automatically updates the mark in 'internal_marks' ("approving updates the mark automatically"),
      sets status to 'Approved', records approval remark & approved mark, and writes audit logs for BOTH 'internal_marks' and 'mark_correction_requests'.
    """
    req = fetch_one("SELECT * FROM mark_correction_requests WHERE id = %s", (request_id,))
    if not req:
        raise ValueError(f"Mark correction request #{request_id} not found.")

    if req['status'] in ('Approved', 'Rejected'):
        raise ValueError(f"Request #{request_id} has already been resolved as '{req['status']}'.")

    # Authorization check
    if user_role == 'staff' and staff_id:
        if req['staff_id'] != staff_id:
            raise PermissionError("You are not authorized to resolve queries for subjects not assigned to you.")

    action_type = str(action_type or '').strip().lower()
    old_status = req['status']

    if action_type == 'reject':
        # Prompt requirement: "rejecting requires a remark"
        clean_remarks = (remarks or '').strip()
        if not clean_remarks:
            raise ValueError("Rejection remark is mandatory. Please state the academic reason why the query was not accepted.")

        execute("""
            UPDATE mark_correction_requests
            SET status = 'Rejected',
                staff_remarks = %s,
                reviewed_by = %s,
                reviewed_by_name = %s,
                resolved_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (clean_remarks, user_id, user_name, request_id))

        log_audit(
            table_name='mark_correction_requests',
            record_id=request_id,
            action='QUERY_REJECTED',
            field_name='status',
            old_value=old_status,
            new_value='Rejected',
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            notes=f"Query rejected with faculty remark: {clean_remarks}"
        )
        return {'status': 'Rejected', 'message': 'Correction query rejected with mandatory remark recorded.'}

    elif action_type == 'approve':
        # Prompt requirement: "Approving updates the mark automatically"
        if new_mark is None or str(new_mark).strip() == '':
            # If not provided, fallback to expected_mark if set, else error
            if req['expected_mark'] is not None:
                new_mark = req['expected_mark']
            else:
                raise ValueError("Please specify the corrected mark to be applied.")

        try:
            new_mark_float = round(float(new_mark), 2)
        except (ValueError, TypeError):
            raise ValueError("Corrected mark must be a valid numeric score.")

        max_allowed = float(req['max_marks'])
        if new_mark_float < 0 or new_mark_float > max_allowed:
            raise ValueError(f"Corrected mark must be between 0 and {max_allowed}.")

        # Retrieve previous mark from internal_marks
        curr_mark_record = fetch_one("SELECT marks_obtained FROM internal_marks WHERE id = %s", (req['mark_id'],))
        old_mark_obtained = float(curr_mark_record['marks_obtained']) if curr_mark_record else float(req['current_mark'])

        clean_remarks = (remarks or '').strip() or f"Mark corrected from {old_mark_obtained} to {new_mark_float} upon faculty review."

        # 1. Automatically update internal_marks
        execute("""
            UPDATE internal_marks
            SET marks_obtained = %s
            WHERE id = %s
        """, (new_mark_float, req['mark_id']))

        # 2. Update mark_correction_requests
        execute("""
            UPDATE mark_correction_requests
            SET status = 'Approved',
                approved_mark = %s,
                staff_remarks = %s,
                reviewed_by = %s,
                reviewed_by_name = %s,
                resolved_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (new_mark_float, clean_remarks, user_id, user_name, request_id))

        # 3. Log audit for internal_marks table update
        log_audit(
            table_name='internal_marks',
            record_id=req['mark_id'],
            action='MARK_CORRECTION',
            field_name='marks_obtained',
            old_value=old_mark_obtained,
            new_value=new_mark_float,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            notes=f"Auto-updated via approved Correction Request #{request_id}. Remarks: {clean_remarks}"
        )

        # 4. Log audit for mark_correction_requests table update
        log_audit(
            table_name='mark_correction_requests',
            record_id=request_id,
            action='QUERY_APPROVED',
            field_name='status',
            old_value=old_status,
            new_value='Approved',
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            notes=f"Mark changed from {old_mark_obtained} to {new_mark_float}. Remarks: {clean_remarks}"
        )

        return {
            'status': 'Approved',
            'old_mark': old_mark_obtained,
            'new_mark': new_mark_float,
            'message': f'Correction query approved! Mark automatically updated to {new_mark_float}.'
        }
    else:
        raise ValueError(f"Unknown action '{action_type}'. Must be 'approve' or 'reject'.")


def get_student_marks_with_query_status(student_id):
    """
    Fetches each internal mark for a student along with the latest correction request status.
    Enables displaying the 'Raise Query' button beside each mark, or the current status badge if already raised.
    """
    query = """
    SELECT 
        m.id as mark_id,
        m.student_id,
        m.subject_id,
        m.test_number,
        m.marks_obtained,
        m.max_marks,
        ROUND((m.marks_obtained / NULLIF(m.max_marks, 0)) * 100.0, 1) as percentage,
        sub.subject_code,
        sub.subject_name,
        sub.semester,
        COALESCE(st.name, 'Faculty') as staff_name,
        req.id as query_id,
        req.status as query_status,
        req.reason as query_reason,
        req.expected_mark as query_expected_mark,
        req.student_note as query_student_note,
        req.staff_remarks as query_staff_remarks,
        req.approved_mark as query_approved_mark,
        req.created_at as query_created_at,
        req.resolved_at as query_resolved_at
    FROM internal_marks m
    JOIN subjects sub ON m.subject_id = sub.subjectid
    LEFT JOIN staff st ON sub.staff_id = st.staffid
    LEFT JOIN (
        -- Pick the most recently created query for each mark
        SELECT r1.*
        FROM mark_correction_requests r1
        JOIN (
            SELECT mark_id, MAX(id) as max_id
            FROM mark_correction_requests
            GROUP BY mark_id
        ) r2 ON r1.id = r2.max_id
    ) req ON m.id = req.mark_id
    WHERE m.student_id = %s
    ORDER BY sub.subject_code, m.test_number
    """
    rows = fetch_all(query, (student_id,)) or []
    results = []
    for r in rows:
        row_dict = dict(r)
        row_dict['status'] = 'Pass' if float(row_dict.get('percentage') or 0.0) >= 50.0 else 'Fail'
        if row_dict.get('query_id'):
            age = calculate_age_info(row_dict['query_created_at'], row_dict['query_status'])
            row_dict['age_info'] = age
        else:
            row_dict['age_info'] = None
        results.append(row_dict)
    return results


def get_student_queries(student_id):
    """
    Fetches all mark correction requests submitted by a specific student.
    """
    query = """
    SELECT 
        req.*,
        sub.subject_code,
        sub.subject_name,
        sub.semester,
        COALESCE(st.name, 'Faculty') as staff_name,
        s.regno,
        s.name as student_name
    FROM mark_correction_requests req
    JOIN subjects sub ON req.subject_id = sub.subjectid
    LEFT JOIN staff st ON req.staff_id = st.staffid
    JOIN students s ON req.student_id = s.studentid
    WHERE req.student_id = %s
    ORDER BY req.created_at DESC
    """
    rows = fetch_all(query, (student_id,)) or []
    for r in rows:
        r['age_info'] = calculate_age_info(r['created_at'], r['status'])
        if r.get('resolved_at'):
            r['resolved_age_info'] = calculate_age_info(r['resolved_at'], r['status'])
    return rows


def get_staff_queries(staff_id, status_filter=None):
    """
    Fetches mark correction requests for subjects assigned to a given staff member.
    Includes SLA overdue calculations.
    """
    params = [staff_id]
    where_clauses = ["req.staff_id = %s"]

    if status_filter and status_filter != 'all':
        if status_filter == 'pending':
            where_clauses.append("req.status IN ('Raised', 'Under Review')")
        elif status_filter == 'overdue':
            where_clauses.append("req.status IN ('Raised', 'Under Review')")
        else:
            where_clauses.append("req.status = %s")
            params.append(status_filter)

    query = f"""
    SELECT 
        req.*,
        sub.subject_code,
        sub.subject_name,
        sub.semester,
        s.regno,
        s.name as student_name,
        s.department,
        s.year,
        st.name as staff_name
    FROM mark_correction_requests req
    JOIN subjects sub ON req.subject_id = sub.subjectid
    JOIN students s ON req.student_id = s.studentid
    LEFT JOIN staff st ON req.staff_id = st.staffid
    WHERE {' AND '.join(where_clauses)}
    ORDER BY 
        CASE 
            WHEN req.status = 'Raised' THEN 1
            WHEN req.status = 'Under Review' THEN 2
            ELSE 3
        END,
        req.created_at ASC
    """
    rows = fetch_all(query, tuple(params)) or []
    results = []
    for r in rows:
        r_dict = dict(r)
        age = calculate_age_info(r_dict['created_at'], r_dict['status'])
        r_dict['age_info'] = age
        r_dict['is_overdue'] = age['is_overdue']

        if status_filter == 'overdue' and not age['is_overdue']:
            continue
        results.append(r_dict)
    return results


def get_hod_queries(status_filter=None, staff_id=None, subject_id=None, overdue_only=False, search=None):
    """
    Fetches department-wide mark correction requests with full student, subject, and faculty details.
    Allows filtering by status, staff, subject, search query, and overdue flag.
    """
    params = []
    where_clauses = ["1=1"]

    if status_filter and status_filter != 'all':
        if status_filter == 'pending':
            where_clauses.append("req.status IN ('Raised', 'Under Review')")
        elif status_filter == 'overdue':
            where_clauses.append("req.status IN ('Raised', 'Under Review')")
        else:
            where_clauses.append("req.status = %s")
            params.append(status_filter)

    if staff_id and str(staff_id) != 'all':
        where_clauses.append("req.staff_id = %s")
        params.append(staff_id)

    if subject_id and str(subject_id) != 'all':
        where_clauses.append("req.subject_id = %s")
        params.append(subject_id)

    if search:
        where_clauses.append("(s.name LIKE %s OR s.regno LIKE %s OR sub.subject_name LIKE %s OR sub.subject_code LIKE %s)")
        q = f"%{search.strip()}%"
        params.extend([q, q, q, q])

    query = f"""
    SELECT 
        req.*,
        sub.subject_code,
        sub.subject_name,
        sub.semester,
        s.regno,
        s.name as student_name,
        s.department,
        s.year,
        COALESCE(st.name, 'Unassigned') as staff_name
    FROM mark_correction_requests req
    JOIN subjects sub ON req.subject_id = sub.subjectid
    JOIN students s ON req.student_id = s.studentid
    LEFT JOIN staff st ON req.staff_id = st.staffid
    WHERE {' AND '.join(where_clauses)}
    ORDER BY 
        CASE 
            WHEN req.status = 'Raised' THEN 1
            WHEN req.status = 'Under Review' THEN 2
            ELSE 3
        END,
        req.created_at ASC
    """
    rows = fetch_all(query, tuple(params)) or []
    results = []
    for r in rows:
        r_dict = dict(r)
        age = calculate_age_info(r_dict['created_at'], r_dict['status'])
        r_dict['age_info'] = age
        r_dict['is_overdue'] = age['is_overdue']

        if (overdue_only or status_filter == 'overdue') and not age['is_overdue']:
            continue
        results.append(r_dict)
    return results


def get_hod_summary_stats():
    """
    Returns department-level KPIs:
    - Pending counts (Raised + Under Review)
    - Requests open too long (> 48 hours SLA breach)
    - Approved counts
    - Rejected counts
    - Total queries
    - Breakdown by staff & subject
    """
    all_queries = fetch_all("""
        SELECT req.id, req.status, req.staff_id, req.subject_id, req.created_at,
               st.name as staff_name, sub.subject_code, sub.subject_name
        FROM mark_correction_requests req
        LEFT JOIN staff st ON req.staff_id = st.staffid
        JOIN subjects sub ON req.subject_id = sub.subjectid
    """) or []

    total_count = len(all_queries)
    raised_count = 0
    under_review_count = 0
    approved_count = 0
    rejected_count = 0
    overdue_count = 0

    pending_by_staff = {}
    pending_by_subject = {}

    for q in all_queries:
        st = q['status']
        if st == 'Raised':
            raised_count += 1
        elif st == 'Under Review':
            under_review_count += 1
        elif st == 'Approved':
            approved_count += 1
        elif st == 'Rejected':
            rejected_count += 1

        is_pending = st in ('Raised', 'Under Review')
        age = calculate_age_info(q['created_at'], st)
        if age['is_overdue']:
            overdue_count += 1

        if is_pending:
            staff_label = q['staff_name'] or f"Staff #{q['staff_id']}"
            pending_by_staff[staff_label] = pending_by_staff.get(staff_label, 0) + 1

            sub_label = f"{q['subject_code']} - {q['subject_name']}"
            pending_by_subject[sub_label] = pending_by_subject.get(sub_label, 0) + 1

    pending_count = raised_count + under_review_count

    return {
        'total_count': total_count,
        'pending_count': pending_count,
        'raised_count': raised_count,
        'under_review_count': under_review_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'overdue_count': overdue_count,
        'pending_by_staff': pending_by_staff,
        'pending_by_subject': pending_by_subject
    }


def get_query_details(request_id):
    """
    Returns full details for a single mark correction request.
    """
    query = """
    SELECT 
        req.*,
        sub.subject_code,
        sub.subject_name,
        sub.semester,
        s.regno,
        s.name as student_name,
        s.department,
        s.year,
        s.email as student_email,
        COALESCE(st.name, 'Unassigned') as staff_name
    FROM mark_correction_requests req
    JOIN subjects sub ON req.subject_id = sub.subjectid
    JOIN students s ON req.student_id = s.studentid
    LEFT JOIN staff st ON req.staff_id = st.staffid
    WHERE req.id = %s
    """
    row = fetch_one(query, (request_id,))
    if not row:
        return None
    res = dict(row)
    res['age_info'] = calculate_age_info(res['created_at'], res['status'])
    return res


def get_audit_trail_for_request(request_id):
    """
    Returns audit trail records for a specific request and its associated internal_marks change.
    """
    req = fetch_one("SELECT mark_id FROM mark_correction_requests WHERE id = %s", (request_id,))
    mark_id = req['mark_id'] if req else None

    if mark_id:
        query = """
        SELECT * FROM audit_log
        WHERE (table_name = 'mark_correction_requests' AND record_id = %s)
           OR (table_name = 'internal_marks' AND record_id = %s)
        ORDER BY changed_at ASC, id ASC
        """
        rows = fetch_all(query, (request_id, mark_id)) or []
    else:
        query = """
        SELECT * FROM audit_log
        WHERE table_name = 'mark_correction_requests' AND record_id = %s
        ORDER BY changed_at ASC, id ASC
        """
        rows = fetch_all(query, (request_id,)) or []

    results = []
    for r in rows:
        r_dict = dict(r)
        r_dict['age_info'] = calculate_age_info(r_dict['changed_at'], 'Logged')
        results.append(r_dict)
    return results


def get_all_audit_logs(limit=100, table_filter=None, search=None):
    """
    Fetches recent audit log entries for HOD compliance and audit view.
    """
    params = []
    where_clauses = ["1=1"]

    if table_filter and table_filter != 'all':
        where_clauses.append("table_name = %s")
        params.append(table_filter)

    if search:
        where_clauses.append("(changed_by_name LIKE %s OR notes LIKE %s OR action LIKE %s)")
        q = f"%{search.strip()}%"
        params.extend([q, q, q])

    params.append(limit)

    query = f"""
    SELECT * FROM audit_log
    WHERE {' AND '.join(where_clauses)}
    ORDER BY changed_at DESC, id DESC
    LIMIT %s
    """
    rows = fetch_all(query, tuple(params)) or []
    for r in rows:
        r['age_info'] = calculate_age_info(r['changed_at'], 'Logged')
    return rows
