# Copyright 2013 IBM Corp.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import webob.exc

from glance.common import wsgi
from glance.i18n import _


class TasksController(object):
    """Return Gone for the deprecated public Tasks API."""

    def gone(self, req, **kwargs):
        msg = _("The Tasks API is no longer available. Use the "
                "interoperable image import API and "
                "GET /v2/images/{image_id}/tasks instead.")
        raise webob.exc.HTTPGone(explanation=msg,
                                 request=req,
                                 content_type='text/plain')


class RequestDeserializer(wsgi.JSONRequestDeserializer):
    """Avoid parsing deprecated request bodies before returning Gone."""

    def default(self, request):
        return {}


def create_resource():
    return wsgi.Resource(TasksController(), RequestDeserializer())
