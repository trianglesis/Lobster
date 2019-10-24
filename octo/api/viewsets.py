
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from octo.api.serializers import CeleryTaskmetaSerializer, PeriodicTaskSerializer
from django_celery_beat.models import PeriodicTask
from octo.models import CeleryTaskmeta

import logging
log = logging.getLogger("octo.octologger")


class CeleryTaskmetaViewSet(viewsets.ModelViewSet):
    queryset = CeleryTaskmeta.objects.all().order_by('-date_done')
    serializer_class = CeleryTaskmetaSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )


class PeriodicTaskViewSet(viewsets.ModelViewSet):
    queryset = PeriodicTask.objects.all().order_by('-date_changed')
    serializer_class = PeriodicTaskSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )
