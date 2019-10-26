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
from selector_out.forms import TestPastDays

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
        page_widgets = loader.get_template('admin_workbench/workbench_widgets.html')

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

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.routine_run', login_url='/unauthorized_banner/')
    def failed_test_prepare(request):
        user_name, user_string = UserCheck().user_string_f(request)
        log.debug("<=WEB OCTO AMD=> failed_test_prepare(): %s", user_string)
        page_widgets = loader.get_template('digests/dev/failed_select_prepare_rerun.html')

        fake_run = request.GET.get('fake_run', False)
        send_mail = request.GET.get('send_mail', True)  # Send mail when this view runs
        branch = request.GET.get('branch', 'tkn_main')
        addm_name = request.GET.get('addm_name', 'double_decker')
        wipe = request.GET.get('wipe', False)
        info = request.GET.get('info', True)
        addm_group = request.GET.get('addm_group', None)
        debug = request.GET.get('debug', False)

        sorted_tests_l, show_patterns_list, failed_patterns, patterns_to_test, all_tests_w = OptionalTestsSelect().select_latest_failed_sort(
            branch=branch, addm_name=addm_name, info=info)
        tsk_msg = 'tag=failed_test_run_routine;ype=routine;user_name={u_name};|{branch}:{addm_name}'
        t_tag = tsk_msg.format(branch=branch, u_name=user_name, addm_name=str(addm_name))
        subject = "Selected all test fails to run again.".format(branch, addm_name)

        if request.method == 'GET':

            widgets = dict(
                SUBJECT=subject,
                SEND_MAIL=send_mail,
                BRANCH=branch,
                ADDM_NAME=addm_name,
                FAKE_RUN=fake_run,
                WIPE=wipe,
                INFO=info,
                ADDM_GROUP=addm_group,
                # Selected:
                sorted_tests_l=sorted_tests_l,
                show_patterns_list=show_patterns_list,
                failed_patterns=failed_patterns,
                patterns_to_test=patterns_to_test,
                all_tests_w=all_tests_w,
                DEBUG=debug,
            )
            return HttpResponse(page_widgets.render(widgets, request))
        # When POST - run tests:
        else:
            page_widgets = loader.get_template('admin_workbench/workbench_widgets.html')
            optional_kw = dict(
                fake_run=fake_run,
                wipe=wipe,
                user_name=user_name,
                addm_name=addm_name,
                addm_group=addm_group,
                branch=branch,
                test_items_l=sorted_tests_l,
                patterns_dir_list=show_patterns_list,
            )
            Runner.fire_t(TPatternRoutine.t_routine_optional_test, fake_run=True,
                          t_args=[t_tag], t_kwargs=optional_kw)
            # if send_mail:
            #     user_email = [request.user.email]
            #     TMail().long_r(mode='start', user_email=user_email, start_args=optional_kw,
            #                    addm_group=addm_name, branch=branch, start_time=datetime.datetime.now())

            subject = "'{0} {1}'. Custom test routine has been added to queue!.".format(branch, addm_name)
            widgets = dict(SUBJECT=subject)
            # return HttpResponse(page_widgets.render(widgets, request))
            # return redirect('/octo_admin/workers_status/')
            return redirect('/')

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.routine_run', login_url='/unauthorized_banner/')
    def failed_test_run(request):
        user_name, user_string = UserCheck().user_string_f(request)
        log.debug("<=WEB OCTO AMD=> failed_test_run(): %s", user_string)
        page_widgets = loader.get_template('admin_workbench/workbench_widgets.html')

        send_mail = request.GET.get('send_mail', True)  # Send mail when this view runs
        branch = request.GET.get('branch', True)
        addm_name = request.GET.get('addm_name', True)
        fake_run = request.GET.get('fake_run', False)
        wipe = request.GET.get('wipe', True)
        addm_group = request.GET.get('addm_group', None)

        test_items_l, patterns_dir_list = OptionalTestsSelect().select_latest_failed_sort(branch=branch,
                                                                                          addm_name=addm_name)

        tsk_msg = 'tag=failed_test_run_routine;ype=routine;user_name={u_name};|{branch}:{addm_name}'
        t_tag = tsk_msg.format(branch=branch, u_name=user_name, addm_name=str(addm_name))

        optional_kw = dict(
            fake_run=fake_run,
            wipe=wipe,
            user_name=user_name,
            addm_name=addm_name,
            addm_group=addm_group,
            branch=branch,
            test_items_l=test_items_l,
            patterns_dir_list=patterns_dir_list,
        )

        Runner.fire_t(TPatternRoutine.t_routine_optional_test, t_args=[t_tag], t_kwargs=optional_kw)
        if send_mail:
            user_email = [request.user.email]
            TMail().long_r(mode='start', user_email=user_email, start_args=optional_kw,
                           addm_group=addm_name, branch=branch, start_time=datetime.datetime.now())

        subject = "'{0} {1}'. Custom test routine has been added to queue!.".format(branch, addm_name)
        widgets = dict(SUBJECT=subject)
        return HttpResponse(page_widgets.render(widgets, request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.routine_run', login_url='/unauthorized_banner/')
    def optional_test_routine(request):
        """
        Placeholder for future optional test runner.
        Same as night routine, but with dynamical args.
        :param request:
        :return:
        """
        user_name, user_string = UserCheck().user_string_f(request)
        log.debug("<=WEB OCTO AMD=> manual_exec_night_run_task(): %s", user_string)
        page_widgets = loader.get_template('admin_workbench/workbench_widgets.html')

        send_mail = request.GET.get('send_mail', True)  # Send mail when this view runs
        addm_group = request.GET.get('addm_group', None)  # When None - assign one from free/minimal workers
        user = request.GET.get('user', None)  # Select user patterns
        branch = request.GET.get('branch', None)  # Select from branch
        change = request.GET.get('change', None)  # Select by p4 change
        excluded_seq = request.GET.get('exclude', None)  # Exclude patterns by folder name
        library = request.GET.get('library', None)  # Select full library
        last_days = request.GET.get('last_days', None)  # Select changed for the last n days
        date_from = request.GET.get('date_from', None)  # Select changes from date till tomorrow
        sel_patterns = request.GET.get('sel_patterns', None)  # Select only patterns from list
        test_output_mode = request.GET.get('test_output_mode', False)  # Debug:
        wipe_last = request.GET.get('wipe_last', False)  # Wipe LastTests logs
        wide_addm = request.GET.get('wide_addm', False)  # Use all ADDM workers possible
        sync_data = request.GET.get('sync_data', False)  # Sync p4 data or not

        tsk_msg = 'tag=night_routine;lock=True;type=routine;user_name={u_name};excl={excl};use_patterns={sel_p}|{branch} on: {addms}'
        t_tag = tsk_msg.format(branch=branch, u_name=user_name,
                               addms=str(addm_group), excl=str(excluded_seq), sel_p=str(sel_patterns))

        optional_kw = dict(
            user_name=user_name,
            addm_group=addm_group,
            user=user,
            branch=branch,
            change=change,
            excluded_seq=excluded_seq,
            library=library,
            last_days=last_days,
            date_from=date_from,
            sel_patterns=sel_patterns,
            test_output_mode=test_output_mode,
            wipe_last=wipe_last,
            wide_addm=wide_addm,
            sync_data=sync_data,
        )
        Runner.fire_t(TPatternRoutine.t_routine_optional_test, t_args=[t_tag], t_kwargs=optional_kw)
        if send_mail:
            user_email = [request.user.email]
            TMail().long_r(mode='start', user_email=user_email, start_args=optional_kw,
                           addm_group=addm_group, branch=branch, start_time=datetime.datetime.now())

        subject = "'{0} {1}'. Custom test routine has been added to queue!.".format(branch, addm_group)
        widgets = dict(SUBJECT=subject)
        return HttpResponse(page_widgets.render(widgets, request))


class Reports:
    """
    Regular reports from test databases for addms, patterns and tests.
    """

    # LEVEL 1 report request TOP:
    @staticmethod
    def general_addm(request):
        """
        TOP Digest for all ADDM separated on branches.
        :param request: /?table=LAST_SHIP_TESTS&branch=tkn_ship&addm_name=all_addms
        :return:
        """
        addm_summary = loader.get_template('OLD/general_addm.html')
        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=VIEW SELECTOR=> general_addm(): %s", user_str)

        # addm_summary = loader.get_template('OLD/general_addm.html')
        branch = request.GET.get('branch', 'tkn_main')
        addm_name = request.GET.get('addm_name', 'all_addms')

        # TODO: Change workers statuses to new design later!
        addm_items_d = SelectorRequestsHelpers().addm_summary_draw(branch, addm_name)
        minmax_test_date = PatternsDjangoTableOper().latest_tests_minmax_date(branch)

        addm_ver = addm_items_d[0].get('ADDM_VER', str(99.9))
        if addm_ver:
            addms_sort = sorted(addm_items_d, key=itemgetter('ADDM_VER'), reverse=True)
        else:
            addms_sort = sorted(addm_items_d, key=itemgetter('ADDM_CODENAME'), reverse=True)

        patterns_contxt = dict(
            HAV_PLACE='ADDM Summary',
            MIN_TEST_DATE=minmax_test_date['min_test_date'],
            MAX_TEST_DATE=minmax_test_date['max_test_date'],
            BRANCH=branch,
            ADDM_DIGEST=addms_sort,
            NAV_HEAD_DRAW=True,
        )
        return HttpResponse(addm_summary.render(patterns_contxt, request))

    # LEVEL 2 report request TOP:
    @staticmethod
    def patterns_digest(request):
        """
        Next after ADDM Top - link to patterns digest - separate for each ADDM version. Tabs.
        :param request: ?table=LAST_SHIP_TESTS&branch=tkn_ship&addm_name=aardvark
        :return:
        """
        patterns_summary = loader.get_template('OLD/patterns_digest.html')
        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=VIEW SELECTOR=> patterns_digest(): %s", user_str)
        # patterns_summary = loader.get_template('OLD/patterns_digest.html')

        # Assign args:
        branch = request.GET.get('branch', 'tkn_main')
        addm_name = request.GET.get('addm_name', 'double_decker')
        fail_only = request.GET.get('fail_only', '')
        skip_only = request.GET.get('skip_only', '')
        error_only = request.GET.get('error_only', '')
        pass_only = request.GET.get('pass_only', '')
        not_pass_only = request.GET.get('not_pass_only', '')

        date_start = request.GET.get('date_from', '')
        date_end = request.GET.get('date_last', '')

        pattern_library = request.GET.get('pattern_library', '')
        pattern_folder = request.GET.get('pattern_folder', '')

        sort_by = request.GET.get('sort_by', 'test_date_time')
        adprod_user = request.GET.get('adprod_user', '')
        # TODO: Later - can be possible a way to sort in both directions...
        sort_ord = request.GET.get('sort_asc', 'sort_desc')

        test_select = TestPastDays()

        # log.debug("patterns_digest adprod_user: %s", adprod_user)

        # Assign usual args for querying:
        query_args = dict(
            branch=branch,
            addm_name=addm_name,
            fail_only=fail_only,
            skip_only=skip_only,
            error_only=error_only,
            pass_only=pass_only,
            not_pass_only=not_pass_only,
            date_start=date_start,
            date_end=date_end,
            user_name=user_name,
            by_user=adprod_user,
        )

        # SELECT Min/Max dates in last tests table:
        minmax_test_date = PatternsDjangoTableOper().latest_tests_minmax_date(branch)

        # Select patterns and PRE-make table with patterns details.
        # patterns_d_list = SelectorRequestsHelpers().patterns_summary_log_draw(query_args)
        patterns_digest = PatternsDjangoModelRaw().patterns_tests_latest_digest(query_args)

        start_date = minmax_test_date.get('min_test_date', "N/A")
        end_date = minmax_test_date.get('max_test_date', "N/A")

        patterns_contxt = dict(
            HAV_PLACE='Patterns digest',
            PATTERNS_CONTENT=patterns_digest,
            BRANCH=branch,
            ADDM_NAME=addm_name,
            MIN_TEST_DATE=minmax_test_date['min_test_date'],
            MAX_TEST_DATE=minmax_test_date['max_test_date'],
            DATE_FROM=date_start,
            DATE_LAST=date_end,
            FAIL_ONLY=fail_only,
            ERROR_ONLY=error_only,
            SKIP_ONLY=skip_only,
            PASS_ONLY=pass_only,
            NOT_PASS_ONLY=not_pass_only,
            PATTERN_LIBRARY=pattern_library,
            PATTERN_FOLDER=pattern_folder,
            START_DATE=start_date,
            END_DATE=end_date,
            NAV_HEAD_DRAW=True,
            TABS_DRAW=True,
            ADDM_NAVS_LINK="patterns_digest",
            # TODO: Later - can be possible a way to sort in both directions...
            SORT_ORD=sort_ord,
            SORT_BY=sort_by,
            test_select_form=test_select,
            ADPROD_USER=adprod_user,
        )

        return HttpResponse(patterns_summary.render(patterns_contxt, request))

    # LEVEL 3 report request TOP:
    @staticmethod
    def pattern_logs(request):
        """
        Detailed log of selected pattern from pattern digest.
        Now include all, and ok. Should use tabs for OK or Not OK

        :param request: table=LAST_SHIP_TESTS&branch=tkn_ship&pattern_library=CORE
        :return:
        """
        tests_summary = loader.get_template('OLD/pattern_logs.html')
        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=VIEW SELECTOR=> pattern_detailed_log(): %s", user_str)
        # tests_summary = loader.get_template('OLD/pattern_logs.html')

        date_time_now = datetime.datetime.now()
        date_today = date_time_now.strftime('%Y-%m-%d')

        # Request:
        branch = request.GET.get('branch', 'tkn_main')
        # test_function    = request.GET.get('test_function', 'tkn_main')
        addm_name = request.GET.get('addm_name', 'double_decker')
        pattern_library = request.GET.get('pattern_library', False)
        pattern_folder = request.GET.get('pattern_folder', False)
        fail_only = request.GET.get('fail_only', '')
        skip_only = request.GET.get('skip_only', '')
        error_only = request.GET.get('error_only', '')
        pass_only = request.GET.get('pass_only', '')
        not_pass_only = request.GET.get('not_pass_only', '')

        if not pattern_library:
            log.error("pattern_logs: There is no patter lib %s", pattern_library)

        sort_date_exec = request.GET.get('sort_date_exec', '')
        debug_flag = request.GET.get('debug_flag', False)

        query_args = dict(
            branch=branch,
            fail_only=fail_only,
            skip_only=skip_only,
            error_only=error_only,
            pass_only=pass_only,
            not_pass_only=not_pass_only,
            addm_name=addm_name,
            pattern_folder=pattern_folder,
            pattern_library=pattern_library,
            sort_date_exec=sort_date_exec,
        )

        # SELECT by django - with selected attrs:
        if pattern_library and pattern_folder:
            latest_records = PatternsDjangoTableOper().select_latest_records_by_pattern(query_args=query_args)
        elif pattern_library and not pattern_folder:
            query_args.pop('pattern_folder')
            latest_records = PatternsDjangoTableOper().select_latest_records(query_args, True)
        else:
            latest_records = PatternsDjangoTableOper().select_latest_records(query_args, True)

        # compose_args = dict(
        #     latest_records = latest_records,
        #     branch         = branch,
        #     user_name      = user_name,
        #     date_time_now  = date_time_now,
        #     addm_name      = addm_name,
        #     detailed_log   = False,
        #     sort_date_exec = sort_date_exec,
        # )
        # latest_records_contxt  = SelectorRequestsHelpers().__patterns_detailed_log_draw(compose_args)
        # Execute query for MAX/MIN dates from latest table:

        minmax_test_date = PatternsDjangoTableOper().latest_tests_minmax_date(branch)
        tests_pattern_context = dict(
            HAV_PLACE='Patterns log',
            LATEST_TESTS=latest_records,
            DATE_FROM="Latest",
            DATE_LAST=date_today,
            DATE_START=date_time_now.strftime('%Y-%m-%d'),
            BRANCH=branch,
            FAIL_ONLY=fail_only,
            SKIP_ONLY=skip_only,
            ERROR_ONLY=error_only,
            PASS_ONLY=pass_only,
            NOT_PASS_ONLY=not_pass_only,
            PATTERN_LIBRARY=pattern_library,
            PATTERN_FOLDER=pattern_folder,
            MIN_TEST_DATE=minmax_test_date['min_test_date'],
            MAX_TEST_DATE=minmax_test_date['max_test_date'],
            START_DATE=minmax_test_date.get('min_test_date', date_today),
            END_DATE=minmax_test_date.get('max_test_date', date_today),
            ADDM_NAME=addm_name,
            NAV_HEAD_DRAW=True,
            TABS_DRAW=True,
            ADDM_NAVS_LINK="pattern_detailed_log",
            DEBUG_DATA=debug_flag,
        )
        return HttpResponse(tests_summary.render(tests_pattern_context, request))

    @staticmethod
    def last_success(request):
        """
        Show test records for single item with status of success

        :param request:
        :return:
        """
        tests_summary = loader.get_template('digests/tables_details/last_success.html')
        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=VIEW SELECTOR=> pattern_detailed_log(): %s", user_str)

        branch = request.GET.get('branch', 'tkn_main')
        test_function = request.GET.get('test_function', 'tkn_main')
        pattern_library = request.GET.get('pattern_library', False)
        pattern_folder = request.GET.get('pattern_folder', False)
        addm_name = request.GET.get('addm_name', False)

        query_args = dict(branch=branch, test_function=test_function, addm_name=addm_name,
                          pattern_library=pattern_library, pattern_folder=pattern_folder)
        latest_records = PatternsDjangoTableOper().select_history_test_last_success(query_args)

        return HttpResponse(tests_summary.render(dict(
            LATEST_TESTS=latest_records, BRANCH=branch, ADDM_NAME=addm_name, SUBJECT='All logs for single test'),
            request))

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
        log.debug("<=VIEW SELECTOR=> patterns_digest(): %s", user_str)
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


class Patterns:

    # Select one library TKN patterns:
    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def _old_tku_pattern_libraries(request):
        """
        Show all patterns from database with useful details and button for test execution.
        """
        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=VIEW SELECTOR=> _old_tku_pattern_libraries(): %s", user_str)
        patterns_summary = loader.get_template('OLD/tku_patterns_report.html')

        # page = request.GET.get('page')
        # diff_branches = request.GET.get('diff_branches', False)
        release = request.GET.get('release', False)
        everything = request.GET.get('everything', False)
        branch = request.GET.get('branch', 'tkn_main')
        pattern_library = request.GET.get('pattern_library')
        is_key_pattern = request.GET.get('is_key_pattern')

        query_args = dict(
            user_name=user_name,
            pattern_library=pattern_library,
            is_key_pattern=is_key_pattern,
            branch=branch,
            release=release,
            everything=everything,
            select_mode="release" if release else "everything")

        all_patterns, date_start, latest_date = PatternsDjangoTableOper().select_all_patterns(query_args)
        patterns_contxt = dict(
            ALL_PATTERNS=all_patterns.order_by('-change_time'),
            PATTERN_LIBRARY=pattern_library,
            # DATE_START=date_start,
            # LATEST_DATE=latest_date,
            LIB=pattern_library if pattern_library else "All",
            START=date_start,
            END=latest_date,
            CHANGE_MAX=all_patterns.aggregate(Max('change')),
            DATE_MAX=all_patterns.aggregate(Max('change_time')),
            BRANCH=branch,
            RELEASE=release,
            SELECT_MODE=query_args['select_mode']
        )

        return HttpResponse(patterns_summary.render(patterns_contxt, request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def _old_tku_pattern_tests(request):
        """
        Select tku patterns BUT grouped by test.py's
        :param request:
        :return:
        """
        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=VIEW SELECTOR=> _old_tku_pattern_libraries(): %s", user_str)
        patterns_summary = loader.get_template('OLD/tku_patterns_tests.html')

        branch = request.GET.get('branch', 'tkn_main')
        pattern_library = request.GET.get('pattern_library', None)
        is_key_pattern = request.GET.get('is_key_pattern', None)
        select_release = request.GET.get('release', False)

        date_from = request.GET.get('date_from', None)
        date_to = request.GET.get('date_to', None)

        # if not date_from and select_release:
        #     date_from = DjangoTableOper.release_db_date()['start_date']
        # elif date_from and not select_release:
        #     date_from.strftime('%Y-%m-%d')
        # else:
        #     date_from = '1970-01-01'
        #
        # if not date_to:
        #     date_to = DjangoTableOper.release_db_date()['today']
        # else:
        #     date_to.strftime('%Y-%m-%d')

        date_from, date_to, selected_tku_tests = PatternsDjangoTableOper().select_tku_test_patterns(
            branch=branch, pattern_library=pattern_library, is_key_pattern=is_key_pattern,
            date_from=date_from, date_to=date_to, select_release=select_release)

        # log.debug("selected_tku_tests %s", selected_tku_tests)

        patterns_contxt = dict(
            ALL_PATTERNS=selected_tku_tests.order_by('-change_time'),
            CHANGE_MAX=selected_tku_tests.aggregate(Max('change')),
            DATE_MAX=selected_tku_tests.aggregate(Max('change_time')),
            DATE_FROM=date_from,
            DATE_TO=date_to,
            IS_KEY_PATTERN=is_key_pattern,
            PATTERN_LIBRARY=pattern_library,
            RELEASE=select_release,
            BRANCH=branch,
            SUBJECT='Only tests which where affected during selected period'
        )

        return HttpResponse(patterns_summary.render(patterns_contxt, request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def _example_only_patterns_to_test_at_night(request):
        """
        Show all patterns which usually used on night routine.
        :param request:
        :return:
        """
        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=VIEW SELECTOR=> _example_only_patterns_to_test_at_night(): %s", user_str)
        patterns_summary = loader.get_template('OLD/tku_patterns_night_set.html')

        sort_by = request.GET.get('sort_by', 'change_time')
        asc = request.GET.get('asc', False)
        desc = request.GET.get('desc', False)
        sel_opts = dict()

        sel_opts.update(date_from='2017-09-25', branch='tkn_main')  # 1.1 Select all for TKN_MAIN:
        tkn_main_tests = PatternsDjangoTableOper.sel_tests_dynamical(sel_opts=sel_opts)
        sel_opts.update(date_from='2017-10-12', branch='tkn_ship')  # 1.2 Select all for TKN_SHIP:
        tkn_ship_tests = PatternsDjangoTableOper.sel_tests_dynamical(sel_opts=sel_opts)
        sum_tests = tkn_main_tests | tkn_ship_tests  # 2. Summarize all tests and sort:
        # sorted_tests_l = TestPrepCases.test_items_sorting(sum_tests, exclude=excluded_seq)

        patterns_contxt = dict(
            ALL_PATTERNS=sum_tests,
            CHANGE_MAX=sum_tests.aggregate(Max('change')),
            DATE_MAX=sum_tests.aggregate(Max('change_time')),
            SORT_BY=sort_by,
            ASC=asc,
            DESC=desc,
            SUBJECT='All tests for usual night routine test run.'
        )

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
        page_widgets = loader.get_template('admin_workbench/workbench_widgets.html')
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
        page_widgets = loader.get_template('admin_workbench/workbench_widgets.html')
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
        page_widgets = loader.get_template('admin_workbench/workbench_widgets.html')
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
    queryset = TestLatestDigestAll.objects.all()

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

        if sel_opts.get('addm_name'):
            # log.debug("use: addm_name")
            self.queryset = self.queryset.filter(addm_name__exact=sel_opts.get('addm_name'))
        if sel_opts.get('tkn_branch'):
            # log.debug("use: tkn_branch")
            self.queryset = self.queryset.filter(tkn_branch__exact=sel_opts.get('tkn_branch'))
        if sel_opts.get('change_user'):
            # log.debug("use: change_user")
            self.queryset = self.queryset.filter(change_user__exact=sel_opts.get('change_user'))

        self.queryset = tst_status_selector(self.queryset, sel_opts)
        # log.debug("TestLastDigestListView self.queryset explain \n%s", self.queryset.explain())
        return self.queryset


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
    template_name = 'digests/dev/tests_history_day.html'
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
    template_name = 'digests/dev/tests_history_day.html'
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
    template_name = 'digests/dev/tests_history_day.html'
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
        sel_opts = compose_selector(self.request.GET)
        # Not the best idea: remove inter-selection args, when call this func from another views: octo.views.UserMainPage.get_queryset
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
