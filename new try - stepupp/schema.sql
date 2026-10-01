-- Subject Notes Table Schema
CREATE TABLE IF NOT EXISTS notes (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    subject_id   INT NOT NULL,
    staff_id     INT NOT NULL,
    title        VARCHAR(150) NOT NULL,
    filename     VARCHAR(255) NOT NULL,
    stored_path  VARCHAR(255) NOT NULL,
    uploaded_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(subjectid),
    FOREIGN KEY (staff_id) REFERENCES staff(staffid)
);

-- Gallery Table Schema
CREATE TABLE IF NOT EXISTS gallery (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    title         VARCHAR(150) NOT NULL,
    description   VARCHAR(500),
    event_date    DATE,
    image_path    VARCHAR(255) NOT NULL,
    uploaded_by   VARCHAR(60) DEFAULT 'HOD',
    uploaded_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Mark Correction Requests Workflow Schema
CREATE TABLE IF NOT EXISTS mark_correction_requests (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    mark_id           INT NOT NULL,
    student_id        INT NOT NULL,
    subject_id        INT NOT NULL,
    staff_id          INT NOT NULL,
    test_number       INT NOT NULL DEFAULT 1,
    current_mark      DECIMAL(5,2) NOT NULL,
    max_marks         DECIMAL(5,2) NOT NULL DEFAULT 100.00,
    expected_mark     DECIMAL(5,2) NULL,
    reason            VARCHAR(100) NOT NULL,
    student_note      TEXT NOT NULL,
    status            VARCHAR(30) NOT NULL DEFAULT 'Raised',
    staff_remarks     TEXT NULL,
    approved_mark     DECIMAL(5,2) NULL,
    reviewed_by       INT NULL,
    reviewed_by_name  VARCHAR(100) NULL,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolved_at       DATETIME NULL,
    FOREIGN KEY (mark_id) REFERENCES internal_marks(id),
    FOREIGN KEY (student_id) REFERENCES students(studentid),
    FOREIGN KEY (subject_id) REFERENCES subjects(subjectid),
    FOREIGN KEY (staff_id) REFERENCES staff(staffid)
);

-- Comprehensive Security & Accountability Audit Log Schema
CREATE TABLE IF NOT EXISTS audit_log (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    table_name          VARCHAR(60) NOT NULL,
    record_id           INT NOT NULL,
    action              VARCHAR(50) NOT NULL,
    field_name          VARCHAR(60) NULL,
    old_value           TEXT NULL,
    new_value           TEXT NULL,
    changed_by_user_id  INT NULL,
    changed_by_name     VARCHAR(100) NOT NULL,
    changed_by_role     VARCHAR(30) NOT NULL,
    changed_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes               TEXT NULL
);

-- College Timetable Management Schema
CREATE TABLE IF NOT EXISTS timetable (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    day_of_week   VARCHAR(20) NOT NULL,
    period_number INT NOT NULL,
    time_slot     VARCHAR(60) NOT NULL,
    subject_code  VARCHAR(20) NOT NULL,
    staff_id      INT NULL,
    classroom     VARCHAR(50) NOT NULL,
    year          VARCHAR(20) NOT NULL DEFAULT 'Third year',
    section       VARCHAR(10) NOT NULL DEFAULT 'A',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_code) REFERENCES subjects(subject_code) ON DELETE CASCADE,
    FOREIGN KEY (staff_id) REFERENCES staff(staffid) ON DELETE SET NULL
);

-- =========================================================================
-- High-Performance Composite & Single-Column Indexes for Live MySQL
-- Eliminates table scans, filesorts, and speeds up JOINs/aggregations
-- =========================================================================

-- Attendance table indexes
CREATE INDEX idx_att_date ON attendance (date);
CREATE INDEX idx_att_subject_id ON attendance (subject_id);
CREATE INDEX idx_att_status ON attendance (status);
CREATE INDEX idx_att_date_subj ON attendance (date, subject_id);
CREATE INDEX idx_att_subj_stud ON attendance (subject_id, student_id);

-- Internal marks table indexes
CREATE INDEX idx_marks_subj_test ON internal_marks (subject_id, test_number);
CREATE INDEX idx_marks_stud_subj ON internal_marks (student_id, subject_id);

-- Students table indexes
CREATE INDEX idx_students_year ON students (year);
CREATE INDEX idx_students_dept_sec ON students (department, section);

-- Notifications table indexes
CREATE INDEX idx_notif_active_exp ON notifications (is_active, expires_at);

-- Notes table indexes
CREATE INDEX idx_notes_staff_up ON notes (staff_id, uploaded_at);
CREATE INDEX idx_notes_subj_up ON notes (subject_id, uploaded_at);

-- Gallery table indexes
CREATE INDEX idx_gallery_uploaded ON gallery (uploaded_at);

-- Timetable table indexes
CREATE INDEX idx_tt_lookup ON timetable (year, section, day_of_week, period_number);

-- Audit log table indexes
CREATE INDEX idx_audit_tbl_time ON audit_log (table_name, changed_at);

-- Mark correction requests table indexes
CREATE INDEX idx_mcr_staff_stat ON mark_correction_requests (staff_id, status);
CREATE INDEX idx_mcr_stud_stat ON mark_correction_requests (student_id, status);

