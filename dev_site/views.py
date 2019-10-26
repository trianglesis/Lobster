"""
OCTO DEV views only
"""

import socket

from datetime import datetime
from django.http import HttpResponse
from django.template import loader
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required

from octo.helpers.tasks_mail_send import Mails
from octo.helpers.tasks_helpers import TMail

from octo_adm.tasks import ADDMCases
from octo_adm.tasks import TaskADDMService

from octo_tku_patterns.tasks import TPatternParse
from octo_tku_patterns.table_oper import PatternsDjangoModelRaw

from octo_adm.user_operations import UserCheck
from run_core.p4_operations import PerforceOperations as P4_Oper
from run_core.local_operations import LocalPatternsParse

from run_core.models import Options
from dev_site.tasks import DevTRoutine
from dev_site.tasks import DevRunner
# Python logger
import logging

log = logging.getLogger("octo.octologger")


class DevRunTasks:

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.routine_run', login_url='/unauthorized_banner/')
    def dev_manual_exec_night_run_task(request):
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
                         addm_group=addm_group_l, branch=branch, start_time=datetime.now())

        DevRunner.fire_t(DevTRoutine.dev_t_routine_night_tests,
                         t_args=[t_tag],
                         t_kwargs=dict(branch=branch,
                                       user_name=user_name,
                                       addm_group=addm_group_l,
                                       test_output_mode=test_output_mode,
                                       excluded_seq=excluded_seq,
                                       sel_patterns=sel_patterns,
                                       send_mail=send_mail,
                                       ))

        subject = "'{0} {1}'. Manual night test run has been added to queue!.".format(branch, addm_group_l)
        widgets = dict(SUBJECT=subject)
        return HttpResponse(page_widgets.render(widgets, request))


