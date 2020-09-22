"""
Input requests - output pages with some results.

"""

# Python logger
import logging
import datetime

from celery.result import AsyncResult
from django import forms
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Max
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template import loader

from django.utils import timezone

from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.dates import ArchiveIndexView, DayArchiveView, TodayArchiveView
from django.views.generic.edit import UpdateView, CreateView
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.cache import cache_control

from django.utils.decorators import method_decorator

from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from octo_tku_patterns.api.serializers import TestLatestDigestAllSerializer, TestHistoryDigestDailySerializer, \
    TestCasesSerializer, TestHistorySerializer, TestLastSerializer

from octo.api.serializers import CeleryTaskmetaSerializer
from octo.cache import OctoCache
from octo.models import CeleryTaskmeta
from octo_tku_patterns.model_views import *
from octo_tku_patterns.models import TestLast, TestHistory, TestCases, TestCasesDetails
from octo_tku_patterns.table_oper import PatternsDjangoTableOper
from octo_tku_patterns.tasks import TPatternRoutine

log = logging.getLogger("octo.octologger")


class Reports:
    """
    Regular reports from test databases for addms, patterns and tests.
    """

    @staticmethod
    def patterns_top_long(request):
        """
        Show top 20 of most slow ot log running tests-patterns.
        Group by ADDM?
        :param request:
        :return:
        """
        patterns_summary = loader.get_template('OLD/top_long_tests.html')

        branch = request.GET.get('branch', 'tkn_main')
        count = request.GET.get('count', 20)

        tests_top_sort = TestLast.objects.filter(time_spent_test__isnull=False).order_by('-time_spent_test')

        try:
            top = int(count)
            slice_top = tests_top_sort[:top]
            subject = ''
        except Exception as e:
            slice_top = []
            subject = 'Error, cannot convert arg "count" to int: {}'.format(e)

        patterns_contxt = dict(LONG_TESTS=slice_top, MAX_LONG=tests_top_sort, BRANCH=branch, COUNT=count,
                               SUBJECT=subject)
        return HttpResponse(patterns_summary.render(patterns_contxt, request))


def compose_selector(request_data):
    selector = dict()
    selector.update(
        test_type=request_data.get('test_type', None),
        tkn_branch=request_data.get('tkn_branch', None),
        change_user=request_data.get('change_user', None),
        change_review=request_data.get('change_review', None),
        change_ticket=request_data.get('change_ticket', None),
        pattern_library=request_data.get('pattern_library', None),
        pattern_folder_name=request_data.get('pattern_folder_name', None),
        test_case_dir=request_data.get('test_case_dir', None),
        pattern_folder_names=request_data.get('pattern_folder_names', []),
        change=request_data.get('change', None),
        # For day, week, month, year
        last_days=request_data.get('last_days', None),
        # Additional select: not used now
        date_from=request_data.get('date_from', None),
        exclude=request_data.get('exclude', None),
        # For test selectors
        addm_name=request_data.get('addm_name', None),
        addm_group=request_data.get('addm_group', None),
        addm_v_int=request_data.get('addm_v_int', None),
        addm_host=request_data.get('addm_host', None),
        addm_ip=request_data.get('addm_ip', None),
        # Better levels: pass, fail, notpass, error, skip
        tst_status=request_data.get('tst_status', None),
        # For single test.py record sorting:
        test_py_path=request_data.get('test_py_path', None),
        # For single test item sorting:
        tst_name=request_data.get('tst_name', None),
        tst_class=request_data.get('tst_class', None),
        tst_age=request_data.get('tst_age', None),
        # For debug
        # To test multiple cases we can just pass their ids:
        cases_ids=request_data.get('cases_ids', []),
    )
    return selector


def tst_status_selector(queryset, sel_opts):
    if sel_opts.get('tst_status') == 'pass':
        queryset = queryset.filter(fails__lte=0, error__lte=0)
    elif sel_opts.get('tst_status') == 'fail':
        queryset = queryset.filter(fails__gte=1)
    elif sel_opts.get('tst_status') == 'notpass':
        queryset = queryset.filter(Q(fails__gte=1) | Q(error__gte=1))
    elif sel_opts.get('tst_status') == 'error':
        queryset = queryset.filter(error__gte=1)
    elif sel_opts.get('tst_status') == 'skip':
        queryset = queryset.filter(skipped__gte=1)
    # # TODO: Add selector for anything NOT as above!
    # elif sel_opts.get('tst_status') == 'else':
    #     # log.debug("use: else")
    #     queryset = queryset.filter(skipped__gte=1)
    else:
        pass
        # log.debug("use: TestLatestDigestAll")
        # queryset = TestLatestDigestAll.objects.all()
    return queryset


