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
