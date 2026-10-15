# Copyright 2026 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import http.client as http
import uuid

from glance.tests import functional


class TestTasksAPIGone(functional.SynchronousAPIBase):

    def test_task_endpoints_return_gone(self):
        self.start_server()
        task_id = str(uuid.uuid4())

        response = self.api_get('/v2/tasks')
        self.assertEqual(http.GONE, response.status_code)

        response = self.api_post('/v2/tasks', json={'type': 'import'})
        self.assertEqual(http.GONE, response.status_code)

        response = self.api_post('/v2/tasks', data=b'{invalid')
        self.assertEqual(http.GONE, response.status_code)

        response = self.api_get('/v2/tasks/%s' % task_id)
        self.assertEqual(http.GONE, response.status_code)

        response = self.api_delete('/v2/tasks/%s' % task_id)
        self.assertEqual(http.GONE, response.status_code)

    def test_task_schema_endpoints_return_gone(self):
        self.start_server()

        response = self.api_get('/v2/schemas/task')
        self.assertEqual(http.GONE, response.status_code)

        response = self.api_get('/v2/schemas/tasks')
        self.assertEqual(http.GONE, response.status_code)

    def test_unsupported_task_method_is_rejected(self):
        self.start_server()

        response = self.api_put('/v2/tasks', json={})
        self.assertEqual(http.METHOD_NOT_ALLOWED, response.status_code)