# Search for test cases or test cases logs:
class SearchCasesAndLogs(ListView):
    __url_path = '/octo_tku_patterns/search/'
    template_name = 'digests/dev/search_cases_and_logs.html'
    context_object_name = 'search_results'

    @staticmethod
    def query_runner(query):
        queryset_cases = TestCases.objects.filter(
            Q(pattern_folder_name__icontains=query)
            | Q(test_py_path__icontains=query)
            | Q(change__icontains=query)
            | Q(change_desc__icontains=query)
            | Q(change_user__icontains=query)
            | Q(change_review__icontains=query)
            | Q(change_ticket__icontains=query)
        )
        queryset_last = TestLast.objects.filter(
            Q(pattern_folder_name__icontains=query)
            | Q(test_py_path__icontains=query)
            | Q(tst_name__icontains=query)
            | Q(tst_class__icontains=query)
        )
        # queryset_last_digest = TestLatestDigestAll.objects.filter(
        #     Q(pattern_folder_name__icontains=query)
        #     | Q(test_py_path__icontains=query)
        #     | Q(change__icontains=query)
        #     | Q(change_desc__icontains=query)
        #     | Q(change_user__icontains=query)
        #     | Q(change_review__icontains=query)
        #     | Q(change_ticket__icontains=query)
        # )
        # queryset_history_digest = TestHistory.objects.filter(
        #     Q(pattern_folder_name__icontains=query)
        #     | Q(test_py_path__icontains=query)
        #     | Q(tst_name__icontains=query)
        #     | Q(tst_class__icontains=query)
        # )[:500]

        queryset = dict(
            cases=queryset_cases,
            tests_last=queryset_last,
            # tests_history=queryset_history_digest,
            # tests_last_digest=queryset_last_digest,
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super(SearchCasesAndLogs, self).get_context_data(**kwargs)
        addm_names = OctoCache().cache_query(
            AddmDigest.objects.values('addm_name').order_by('-addm_name').distinct())
        context.update(selector=compose_selector(self.request.GET), selector_str='', addm_names=addm_names)
        return context

    def get_queryset(self):
        if self.request.method == 'GET':
            query = self.request.GET.get('q')
            return self.query_runner(query)


# TKU Upload test workbench:
class TKNCasesWorkbenchView(TemplateView):
    __url_path = '/octo_tku_patterns/cases_workbench/'
    template_name = 'cases_workbench.html'
    context_object_name = 'objects'
    title = 'Test Cases Workbench'


# Test reports:
# ADDM Digest summary:
@method_decorator(cache_control(max_age=60 * 5), name='dispatch')
class AddmDigestListView(ListView):
    __url_path = '/octo_tku_patterns/addm_digest/'
    # model = AddmDigest
    template_name = 'digests/addm_digest.html'
    context_object_name = 'addm_digest'

    def get_queryset(self):
        queryset = OctoCache().cache_query(AddmDigest.objects.all())
        return queryset


# Pattern Digest or Cases Digest summary:
@method_decorator(cache_control(max_age=60 * 5), name='dispatch')
class TestLastDigestListView(ListView):
    __url_path = '/octo_tku_patterns/tests_last/'
    template_name = 'digests/tests_last.html'
    context_object_name = 'tests_digest'
    # Check if this is useful case to have queryset loaded on view class init:

    def get_context_data(self, **kwargs):
        context = super(TestLastDigestListView, self).get_context_data(**kwargs)
        # Get unique addm names based on table latest run:
        addm_names = OctoCache().cache_query(
            AddmDigest.objects.values('addm_name').order_by('-addm_name').distinct())
        # TODO: Use regroup for this on page, or move to JS work:
        branch_qs = OctoCache().cache_query(
            TestLatestDigestAll.objects.filter(tkn_branch__isnull=False).values('tkn_branch').annotate(
                total=Count('tkn_branch')).order_by('tkn_branch'))
        test_type_qs = OctoCache().cache_query(
            TestLatestDigestAll.objects.filter(test_type__isnull=False).values('test_type').annotate(
                total=Count('test_type')).order_by('test_type'))
        pattern_library_qs = OctoCache().cache_query(
            TestLatestDigestAll.objects.filter(pattern_library__isnull=False).values('pattern_library').annotate(
                total=Count('pattern_library')).order_by('pattern_library'))
        change_user_qs = OctoCache().cache_query(
            TestLatestDigestAll.objects.filter(change_user__isnull=False).values('change_user').annotate(
                total=Count('change_user')).order_by('change_user'))

        context.update(
            selector=compose_selector(self.request.GET),
            selector_str='',
            addm_names=addm_names,
            branch_qs=branch_qs,
            test_type_qs=test_type_qs,
            pattern_library_qs=pattern_library_qs,
            change_user_qs=change_user_qs,
            tests_digest_json='',
        )

        context['tests_digest'] = context['object_list']
        context['tests_digest_json'] = JSONRenderer().render(
                TestLatestDigestAllSerializer(context['object_list'], many=True).data).decode('utf-8')
        return context

    def get_queryset(self):
        sel_opts = compose_selector(self.request.GET)
        queryset = TestLatestDigestAll.objects.all()
        if sel_opts.get("test_type"):
            queryset = queryset.filter(test_type__exact=sel_opts.get("test_type"))
        else:
            queryset = queryset.filter(pattern_library__isnull=False, pattern_folder_name__isnull=False)
        if sel_opts.get('addm_name'):
            queryset = queryset.filter(addm_name__exact=sel_opts.get('addm_name'))
        if sel_opts.get('tkn_branch'):
            queryset = queryset.filter(tkn_branch__exact=sel_opts.get('tkn_branch'))
        if sel_opts.get('change_user'):
            queryset = queryset.filter(change_user__exact=sel_opts.get('change_user'))
        if sel_opts.get('pattern_library'):
            queryset = queryset.filter(pattern_library__exact=sel_opts.get('pattern_library'))
        queryset = tst_status_selector(queryset, sel_opts)
        return queryset


# Test last table - show single(or all with status) test results for test.py
@method_decorator(cache_control(max_age=60 * 5), name='dispatch')
class TestLastSingleDetailedListView(ListView):
    __url_path = '/octo_tku_patterns/test_details/'
    template_name = 'digests/test_details.html'
    # model = TestLast
    context_object_name = 'test_detail'
    allow_empty = True

    def get_context_data(self, **kwargs):
        addm_names = OctoCache().cache_query(
            AddmDigest.objects.values('addm_name').order_by('-addm_name').distinct())
        branch_qs = OctoCache().cache_query(
            TestLatestDigestAll.objects.filter(tkn_branch__isnull=False).values('tkn_branch').annotate(
                total=Count('tkn_branch')).order_by('tkn_branch'))

        if self.request.method == 'GET':
            context = super(TestLastSingleDetailedListView, self).get_context_data(**kwargs)
            context.update(
                selector=compose_selector(self.request.GET),
                selector_str='',
                addm_names=addm_names,
                branch_qs=branch_qs,
                # HERE: Adding JSON for JS operations
                tests_digest_json='',
            )
            context['test_detail'] = OctoCache().cache_query(
                context['test_detail'])
            context['tests_digest_json'] = JSONRenderer().render(
                    TestLastSerializer(context['test_detail'], many=True).data).decode('utf-8')
            return context

    def get_queryset(self):
        sel_opts = compose_selector(self.request.GET)
        queryset = PatternsDjangoTableOper.sel_dynamical(TestLast, sel_opts=sel_opts)
        return queryset


# Test history table - show single test.py unit historical runs.
@method_decorator(cache_control(max_age=60 * 5), name='dispatch')
class TestItemSingleHistoryListView(ListView):
    __url_path = '/octo_tku_patterns/test_item_history/'
    """
    Show page for
        - one test000 item history log
        - one test.py case history log for 1 day(24hr)
            - browse over days
            - change addm tab saving selected day
    """
    # model = TestHistory
    allow_empty = True
    template_name = 'digests/test_details.html'
    context_object_name = 'test_detail'
    # paginate_by = 500

    def get_context_data(self, **kwargs):
        context = super(TestItemSingleHistoryListView, self).get_context_data(**kwargs)
        addm_names = OctoCache().cache_query(
            AddmDigest.objects.values('addm_name').order_by('-addm_name').distinct())
        branch_qs = OctoCache().cache_query(
            TestHistory.objects.filter(tkn_branch__isnull=False).values('tkn_branch').annotate(
                total=Count('tkn_branch')).order_by('tkn_branch'))
        if self.request.method == 'GET':
            context.update(
                selector=compose_selector(self.request.GET),
                selector_str='',
                branch_qs=branch_qs,
                addm_names=addm_names,
                tests_digest_json='',
            )
            context['test_detail'] = OctoCache().cache_query(
                context['test_detail'])
            context['tests_digest_json'] = JSONRenderer().render(
                    TestHistorySerializer(context['test_detail'], many=True).data).decode('utf-8')
            return context

    def get_queryset(self):
        sel_opts = compose_selector(self.request.GET)
        # Select by: branch, pattern_lib, pattern_folder, tst_calss, tst_name
        queryset = PatternsDjangoTableOper.sel_dynamical(TestHistory, sel_opts=sel_opts)
        return queryset


# Test History Latest View:
@method_decorator(cache_control(max_age=60 * 5), name='dispatch')
class TestHistoryArchiveIndexView(ArchiveIndexView):
    """
    This will show INDEX of everything in TestHistory.
    We don't need this kind of detalisations often. Think something interesting here.
    """
    __url_path = '/octo_tku_patterns/test_history_index/'
    # model = TestHistory
    date_field = "test_date_time"
    allow_future = True
    allow_empty = True
    template_name = 'digests/tests_history_day.html'
    context_object_name = 'test_detail'

    def get_context_data(self, **kwargs):
        branch_qs = OctoCache().cache_query(
            TestHistory.objects.filter(tkn_branch__isnull=False).values('tkn_branch').annotate(
                total=Count('tkn_branch')).order_by('tkn_branch'))
        context = super(TestHistoryArchiveIndexView, self).get_context_data(**kwargs)
        context.update(
            selector=compose_selector(self.request.GET),
            branch_qs=branch_qs,
            selector_str='',
        )
        context['test_detail'] = OctoCache().cache_query(
            context['test_detail'])
        return context

    def get_queryset(self):
        # date = datetime.date.today()
        # log.info(f"day - {date} previous_day - {self.get_previous_day(date)} next_day - {self.get_next_day(date)} previous_month - {self.get_previous_month(date)} next_month - {self.get_next_month(date)}")
        sel_opts = compose_selector(self.request.GET)
        queryset = PatternsDjangoTableOper.sel_dynamical(TestHistory, sel_opts=sel_opts)
        return queryset


# Test History Daily View:
@method_decorator(cache_control(max_age=60 * 5), name='dispatch')
class TestHistoryDayArchiveView(DayArchiveView):
    """
    It will show detailed test logs for selected day.
    Sorting by usual values, such as test_py, tst_status and so on.
    Useful case when want to show particular test case logs by date
        octo_tku_patterns/test_history_day/2019/sep/30/?test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE/SymantecAntiVirus/tests/test.py
        octo_tku_patterns/test_history_day/2020/feb/22/?tst_status=notpass;test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE/Celerra/tests/test.py;
    """
    __url_path = '/octo_tku_patterns/test_history_day/<int:year>/<str:month>/<int:day>/'
    # model = TestHistory
    # queryset = TestHistory.objects.all()
    date_field = "test_date_time"
    allow_future = True
    allow_empty = True
    template_name = 'digests/tests_history_day.html'
    context_object_name = 'test_detail'
    paginate_by = 500

    def get_context_data(self, **kwargs):

        addm_names = OctoCache().cache_query(
            AddmDigest.objects.values('addm_name').order_by('-addm_name').distinct())
        branch_qs = OctoCache().cache_query(
            TestHistory.objects.filter(tkn_branch__isnull=False).values('tkn_branch').annotate(
                total=Count('tkn_branch')).order_by('tkn_branch'))
        if self.request.method == 'GET':
            context = super(TestHistoryDayArchiveView, self).get_context_data(**kwargs)
            context.update(
                selector=compose_selector(self.request.GET),
                selector_str='',
                addm_names=addm_names,
                branch_qs=branch_qs,
            )
            if context['test_detail']:
                context['test_detail'] = OctoCache().cache_query(
                    context['test_detail'])
            return context

    def get_queryset(self):
        sel_opts = compose_selector(self.request.GET)
        queryset = PatternsDjangoTableOper.sel_dynamical(TestHistory, sel_opts=sel_opts)
        return queryset


# Test History Today View:
@method_decorator(cache_control(max_age=60 * 30), name='dispatch')
class TestHistoryTodayArchiveView(TodayArchiveView):
    """
    Such as TestHistoryDayArchiveView but with no specified date, use default as today.
    Can browse then to past/future.
    Cane be specified by selectables and sorting.
    """
    __url_path = '/octo_tku_patterns/test_history_today/'
    # model = TestHistory
    date_field = "test_date_time"
    allow_future = True
    allow_empty = True
    template_name = 'digests/tests_history_day.html'
    context_object_name = 'test_detail'

    def get_context_data(self, **kwargs):
        context = super(TestHistoryTodayArchiveView, self).get_context_data(**kwargs)
        context.update(
            selector=compose_selector(self.request.GET),
            selector_str='',
        )
        context['test_detail'] = OctoCache().cache_query(
            context['test_detail'])
        return context

    def get_queryset(self):
        sel_opts = compose_selector(self.request.GET)
        queryset = PatternsDjangoTableOper.sel_dynamical(TestHistory, sel_opts=sel_opts)
        return queryset


# Test History Digest Today View:
@method_decorator(cache_control(max_age=60 * 30), name='dispatch')
class TestHistoryDigestTodayView(TodayArchiveView):
    """
    PLAN: Should show digest as usual, but locked to today's date, it could possible be used as default digest
    but with historical browsing past\future. Can be detailed by statuses, branch - as usual TestLast Digest view?
    TODO: Use: https://stackoverflow.com/questions/4631865/caching-query-results-in-django

    """
    __url_path = '/octo_tku_patterns/test_history_digest_today/'
    # model = TestHistoryDigestDaily
    date_field = "test_date_time"
    allow_future = True
    allow_empty = True
    template_name = 'digests/tests_last.html'
    sel_opts = False
    context_object_name = 'tests_digest'

    def get_context_data(self, **kwargs):
        branch_qs = OctoCache().cache_query(
            TestLatestDigestAll.objects.filter(tkn_branch__isnull=False).values('tkn_branch').annotate(
                total=Count('tkn_branch')).order_by('tkn_branch'))
        addm_names = OctoCache().cache_query(
            AddmDigest.objects.values('addm_name').order_by('-addm_name').distinct())
        test_type_qs = OctoCache().cache_query(
            TestLatestDigestAll.objects.filter(test_type__isnull=False).values('test_type').annotate(
                total=Count('test_type')).order_by('test_type'))
        pattern_library_qs = OctoCache().cache_query(
            TestLatestDigestAll.objects.filter(pattern_library__isnull=False).values('pattern_library').annotate(
                total=Count('pattern_library')).order_by('pattern_library'))
        change_user_qs = OctoCache().cache_query(
            TestLatestDigestAll.objects.filter(change_user__isnull=False).values('change_user').annotate(
                total=Count('change_user')).order_by('change_user'))

        if self.request.method == 'GET':
            context = super(TestHistoryDigestTodayView, self).get_context_data(**kwargs)
            context.update(
                SUBJECT='Test History Digest day',
                selector=compose_selector(self.request.GET),
                selector_str='',
                addm_names=addm_names,
                branch_qs=branch_qs,
                test_type_qs=test_type_qs,
                pattern_library_qs=pattern_library_qs,
                change_user_qs=change_user_qs,
                tests_digest_json='',
            )
            # NOTE: This should be auto-cache-able, so apache do not kill request on timeout
            context['tests_digest'] = context['tests_digest']
            context['tests_digest_json'] = TestHistoryDigestDailySerializer(context["object_list"], many=True).data
            return context

    def get_queryset(self):
        if not self.sel_opts:
            self.sel_opts = compose_selector(self.request.GET)

        if self.sel_opts.get("test_type"):
            queryset = TestHistoryDigestDaily.objects.filter(test_type__exact=self.sel_opts.get("test_type"))
        else:
            queryset = TestHistoryDigestDaily.objects.filter(pattern_library__isnull=False,
                                                             pattern_folder_name__isnull=False)

        if self.sel_opts.get('addm_name'):
            queryset = queryset.filter(addm_name__exact=self.sel_opts.get('addm_name'))
        if self.sel_opts.get('tkn_branch'):
            queryset = queryset.filter(tkn_branch__exact=self.sel_opts.get('tkn_branch'))
        if self.sel_opts.get('change_user'):
            queryset = queryset.filter(change_user__exact=self.sel_opts.get('change_user'))
        if self.sel_opts.get('pattern_library'):
            queryset = queryset.filter(pattern_library__exact=self.sel_opts.get('pattern_library'))
        queryset = tst_status_selector(queryset, self.sel_opts)
        return queryset


# Test History Digest Daily View:
@method_decorator(cache_control(max_age=60 * 30), name='dispatch')
class TestHistoryDigestDailyView(DayArchiveView):
    __url_path = '/octo_tku_patterns/test_history_digest_day/'
    # model = TestHistoryDigestDaily
    date_field = "test_date_time"
    allow_future = True
    allow_empty = True
    template_name = 'digests/tests_last.html'
    context_object_name = 'tests_digest'

    def get_context_data(self, **kwargs):
        addm_names = OctoCache().cache_query(
            AddmDigest.objects.values('addm_name').order_by('-addm_name').distinct())
        if self.request.method == 'GET':
            context = super(TestHistoryDigestDailyView, self).get_context_data(**kwargs)
            context.update(
                selector=compose_selector(self.request.GET),
                selector_str='',
                addm_names=addm_names,
                tests_digest_json='',
            )
            # log.debug(f"Test digest history day query: {context['object_list'].query}")
            context['tests_digest'] = context['tests_digest']
            context['tests_digest_json'] = JSONRenderer().render(
                    TestLatestDigestAllSerializer(context['tests_digest'], many=True).data).decode('utf-8')
            return context

    def get_queryset(self):
        sel_opts = compose_selector(self.request.GET)
        queryset = TestHistoryDigestDaily.objects.all()

        if sel_opts.get('addm_name'):
            queryset = queryset.filter(addm_name__exact=sel_opts.get('addm_name'))
        if sel_opts.get('tkn_branch'):
            queryset = queryset.filter(tkn_branch__exact=sel_opts.get('tkn_branch'))
        if sel_opts.get('change_user'):
            queryset = queryset.filter(change_user__exact=sel_opts.get('change_user'))

        queryset = tst_status_selector(queryset, sel_opts)
        return queryset


# Dev Test History Digest WeekEnd:


# Cases
@method_decorator(cache_control(max_age=60 * 5), name='dispatch')
class TestCasesListView(ListView):
    __url_path = '/octo_tku_patterns/test_cases/'
    # model = TestCases
    # queryset = TestCases.objects.all()
    template_name = 'cases_groups/cases/cases_table.html'
    context_object_name = 'test_cases'
    paginate_by = 600

    def get_context_data(self, **kwargs):
        context = super(TestCasesListView, self).get_context_data(**kwargs)
        debug = self.request.GET.get('debug', False)

        branch_qs = OctoCache().cache_query(
            TestCases.objects.filter(tkn_branch__isnull=False).values('tkn_branch').annotate(
                total=Count('tkn_branch')).order_by('tkn_branch'))
        test_type_qs = OctoCache().cache_query(
            TestCases.objects.filter(test_type__isnull=False).values('test_type').annotate(
                total=Count('test_type')).order_by('test_type'))
        pattern_library_qs = OctoCache().cache_query(
            TestCases.objects.filter(pattern_library__isnull=False).values('pattern_library').annotate(
                total=Count('pattern_library')).order_by('pattern_library'))

        # TODO: Get test cases groups by REST
        context.update(
            selector=compose_selector(self.request.GET),
            selector_str='',
            branch_qs=branch_qs,
            test_type_qs=test_type_qs,
            pattern_library_qs=pattern_library_qs,
            test_cases_json='',
            debug=debug,
        )
        # NOTE: This check may be resolving the query. It's fast, but check later.
        if context['test_cases']:
            context['test_cases'] = OctoCache().cache_query(
                context['test_cases'])
            context['test_cases_json'] = OctoCache().cache_item(
                JSONRenderer().render(TestCasesSerializer(context["test_cases"], many=True).data).decode('utf-8'),
                hkey='TestCasesListView_tests_test_cases_json', key='TestCases')
        return context

    def get_queryset(self):
        sel_opts = compose_selector(self.request.GET)
        sel_opts.pop('tst_status')
        queryset = PatternsDjangoTableOper.sel_dynamical(TestCases, sel_opts=sel_opts)

        if sel_opts.pop('last_days') == '90':
            key_group = TestCasesDetails.objects.get(title__exact='key')
            included = key_group.test_cases.values('id')
            key_cases = PatternsDjangoTableOper.sel_dynamical(TestCases, sel_opts=sel_opts)
            key_cases = key_cases.filter(id__in=included)
            queryset = queryset | key_cases

        # Can be sorted by: branch, library, user, change number, test_type, review, JIRA, maybe: group
        # if sel_opts.get('test_type'):
        #     queryset = queryset.filter(test_type__exact=sel_opts.get('test_type'))
        # if sel_opts.get('tkn_branch'):
        #     queryset = queryset.filter(tkn_branch__exact=sel_opts.get('tkn_branch'))
        # if sel_opts.get('change_user'):
        #     queryset = queryset.filter(change_user__exact=sel_opts.get('change_user'))
        # if sel_opts.get('change_review'):
        #     queryset = queryset.filter(change_review__exact=sel_opts.get('change_review'))
        # if sel_opts.get('change_ticket'):
        #     queryset = queryset.filter(change_ticket__exact=sel_opts.get('change_ticket'))
        # if sel_opts.get('pattern_library'):
        #     queryset = queryset.filter(pattern_library__exact=sel_opts.get('pattern_library'))
        return queryset


class TestCaseDetailView(DetailView):
    __url_path = '/octo_tku_patterns/test_case/<int:pk>/'
    template_name = 'cases_groups/cases/case_single.html'
    context_object_name = 'case'
    model = TestCases

    def get_context_data(self, **kwargs):
        context = super(TestCaseDetailView, self).get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context


# Cases groups
@method_decorator(cache_control(max_age=60 * 5), name='dispatch')
class TestCasesUpdateView(UpdateView):
    __url_path = '/octo_tku_patterns/test_case/change/<int:pk>/'
    template_name = 'cases_groups/cases/case_update_create.html'
    model = TestCases
    fields = (
        'test_type',
        'tkn_branch',
        'pattern_library',
        'pattern_folder_name',
        'pattern_folder_path',
        'pattern_library_path',
        'test_case_dir',
        'change',
        'change_desc',
        'change_user',
        'change_review',
        'change_ticket',
        'change_time',
        'test_case_depot_path',
        'test_py_path',
        'test_py_path_template',
        'test_dir_path',
        'test_dir_path_template',
        'test_time_weight',
    )
    # readonly_fields = ('created_time', 'change_time')
    success_url = 'test_case'
    template_name_suffix = '_update_form'

    def get_form(self, **kwargs):
        form = super(TestCasesUpdateView, self).get_form()
        form.fields['change_desc'].widget = forms.widgets.Textarea(attrs={'rows': 10, 'cols': 80})
        form.fields['pattern_folder_path'].widget = forms.widgets.TextInput(attrs={'size': 90})
        form.fields['pattern_library_path'].widget = forms.widgets.TextInput(attrs={'size': 90})
        form.fields['test_case_dir'].widget = forms.widgets.TextInput(attrs={'size': 90})
        form.fields['test_case_depot_path'].widget = forms.widgets.TextInput(attrs={'size': 90})
        form.fields['test_py_path'].widget = forms.widgets.TextInput(attrs={'size': 100})
        form.fields['test_py_path_template'].widget = forms.widgets.TextInput(attrs={'size': 90})
        form.fields['test_dir_path'].widget = forms.widgets.TextInput(attrs={'size': 90})
        form.fields['test_dir_path_template'].widget = forms.widgets.TextInput(attrs={'size': 90})
        form.fields['change_time'].widget = forms.widgets.DateTimeInput()
        return form

    def form_valid(self, form):
        post = form.save(commit=False)
        post.save()
        return redirect('test_case', pk=post.pk)


class TestCasesDetailsListView(ListView):
    __url_path = '/octo_tku_patterns/test_cases_groups/'
    # queryset = TestCases.objects.all().order_by('-change_time').values()
    # model = TestCasesDetails
    context_object_name = 'groups'
    template_name = 'cases_groups/groups/groups_table.html'
    paginate_by = 50

    def get_queryset(self):
        queryset = TestCasesDetails.objects.all().order_by('-changed_date')
        return queryset


class TestCasesDetailsDetailView(DetailView):
    __url_path = '/octo_tku_patterns/test_cases_group/<int:pk>/'
    template_name = 'cases_groups/groups/group_single.html'
    context_object_name = 'group'
    model = TestCasesDetails

    def get_context_data(self, **kwargs):
        context = super(TestCasesDetailsDetailView, self).get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context


@method_decorator(login_required, name='dispatch')
class TestCasesDetailsUpdateView(UpdateView):
    __url_path = '/octo_tku_patterns/test_cases_group/change/<int:pk>/'
    template_name = 'cases_groups/groups/group_update_create.html'
    model = TestCasesDetails
    fields = (
        'title',
        'author',
        'test_cases',
        'description',
    )

    success_url = 'test_cases_group'
    template_name_suffix = '_update_form'

    def get_form(self, **kwargs):
        form = super(TestCasesDetailsUpdateView, self).get_form()
        form.fields['title'].widget = forms.widgets.TextInput(
            attrs={'class': 'form-control', 'id': 'title', 'type': 'text'})
        form.fields['description'].widget = forms.widgets.Textarea(
            attrs={'class': 'form-control', 'id': 'description', 'type': 'text', 'rows': 5})

        return form

    def form_valid(self, form):
        post = form.save(commit=False)
        post.changed_date = timezone.now()
        post.title = post.title.replace(' ', '_').lower()
        post.save()
        form.save_m2m()
        return redirect('test_cases_group', pk=post.pk)


@method_decorator(login_required, name='dispatch')
class TestCasesDetailsCreateView(CreateView):
    __url_path = '/octo_tku_patterns/test_cases_group/create/'
    template_name = 'cases_groups/groups/group_update_create.html'
    model = TestCasesDetails
    fields = (
        'title',
        'author',
        'test_cases',
        'description',
    )

    success_url = 'test_cases_group'
    template_name_suffix = '_update_form'

    def get_form(self, **kwargs):
        form = super(TestCasesDetailsCreateView, self).get_form()
        form.fields['title'].widget = forms.widgets.TextInput(
            attrs={'class': 'form-control', 'id': 'title', 'type': 'text'})
        form.fields['description'].widget = forms.widgets.Textarea(
            attrs={'class': 'form-control', 'id': 'description', 'type': 'text', 'rows': 5})
        return form

    def form_valid(self, form):
        post = form.save(commit=False)
        post.changed_date = timezone.now()
        post.title = post.title.replace(' ', '_').lower()
        post.save()
        form.save_m2m()
        return redirect('test_cases_group', pk=post.pk)


# Operations:
@method_decorator(login_required, name='dispatch')
class TestCaseRunTestREST(APIView):
    __url_path = '/octo_tku_patterns/test_execute_web/'
    __url_path_alt = '/octo_tku_patterns/user_test_add/'
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request=None):
        task_id = self.request.GET.get('task_id', None)
        # log.debug("<=TestCaseRunTestREST=> GET - retrieve task by task_id: %s", task_id)
        # log.debug("task id by request: %s", task_id)
        # Get task status from celery-app
        if not task_id:
            help_ = dict(
                doc="Run task 't_test_prep'. Task params can be: cases_ids, pattern_folder_names, change, "
                    "change_user, change_review, change_ticket, test_py_path. "
                    "Test modes: test_wipe_run, test_p4_run, test_instant_run"
            )
            return Response(help_)

        tasks = CeleryTaskmeta.objects.filter(task_id__exact=task_id)
        if tasks:
            serializer = CeleryTaskmetaSerializer(tasks, many=True)
            return Response(serializer.data)
        else:
            res = AsyncResult(task_id)
            task_res = dict(
                task_id=task_id,
                status=res.status,
                result=res.result,
                state=res.state,
                args=res.args,
            )
            # log.debug("Task result: %s", task_res)
            return Response([task_res])

    def post(self, request=None):
        selector = compose_selector(self.request.data)
        # json_ = {"tkn_branch": "tkn_main", "pattern_library": "CORE", "pattern_folder_name": "10genMongoDB", "refresh": "1"}
        if any(value for value in selector.values()):
            pass
        else:
            return Response(dict(task_id='Cannot run test without any selection'))

        obj = dict(
            context=dict(selector=selector),
            request=self.request.data,
            user_name=self.request.user.username,
            user_email=self.request.user.email,
        )
        # TaskPrepare(obj).run_tku_patterns()
        t_tag = f'tag=t_test_prep;user_name={self.request.user.username};'
        t_queue = 'w_routines@tentacle.dq2'
        t_routing_key = 'routines.TRoutine.t_test_prep'
        task_added = TPatternRoutine.t_test_prep.apply_async(
            args=[t_tag],
            kwargs=dict(obj=obj),
            queue=t_queue,
            routing_key=t_routing_key,
        )
        return Response(dict(task_id=task_added.id))


# DEVELOPMENT VIEWS:

## View for teams:
class AddmDigestListViewTeams(ListView):
    __url_path = '/octo_tku_patterns/addm_digest_short/'
    model = AddmDigest
    template_name = 'digests/addm_digest_short.html'
    context_object_name = 'addm_digest'


class TestLastDigestListViewShort(TestLastDigestListView):
    __url_path = '/octo_tku_patterns/patterns_digest_short/'
    template_name = 'digests/tests_last_short.html'
    context_object_name = 'tests_digest'


class TestLastDigestListViewBoxes(ListView):
    """
    Grouped by library - view for general reposting for external purposes.

    """
    __url_path = '/octo_tku_patterns/patterns_digest_boxes/'
    template_name = 'digests/tests_last_boxes.html'
    context_object_name = 'tests_digest'

    def get_queryset(self):
        queryset = TestLatestDigestLibShort.objects.all()
        queryset = queryset.filter(pattern_library__isnull=False).order_by('pattern_library')
        return queryset