import os
import time
import sqlite3
import threading
import queue
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

DB_HOST = os.getenv('DB_HOST', 'iriguchi.proxy.rlwy.net')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'KnFpfXxCggQUXxaDvDpSfuWsDUqgMMDw')
DB_NAME = os.getenv('DB_NAME', 'railway')
DB_PORT = int(os.getenv('DB_PORT', 30160))
SECRET_KEY = os.getenv('SECRET_KEY', 'msec_it_student_analytics_secret_key_2026')
DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', 6))

SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'student_analytics.db')

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

class PooledMySQLConnection:
    """
    Proxy wrapper around raw MySQL connection that safely intercepts close()
    and returns the underlying live connection back to the shared pool
    instead of terminating the TCP socket.
    """
    def __init__(self, raw_conn, pool):
        self._raw_conn = raw_conn
        self._pool = pool
        self._is_closed = False

    def close(self):
        if not self._is_closed:
            self._is_closed = True
            if self._pool and self._raw_conn:
                self._pool.return_connection(self._raw_conn)

    def cursor(self, *args, **kwargs):
        return self._raw_conn.cursor(*args, **kwargs)

    def commit(self):
        return self._raw_conn.commit()

    def rollback(self):
        return self._raw_conn.rollback()

    def is_connected(self):
        return self._raw_conn.is_connected()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __getattr__(self, name):
        return getattr(self._raw_conn, name)

class HighPerformanceMySQLPool:
    """
    High-throughput, thread-safe connection pool with on-demand pre-warming,
    instant connection reuse, auto-reconnect, and background keep-alive.
    Dramatically eliminates the ~14-second TCP/TLS handshake latency on every request.
    """
    def __init__(self, pool_size=6):
        self.pool_size = max(3, pool_size)
        self.queue = queue.Queue(maxsize=self.pool_size)
        self.total_created = 0
        self.lock = threading.Lock()
        self._keepalive_started = False

    def _create_raw_connection(self):
        import mysql.connector
        return mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
            connect_timeout=8,
            autocommit=True,
            buffered=True
        )

    def get_connection(self, timeout=12.0):
        # 1. Reuse existing live connection from pool (instant 0.000s)
        try:
            conn = self.queue.get_nowait()
            if self._is_conn_healthy(conn):
                return conn
            else:
                self._safe_close(conn)
                with self.lock:
                    self.total_created = max(0, self.total_created - 1)
        except queue.Empty:
            pass

        # 2. If under limit, create a new pooled connection
        with self.lock:
            if self.total_created < self.pool_size:
                self.total_created += 1
                try:
                    conn = self._create_raw_connection()
                    self._start_keepalive_if_needed()
                    return conn
                except Exception as e:
                    self.total_created = max(0, self.total_created - 1)
                    raise e

        # 3. If pool is at limit, wait for an idle connection to be returned
        try:
            conn = self.queue.get(timeout=timeout)
            if self._is_conn_healthy(conn):
                return conn
            else:
                self._safe_close(conn)
                conn = self._create_raw_connection()
                return conn
        except queue.Empty:
            # Emergency temporary fallback connection
            return self._create_raw_connection()

    def return_connection(self, conn):
        if not conn:
            return
        if self._is_conn_healthy(conn):
            try:
                self.queue.put_nowait(conn)
            except queue.Full:
                self._safe_close(conn)
                with self.lock:
                    self.total_created = max(0, self.total_created - 1)
        else:
            self._safe_close(conn)
            with self.lock:
                self.total_created = max(0, self.total_created - 1)

    def _is_conn_healthy(self, conn):
        try:
            if conn and conn.is_connected():
                return True
            if conn:
                conn.reconnect(attempts=1, delay=0.2)
                return conn.is_connected()
        except Exception:
            return False
        return False

    def _safe_close(self, conn):
        try:
            if conn:
                conn.close()
        except Exception:
            pass

    def _start_keepalive_if_needed(self):
        if self._keepalive_started:
            return
        self._keepalive_started = True

        def _keepalive_worker():
            while True:
                time.sleep(50)  # Ping every 50 seconds to prevent Railway proxy idle drops
                temp_list = []
                while not self.queue.empty():
                    try:
                        c = self.queue.get_nowait()
                        temp_list.append(c)
                    except queue.Empty:
                        break
                for c in temp_list:
                    try:
                        cur = c.cursor()
                        cur.execute("SELECT 1")
                        cur.fetchall()
                        cur.close()
                        self.queue.put_nowait(c)
                    except Exception:
                        self._safe_close(c)
                        with self.lock:
                            self.total_created = max(0, self.total_created - 1)

        t = threading.Thread(target=_keepalive_worker, daemon=True, name="MySQLKeepAliveWorker")
        t.start()

