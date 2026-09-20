import os
import time
import sqlite3
import threading
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

# Circuit breaker state for MySQL failover
_mysql_unavailable_until = 0.0
_mysql_lock = threading.Lock()
_sqlite_thread_local = threading.local()

def _create_sqlite_connection():
    """Creates a high-performance SQLite connection with optimal pragmas."""
    conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False, timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode = WAL")
        cur.execute("PRAGMA synchronous = NORMAL")
        cur.execute("PRAGMA cache_size = -64000")
        cur.execute("PRAGMA temp_store = MEMORY")
        cur.execute("PRAGMA mmap_size = 268435456")
        cur.close()
    except Exception:
        pass
    return conn

def get_db_connection():
    """
    Connects to MySQL if DB_TYPE=mysql and host is reachable.
    Uses circuit-breaker cooldown (60s) to prevent recurring 5-second socket timeouts when MySQL is down.
    Automatically falls back to local SQLite with zero latency.
    """
    global _mysql_unavailable_until
    db_type = os.getenv('DB_TYPE', 'sqlite').lower()
    fallback_allowed = os.getenv('DB_FALLBACK', 'true').lower() in ('true', '1', 'yes')
    
    if db_type == 'mysql':
        now = time.time()
        with _mysql_lock:
            can_try_mysql = (now >= _mysql_unavailable_until)

        if can_try_mysql:
            try:
                import mysql.connector
                conn = mysql.connector.connect(
                    host=DB_HOST,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME,
                    port=DB_PORT,
                    connect_timeout=3
                )
                return conn, 'mysql'
            except Exception as err:
                with _mysql_lock:
                    _mysql_unavailable_until = time.time() + 60.0  # Cooldown for 60s
                print(f"Warning: MySQL unavailable ({err}). Cooling down for 60s. Serving from local SQLite.")
                if not fallback_allowed:
                    raise err

    # High-performance SQLite engine
    conn = _create_sqlite_connection()
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
                cursor.close()
                conn.close()
                return lastrowid
            if fetchone:
                row = cursor.fetchone()
                result = dict(row) if row else None
                cursor.close()
                conn.close()
                return result
            if fetchall:
                rows = cursor.fetchall()
                result = [dict(r) for r in rows]
                cursor.close()
                conn.close()
                return result
            cursor.close()
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

