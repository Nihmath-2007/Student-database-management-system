import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from werkzeug.security import generate_password_hash
from config.database import get_db_connection, execute_query

def init_db(force=False):
    """
    Initializes database session.
    When connected to live Railway MySQL:
      - Ensures the 'users' table exists.
      - Seeds default HOD, Staff, and Student users if empty.
      - Does NOT parse local .sql files or mutate existing Railway MySQL tables.
    """
    conn, engine = get_db_connection()
    print(f"Connected to live database engine: {engine}")

    try:
        from services.correction_service import init_correction_tables
        init_correction_tables()
    except Exception as corr_err:
        print(f"Notice: init_correction_tables in init_db: {corr_err}")

    if engine == 'mysql':
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Ensure 'users' table exists in Railway MySQL
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL,
                student_id INT NULL,
                staff_id INT NULL,
                FOREIGN KEY (student_id) REFERENCES students(studentid) ON DELETE CASCADE,
                FOREIGN KEY (staff_id) REFERENCES staff(staffid) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # Ensure 'notifications' and 'notification_dismissals' tables exist in MySQL
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(150) NOT NULL,
                message TEXT NOT NULL,
                audience VARCHAR(50) NOT NULL DEFAULT 'everyone',
                priority VARCHAR(20) NOT NULL DEFAULT 'medium',
                created_by INT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATE NOT NULL,
                is_active INT DEFAULT 1
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_dismissals (
                id INT AUTO_INCREMENT PRIMARY KEY,
                notification_id INT NOT NULL,
                user_id INT NOT NULL,
                dismissed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_notif_user (notification_id, user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # Ensure 'notes' table exists in MySQL
            cursor.execute("""
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
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # Ensure 'gallery' table exists in MySQL
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS gallery (
                id            INT AUTO_INCREMENT PRIMARY KEY,
                title         VARCHAR(150) NOT NULL,
                description   VARCHAR(500),
                event_date    DATE,
                image_path    VARCHAR(255) NOT NULL,
                uploaded_by   VARCHAR(60) DEFAULT 'HOD',
                uploaded_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            conn.commit()

            # Ensure 'section' column exists in students (MySQL)
            try:
                cursor.execute("SHOW COLUMNS FROM students LIKE 'section'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE students ADD COLUMN section VARCHAR(10) DEFAULT 'A'")
                    conn.commit()
            except Exception as sec_err:
                print(f"Notice: students.section column check in MySQL: {sec_err}")

            # Check if users exist
            cursor.execute("SELECT COUNT(*) as cnt FROM users")
            row = cursor.fetchone()
            user_count = row['cnt'] if row else 0

            if user_count == 0:
                print("Seeding default authentication accounts into Railway MySQL...")
                user_rows = []
                
                # 1. HOD User
                hod_hash = generate_password_hash('hod123')
                user_rows.append(('hod', hod_hash, 'hod', None, None))

                # 2. Staff Users
                cursor.execute("SELECT staffid FROM staff")
                staff_members = cursor.fetchall()
                staff_hash = generate_password_hash('staff123')
                for st in staff_members:
                    username = f"staff{st['staffid']}"
                    user_rows.append((username, staff_hash, 'staff', None, st['staffid']))

                # 3. Student Users
                cursor.execute("SELECT studentid, regno FROM students")
                students = cursor.fetchall()
                student_hash = generate_password_hash('student123')
                for s in students:
                    username = str(s['regno']).strip()
                    user_rows.append((username, student_hash, 'student', s['studentid'], None))

                cursor.executemany(
                    "INSERT INTO users (username, password_hash, role, student_id, staff_id) VALUES (%s, %s, %s, %s, %s)",
                    user_rows
                )
                conn.commit()
                print(f"Successfully initialized {len(user_rows)} users in Railway MySQL.")
            else:
                print(f"Railway MySQL connected with {user_count} active user accounts.")

            cursor.close()
            return
        except Exception as e:
            print(f"Error initializing Railway MySQL database: {e}")
            raise e

    # Fallback for local SQLite engine if explicitly set
    else:
        cursor = conn.cursor()
        try:
            # Ensure high-performance indexes exist
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendance_student_status ON attendance(student_id, status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_internal_marks_student ON internal_marks(student_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_internal_marks_subject ON internal_marks(subject_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_subjects_staff ON subjects(staff_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_year ON students(year)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            conn.commit()
        except Exception as idx_err:
            print(f"Notice: Index optimization skipped: {idx_err}")

        # Ensure 'notifications' and 'notification_dismissals' tables exist in SQLite
        try:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(150) NOT NULL,
                message TEXT NOT NULL,
                audience VARCHAR(50) NOT NULL DEFAULT 'everyone',
                priority VARCHAR(20) NOT NULL DEFAULT 'medium',
                created_by INT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATE NOT NULL,
                is_active INT DEFAULT 1
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_dismissals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notification_id INT NOT NULL,
                user_id INT NOT NULL,
                dismissed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(notification_id, user_id)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id   INT NOT NULL,
                staff_id     INT NOT NULL,
                title        VARCHAR(150) NOT NULL,
                filename     VARCHAR(255) NOT NULL,
                stored_path  VARCHAR(255) NOT NULL,
                uploaded_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects(subjectid),
                FOREIGN KEY (staff_id) REFERENCES staff(staffid)
            );
            """)

            # Ensure 'gallery' table exists in SQLite
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS gallery (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                title         VARCHAR(150) NOT NULL,
                description   VARCHAR(500),
                event_date    DATE,
                image_path    VARCHAR(255) NOT NULL,
                uploaded_by   VARCHAR(60) DEFAULT 'HOD',
                uploaded_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conn.commit()
        except Exception as notif_t_err:
            print(f"Notice: notifications table creation in SQLite: {notif_t_err}")

        # Ensure 'section' column exists in students (SQLite)
        try:
            cursor.execute("PRAGMA table_info(students)")
            cols = [col[1] for col in cursor.fetchall()]
            if 'section' not in cols:
                cursor.execute("ALTER TABLE students ADD COLUMN section VARCHAR(10) DEFAULT 'A'")
                conn.commit()
                print("Added 'section' column to students table.")
        except Exception as sec_err:
            print(f"Notice: students.section column check in SQLite: {sec_err}")

        # Seed sample notifications in SQLite if empty
        try:
            cursor.execute("SELECT COUNT(*) FROM notifications")
            notif_cnt = cursor.fetchone()[0]
            if notif_cnt == 0:
                cursor.execute("""
                INSERT INTO notifications (title, message, audience, priority, expires_at, is_active)
                VALUES 
                (?, ?, ?, ?, ?, 1),
                (?, ?, ?, ?, ?, 1)
                """, (
                    'Internal Assessment-II Exam Schedule Announced',
                    'IA-2 Examinations for all IT Department students will commence next week. Verify timetable and seating allocations.',
                    'everyone',
                    'urgent',
                    '2027-12-31',
                    'Academic Project Phase-1 Documentation Reminder',
                    'All 3rd Year and Final Year IT students must submit their project abstracts and guide approvals by 5:00 PM.',
                    'Third year',
                    'high',
                    '2027-12-31'
                ))
                conn.commit()
                print("Seeded sample HOD announcements into notifications table.")
        except Exception as seed_notif_err:
            print(f"Notice: notifications seed in SQLite: {seed_notif_err}")

        if not force:
            try:
                cursor.execute("SELECT COUNT(*) FROM users")
                cnt = cursor.fetchone()[0]
                if cnt > 0:
                    print(f"SQLite Database already initialized with {cnt} users. Optimized indexes active.")
                    cursor.close()
                    conn.close()
                    return
            except Exception:
                pass

        cursor.close()
        conn.close()

if __name__ == '__main__':
    init_db()
