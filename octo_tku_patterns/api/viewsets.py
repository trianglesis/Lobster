
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action

from rest_framework.permissions import IsAuthenticatedOrReadOnly

from octo_tku_patterns.models import TestCases, TestCasesDetails, TestLast, TestHistory
from octo_tku_patterns.api.serializers import TestCasesSerializer, TestCasesDetailsSerializer, \
    TestLastSerializer, TestHistorySerializer
from octo_tku_patterns.api.mixins import TaskOperMixin

from octo.models import CeleryTaskmeta
from octo.api.serializers import CeleryTaskmetaSerializer

import logging
log = logging.getLogger("octo.octologger")


class TestCasesSerializerViewSet(viewsets.ModelViewSet):
    queryset = TestCases.objects.all().order_by('-change_time')
    serializer_class = TestCasesSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )


class TestCasesDetailsSerializerViewSet(viewsets.ModelViewSet):
    queryset = TestCasesDetails.objects.all().order_by('-changed_date')
    serializer_class = TestCasesDetailsSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )


class TestLastViewSet(viewsets.ModelViewSet):
    queryset = TestLast.objects.all().order_by('-test_date_time')
    serializer_class = TestLastSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )


class TestHistoryViewSet(viewsets.ModelViewSet):
    queryset = TestHistory.objects.all().order_by('-test_date_time')
    serializer_class = TestHistorySerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )


class TestCaseActionsViewSet(TaskOperMixin, viewsets.ViewSet):
    """
    A viewset that provides the standard actions
    """
    queryset = CeleryTaskmeta.objects.all().order_by('id')
    serializer_class = CeleryTaskmetaSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )