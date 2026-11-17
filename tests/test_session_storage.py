import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import session_storage as storage


class SessionStorage(unittest.TestCase):
    def test_reopening_sqlite_keeps_rows_and_failed_write_rolls_back(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'DESCENT_DATABASE_URL': ''}):
            path = Path(temp) / 'sessions.sqlite3'
            storage.initialize_database(path)
            with storage.connection(path, True) as conn:
                conn.execute('INSERT INTO game_sessions VALUES(?,?,?,?)', ('test-hash', '{}', 1.0, 0))
            storage.initialize_database(path)
            with self.assertRaises(RuntimeError):
                with storage.connection(path, True) as conn:
                    conn.execute('UPDATE game_sessions SET version=? WHERE token_hash=?', (1, 'test-hash'))
                    raise RuntimeError('abort')
            with storage.connection(path) as conn:
                row = conn.execute('SELECT version FROM game_sessions WHERE token_hash=?', ('test-hash',)).fetchone()
            self.assertEqual(row['version'], 0)

    def test_postgres_failure_never_silently_uses_local_file(self):
        psycopg = MagicMock()
        psycopg.connect.side_effect = ConnectionError('unavailable')
        rows = MagicMock()
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'DESCENT_DATABASE_URL': 'postgresql://unavailable.test/db'}), patch.dict('sys.modules', {'psycopg': psycopg, 'psycopg.rows': rows}):
            path = Path(temp) / 'must-not-exist.sqlite3'
            with self.assertRaises(ConnectionError):
                with storage.connection(path) as conn:
                    conn.execute('SELECT 1')
            self.assertFalse(path.exists())
