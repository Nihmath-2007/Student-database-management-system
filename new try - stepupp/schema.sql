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
