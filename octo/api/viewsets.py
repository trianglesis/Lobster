
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from octo.api.serializers import CeleryTaskmetaSerializer, PeriodicTaskSerializer, StandardResultsSetPagination
from django_celery_beat.models import PeriodicTask
from octo.models import CeleryTaskmeta

import logging
log = logging.getLogger("octo.octologger")


class CeleryTaskmetaViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultsSetPagination
    serializer_class = CeleryTaskmetaSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )
    queryset = CeleryTaskmeta.objects.all()

    def get_queryset(self):
        status = self.request.GET.get("status", None)

        queryset = CeleryTaskmeta.objects.all()
        if status:
            queryset = self.queryset.filter(status__exact=status)
        return queryset.order_by('-date_done')


class PeriodicTaskViewSet(viewsets.ModelViewSet):
    serializer_class = PeriodicTaskSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )
    queryset = PeriodicTask.objects.all().order_by('-date_changed')
