import os
import time
import sqlite3
import threading
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

DB_HOST = os.getenv('DB_HOST', 'iriguchi.proxy.rlwy.net')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'KnFpfXxCggQUXxaDvDpSfuWsDUqgMMDw')
DB_NAME = os.getenv('DB_NAME', 'railway')
DB_PORT = int(os.getenv('DB_PORT', 30160))
SECRET_KEY = os.getenv('SECRET_KEY', 'msec_it_student_analytics_secret_key_2026')

SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'student_analytics.db')

_thread_local = threading.local()

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

def _get_mysql_connection():
    """Returns a thread-local cached MySQL connection with automatic keep-alive."""
    conn = getattr(_thread_local, 'mysql_conn', None)
    if conn is not None:
        try:
            if conn.is_connected():
                return conn
            conn.ping(reconnect=True, attempts=3, delay=1)
            return conn
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            _thread_local.mysql_conn = None

    import mysql.connector
    new_conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        connect_timeout=15,
        autocommit=True
    )
    _thread_local.mysql_conn = new_conn
    return new_conn

def get_db_connection():
    """
    Connects to live Railway MySQL database.
    Uses cached thread-local connection for low-latency queries.
    Never falls back to SQLite unless DB_FALLBACK is explicitly set to true.
    """
    db_type = os.getenv('DB_TYPE', 'mysql').lower()
    fallback_allowed = os.getenv('DB_FALLBACK', 'false').lower() in ('true', '1', 'yes')
    
    if fallback_allowed and db_type == 'sqlite':
        conn = _create_sqlite_connection()
        return conn, 'sqlite'

    try:
        conn = _get_mysql_connection()
        return conn, 'mysql'
    except Exception as err:
        print(f"Error connecting to live Railway MySQL ({err}).")
        if fallback_allowed:
            conn = _create_sqlite_connection()
            return conn, 'sqlite'
        raise err

def execute_query(query, params=(), fetchall=True, fetchone=False, commit=False):
    """
    Executes a query safely handling both MySQL and SQLite parameter placeholders (%s vs ?).
    Reuses thread-local connection for maximum performance.
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
                return lastid
            if fetchone:
                row = cursor.fetchone()
                cursor.close()
                return row
            if fetchall:
                rows = cursor.fetchall()
                cursor.close()
                return rows
            cursor.close()
            return None
    except Exception as e:
        if db_engine == 'mysql':
            try:
                if hasattr(_thread_local, 'mysql_conn') and _thread_local.mysql_conn:
                    _thread_local.mysql_conn.close()
            except Exception:
                pass
            _thread_local.mysql_conn = None
        else:
            try:
                conn.close()
            except Exception:
                pass
        raise e


def fetch_all(query, params=()):
    """Executes a query and returns all matching records as a list of dictionaries."""
    return execute_query(query, params, fetchall=True)


def fetch_one(query, params=()):
    """Executes a query and returns a single matching record as a dictionary or None."""
    return execute_query(query, params, fetchone=True)


def execute(query, params=()):
    """Executes an INSERT/UPDATE/DELETE query with commit and returns lastrowid."""
    return execute_query(query, params, commit=True)

