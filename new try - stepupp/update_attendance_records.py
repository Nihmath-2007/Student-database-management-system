import sys
import os
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config.database import get_db_connection
from services.cache_service import api_cache

JULY_DATES = [
    '2026-07-14', '2026-07-15', '2026-07-16', '2026-07-17',
    '2026-07-20', '2026-07-21', '2026-07-22', '2026-07-23', '2026-07-24',
    '2026-07-27', '2026-07-28', '2026-07-29', '2026-07-30', '2026-07-31'
]

AUGUST_DATES = [
    '2026-08-03', '2026-08-04', '2026-08-05', '2026-08-06', '2026-08-07',
    '2026-08-10', '2026-08-11', '2026-08-12', '2026-08-13', '2026-08-14',
    '2026-08-17', '2026-08-18', '2026-08-19', '2026-08-20', '2026-08-21',
    '2026-08-24', '2026-08-25', '2026-08-26', '2026-08-27', '2026-08-28',
    '2026-08-31'
]

JULY_DATA = {
    '5001': (14, 0), '5002': (14, 0), '5003': (10, 4), '5004': (9, 5), '5005': (9, 5),
    '5006': (12, 2), '5007': (2, 12), '5008': (9, 5), '5009': (3, 11), '5010': (14, 0),
    '5011': (10, 4), '5012': (11, 3), '5013': (14, 0), '5015': (13, 1), '5016': (14, 0),
    '5017': (9, 5), '5018': (12, 2), '5019': (8, 6), '5020': (9, 5), '5021': (10, 4),
    '5022': (6, 8), '5023': (11, 3), '5024': (4, 10), '5025': (11, 3), '5026': (11, 3),
    '5027': (11, 3), '5028': (12, 2), '5029': (8, 6), '5030': (10, 4), '5031': (9, 5),
    '5032': (7, 7), '5033': (8, 6), '5034': (1, 13), '5035': (8, 6), '5036': (14, 0),
    '5037': (9, 5), '5038': (13, 1), '5039': (12, 2), '5040': (8, 6), '5041': (10, 4),
    '5042': (13, 1), '5043': (13, 1), '5044': (8, 6), '5045': (14, 0), '5046': (14, 0),
    '5047': (10, 4), '5048': (14, 0), '5050': (6, 8), '5051': (11, 3), '5052': (11, 3),
    '5053': (5, 9), '5301': (6, 8), '5302': (7, 7), '5303': (4, 10), '5304': (9, 5),
    '5305': (14, 0), '5306': (8, 6), '5307': (9, 5), '5308': (10, 4), '5309': (7, 7),
    '5310': (8, 6), '5311': (10, 4),
}

AUGUST_DATA = {
    '5001': (21, 0), '5002': (21, 0), '5003': (18, 3), '5004': (20, 1), '5005': (12, 9),
    '5006': (19, 2), '5007': (19, 2), '5008': (13, 8), '5009': (14, 7), '5010': (21, 0),
    '5011': (18, 3), '5012': (16, 5), '5013': (18, 3), '5015': (20, 1), '5016': (19, 2),
    '5017': (21, 0), '5018': (11, 10), '5019': (16, 5), '5020': (19, 2), '5021': (21, 0),
    '5022': (14, 7), '5023': (17, 4), '5024': (13, 8), '5025': (19, 2), '5026': (14, 7),
    '5027': (21, 0), '5028': (20, 1), '5029': (16, 5), '5030': (15, 6), '5031': (16, 5),
    '5032': (18, 3), '5033': (15, 6), '5034': (7, 14), '5035': (17, 4), '5036': (18, 3),
    '5037': (18, 3), '5038': (20, 1), '5039': (14, 7), '5040': (16, 5), '5041': (18, 3),
    '5042': (19, 2), '5043': (21, 0), '5044': (15, 6), '5045': (17, 4), '5046': (16, 5),
    '5047': (18, 3), '5048': (16, 5), '5050': (15, 6), '5051': (17, 4), '5052': (20, 1),
    '5053': (14, 7), '5301': (17, 4), '5302': (16, 5), '5303': (18, 3), '5304': (15, 6),
    '5305': (21, 0), '5306': (18, 3), '5307': (19, 2), '5308': (19, 2), '5309': (13, 8),
    '5310': (16, 5), '5311': (18, 3),
}

def pick_absent_dates(dates, absent_count, student_id):
    """Deterministically pick absent dates for a student."""
    if absent_count == 0:
        return set()
    n = len(dates)
    if absent_count >= n:
        return set(dates)
    
    # Deterministic pseudo-random selection based on student_id and salt
    rng = random.Random(student_id * 10007 + n)
    indices = list(range(n))
    chosen_indices = rng.sample(indices, absent_count)
    return set(dates[i] for i in chosen_indices)

