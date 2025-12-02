"""
Database Connection and Base Operations
Provides connection pooling and transaction management
"""

import os
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2.extensions import register_adapter, AsIs
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

# Register UUID adapter for psycopg2
def adapt_uuid(uuid_obj):
    return AsIs(f"'{uuid_obj}'")

register_adapter(UUID, adapt_uuid)


class DatabaseConnection:
    """Manages PostgreSQL connection pool"""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL not provided")

        # Create connection pool
        self.pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=20,
            dsn=self.database_url
        )
        logger.info("Database connection pool initialized")

    @contextmanager
    def get_connection(self):
        """Get connection from pool"""
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    @contextmanager
    def get_cursor(self, dict_cursor=True):
        """Get cursor with optional dict results"""
        with self.get_connection() as conn:
            cursor_factory = RealDictCursor if dict_cursor else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error: {e}")
                raise
            finally:
                cursor.close()

    @contextmanager
    def transaction(self):
        """Transaction context manager"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction error: {e}")
                raise
            finally:
                cursor.close()

    def execute_query(self, query: str, params: Optional[tuple] = None, fetch=True) -> Optional[List[Dict]]:
        """Execute a single query"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            if fetch:
                return cursor.fetchall()
            return None

    def execute_many(self, query: str, params_list: List[tuple]):
        """Execute query multiple times"""
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)

    def execute_values(self, query: str, values: List[tuple], page_size: int = 100):
        """Bulk insert with execute_values"""
        with self.get_cursor(dict_cursor=False) as cursor:
            execute_values(cursor, query, values, page_size=page_size)

    def close(self):
        """Close all connections in pool"""
        self.pool.closeall()
        logger.info("Database connection pool closed")


# Global database instance
_db: Optional[DatabaseConnection] = None


def get_db() -> DatabaseConnection:
    """Get or create global database instance"""
    global _db
    if _db is None:
        _db = DatabaseConnection()
    return _db


def close_db():
    """Close global database instance"""
    global _db
    if _db:
        _db.close()
        _db = None
