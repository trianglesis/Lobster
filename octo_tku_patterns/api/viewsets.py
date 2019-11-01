
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from octo.api.serializers import *

from octo_adm.user_operations import UserCheck

from octo_tku_patterns.models import TestCases, TestCasesDetails, TestLast, TestHistory
from octo_tku_patterns.api.serializers import TestCasesSerializer, TestCasesDetailsSerializer, \
    TestLastSerializer, TestHistorySerializer
from octo_tku_patterns.api.mixins import TaskOperMixin

from octo_tku_patterns.table_oper import PatternsDjangoTableOper
from octo_tku_patterns.views import compose_selector


from octo.models import CeleryTaskmeta
from octo.api.serializers import CeleryTaskmetaSerializer

import logging
log = logging.getLogger("octo.octologger")


class TestCasesSerializerViewSet(viewsets.ModelViewSet):
    queryset = TestCases.objects.all().order_by('change_time')
    serializer_class = TestCasesSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        UserCheck().logator(self.request, 'info', "<=TestCasesSerializerViewSet=> REST is asking for a test case!")
        sel_opts = compose_selector(self.request.GET)
        # Not the best idea: remove inter-selection args, when call this func from another views: octo.views.UserMainPage.get_queryset
        sel_opts.pop('tst_status')
        queryset = PatternsDjangoTableOper.sel_dynamical(TestCases, sel_opts=sel_opts)
        return queryset.order_by('change_time')


class TestCasesDetailsSerializerViewSet(viewsets.ModelViewSet):
    queryset = TestCasesDetails.objects.all().order_by('test_date_time')
    serializer_class = TestCasesDetailsSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )
    pagination_class = StandardResultsSetPagination


class TestLastViewSet(viewsets.ModelViewSet):
    queryset = TestLast.objects.all().order_by('test_date_time')
    serializer_class = TestLastSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        UserCheck().logator(self.request, 'info', "<=TestLastViewSet=> REST is asking fot a test last")
        sel_opts = compose_selector(self.request.GET)
        queryset = PatternsDjangoTableOper.sel_dynamical(TestLast, sel_opts=sel_opts)
        # log.debug("TestLastViewSet queryset explain \n%s", queryset.explain())
        return queryset.order_by('test_date_time')


class TestHistoryViewSet(viewsets.ModelViewSet):
    queryset = TestHistory.objects.all().order_by('test_date_time')
    serializer_class = TestHistorySerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        UserCheck().logator(self.request, 'info', "<=TestHistoryViewSet=> REST is asking fot a test hist")
        sel_opts = compose_selector(self.request.GET)
        # sel_opts.pop('tst_status')
        queryset = PatternsDjangoTableOper.sel_dynamical(TestHistory, sel_opts=sel_opts)
        # queryset = tst_status_selector(queryset, sel_opts)
        # log.debug("TestHistoryViewSet queryset explain \n%s", queryset.explain())
        return queryset.order_by('test_date_time')
