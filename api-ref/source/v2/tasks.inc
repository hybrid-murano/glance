.. -*- rst -*-

.. _legacy-tasks-api:

Legacy Tasks API
****************

The deprecated Tasks API was removed in the 2027.1 release. The following
endpoints remain routable for client compatibility and return ``410 Gone``:

* ``GET /v2/tasks``
* ``POST /v2/tasks``
* ``GET /v2/tasks/{task_id}``
* ``DELETE /v2/tasks/{task_id}``
* ``GET /v2/schemas/task``
* ``GET /v2/schemas/tasks``

Use the interoperable image import API and
``GET /v2/images/{image_id}/tasks`` instead.