# Global connection pool instance
_mysql_pool = HighPerformanceMySQLPool(pool_size=DB_POOL_SIZE)

def get_db_connection():
    """
    Connects to live Railway MySQL database using thread-safe pooled connection.
    Returns PooledMySQLConnection which safely returns to pool when closed.
    """
    db_type = os.getenv('DB_TYPE', 'mysql').lower()
    fallback_allowed = os.getenv('DB_FALLBACK', 'false').lower() in ('true', '1', 'yes')

    if fallback_allowed and db_type == 'sqlite':
        conn = _create_sqlite_connection()
        return conn, 'sqlite'

    try:
        raw_conn = _mysql_pool.get_connection()
        return PooledMySQLConnection(raw_conn, _mysql_pool), 'mysql'
    except Exception as err:
        print(f"Error connecting to live Railway MySQL ({err}).")
        if fallback_allowed:
            conn = _create_sqlite_connection()
            return conn, 'sqlite'
        raise err

def _execute_sqlite_fallback(query, params, fetchall, fetchone, commit):
    conn = _create_sqlite_connection()
    cursor = None
    try:
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
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass

def execute_query(query, params=(), fetchall=True, fetchone=False, commit=False):
    """
    Executes a query safely with automatic pooled connection check-out and return.
    """
    db_type = os.getenv('DB_TYPE', 'mysql').lower()
    fallback_allowed = os.getenv('DB_FALLBACK', 'false').lower() in ('true', '1', 'yes')

    if fallback_allowed and db_type == 'sqlite':
        return _execute_sqlite_fallback(query, params, fetchall, fetchone, commit)

    raw_conn = None
    cursor = None
    try:
        raw_conn = _mysql_pool.get_connection()
        cursor = raw_conn.cursor(dictionary=True)
        cursor.execute(query, params)
        if commit:
            raw_conn.commit()
            return cursor.lastrowid
        if fetchone:
            return cursor.fetchone()
        if fetchall:
            return cursor.fetchall()
        return None
    except Exception as e:
        if raw_conn:
            try:
                raw_conn.rollback()
            except Exception:
                pass
        if fallback_allowed and os.path.exists(SQLITE_DB_PATH):
            print(f"Notice: MySQL query failed ({e}), falling back to SQLite.")
            return _execute_sqlite_fallback(query, params, fetchall, fetchone, commit)
        raise e
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if raw_conn:
            _mysql_pool.return_connection(raw_conn)

def execute_many(query, seq_of_params):
    """
    Executes a batch of queries in a single round-trip using cursor.executemany.
    Dramatically accelerates bulk inserts and updates.
    """
    if not seq_of_params:
        return 0
    db_type = os.getenv('DB_TYPE', 'mysql').lower()
    fallback_allowed = os.getenv('DB_FALLBACK', 'false').lower() in ('true', '1', 'yes')

    if fallback_allowed and db_type == 'sqlite':
        conn = _create_sqlite_connection()
        cursor = None
        try:
            sqlite_query = query.replace('%s', '?')
            cursor = conn.cursor()
            cursor.executemany(sqlite_query, seq_of_params)
            conn.commit()
            return cursor.rowcount
        finally:
            if cursor:
                try: cursor.close()
                except Exception: pass
            if conn:
                try: conn.close()
                except Exception: pass

    raw_conn = None
    cursor = None
    try:
        raw_conn = _mysql_pool.get_connection()
        cursor = raw_conn.cursor()
        cursor.executemany(query, seq_of_params)
        raw_conn.commit()
        return cursor.rowcount
    except Exception as e:
        if raw_conn:
            try:
                raw_conn.rollback()
            except Exception:
                pass
        raise e
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if raw_conn:
            _mysql_pool.return_connection(raw_conn)

def fetch_all(query, params=()):
    """Executes a query and returns all matching records as a list of dictionaries."""
    return execute_query(query, params, fetchall=True)

def fetch_one(query, params=()):
    """Executes a query and returns a single matching record as a dictionary or None."""
    return execute_query(query, params, fetchone=True)

def execute(query, params=()):
    """Executes an INSERT/UPDATE/DELETE query with commit and returns lastrowid."""
    return execute_query(query, params, commit=True)
