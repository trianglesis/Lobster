"""
Input requests - output pages with some results.

"""

import datetime
from django.utils import timezone
from operator import itemgetter

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.db.models import Max, Q
from django.http import HttpResponse
from django.template import loader

from django import forms
from django.utils.decorators import method_decorator

from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.edit import UpdateView, CreateView
from django.views.generic.dates import ArchiveIndexView, DayArchiveView, TodayArchiveView, DayMixin, MonthMixin, YearMixin

from octo.octo_celery import app
from celery.result import AsyncResult

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated

from rest_framework.decorators import api_view
from rest_framework import authentication, permissions

from octo_adm.user_operations import UserCheck
from octo_adm.request_service import SelectorRequestsHelpers

from run_core.addm_operations import ADDMOperations

from octo.helpers.tasks_run import Runner

from octo.helpers.tasks_helpers import TMail
from octo.helpers.tasks_mail_send import Mails

from octo.models import CeleryTaskmeta
from octo.api.serializers import CeleryTaskmetaSerializer

from octo_tku_patterns.models import TestLast, TestHistory, TestCases, TestCasesDetails
from octo_tku_patterns.model_views import *

from octo_tku_patterns.table_oper import PatternsDjangoTableOper, PatternsDjangoModelRaw
from octo_tku_patterns.tasks import TPatternRoutine, TPatternParse, TaskPrepare
from octo_tku_patterns.user_test_balancer import OptionalTestsSelect

# from octo_tku_patterns.task_prep import TaskPrepare

# Python logger
import logging

log = logging.getLogger("octo.octologger")


