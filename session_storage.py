"""Session database selection; never fall back after a configured PG failure."""
from contextlib import contextmanager
import os
import sqlite3


def postgres_url():
    return os.environ.get('DESCENT_DATABASE_URL', '').strip()


class PostgresConnection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, params=()):
        # All existing session queries use positional value placeholders only.
        return self.connection.execute(sql.replace('?', '%s'), params)


@contextmanager
def connection(sqlite_path, write=False):
    if postgres_url():
        import psycopg
        from psycopg.rows import dict_row
        conn = psycopg.connect(postgres_url(), connect_timeout=10,
                               autocommit=not write, row_factory=dict_row)
        try:
            yield PostgresConnection(conn)
            if write:
                conn.commit()
        except Exception:
            if write:
                conn.rollback()
            raise
        finally:
            conn.close()
        return
    conn = sqlite3.connect(str(sqlite_path), timeout=12)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA busy_timeout=12000')
    if write:
        conn.execute('BEGIN IMMEDIATE')
    try:
        yield conn
        if write:
            conn.commit()
    except Exception:
        if write:
            conn.rollback()
        raise
    finally:
        conn.close()


def initialize(sqlite_path):
    if not postgres_url():
        with sqlite3.connect(str(sqlite_path), timeout=10) as conn:
            conn.execute('PRAGMA journal_mode=WAL')
    with connection(sqlite_path, write=True) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS game_sessions ('
                     'token_hash TEXT PRIMARY KEY, state_json TEXT NOT NULL, '
                     'updated_at DOUBLE PRECISION NOT NULL, version INTEGER NOT NULL DEFAULT 0)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_updated ON game_sessions(updated_at)')


def initialize_database(sqlite_path):
    with connection(sqlite_path, write=True) as conn:
        number_type = 'DOUBLE PRECISION' if postgres_url() else 'REAL'
        conn.execute('CREATE TABLE IF NOT EXISTS game_sessions ('
                     'token_hash TEXT PRIMARY KEY, state_json TEXT NOT NULL, '
                     'updated_at ' + number_type + ' NOT NULL, '
                     'version INTEGER NOT NULL DEFAULT 0)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_updated ON game_sessions(updated_at)')
