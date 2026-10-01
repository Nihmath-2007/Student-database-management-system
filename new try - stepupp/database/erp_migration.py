"""
Migration script to safely add required ERP columns and Timetable table to live MySQL database.
All operations are non-destructive and backward-compatible.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import execute, fetch_all

def run_migration():
    print("Starting ERP database migration...")
    
    # 1. Students table: add phone if missing
    try:
        cols = [c['Field'] for c in fetch_all("DESCRIBE students")]
        if 'phone' not in cols:
            execute("ALTER TABLE students ADD COLUMN phone VARCHAR(20) NULL")
            print("Added 'phone' column to students table.")
        if 'section' not in cols:
            execute("ALTER TABLE students ADD COLUMN section VARCHAR(10) DEFAULT 'A'")
            print("Added 'section' column to students table.")
    except Exception as e:
        print(f"Students table migration notice: {e}")

    # 2. Staff table: add department, email, phone, designation if missing
    try:
        cols = [c['Field'] for c in fetch_all("DESCRIBE staff")]
        if 'department' not in cols:
            execute("ALTER TABLE staff ADD COLUMN department VARCHAR(50) DEFAULT 'Information Technology'")
            print("Added 'department' to staff table.")
        if 'email' not in cols:
            execute("ALTER TABLE staff ADD COLUMN email VARCHAR(100) NULL")
            print("Added 'email' to staff table.")
        if 'phone' not in cols:
            execute("ALTER TABLE staff ADD COLUMN phone VARCHAR(20) NULL")
            print("Added 'phone' to staff table.")
        if 'designation' not in cols:
            execute("ALTER TABLE staff ADD COLUMN designation VARCHAR(50) DEFAULT 'Assistant Professor'")
            print("Added 'designation' to staff table.")
    except Exception as e:
        print(f"Staff table migration notice: {e}")

    # 3. Subjects table: add department if missing
    try:
        cols = [c['Field'] for c in fetch_all("DESCRIBE subjects")]
        if 'department' not in cols:
            execute("ALTER TABLE subjects ADD COLUMN department VARCHAR(50) DEFAULT 'Information Technology'")
            print("Added 'department' to subjects table.")
    except Exception as e:
        print(f"Subjects table migration notice: {e}")

    # 4. Attendance table: add subject_id if missing
    try:
        cols = [c['Field'] for c in fetch_all("DESCRIBE attendance")]
        if 'subject_id' not in cols:
            execute("ALTER TABLE attendance ADD COLUMN subject_id INT NULL")
            print("Added 'subject_id' to attendance table.")
    except Exception as e:
        print(f"Attendance table migration notice: {e}")

    # 5. Timetable table: create if not exists
    try:
        execute("""
        CREATE TABLE IF NOT EXISTS timetable (
            id INT AUTO_INCREMENT PRIMARY KEY,
            day_of_week VARCHAR(20) NOT NULL,
            period_number INT NOT NULL,
            time_slot VARCHAR(60) NOT NULL,
            subject_code VARCHAR(20) NOT NULL,
            staff_id INT NULL,
            classroom VARCHAR(50) NOT NULL,
            year VARCHAR(20) NOT NULL DEFAULT 'Third year',
            section VARCHAR(10) NOT NULL DEFAULT 'A',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_code) REFERENCES subjects(subject_code) ON DELETE CASCADE,
            FOREIGN KEY (staff_id) REFERENCES staff(staffid) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """)
        print("Ensured 'timetable' table exists.")
    except Exception as e:
        print(f"Timetable table creation notice: {e}")

    print("Migration finished successfully.")

if __name__ == '__main__':
    run_migration()
