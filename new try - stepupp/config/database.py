import os
import sqlite3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'altaria.proxy.rlwy.net')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'qcIobVysrnYsWmrFsWVMJsbnnnlfipll')
DB_NAME = os.getenv('DB_NAME', 'railway')
DB_PORT = int(os.getenv('DB_PORT', 33690))
SECRET_KEY = os.getenv('SECRET_KEY', 'msec_it_student_analytics_secret_key_2026')

SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'student_analytics.db')

def get_db_connection():
    """
    Connects to MySQL if DB_TYPE=mysql.
    Automatically falls back to local SQLite (student_analytics.db) if DB_TYPE=sqlite or MySQL connection fails.
    """
    db_type = os.getenv('DB_TYPE', 'sqlite').lower()
    fallback_allowed = os.getenv('DB_FALLBACK', 'true').lower() in ('true', '1', 'yes')
    
    if db_type == 'mysql':
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                port=DB_PORT,
                connect_timeout=5
            )
            return conn, 'mysql'
        except Exception as err:
            print(f"Warning: Failed to connect to MySQL database at {DB_HOST}:{DB_PORT}: {err}")
            if not fallback_allowed:
                raise err
            print("Notice: Automatically falling back to local SQLite database (student_analytics.db)...")

    # SQLite fallback / default local DB engine if explicitly requested or fallback
    conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn, 'sqlite'

def execute_query(query, params=(), fetchall=True, fetchone=False, commit=False):
    """
    Executes a query safely handling both MySQL and SQLite parameter placeholders (%s vs ?).
    Returns list of dicts for SELECT queries.
    """
    conn, db_engine = get_db_connection()
    try:
        if db_engine == 'sqlite':
            # Convert MySQL %s placeholder to SQLite ? placeholder if needed
            sqlite_query = query.replace('%s', '?')
            cursor = conn.cursor()
            cursor.execute(sqlite_query, params)
            if commit:
                conn.commit()
                lastrowid = cursor.lastrowid
                conn.close()
                return lastrowid
            if fetchone:
                row = cursor.fetchone()
                conn.close()
                return dict(row) if row else None
            if fetchall:
                rows = cursor.fetchall()
                conn.close()
                return [dict(r) for r in rows]
            conn.close()
            return None
        else:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            if commit:
                conn.commit()
                lastid = cursor.lastrowid
                cursor.close()
                conn.close()
                return lastid
            if fetchone:
                row = cursor.fetchone()
                cursor.close()
                conn.close()
                return row
            if fetchall:
                rows = cursor.fetchall()
                cursor.close()
                conn.close()
                return rows
            cursor.close()
            conn.close()
            return None
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        raise e
