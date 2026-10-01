"""
Database connection and query execution helpers.
Provides fetch_all, fetch_one, execute, and execute_many wrappers matching standard project patterns.
"""
from config.database import get_db_connection, execute_query, fetch_all, fetch_one, execute, execute_many

__all__ = ['get_db_connection', 'execute_query', 'fetch_all', 'fetch_one', 'execute', 'execute_many']
