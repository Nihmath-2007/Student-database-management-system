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
            conn.commit()

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
            conn.close()
            return
        except Exception as e:
            print(f"Error initializing Railway MySQL database: {e}")
            try:
                conn.close()
            except Exception:
                pass
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