def update_all_attendance():
    conn, db_type = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT studentid, regno, name FROM students ORDER BY studentid")
    students = cur.fetchall()
    
    # Map ending 4-digits to studentid
    reg_to_id = {s[1][-4:]: s[0] for s in students}
    print(f"Total students found in DB: {len(students)}")
    
    all_records = []
    
    for suffix, (j_pres, j_abs) in JULY_DATA.items():
        if suffix not in reg_to_id:
            print(f"Warning: suffix {suffix} not found in DB!")
            continue
        stud_id = reg_to_id[suffix]
        absent_dates = pick_absent_dates(JULY_DATES, j_abs, stud_id)
        for d in JULY_DATES:
            status = 'Absent' if d in absent_dates else 'Present'
            all_records.append((stud_id, d, status))

    for suffix, (a_pres, a_abs) in AUGUST_DATA.items():
        if suffix not in reg_to_id:
            print(f"Warning: suffix {suffix} not found in DB!")
            continue
        stud_id = reg_to_id[suffix]
        absent_dates = pick_absent_dates(AUGUST_DATES, a_abs, stud_id)
        for d in AUGUST_DATES:
            status = 'Absent' if d in absent_dates else 'Present'
            all_records.append((stud_id, d, status))

    print(f"Generated {len(all_records)} total daily attendance records ({len(JULY_DATES)} July + {len(AUGUST_DATES)} August = 35 days x 62 students = {35 * 62})")

    # Clear existing attendance table
    print("Clearing existing attendance table...")
    cur.execute("DELETE FROM attendance")
    
    # Batch insert all records
    print("Inserting updated attendance records...")
    insert_sql = "INSERT INTO attendance (student_id, date, status) VALUES (%s, %s, %s)"
    cur.executemany(insert_sql, all_records)
    conn.commit()
    print("Successfully committed all records to database!")

    # Verify counts
    cur.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM attendance")
    print("Attendance stats:", cur.fetchone())

    # Check first 5 students' total present/absent
    cur.execute("""
        SELECT s.regno, s.name,
               SUM(CASE WHEN MONTH(a.date)=7 AND a.status='Present' THEN 1 ELSE 0 END) as jul_p,
               SUM(CASE WHEN MONTH(a.date)=7 AND a.status='Absent' THEN 1 ELSE 0 END) as jul_a,
               SUM(CASE WHEN MONTH(a.date)=8 AND a.status='Present' THEN 1 ELSE 0 END) as aug_p,
               SUM(CASE WHEN MONTH(a.date)=8 AND a.status='Absent' THEN 1 ELSE 0 END) as aug_a,
               COUNT(*) as total_days,
               ROUND((SUM(a.status='Present') * 100.0) / COUNT(*), 1) as att_pct
        FROM students s
        JOIN attendance a ON s.studentid = a.student_id
        GROUP BY s.studentid
        ORDER BY s.studentid
        LIMIT 5
    """)
    rows = cur.fetchall()
    print("\nVerification sample:")
    for r in rows:
        print(r)

    # Also update railway_attendance.sql
    cur.execute("SELECT id, student_id, date, status FROM attendance ORDER BY id")
    rows = cur.fetchall()
    val_strs = [f"({r[0]},{r[1]},'{r[2].strftime('%Y-%m-%d')}','{r[3]}')" for r in rows]
    values_sql = ",\n".join(val_strs)
    dump_sql = f"""-- MySQL dump
USE railway;
DROP TABLE IF EXISTS `attendance`;
CREATE TABLE `attendance` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `date` date NOT NULL,
  `status` enum('Present','Absent') NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_student_date` (`student_id`,`date`),
  CONSTRAINT `attendance_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`studentid`)
) ENGINE=InnoDB AUTO_INCREMENT={len(rows)+1} DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

LOCK TABLES `attendance` WRITE;
INSERT INTO `attendance` VALUES
{values_sql};
UNLOCK TABLES;
"""
    sql_path = os.path.join(BASE_DIR, 'railway_attendance.sql')
    with open(sql_path, 'w', encoding='utf-8') as f:
        f.write(dump_sql)
    print(f"Updated {sql_path} with {len(rows)} records.")

    cur.close()
    conn.close()

    # Clear in-memory caches
    api_cache.invalidate()
    print("\nAPI Cache cleared.")

if __name__ == '__main__':
    update_all_attendance()