class TestRuns:

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.test_run', login_url='/unauthorized_banner/')
    def test_execute_web(request):
        """

            This func run test or list of tests in Celery job as one long chain of tests
            for each ADDM.

            Tests wouldn't mix between workers because they run in separate loop for each ADDM,
            but Celery will treat this as one long job.

        :param request:
        :return:
        """
        user_name, user_string = UserCheck().user_string_f(request)
        page_widgets = loader.get_template('small_blocks/user_test_added.html')
        log.debug("<=WEB OCTO AMD=> test_execute_web(): %s", user_string)

        # TODO: Change selector arg to depot path or test.py path?
        pattern_library = request.GET.get('pattern_library', False)
        pattern_folder = request.GET.get('pattern_folder', False)
        branch = request.GET.get('tkn_branch', False)
        addm_group = request.GET.get('addm_group', None)
        refresh = request.GET.get('refresh', False)
        wipe = request.GET.get('wipe', False)
        fake_run = request.GET.get('fake_run', False)
        test_function = request.GET.get('test_function', '')  # request will clear extra symbol '+'

        # lock=True;  - is not used, to allow other users to run tests on the same worker!
        task_string = 'tag=t_routine_user_tests;type=routine;branch={branch};' \
                      'addm_group={addm_group};user_name={user_name};refresh={refresh};{pattern_library}/{pattern_folder_name}'
        t_tag_d = task_string.format(branch=branch,
                                     user_name=user_name,
                                     addm_group=addm_group,
                                     refresh=refresh,
                                     pattern_library=pattern_library,
                                     pattern_folder_name=pattern_folder)

        user_email = [request.user.email]

        widgets = dict(
            SUBJECT='Selected test queued! Wait for initial mail.',
            OPTION_VALUES=dict(
                USER_NAME=user_name,
                BRANCH=branch,
                CUSTOM_TEST=pattern_folder,
                TEST_FUNCTION=test_function,
                ADDM_GROUP=addm_group,
                REFRESH=refresh,
                USER_EMAIL=user_email,
                PATTERN_LIBRARY=pattern_library
            ))

        log.debug("<=OCTO ADM=> User test test_execute_web: \n%s", t_tag_d)
        Runner.fire_t(TPatternRoutine.t_routine_user_tests, fake_run=fake_run,
                      t_args=[t_tag_d], t_kwargs=dict(pattern_library=pattern_library,
                                                      pattern_folder=pattern_folder,
                                                      test_function=test_function,
                                                      branch=branch,
                                                      addm_group=addm_group,
                                                      refresh=refresh,
                                                      wipe=wipe,
                                                      fake_run=fake_run,
                                                      user_name=user_name,
                                                      user_email=user_email)
                      )
        return HttpResponse(page_widgets.render(widgets, request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.routine_run', login_url='/unauthorized_banner/')
    def manual_exec_night_run_task(request):
        """
        Run full scenario for typical night run.
        Execute night test routine.
        This routine should be the same for all times.
        Only use -exclude arg and addm list.

        :param request:
        :return:
        """
        user_name, user_string = UserCheck().user_string_f(request)
        log.debug("<=WEB OCTO AMD=> manual_exec_night_run_task(): %s", user_string)
        page_widgets = loader.get_template('service/task-action-request-added-started.html')

        fake_run = request.GET.get('fake_run', False)
        branch = request.GET.get('branch', None)
        send_mail = request.GET.get('send_mail', False)
        addm_group_l = request.GET.get('addm_group', None)
        excluded_seq = request.GET.get('excluded_seq', None)
        sel_patterns = request.GET.get('sel_patterns', None)

        # Debug:
        test_output_mode = request.GET.get('test_output_mode', False)

        tsk_msg = 'tag=night_routine;lock=True;type=routine;user_name={u_name};excl={excl};use_patterns={sel_p}|{branch} on: {addms}'
        t_tag = tsk_msg.format(branch=branch, u_name=user_name,
                               addms=str(addm_group_l), excl=str(excluded_seq), sel_p=str(sel_patterns))

        if send_mail:
            user_email = [request.user.email]
            TMail().long_r(mode='start', r_type='Night web', user_email=user_email, start_args=(branch, addm_group_l),
                           addm_group=addm_group_l, branch=branch, start_time=datetime.datetime.now())

        Runner.fire_t(TPatternRoutine.t_routine_night_tests, fake_run=fake_run,
                      t_args=[t_tag],
                      t_kwargs=dict(
                          branch=branch,
                          user_name=user_name,
                          addm_group=addm_group_l,
                          test_output_mode=test_output_mode,
                          excluded_seq=excluded_seq,
                          sel_patterns=sel_patterns)
                      )

        subject = "'{0} {1}'. Manual night test run has been added to queue!.".format(branch, addm_group_l)
        widgets = dict(SUBJECT=subject)
        return HttpResponse(page_widgets.render(widgets, request))


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
        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=VIEW SELECTOR=> patterns_top_long(): %s", user_str)
        branch = request.GET.get('branch', 'tkn_main')
        count = request.GET.get('count', 20)

        tests_top_sort = PatternsDjangoModelRaw().select_latest_long_tests(branch)

        try:
            top = int(count)
            slice_top = tests_top_sort[:top]
            subject = ''
        except Exception as e:
            slice_top = []
            subject = 'Error, cannot convert arg "count" to int: {}'.format(e)

        patterns_contxt = dict(LONG_TESTS=slice_top, BRANCH=branch, COUNT=count, SUBJECT=subject)
        return HttpResponse(patterns_summary.render(patterns_contxt, request))


class PatternsService:

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.test_run', login_url='/unauthorized_banner/')
    def sync_patterns(request):
        """
        Sync new pattern and test files to selected ADDM group. OR sync everything to everything

        :return:
        """
        page_widgets = loader.get_template('service/task-action-request-added-started.html')
        user_name, user_string = UserCheck().user_string_f(request)
        log.debug("<=WEB OCTO AMD=> sync_patterns(): %s", user_string)
        addm_group = request.GET.get('addm_group', None)

        addm_set = ADDMOperations().select_addm_set(addm_group=addm_group)
        # noinspection PyUnusedLocal
        # TODOL Check for queryset

        task = Runner.fire_t(TPatternParse().t_addm_rsync_threads,
                             t_queue=addm_set[0]['addm_group'] + '@tentacle.dq2',
                             t_args=['tag=t_addm_rsync_threads;type=request;user={};'.format(user_name)],
                             t_kwargs=dict(addm_items=addm_set),
                             t_routing_key='TExecTest.t_addm_rsync_threads.{0}'.format(addm_set[0]['addm_group']))
        # Get task ID?
        subject = "User request: '{}' {}. " \
                  "Will sync from Octopus NFS:\n" \
                  "from '/usr/tideway/TKU/addm/' to '/usr/tideway/SYNC/addm/'\n" \
                  "from '/usr/tideway/TKU/python/testutils/' to '/usr/tideway/python/testutils/'\n" \
                  "from '/usr/tideway/TKU/utils/' to '/usr/tideway/utils/'\n" \
                  "for each ADDM VM from DB if group {}".format("sync_patterns", 'info_string-dev', addm_group)
        Mails.short(subject='sync_patterns', body=subject, send_to=[request.user.email])
        return HttpResponse(page_widgets.render(dict(SUBJECT=subject), request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.test_run', login_url='/unauthorized_banner/')
    def parse_patterns_user(request):
        """
        Run sync of all files from depot to addms, and parse changes:
            - p4 sync smart (only latest between changes)
            - p4 fstat\\changes (get changed files and infos)
            - addm sync - to rsync all files on selected addm groups.
        If group is not set - sync all available addms

        :return:
        """
        page_widgets = loader.get_template('service/task-action-request-added-started.html')
        user_name, user_string = UserCheck().user_string_f(request)

        branch = request.GET.get('branch', False)
        addm_group = request.GET.get('addm_group', None)
        sync_shares = request.GET.get('sync_shares', False)
        log.debug("<=WEB OCTO AMD=>   user_manual_parse_sync(): %s Group: %s", user_string, addm_group)
        if branch:
            info_string = dict(branch=branch, user_name=user_name, addm_group=addm_group)

            # lock=True;  - is not used, to allow other users to run tests on the same worker!
            tsk_msg = 'tag=user_parse_patterns;type=routine;user_name={user_name};sync_shares={sync_shares} ' \
                      '| on: "{addm_group}" by: {user_name}'
            t_tag = tsk_msg.format(user_name=user_name,
                                   addm_group=addm_group,
                                   sync_shares=sync_shares)

            Runner.fire_t(TPatternParse.t_routine_user_parse_patt,
                          t_args=[t_tag],
                          t_kwargs=dict(branch=branch, info_string=info_string, addm_group=addm_group,
                                        sync_shares=sync_shares, user_name=user_name))
            if addm_group:
                subject = "User request: '{}' {}. For selected group.".format("parse_n_sync", info_string)
            else:
                subject = "User request: '{}' {}. For all addms!".format("parse_n_sync", info_string)
            Mails.short(subject=subject, body=subject, send_to=[request.user.email])
            return HttpResponse(page_widgets.render(dict(SUBJECT=subject), request))
        else:
            # No branch selected - will run for each branch:
            for branch in ['tkn_main', 'tkn_ship']:
                info_string = dict(branch=branch, user_name=user_name, addm_group=addm_group)
                # lock=True;  - is not used, to allow other users to run tests on the same worker!
                tsk_msg = 'tag=user_parse_patterns;type=routine;user_name={user_name};sync_shares={sync_shares} ' \
                          '| on: "{addm_group}" by: {user_name}'
                t_tag = tsk_msg.format(user_name=user_name, addm_group=addm_group, sync_shares=sync_shares)
                Runner.fire_t(TPatternParse.t_routine_user_parse_patt,
                              t_args=[t_tag],
                              t_kwargs=dict(branch=branch, info_string=info_string, addm_group=addm_group,
                                            sync_shares=sync_shares, user_name=user_name))

            if addm_group:
                subject = "User request: '{}' {}. For selected group.".format("parse_n_sync", info_string)
            else:
                subject = "User request: '{}' {}. For all addms and branches!".format("parse_n_sync", info_string)

            Mails.short(subject=subject, body=subject, send_to=[request.user.email])
            return HttpResponse(page_widgets.render(dict(SUBJECT=subject), request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.service_run', login_url='/unauthorized_banner/')
    def patterns_weight_compute(request):
        """
        Execute task which compute patterns tests time weight.
        :param request:
        :return:
        """
        user_name, user_string = UserCheck().user_string_f(request)
        page_widgets = loader.get_template('service/task-action-request-added-started.html')
        last_days = request.GET.get('last_days', 7)
        subject = 'Run pattern test weight compute task. Use last days {}. By {}'.format(last_days, user_string)
        Runner.fire_t(TPatternParse.t_pattern_weight_index,
                      t_args=[subject], t_kwargs=dict(last_days=last_days))
        return HttpResponse(page_widgets.render(dict(SUBJECT=subject), request))


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
        # log.debug("use: pass_only")
        queryset = queryset.filter(fails__lte=0, error__lte=0)
    elif sel_opts.get('tst_status') == 'fail':
        # log.debug("use: fail_only")
        queryset = queryset.filter(fails__gte=1)
    elif sel_opts.get('tst_status') == 'notpass':
        # log.debug("use: not_pass_only")
        queryset = queryset.filter(Q(fails__gte=1) | Q(error__gte=1))
    elif sel_opts.get('tst_status') == 'error':
        # log.debug("use: error_only")
        queryset = queryset.filter(error__gte=1)
    elif sel_opts.get('tst_status') == 'skip':
        # log.debug("use: skip_only")
        queryset = queryset.filter(skipped__gte=1)
    else:
        log.debug("use: TestLatestDigestAll")
        # queryset = TestLatestDigestAll.objects.all()
    return queryset


# Seach for test cases or test cases logs:
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
        queryset_last_digest = TestLatestDigestAll.objects.filter(
            Q(pattern_folder_name__icontains=query)
            | Q(test_py_path__icontains=query)
            | Q(change__icontains=query)
            | Q(change_desc__icontains=query)
            | Q(change_user__icontains=query)
            | Q(change_review__icontains=query)
            | Q(change_ticket__icontains=query)
        )

        queryset = dict(
            cases=queryset_cases,
            tests_last=queryset_last,
            tests_last_digest=queryset_last_digest,
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super(SearchCasesAndLogs, self).get_context_data(**kwargs)
        addm_names = AddmDigest.objects.values('addm_name').order_by('-addm_name').distinct()
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
class AddmDigestListView(ListView):
    __url_path = '/octo_tku_patterns/addm_digest/'
    model = AddmDigest
    template_name = 'digests/addm_digest.html'
    context_object_name = 'addm_digest'


# Pattern Digest or Cases Digest summary:
class TestLastDigestListView(ListView):
    __url_path = '/octo_tku_patterns/tests_last/'
    template_name = 'digests/tests_last.html'
    context_object_name = 'tests_digest'
    # Check if this is usefule case to have queryset loaded on view class init:

    def get_context_data(self, **kwargs):
        # UserCheck().logator(self.request, 'info', "<=TestLastDigestListView=> get_context_data")

        # Get unique addm names based on table latest run:
        addm_names = AddmDigest.objects.values('addm_name').order_by('-addm_name').distinct()
        # log.debug("TestLastDigestListView addm_names explain \n%s", addm_names.explain())

        if self.request.method == 'GET':
            # log.debug("METHOD: GET - show test cases digest")
            context = super(TestLastDigestListView, self).get_context_data(**kwargs)
            context.update(selector=compose_selector(self.request.GET), selector_str='', addm_names=addm_names)
            return context

    def get_queryset(self):
        # UserCheck().logator(self.request, 'info', "<=TestLastDigestListView=> get_queryset")
        sel_opts = compose_selector(self.request.GET)
        queryset = TestLatestDigestAll.objects.all()

        if sel_opts.get('addm_name'):
            # log.debug("use: addm_name")
            queryset = queryset.filter(addm_name__exact=sel_opts.get('addm_name'))
        if sel_opts.get('tkn_branch'):
            # log.debug("use: tkn_branch")
            queryset = queryset.filter(tkn_branch__exact=sel_opts.get('tkn_branch'))
        if sel_opts.get('change_user'):
            # log.debug("use: change_user")
            queryset = queryset.filter(change_user__exact=sel_opts.get('change_user'))

        queryset = tst_status_selector(queryset, sel_opts)
        # log.debug("TestLastDigestListView queryset explain \n%s", queryset.explain())
        return queryset


# Test last table - show single(or all with status) test results for test.py
class TestLastSingleDetailedListView(ListView):
    __url_path = '/octo_tku_patterns/test_details/'
    template_name = 'digests/test_details.html'
    context_object_name = 'test_detail'
    model = TestLast
    allow_empty = True

    def get_context_data(self, **kwargs):
        # UserCheck().logator(self.request, 'info', "<=TestLastSingleDetailedListView=> test single table context")
        # Get unique addm names based on table latest run:
        addm_names = AddmDigest.objects.values('addm_name').order_by('-addm_name').distinct()
        log.debug("Set of addm_names: %s", addm_names)

        if self.request.method == 'GET':
            # log.debug("<=TestLastSingleDetailedListView=> METHOD: GET - show tests items")
            context = super(TestLastSingleDetailedListView, self).get_context_data(**kwargs)
            context.update(selector=compose_selector(self.request.GET), selector_str='', addm_names=addm_names)
            return context

    def get_queryset(self):
        # UserCheck().logator(self.request, 'info', "<=TestLastSingleDetailedListView=> test cases table queryset")
        sel_opts = compose_selector(self.request.GET)
        queryset = PatternsDjangoTableOper.sel_dynamical(TestLast, sel_opts=sel_opts)
        # log.debug("TestLastSingleDetailedListView queryset explain \n%s", queryset.explain())
        # log.debug("<=TestLastSingleDetailedListView=> selected len: %s query: \n%s", queryset.count(), queryset.query)
        return queryset


# Test history table - show single test.py unit historical runs.
class TestItemSingleHistoryListView(ListView):
    __url_path = '/octo_tku_patterns/test_item_history/'
    """
    Show page for
        - one test000 item history log
        - one test.py case history log for 1 day(24hr)
            - browse over days
            - change addm tab saving selected day
    """
    model = TestHistory
    allow_empty = True
    template_name = 'digests/test_details.html'
    context_object_name = 'test_detail'
    # paginate_by = 500

    def get_context_data(self, **kwargs):
        # UserCheck().logator(self.request, 'info', "<=TestItemSingleHistoryListView=> test item table context")
        context = super(TestItemSingleHistoryListView, self).get_context_data(**kwargs)
        # Get unique addm names based on table latest run:
        addm_names = AddmDigest.objects.values('addm_name').order_by('-addm_name').distinct()
        # log.debug("Set of addm_names: %s", addm_names)

        if self.request.method == 'GET':
            # log.debug("<=TestItemSingleHistoryListView=> METHOD: GET - show single test case item tests")
            context.update(selector=compose_selector(self.request.GET), selector_str='', addm_names=addm_names)
            return context

    def get_queryset(self):
        # UserCheck().logator(self.request, 'info', "<=TestItemSingleHistoryListView=> test cases table queryset")
        sel_opts = compose_selector(self.request.GET)
        # sel_opts.pop('tst_status')
        queryset = PatternsDjangoTableOper.sel_dynamical(TestHistory, sel_opts=sel_opts)
        # queryset = tst_status_selector(queryset, sel_opts)
        # log.debug("TestItemSingleHistoryListView queryset explain \n%s", queryset.explain())
        return queryset


# Test History Latest View:
class TestHistoryArchiveIndexView(ArchiveIndexView):
    __url_path = '/octo_tku_patterns/test_history_index/'
    model = TestHistory
    date_field = "test_date_time"
    allow_future = False
    allow_empty = True
    template_name = 'digests/tests_history_day.html'
    context_object_name = 'test_detail'

    def get_context_data(self, **kwargs):
        UserCheck().logator(self.request, 'info', "<=TestHistoryArchiveIndexView=> test history index")
        context = super(TestHistoryArchiveIndexView, self).get_context_data(**kwargs)
        context.update(selector=compose_selector(self.request.GET), selector_str='')
        return context


# Test History Daily View:
class TestHistoryDayArchiveView(DayArchiveView):
    """
    http://127.0.0.1:8000/octo_tku_patterns/test_history_day/2019/sep/30/?test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE/SymantecAntiVirus/tests/test.py
    """
    __url_path = '/octo_tku_patterns/test_history_day/<int:year>/<str:month>/<int:day>/'
    model = TestHistory
    date_field = "test_date_time"
    allow_future = False
    allow_empty = True
    template_name = 'digests/tests_history_day.html'
    context_object_name = 'test_detail'

    def get_context_data(self, **kwargs):
        # UserCheck().logator(self.request, 'info', "<=TestHistoryDayArchiveView=> test history by day")
        # Get unique addm names based on table latest run:
        addm_names = AddmDigest.objects.values('addm_name').order_by('-addm_name').distinct()
        # log.debug("Set of addm_names: %s", addm_names)
        if self.request.method == 'GET':
            context = super(TestHistoryDayArchiveView, self).get_context_data(**kwargs)
            context.update(selector=compose_selector(self.request.GET), selector_str='', addm_names=addm_names)
            return context

    def get_queryset(self):
        # UserCheck().logator(self.request, 'info', "<=TestHistoryDayArchiveView=> test cases table queryset")
        sel_opts = compose_selector(self.request.GET)
        queryset = PatternsDjangoTableOper.sel_dynamical(TestHistory, sel_opts=sel_opts)
        # log.debug("TestHistoryDayArchiveView queryset explain \n%s", queryset.explain())
        # log.debug("<=TestHistoryDayArchiveView=> selected len: %s query: \n%s", queryset.count(), queryset.query)
        return queryset


# Test History Today View:
class TestHistoryTodayArchiveView(TodayArchiveView):
    __url_path = '/octo_tku_patterns/test_history_today/'
    model = TestHistory
    date_field = "test_date_time"
    allow_future = False
    allow_empty = True
    template_name = 'digests/tests_history_day.html'
    context_object_name = 'test_detail'

    def get_context_data(self, **kwargs):
        UserCheck().logator(self.request, 'info', "<=TestHistoryTodayArchiveView=> test history today")
        context = super(TestHistoryTodayArchiveView, self).get_context_data(**kwargs)
        context.update(selector=compose_selector(self.request.GET), selector_str='')
        return context


# Cases
class TestCasesListView(ListView):
    __url_path = '/octo_tku_patterns/test_cases/'
    model = TestCases
    context_object_name = 'test_cases'
    template_name = 'cases_groups/cases/cases_table.html'
    paginate_by = 100

    def get_context_data(self, **kwargs):
        UserCheck().logator(self.request, 'info', "<=TestCasesListView=> test cases table context")
        context = super(TestCasesListView, self).get_context_data(**kwargs)
        debug = self.request.GET.get('debug', False)
        context.update(
            selector=compose_selector(self.request.GET),
            selector_str='',
            debug=debug,
        )
        return context

    def get_queryset(self):
        # TODO: Can add order_by custom option, but not sure this is the real usecase...
        UserCheck().logator(self.request, 'info', "<=TestCasesListView=> test cases table queryset")
        queryset = TestCases.objects.all()
        sel_opts = compose_selector(self.request.GET)
        sel_opts.pop('tst_status')
        queryset = PatternsDjangoTableOper.sel_dynamical(TestCases, sel_opts=sel_opts)
        return queryset


class TestCaseDetailView(DetailView):
    __url_path = '/octo_tku_patterns/test_case/<int:pk>/'
    template_name = 'cases_groups/cases/case_single.html'
    context_object_name = 'case'
    model = TestCases

    def get_context_data(self, **kwargs):
        UserCheck().logator(self.request, 'info', "<=TestCaseDetailView=> test case view")
        context = super(TestCaseDetailView, self).get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context


# Cases groups
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
        UserCheck().logator(self.request, 'info', "<=TestCaseDetailView=> test case update")
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
        UserCheck().logator(self.request, 'warning', f"<=TestCaseDetailView=> test case update save: {post}")
        return redirect('test_case', pk=post.pk)


class TestCasesDetailsListView(ListView):
    __url_path = '/octo_tku_patterns/test_cases_groups/'
    # queryset = TestCases.objects.all().order_by('-change_time').values()
    model = TestCasesDetails
    context_object_name = 'groups'
    template_name = 'cases_groups/groups/groups_table.html'
    paginate_by = 50

    def get_queryset(self):
        UserCheck().logator(self.request, 'info', "<=TestCasesDetailsListView=> test case list view")
        queryset = TestCasesDetails.objects.all().order_by('-changed_date')
        return queryset


class TestCasesDetailsDetailView(DetailView):
    __url_path = '/octo_tku_patterns/test_cases_group/<int:pk>/'
    template_name = 'cases_groups/groups/group_single.html'
    context_object_name = 'group'
    model = TestCasesDetails

    def get_context_data(self, **kwargs):
        UserCheck().logator(self.request, 'info', "<=TestCasesDetailsDetailView=> test case group view")
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
        UserCheck().logator(self.request, 'info', "<=TestCasesDetailsListView=> test case edit view")
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
        UserCheck().logator(self.request, 'info', "<=TestCasesDetailsUpdateView=> test case group update")
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
        UserCheck().logator(self.request, 'info', "<=TestCasesDetailsListView=> test case create view")
        form = super(TestCasesDetailsCreateView, self).get_form()
        form.fields['title'].widget = forms.widgets.TextInput(attrs={'class': 'form-control', 'id': 'title', 'type': 'text'})
        form.fields['description'].widget = forms.widgets.Textarea(attrs={'class': 'form-control', 'id': 'description', 'type': 'text', 'rows': 5})
        return form

    def form_valid(self, form):
        post = form.save(commit=False)
        post.changed_date = timezone.now()
        post.title = post.title.replace(' ', '_').lower()
        post.save()
        form.save_m2m()
        UserCheck().logator(self.request, 'info', "<=TestCasesDetailsUpdateView=> test case group create")
        return redirect('test_cases_group', pk=post.pk)


# Operations:
@method_decorator(login_required, name='dispatch')
class TestCaseRunTest(TemplateView):
    __url_path = '/octo_tku_patterns/test_execute_web/'
    template_name = 'actions/test_added.html'
    context_object_name = 'objects'
    title = 'Test added!'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.context = super(TestCaseRunTest, self).get_context_data(**kwargs)

    def get_context_data(self, **kwargs):
        UserCheck().logator(self.request, 'info', "<=TestCaseRunTest=> get_context_data")
        if self.request.method == 'GET':
            selector = compose_selector(self.request.GET)
            self.context.update(selector=selector)

            context = self.context.copy()
            context.pop('view')  # Buffer IO cannot be pickled for celery task.
            obj = dict(
                context=context,
                request=self.request.GET,
                user_name=self.request.user.username,
                user_email=self.request.user.email,
            )
            t_tag = f'tag=t_test_prep;user_name={self.request.user.username};'
            t_queue = 'w_routines@tentacle.dq2'
            t_routing_key = 'routines.TRoutine.t_test_prep'
            task_added = TPatternRoutine.t_test_prep.apply_async(
                args=[t_tag],
                kwargs=dict(obj=obj),
                queue=t_queue,
                routing_key=t_routing_key,
            )

            # On NT this call will stop, initial task will run fake:
            # task_added = Runner.fire_t(TPatternRoutine.t_test_prep,
            #                            t_args=[t_tag],
            #                            t_kwargs=dict(object=obj),
            #                            t_queue='w_routines@tentacle.dq2',
            #                            t_routing_key='routines.TRoutine.t_test_prep'
            #                            )

            self.context.update(task_added='c72d9fa4-6f8e-4b27-b461-ead76b323bcb')
            self.context.update(subject='User test...')

            return self.context


class TestCaseRunTestREST(APIView):
    __url_path = '/octo_tku_patterns/user_test_add/'
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request=None):
        task_id = self.request.GET.get('task_id', 'ThisIsNotTheTaskJustSayingYouKnow?')
        log.debug("<=TestCaseRunTestREST=> GET - retrieve task by task_id: %s", task_id)
        log.debug("task id by request: %s", task_id)
        # Get task status from celery-app

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
            log.debug("Task result: %s", task_res)
            return Response([task_res])

    def post(self, request=None):
        log.debug("<=TestCaseRunTestREST=> POST request args: %s", self.request.data)
        selector = compose_selector(self.request.data)
        log.debug("<=TestCaseRunTestREST=> POST running task with args: %s", selector)
        # json_ = {"tkn_branch": "tkn_main", "pattern_library": "CORE", "pattern_folder_name": "10genMongoDB", "refresh": "1"}

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
class MailTestAddedDev(TemplateView):
    __url_path = '/octo_tku_patterns/mail_test_added_dev/'
    template_name = 'service/emails/statuses/test_added.html'
    context_object_name = 'objects'
    title = 'Test added!'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.context = super(MailTestAddedDev, self).get_context_data(**kwargs)

    def get_context_data(self, **kwargs):
        from octo.win_settings import SITE_DOMAIN, SITE_SHORT_NAME
        from octo.config_cred import mails

        UserCheck().logator(self.request, 'info', "<=MailTestAddedDev=> get_context_data")
        if self.request.method == 'GET':
            selector = compose_selector(self.request.GET)

            admin = mails['admin']

            # Init
            mail_opts_1 = {
                'mode': 'init',
                'view_obj': {
                    'context': {
                        'selector': {'test_type': None, 'tkn_branch': 'tkn_main', 'change_user': None,
                                     'change_review': None,
                                     'change_ticket': None, 'pattern_library': 'CORE',
                                     'pattern_folder_name': '10genMongoDB',
                                     'pattern_folder_names': [], 'change': None, 'last_days': None, 'date_from': None,
                                     'exclude': None, 'addm_name': None, 'addm_group': None, 'addm_v_int': None,
                                     'addm_host': None, 'addm_ip': None, 'tst_status': None, 'test_py_path': None,
                                     'tst_name': None, 'tst_class': None, 'tst_age': None, 'cases_ids': []
                                     }
                    },
                    'request': {'tkn_branch': ['tkn_main'],
                                'pattern_library': ['CORE'],
                                'pattern_folder_name': ['10genMongoDB'], 'wipe': ['1']},
                    'user_name': 'octopus_super',
                    'user_email': admin}}
            # start
            mail_opts_2 = {
                'mode': 'finish',
                'view_obj': {
                    'context': {
                        'selector': {
                            'test_type': None,
                            'tkn_branch': 'tkn_main',
                            'change_user': None,
                            'change_review': None,
                            'change_ticket': None,
                            'pattern_library': 'CORE',
                            'pattern_folder_name': '10genMongoDB',
                            'pattern_folder_names': [], 'change': None, 'last_days': None,
                            'date_from': None, 'exclude': None, 'addm_name': None,
                            'addm_group': None, 'addm_v_int': None, 'addm_host': None,
                            'addm_ip': None, 'tst_status': None, 'test_py_path': None,
                            'tst_name': None, 'tst_class': None, 'tst_age': None,
                            'cases_ids': []
                        }
                    },
                    'request': {
                        'tkn_branch': ['tkn_main'],
                        'pattern_library': ['CORE'],
                        'pattern_folder_name': ['10genMongoDB'],
                        'wipe': ['1']
                    },
                    'user_name': 'octopus_super',
                    'user_email': admin},
                'test_item': {
                    'id': 69,
                    'test_type': 'tku_patterns',
                    'tkn_branch': 'tkn_main',
                    'pattern_library': 'CORE', 'pattern_folder_name': '10genMongoDB',
                    'pattern_folder_path': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/CORE/10genMongoDB',
                    'pattern_library_path': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/CORE',
                    'test_case_dir': '', 'change': '780354', 'change_desc': 'CDM Tests\n',
                    'change_user': 'USER', 'change_review': '', 'change_ticket': '',
                    'change_time': "datetime.datetime(2019, 9, 20, 8, 14, 40, tzinfo=<UTC>)",
                    'test_case_depot_path': '//addm/tkn_main/tku_patterns/CORE/10genMongoDB',
                    'test_py_path': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/CORE/10genMongoDB/tests/test.py',
                    'test_py_path_template': '{}/addm/tkn_main/tku_patterns/CORE/10genMongoDB/tests/test.py',
                    'test_dir_path': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/CORE/10genMongoDB/tests',
                    'test_dir_path_template': '{}/addm/tkn_main/tku_patterns/CORE/10genMongoDB/tests',
                    'test_time_weight': None,
                    'created_time': "datetime.datetime(2019, 9, 5, 9, 14, 18, 925986, tzinfo=<UTC>)"},
                'addm_set': [
                    {'id': 6, 'addm_host': 'vl-aus-tkudev-38', 'addm_name': 'custard_cream', 'tideway_user': 'tideway', 'tideway_pdw': 'S0m3w@y', 'root_user': 'root', 'root_pwd': 'tidewayroot', 'addm_ip': '172.25.144.118', 'addm_v_code': 'ADDM_11_2', 'addm_v_int': '11.2', 'addm_full_version': '11.2.0.6', 'addm_branch': 'r11_2_0_x', 'addm_owner': 'Alex D', 'addm_group': 'alpha', 'disables': None, 'branch_lock': 'tkn_main', 'description': None, 'vm_cluster': 'tku_cluster', 'vm_id': 'vim.VirtualMachine:vm-69'},
                    {'id': 7, 'addm_host': 'vl-aus-tkudev-39', 'addm_name': 'bobblehat', 'tideway_user': 'tideway', 'tideway_pdw': 'S0m3w@y', 'root_user': 'root', 'root_pwd': 'tidewayroot', 'addm_ip': '172.25.144.119', 'addm_v_code': 'ADDM_11_1', 'addm_v_int': '11.1', 'addm_full_version': '11.1.0.8', 'addm_branch': 'r11_1_0_x', 'addm_owner': 'Alex D', 'addm_group': 'alpha', 'disables': None, 'branch_lock': 'tkn_main', 'description': None, 'vm_cluster': 'tku_cluster', 'vm_id': 'vim.VirtualMachine:vm-61'},
                    {'id': 8, 'addm_host': 'vl-aus-tkudev-40', 'addm_name': 'aardvark', 'tideway_user': 'tideway', 'tideway_pdw': 'S0m3w@y', 'root_user': 'root', 'root_pwd': 'tidewayroot', 'addm_ip': '172.25.144.120', 'addm_v_code': 'ADDM_11_0', 'addm_v_int': '11.0', 'addm_full_version': '11.0.0.6', 'addm_branch': 'r11_0_0_x', 'addm_owner': 'Alex D', 'addm_group': 'alpha', 'disables': None, 'branch_lock': 'tkn_main', 'description': None, 'vm_cluster': 'tku_cluster', 'vm_id': 'vim.VirtualMachine:695'},
                    {'id': 9, 'addm_host': 'vl-aus-tkudev-41', 'addm_name': 'double_decker', 'tideway_user': 'tideway', 'tideway_pdw': 'S0m3w@y', 'root_user': 'root', 'root_pwd': 'tidewayroot', 'addm_ip': '172.22.172.53', 'addm_v_code': 'ADDM_11_3', 'addm_v_int': '11.3', 'addm_full_version': '11.3.0.5', 'addm_branch': 'r11_3_x_x', 'addm_owner': 'Alex D', 'addm_group': 'alpha', 'disables': None, 'branch_lock': 'tkn_main', 'description': None, 'vm_cluster': 'tku_cluster', 'vm_id': 'vim.VirtualMachine:727'}
                ]
            }

            if mail_opts_2['test_item']['tkn_branch']:
                subject_str = f'{mail_opts_2["test_item"]["tkn_branch"]} | ' \
                              f'{mail_opts_2["test_item"]["pattern_library"]} | ' \
                              f'{mail_opts_2["test_item"]["pattern_folder_name"]} '
            else:
                subject_str = f'{mail_opts_2["test_item"]["test_py_path_template"]} '

            mode_context = dict(
                # This stage is when routine only starts
                init=dict(
                    subject=f'[{SITE_SHORT_NAME}] User test init: '
                            f'{mail_opts_2["view_obj"]["request"]["tkn_branch"]} | '
                            f'{mail_opts_2["view_obj"]["request"]["pattern_library"]} | '
                            f'{mail_opts_2["view_obj"]["request"]["pattern_folder_name"]}',
                ),
                # This stage is when routine prepare task to run
                start=dict(
                    subject=f'[{SITE_SHORT_NAME}] Test case started: {subject_str}'
                ),
                # This stage is when routine added task and finish loop step
                finish=dict(
                    subject=f'[{SITE_SHORT_NAME}] Test case finished: {subject_str}'
                ),
                # This stage is when routine had any issues
                fail=dict(
                    subject=f'[{SITE_SHORT_NAME}] Test task failed: '
                            f'{mail_opts_2["view_obj"]["request"]["tkn_branch"]} | '
                            f'{mail_opts_2["view_obj"]["request"]["pattern_library"]} | '
                            f'{mail_opts_2["view_obj"]["request"]["pattern_folder_name"]}',
                ),
            )

            self.context.update(
                subject=mode_context['finish'].get('subject'),
                domain=SITE_DOMAIN,
                mail_opts=mail_opts_2,
            )

            return self.context