class DevAdminViews:

    @staticmethod
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def index(request):
        """
        Draw useful widgets for OCTO ADMIN page.

        REMOTE_ADDR – The IP address of the client.
        REMOTE_HOST – The hostname of the client.

        :param request:
        :return:
        """
        page_widgets = loader.get_template('dev_debug_workbench/dev_main.html')
        user_name, user_str = UserCheck().user_string_f(request)

        subject = "Hello  here you can manage Octopus tasks and see stats".format(user_name)

        log.debug("<=WEB OCTO AMD=> Allowed to admin page: %s", user_str)

        widgets = dict(SUBJECT=subject)
        # widgets_page = page_widgets.render(widgets)
        # https://docs.djangoproject.com/en/2.0/topics/http/shortcuts/
        return HttpResponse(page_widgets.render(widgets, request))

    @staticmethod
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def dev_p4_info_web(request):
        """
        Show p4 info
        :param request:
        :return:
        """
        user_name, user_str = UserCheck().user_string_f(request)

        log.debug("<=WEB OCTO AMD=>   p4_info_web(): %s", user_str)

        p4_info_page = loader.get_template(
            'dev_debug_workbench/dev_helpers/p4_infos.html')

        subject = "Perforce information string. On user {0} request.".format(user_name)
        log.info(subject)

        p4_info_get = P4_Oper().p4_info()
        contxt = dict(P4_INFO=p4_info_get, SUBJECT=subject, )

        return HttpResponse(p4_info_page.render(contxt, request))

    @staticmethod
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def dev_parse_local_files(request):
        page_widgets = loader.get_template('service/task-action-request-added-started.html')
        user_name, user_str = UserCheck().user_string_f(request)
        subject = "Please set branch!"
        branch = request.GET.get('branch', False)
        log.debug("<=WEB OCTO AMD=>   parse_patterns(): %s", user_str)
        if branch:
            info_string = dict(branch=branch, user_name=user_name, )
            LocalPatternsParse().compose_tree_paths(tkn_branch=branch)
            subject = "User request: '{}' {}.".format("parse_patterns", info_string)
        return HttpResponse(page_widgets.render(dict(SUBJECT=subject), request))

    @staticmethod
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def dev_test_email_templates(request):
        """

        :param request:
        :return:
        """
        user_name, user_str = UserCheck().user_string_f(request)
        page_widgets = loader.get_template('dev_debug_workbench/dev_main.html')
        log.debug("<=WEB OCTO AMD=>   dev_test_email_templates(): %s", user_str)

        # test_bootstrap = loader.get_template('service/emails/bootstrap_examples/test_bootstrap.html')
        # task_limit = loader.get_template('service/emails/statuses/task_details.html')
        # test_added = loader.get_template('service/emails/statuses/test_added.html')
        # upload_t = loader.get_template('service/emails/statuses/upload_t.html')
        # items_values_text = loader.get_template('service/emails/statuses/items_values_text.html')

        upload_test_addm = loader.get_template('service/emails/upload_test.html')

        # Use different email templates here and send test email to see how it's working:
        user_email = [request.user.email]

        subject = "Upload test mail TEST...".format(user_name)

        mail_details = dict(

            SUBJECT='SUBJECT',
            CURRENT_STATE='CURRENT_STATE',
            TIME_FORMATTED='TIME_FORMATTED',
            ADDM_NAME='ADDM_NAME',
            ADDM_IP='ADDM_IP',
            BRANCH='BRANCH',
            PATTERN_LIBRARY='PATTERN_LIBRARY',
            PATTERN_FOLDER='PATTERN_FOLDER',
            IS_KEY_PATTERN='IS_KEY_PATTERN',
            TEST_PY='TEST_PY',
            PATTERN_FOLDER_PATH_DEPOT='PATTERN_FOLDER_PATH_DEPOT',
        )

        mail_args = dict(
            subject=subject,
            SUBJECT=subject,
            MAIL_DETAILS=mail_details,
            TEXT_BLOCK='Lorem ipsum dolor sit amet, consectetur adipiscing elit. '
                       'Nam magna justo, pretium nec tellus eu, facilisis pellentesque augue. '
                       'Curabitur id mi vitae mauris auctor lacinia. Nam dignissim tortor arcu, at '
                       'commodo lacus efficitur et. Maecenas posuere a tortor nec consequat. '
                       'Suspendisse pulvinar metus eu eros rutrum facilisis. Donec tempus tempor consequat. '
                       'Praesent egestas metus at purus lacinia, eu laoreet leo pharetra. '
                       'Etiam placerat odio nisl, quis porta odio fermentum posuere.',
            send_to=user_email)

        dev_mail_html = upload_test_addm.render(mail_args)

        mail_args.update(mail_html=dev_mail_html)
        Mails.short(  # DEV
            **mail_args)

        widgets = dict(USER_NAME=user_name, SUBJECT=subject)
        return HttpResponse(page_widgets.render(widgets, request))

    @staticmethod
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def dev_get_options_table_values(request):
        user_name, user_str = UserCheck().user_string_f(request)
        page_widgets = loader.get_template(
            'dev_debug_workbench/dev_helpers/unpack_query_results.html')
        log.debug("<=WEB OCTO AMD=>   dev_get_options_table_values(): %s", user_str)

        # Use different email templates here and send test email to see how it's working:
        subject = "Query results and options...".format(user_name)
        p4_path = Options.objects.filter(option_key__exact='PerforceOperations.p4_path').values('option_value')[0]
        # p4_path = Options.objects.filter(option_key__exact='PerforceOperations.p4_path')
        # p4_path = Options.objects.only('PerforceOperations.p4_path')
        # p4_path = Options.objects.get(option_key__exact='PerforceOperations.p4_path')
        # user_email = [request.user.email]

        results_d = dict(
            my_hostname=socket.gethostname(),
            # p4_path=p4_path,
            p4_path=p4_path.get('option_value', 'Neeh'),
        )

        widgets = dict(USER_NAME=user_name,
                       QUERY=results_d,
                       SUBJECT=subject)
        return HttpResponse(page_widgets.render(widgets, request))

    @staticmethod
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def dev_test_email_templates_upload_test(request):
        """

        :param request:
        :return:
        """
        user_name, user_str = UserCheck().user_string_f(request)
        # page_widgets = loader.get_template('octo_adm/debug_dev/dev_main.html')
        log.debug("<=WEB OCTO AMD=>   dev_test_email_templates(): %s", user_str)

        # upload_test_addm = loader.get_template('service/emails/upload_t.html')

        # Use different email templates here and send test email to see how it's working:
        user_email = [request.user.email]
        # subject = "Upload test mail TEST...".format(user_name)

        raw_single_out = dict(
            aardvark=dict(
                tku_type='usual',
                mode='fresh',
                fresh_tku_install=dict(
                    aardvark=dict(
                        composed_results=dict(
                            tku_type='ga_candidate',
                            upload_warnings=[],
                            package_type='TKN_release_2018-07-1-107',
                            tku_month='07',
                            tku_statuses=dict(skipped=[], statuses=[]),
                            addm_ip='172.25.149.234',
                            all_warnings=0,
                            upload_test_str_stderr='',
                            upload_test_status='passed',
                            addm_host='vl-aus-rem-qa5r',
                            tku_build='2018',
                            tested_zips=[{'tku_type': 'ga_candidate', 'zip_type': 'edp',
                                          'package_type': 'TKN_release_2018-07-1-107', 'tku_month': '07',
                                          'tku_date': '1', 'addm_version': '11.0', 'tku_name': 'Extended-Data-Pack',
                                          'tku_pack': '', 'tku_addm_version': '11.0',
                                          'zip_file_name': 'Extended-Data-Pack-2018-07-1-ADDM-11.0+.zip',
                                          'tku_build': '2018',
                                          'zip_file_path': '/home/user/TH_Octopus/UPLOAD/HUB/GA_CANDIDATE/TKN_release_2018-07-1-107/publish/tkn/11.0/edp/Extended-Data-Pack-2018-07-1-ADDM-11.0+.zip'},
                                         {'tku_type': 'ga_candidate', 'zip_type': 'tku',
                                          'package_type': 'TKN_release_2018-07-1-107', 'tku_month': '07',
                                          'tku_date': '1', 'addm_version': '11.0',
                                          'tku_name': 'Technology-Knowledge-Update', 'tku_pack': '',
                                          'tku_addm_version': '11.0',
                                          'zip_file_name': 'Technology-Knowledge-Update-2018-07-1-ADDM-11.0+.zip',
                                          'tku_build': '2018',
                                          'zip_file_path': '/home/user/TH_Octopus/UPLOAD/HUB/GA_CANDIDATE/TKN_release_2018-07-1-107/publish/tkn/11.0/tku/Technology-Knowledge-Update-2018-07-1-ADDM-11.0+.zip'},
                                         {'tku_type': 'ga_candidate', 'zip_type': 'tku',
                                          'package_type': 'TKN_release_2018-07-1-107', 'tku_month': '07',
                                          'tku_date': '1', 'addm_version': '11.0',
                                          'tku_name': 'Technology-Knowledge-Update', 'tku_pack': 'Storage',
                                          'tku_addm_version': '11.0',
                                          'zip_file_name': 'Technology-Knowledge-Update-Storage-2018-07-1-ADDM-11.0+.zip',
                                          'tku_build': '2018',
                                          'zip_file_path': '/home/user/TH_Octopus/UPLOAD/HUB/GA_CANDIDATE/TKN_release_2018-07-1-107/publish/tkn/11.0/tku/Technology-Knowledge-Update-Storage-2018-07-1-ADDM-11.0+.zip'}],
                            time_spent_test='2229.2011892795563',
                            test_case_key='ga_candidate_TKN_release_2018-07-1-107_aardvark_fresh_tku_install',
                            upload_test_str_stdout='b\' Uploaded /usr/tideway/TEMP/TKU-BladeEnclosure-2018-07-1-ADDM-11.0+.zip as "TKU-2018-07-1-ADDM-11.0+"\\n Uploaded /usr/tideway/TEMP/TKU-Core-2018-07-1-ADDM-11.0+.zip adding to "TKU-2018-07-1-ADDM-11.0+"\\n Uploaded /usr/tideway/TEMP/TKU-EOL-Data-2018-07-1-ADDM-11.0+.zip as "EDP-2018-07-1-ADDM-11.0+"\\n Uploaded /usr/tideway/TEMP/TKU-Extended-DB-Discovery-2018-07-1-ADDM-11.0+.zip adding to "TKU-2018-07-1-ADDM-11.0+"\\n Uploaded /usr/tideway/TEMP/TKU-Extended-Middleware-Discovery-2018-07-1-ADDM-11.0+.zip adding to "TKU-2018-07-1-ADDM-11.0+"\\n Uploaded /usr/tideway/TEMP/TKU-HW-Data-Mapping-2018-07-1-ADDM-11.0+.zip adding to "EDP-2018-07-1-ADDM-11.0+"\\n Uploaded /usr/tideway/TEMP/TKU-LoadBalancer-2018-07-1-ADDM-11.0+.zip adding to "TKU-2018-07-1-ADDM-11.0+"\\n Uploaded /usr/tideway/TEMP/TKU-ManagementControllers-2018-07-1-ADDM-11.0+.zip adding to "TKU-2018-07-1-ADDM-11.0+"\\n Uploaded /usr/tideway/TEMP/TKU-Network-2018-07-1-ADDM-11.0+.zip adding to "TKU-2018-07-1-ADDM-11.0+"\\n Uploaded /usr/tideway/TEMP/TKU-NVD-Data-2018-07-1-ADDM-11.0+.zip adding to "EDP-2018-07-1-ADDM-11.0+"\\n Uploaded /usr/tideway/TEMP/TKU-Storage-2018-07-1-ADDM-11.0+.zip as "TKU-Storage-2018-07-1-ADDM-11.0+"\\n Uploaded /usr/tideway/TEMP/TKU-System-2018-07-1-ADDM-11.0+.zip adding to "TKU-2018-07-1-ADDM-11.0+"\\n Updated 340 of 2117 PatternModule nodesUpdated 700 of 2117 PatternModule nodesUpdated 1310 of 2117 PatternModule nodesUpdated 1910 of 2117 PatternModule nodesCompiling 2117 rule modulesCompiling 2117 rule modulesCompiling 2117 rule modulesCompiling 2117 rule modules Evaluating uploads for removal3 knowledge uploads activated\\n\\n\'',
                            addm_name='aardvark',
                            upload_errors=[],
                            tku_date='1',
                            addm_version='11.0',
                            addm_v_int='11.0',
                            all_errors=0,
                            test_time='11-08-22',
                            test_date='2018-07-25'
                        ),
                        mode='fresh',
                        wipe_prod_cont_f=dict(
                            product_content=dict(
                                addm='ADDM: aardvark - vl-aus-rem-qa5r',
                                out='Skipped',
                                msg='<=CMD=> Skipped for "product_content" ADDM: aardvark - vl-aus-rem-qa5r'
                            )
                        ),
                        patterns_wipe_f=dict(
                            tw_pattern_management=dict(
                                addm='ADDM: aardvark - vl-aus-rem-qa5r', timest=62.8553524017334,
                                out=['Removed all pattern modules\n', '\n'],
                                err=[],
                                cmd_item='/usr/tideway/bin/tw_pattern_management -p system --remove-all -f'
                            )
                        ),
                        mode_key='fresh_tku_install'
                    )
                )
            )
        )

        mail_html = TMail().upload_t(
            send=False,
            stage='running', start_time=datetime.now(),
            mode='fresh',
            tku_type='DEV usual',
            user_email=user_email,
            outputs=raw_single_out,
            addm_group='DEV delta',
            addm_name='DEV bobblehat',
            addm_host='DEV vl-aus-rem-qa6i',
        )
        return HttpResponse(mail_html)

        # widgets = dict(USER_NAME = user_name, SUBJECT = subject)
        # return HttpResponse(page_widgets.render(widgets, request))

    @staticmethod
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def dev_test_email_night_routine(request):
        from octo.helpers.tasks_oper import WorkerOperations
        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=WEB OCTO AMD=>   dev_test_email_templates(): %s", user_str)

        test_mode = request.GET.get('test_mode')
        user_email = [request.user.email]
        start_time = datetime.now()

        if test_mode == 'start':
            worker_up = WorkerOperations().worker_heartbeat()
            start_args = dict(
                branch='both', send_mail='True', clean="Deprecate", sync_tku='Deprecate', start_date=start_time,
                addm_group_l=['alpha', 'beta', 'charlie', 'delta'], excluded_list=[''], worker_up=worker_up)
            start = dict(
                send=False,
                mode='start',
                debug_flag=True,
                user_email=user_email,
                branch='both',
                addm_group=['alpha', 'beta', 'charlie', 'delta'],
                start_time=start_time,
                start_args=start_args,
            )
            mail_kwargs = start
        elif test_mode == 'run':
            run = dict(
                send=False,
                debug_flag=True,
                user_email=user_email,
                mode='run',
                branch='both',
                start_time=start_time,
                addm_group='test_case_k',
                addm_group_l='addm_group_l',
                addm_test_pairs_len='addm_test_pairs',  # len(addm_test_pairs)
                test_items_len=666,  # len(test_case_v['test'])
                all_tests=999,  # len(sorted_tests_l)
                addm_used=5,  # len(test_case_v['addm'])
                extra_args='TEST',
            )
            mail_kwargs = run
        elif test_mode == 'fin':
            fin = dict(
                send=False,
                debug_flag=True,
                user_email=user_email,
                mode='fin',
                branch='both',
                start_time=start_time,
                addm_group='test_case_k',
                addm_group_l='addm_group_l',
                addm_test_pairs_len='addm_test_pairs',  # len(addm_test_pairs)
                test_items_len=666,  # len(test_case_v['test'])
                all_tests=999,  # len(sorted_tests_l)
                addm_used=5,  # len(test_case_v['addm'])
                extra_args='TEST',
            )
            mail_kwargs = fin
        else:
            mail_kwargs = dict()

        mail_html = TMail().long_r(**mail_kwargs)
        return HttpResponse(mail_html)
        # widgets = dict(USER_NAME = user_name, SUBJECT = subject)
        # return HttpResponse(page_widgets.render(widgets, request))

    @staticmethod
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def dev_select_night_test(request):
        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=DEV OCTO AMD=> dev_select_night_test(): %s", user_str)

        unpack_q = loader.get_template(
            'dev_debug_workbench/dev_helpers/simple_output.html')

        slice_arg = request.GET.get('test_mode')
        excluded_seq = request.GET.get('excluded_seq', False)
        included_seq = request.GET.get('included_seq', False)

        if excluded_seq:
            excluded_seq = excluded_seq.split(',')
        if included_seq:
            included_seq = included_seq.split(',')

        log.info("slice_arg %s, excluded_seq %s, included_seq %s", slice_arg, excluded_seq, included_seq)

        sorted_tests_l = PatternsDjangoModelRaw.patterns_for_test_both(
            slice_arg=slice_arg, excluded_seq=excluded_seq, included_seq=included_seq)

        contxt = dict(
            # STR_OUTPUT = sorted_tests_l,
            # LIST_OUTPUT = sorted_tests_l,
            # KV_OUTPUT = sorted_tests_l,
            QUERY_OUTPUT=sorted_tests_l,
            SUBJECT='dev_select_night_test')
        return HttpResponse(unpack_q.render(contxt, request))

    @staticmethod
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def dev_cron_items(request):
        # from octo.models import DjangoCeleryBeatPeriodictask
        from django_celery_beat.models import PeriodicTask

        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=DEV OCTO AMD=> dev_cron_items(): %s", user_str)

        planned_tasks = PeriodicTask.objects.filter(enabled__exact=1)
        simple_output = loader.get_template('dev_debug_workbench/debug/dev_cron_simple.html')

        widgets = dict(
            SUBJECT='Select CRON tasks.',
            planned_tasks=planned_tasks,
        )

        return HttpResponse(simple_output.render(widgets, request))


