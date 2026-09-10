# Copyright 2026 RedHat Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sqlite3
from unittest import mock

from glance.image_cache.drivers import common
from glance.tests import utils


class TestSqliteConnectionTimeout(utils.BaseTestCase):

    def _bare_conn(self, timeout_seconds=30.0):
        conn = common.SqliteConnection.__new__(common.SqliteConnection)
        conn.timeout_seconds = timeout_seconds
        return conn

    def test_timeout_returns_on_success(self):
        conn = self._bare_conn()
        self.assertEqual(7, conn._timeout(lambda: 7))

    def test_timeout_retries_database_locked_then_succeeds(self):
        conn = self._bare_conn()
        attempts = iter([0, 1, 2])

        def flaky():
            n = next(attempts)
            if n < 2:
                raise sqlite3.OperationalError('database is locked')
            return 'ok'

        with mock.patch.object(common.time, 'sleep'):
            self.assertEqual('ok', conn._timeout(flaky))

    def test_timeout_raises_when_deadline_exceeded(self):
        conn = self._bare_conn(timeout_seconds=0.01)

        def always_locked():
            raise sqlite3.OperationalError('database is locked')

        # monotonic: deadline at 0+0.01, first loop check, second loop check
        mono = iter([0.0, 0.0, 0.02])

        def fake_monotonic():
            return next(mono)

        with mock.patch.object(
                common.time, 'monotonic', side_effect=fake_monotonic):
            with mock.patch.object(common.time, 'sleep'):
                exc = self.assertRaises(
                    TimeoutError, conn._timeout, always_locked)
        self.assertIn('0.01', str(exc))

    def test_timeout_propagates_non_locked_operational_error(self):
        conn = self._bare_conn()

        def bad_schema():
            raise sqlite3.OperationalError('no such table: missing')

        with mock.patch.object(common.time, 'sleep') as mock_sleep:
            self.assertRaises(
                sqlite3.OperationalError, conn._timeout, bad_schema)
        mock_sleep.assert_not_called()
