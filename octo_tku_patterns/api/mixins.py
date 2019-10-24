from rest_framework.decorators import detail_route
from rest_framework.response import Response

from octo.models import CeleryTaskmeta
from octo.api.serializers import CeleryTaskmetaSerializer

import logging
log = logging.getLogger("octo.octologger")


class TaskOperMixin:

    @detail_route(methods=['GET'])
    def get_task_id_status(self, request, pk=None):
        log.debug("<=TestCaseActions> GET show user task status; %s", (request, pk))
        task_by_id = CeleryTaskmeta.objects.filter(task_id__exact=pk)
        log.debug("task_by_id: %s", task_by_id)
        serializer = CeleryTaskmetaSerializer(task_by_id, many=True)
        log.debug("serializer: %s", serializer.data)
        return Response({'task': serializer.data})

    @detail_route(methods=['POST'])
    def post_task(self, request, pk=None):
        log.debug("<=TestCaseActions> POST user task: %s", (request, pk))
        task_by_id = CeleryTaskmeta.objects.filter(task_id__exact=pk)
        log.debug("task_by_id: %s", task_by_id)
        serializer = CeleryTaskmetaSerializer(task_by_id, many=True)
        log.debug("serializer: %s", serializer.data)
        return Response({'task': serializer.data})