class DevAdminTasksCall:
    """
    Move here all clean tasks and task routine calls
    """

    @staticmethod
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def dev_p4_sync_smart(request):
        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=WEB OCTO AMD=>   DEV_p4_sync_smart(): %s", user_str)
        p4_info_page = loader.get_template(
            'dev_debug_workbench/dev_helpers/p4_infos.html')

        subject = "DEV_p4_sync_smart. Run as task - On user {0} request.".format(user_name)
        log.info(subject)

        branch = "tkn_main"
        DevRunner.fire_t(TPatternParse().t_p4_sync_smart,
                         t_args=['tag=p4_sync_smart_dev;type=request;branch={};user={};'.format(branch, user_name)],
                         t_kwargs={'branch': branch})

        contxt = dict(P4_INFO=[], SUBJECT=subject, )
        return HttpResponse(p4_info_page.render(contxt, request))

    @staticmethod
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def dev_parse_patterns_thread(request):
        """
        Parse Octopus local files.
        :param request:
        :return:
        """
        from octo_tku_patterns.tasks import TPatternParse
        page_widgets = loader.get_template('dev_debug_workbench/dev_main.html')
        user_name, user_str = UserCheck().user_string_f(request)

        log.debug("<=WEB OCTO AMD=>   t_p4_changes_threads(): %s", user_str)

        branch = request.GET.get('branch', 'tkn_main')
        subject = 'Run task_p4_changes_threads_web'

        if branch:
            info_string = dict(branch=branch, user_name=user_name, )
            subject = "Perforce task_parse_pattern_web. On {0} request.".format(info_string)
            tag = 'tag=task_parse_pattern_web;type=request;branch={};user={};'.format(branch, user_name)
            DevRunner.fire_t(TPatternParse().t_p4_changes_threads,
                             t_args=[tag],
                             t_kwargs=dict(branch=branch)
                             )
        return HttpResponse(page_widgets.render(dict(SUBJECT=subject), request))

    @staticmethod
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def dev_addm_custom_cmd(request):
        user_name, user_str = UserCheck().user_string_f(request)
        page_widgets = loader.get_template(
            'dev_debug_workbench/dev_main.html')

        cmd_k = request.GET.get('cmd_k', 'show_v')
        addm_group = request.GET.get('addm_group', 'foxtrot')
        subject = '{} Run custom ADDM CMD'.format(user_name)

        t_tag = 'dev_addm_custom_cmd|cmd_k={};addm_group={};user_name={}'.format(cmd_k, addm_group, user_name)
        DevRunner.fire_t(TaskADDMService.t_routine_addm_cmd,
                         t_args=[t_tag],
                         t_kwargs=dict(cmd_k=cmd_k, subject=subject, addm_group=addm_group, user_name=user_name))

        return HttpResponse(page_widgets.render(dict(SUBJECT=subject), request))

    @staticmethod
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def dev_addm_tw_restart(request):
        user_name, user_str = UserCheck().user_string_f(request)
        page_widgets = loader.get_template(
            'dev_debug_workbench/dev_main.html')

        addm_group = request.GET.get('addm_group', 'foxtrot')
        subject = '{} Run RoutineCases.addm_tw_restart'.format(user_name)

        ADDMCases.addm_tw_restart(subject=subject, addm_group=addm_group, user_name=user_name)

        return HttpResponse(page_widgets.render(dict(SUBJECT=subject), request))


class Old:

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def select_all_routine_logs(request):
        """
        Show all logs

        :param request:
        :return:
        """
        from run_core.models import AddmDev, RoutineExecutionLog
        # TODO: Refactor logs format and views
        logs = loader.get_template(
            'dev_debug_workbench/dev_helpers/routine_exec_log.html')
        user_name, user_string = UserCheck().user_string_f(request)
        log.debug("<=VIEW SELECTOR=> select_all_routine_logs(): %s", user_string)
        all_logs = RoutineExecutionLog.objects.all()
        subject = 'Logs from RoutineExecutionLog'
        upload_test_contxt = dict(SUBJECT=subject, LOG_ITEMS_Q=all_logs)
        return HttpResponse(logs.render(upload_test_contxt, request))