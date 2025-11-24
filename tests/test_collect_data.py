"""
tests/test_collect_data.py
Unit tests for the Nature Remo collector to guarantee API/DB glue stays stable.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from collect_data import fetch_latest_temperature, save_to_turso
from config import DEFAULT_TABLE_NAME, load_env_config


class _DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _DummySession:
    def __init__(self, payload):
        self.payload = payload
        self.request_log = []

    def get(self, url, *, headers, timeout):
        self.request_log.append((url, headers, timeout))
        return _DummyResponse(self.payload)


class _DummyCursor:
    def __init__(self):
        self.executed = []
        self._last_fetch = (1,)

    def execute(self, query, params=None):
        normalized_query = " ".join(query.split())
        self.executed.append((normalized_query, params))
        if "SELECT COUNT" in normalized_query:
            self._last_fetch = (1,)

    def fetchone(self):
        return self._last_fetch


class _DummyConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False
        self.commits = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


class CollectDataTestCase(unittest.TestCase):
    def test_fetch_latest_temperature_returns_first_device(self):
        session = _DummySession(
            [
                {
                    "name": "living",
                    "newest_events": {"te": {"val": 24.5}},
                }
            ]
        )

        name, temperature = fetch_latest_temperature("dummy", session=session)

        self.assertEqual(name, "living")
        self.assertEqual(temperature, 24.5)
        self.assertEqual(session.request_log[0][0], "https://api.nature.global/1/devices")

    def test_save_to_turso_writes_insert(self):
        with mock.patch.dict(
            os.environ,
            {
                "NATURE_REMO_API_KEY": "key",
                "TURSO_DATABASE_URL": "libsql://dummy",
                "TURSO_AUTH_TOKEN": "token",
            },
            clear=False,
        ):
            env = load_env_config()

        cursor = _DummyCursor()
        conn = _DummyConnection(cursor)

        def fake_connect(url, *, auth_token):
            self.assertEqual(url, env.turso_database_url)
            self.assertEqual(auth_token, env.turso_auth_token)
            return conn

        timestamp = save_to_turso(
            "living",
            21.2,
            env=env,
            connect=fake_connect,
        )

        self.assertEqual(conn.commits, 1)
        self.assertTrue(conn.closed)

        insert_query, params = cursor.executed[1]
        self.assertIn(f"INSERT INTO {DEFAULT_TABLE_NAME}", insert_query)
        self.assertEqual(params[0], timestamp)
        self.assertEqual(params[1:], ("living", 21.2))


if __name__ == "__main__":
    unittest.main()
