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
DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', 2))

SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'student_analytics.db')

_pool_lock = threading.Lock()
_mysql_pool = None
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

def _init_mysql_pool():
    """Initializes a thread-safe MySQL connection pool for Railway cloud MySQL."""
    global _mysql_pool
    if _mysql_pool is None:
        with _pool_lock:
            if _mysql_pool is None:
                import mysql.connector.pooling
                try:
                    _mysql_pool = mysql.connector.pooling.MySQLConnectionPool(
                        pool_name="student_erp_pool",
                        pool_size=DB_POOL_SIZE,
                        pool_reset_session=False,
                        host=DB_HOST,
                        user=DB_USER,
                        password=DB_PASSWORD,
                        database=DB_NAME,
                        port=DB_PORT,
                        connect_timeout=10,
                        autocommit=True
                    )
                except Exception as e:
                    print(f"Notice: MySQL pool init deferred/failed: {e}")
                    _mysql_pool = None
    return _mysql_pool

_thread_local = threading.local()

def _get_mysql_connection():
    """
    Retrieves or establishes a thread-local persistent MySQL connection with auto-ping.
    Drastically eliminates TCP handshake latency and prevents port exhaustion during repeated requests.
    """
    conn = getattr(_thread_local, 'conn', None)
    if conn is not None:
        try:
            if conn.is_connected():
                return conn
            else:
                conn.reconnect(attempts=2, delay=1)
                return conn
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            _thread_local.conn = None

    import mysql.connector
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        connect_timeout=10,
        autocommit=True
    )
    _thread_local.conn = conn
    return conn

def get_db_connection():
    """
    Connects to live Railway MySQL database using thread-local pooled connection.
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
    Executes a query safely using thread-local MySQL connection.
    """
    conn, db_engine = get_db_connection()
    cursor = None
    try:
        if db_engine == 'sqlite':
            sqlite_query = query.replace('%s', '?')
            cursor = conn.cursor()
            cursor.execute(sqlite_query, params)
            if commit:
                conn.commit()
                return cursor.lastrowid
            if fetchone:
                row = cursor.fetchone()
                return dict(row) if row else None
            if fetchall:
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
            return None
        else:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            if commit:
                conn.commit()
                return cursor.lastrowid
            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()
            return None
    except Exception as e:
        if db_engine == 'mysql' and conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise e
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if db_engine == 'sqlite' and conn:
            try:
                conn.close()
            except Exception:
                pass

def execute_many(query, seq_of_params):
    """
    Executes a batch of queries in a single round-trip using cursor.executemany.
    Dramatically accelerates bulk inserts and updates.
    """
    if not seq_of_params:
        return 0
    conn, db_engine = get_db_connection()
    cursor = None
    try:
        if db_engine == 'sqlite':
            sqlite_query = query.replace('%s', '?')
            cursor = conn.cursor()
            cursor.executemany(sqlite_query, seq_of_params)
            conn.commit()
            return cursor.rowcount
        else:
            cursor = conn.cursor()
            cursor.executemany(query, seq_of_params)
            conn.commit()
            return cursor.rowcount
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass

def fetch_all(query, params=()):
    """Executes a query and returns all matching records as a list of dictionaries."""
    return execute_query(query, params, fetchall=True)

def fetch_one(query, params=()):
    """Executes a query and returns a single matching record as a dictionary or None."""
    return execute_query(query, params, fetchone=True)

def execute(query, params=()):
    """Executes an INSERT/UPDATE/DELETE query with commit and returns lastrowid."""
    return execute_query(query, params, commit=True)
