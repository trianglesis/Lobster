"""
Celery tasks.
All celery tasks should be collected here.
- Task should execute only separate case or case_routine.
- Task should not execute any code itself.
- Task should have exception handler which output useful data or send mail.
"""
from __future__ import absolute_import, unicode_literals

import datetime
import logging

from django.conf import settings
from django.db.models.query import QuerySet
from django.template import loader
from django.utils import timezone
from rest_framework.renderers import JSONRenderer

from octo.helpers.tasks_helpers import exception
from octo.helpers.tasks_mail_send import Mails
from octo.helpers.tasks_oper import TasksOperations
from octo.helpers.tasks_run import Runner
from octo.octo_celery import app
from octo.settings import SITE_DOMAIN, SITE_SHORT_NAME
from octo_adm.tasks import TaskADDMService
from octo_tku_patterns.api.serializers import TestLatestDigestAllSerializer
from octo_tku_patterns.digests import TestDigestMail
from octo_tku_patterns.model_views import TestLatestDigestAll
from octo_tku_patterns.models import TestLast, TestCases, TestCasesDetails
from octo_tku_patterns.test_executor import TestExecutor
from octotests.tests_discover_run import TestRunnerLoc
from run_core.addm_operations import ADDMStaticOperations
from run_core.local_operations import LocalPatternsP4Parse
from run_core.models import AddmDev, TaskPrepareLog, Options
from run_core.p4_operations import PerforceOperations
from run_core.rabbitmq_operations import RabbitCheck

log = logging.getLogger("octo.octologger")

DAY_LIMIT = 172800
HOURS_2 = 7200
HOURS_1 = 3600
MIN_90 = 5400
MIN_40 = 2400
MIN_20 = 1200
MIN_10 = 600
MIN_5 = 300
MIN_1 = 60
SEC_10 = 10
SEC_1 = 1


# noinspection PyUnusedLocal
class TPatternRoutine:

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TRoutine.t_patt_routines',
              soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_patt_routines(t_tag, **kwargs):
        """
        Can run routines tasks as test methods from unit test case class.
        Reflects external changes to to test file without reload/restart.
        :param t_tag:
        :param kwargs: dict(test_method, test_class, test_module)
        :return:
        """
        log.info(f"<=t_patt_routines=> Running task: {t_tag} kw: {kwargs}", )
        TestRunnerLoc().run_subprocess(**kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TRoutine.t_test_prep',
              soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_test_prep(t_tag, **kwargs):
        """
        User test execution task.
        :param t_tag:
        :param kwargs: view object from request.
        :return:
        """
        log.warning("<=TPatternRoutine=> RUN TaskPrepare.run_tku_patterns %s", t_tag)
        TaskPrepare(kwargs['obj']).run_tku_patterns()


class TPatternExecTest:

    @staticmethod
    @app.task(routing_key='addm_group.TExecTest.t_test_exec_threads.pattern_folder',
              max_retries=1, autoretry_for=(AttributeError,))
    @exception
    def t_test_exec_threads(t_tag, **kwargs):
        log.debug("t_tag: %s", t_tag)
        return TestExecutor().test_run_threads(**kwargs)


class TPatternParse:

    # New:
    @staticmethod
    @app.task(queue='w_parsing@tentacle.dq2', routing_key='parsing.perforce.TExecTest.t_p4_sync_NEW',
              soft_time_limit=MIN_5, task_time_limit=MIN_10)
    @exception
    def t_p4_sync(t_tag):
        log.debug("t_tag: %s", t_tag)
        return LocalPatternsP4Parse().last_changes_get()

    @staticmethod
    @app.task(queue='w_parsing@tentacle.dq2', routing_key='parsing.perforce.TExecTest.t_p4_info',
              soft_time_limit=MIN_1, task_time_limit=MIN_10)
    @exception
    def t_p4_info(t_tag):
        log.debug("t_tag: %s", t_tag)
        return PerforceOperations().p4_info()

    @staticmethod
    @app.task(queue='w_parsing@tentacle.dq2', routing_key='parsing.perforce.TExecTest.t_p4_sync_force',
              soft_time_limit=MIN_20, task_time_limit=MIN_40)
    @exception
    def t_p4_sync_force(t_tag, depot_path):
        """Perforce workspace sync force"""
        log.debug("t_tag: %s", t_tag)
        return PerforceOperations().sync_force(depot_path)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.t_pattern_weight_index',
              soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_pattern_weight_index(t_tag, last_days=30, addm_name='custard_cream'):
        """Calculate pattern time weight on previous execution time"""
        log.debug("t_tag: %s", t_tag)
        PatternTestExecCases.patterns_weight_compute(last_days, addm_name)


class MailDigests:

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.MailDigests.routine_mail',
              soft_time_limit=MIN_10, task_time_limit=MIN_20)
    def routine_mail(tag, **mail_kwargs):
        """
        Send email with task status and details:
        - what task, name, args;
        - when started, added to queue, finished
        - which status have
        - etc.

        :return:
        """
        TestDigestMail().routine_mail(**mail_kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.MailDigests.t_user_digest',
              soft_time_limit=MIN_10, task_time_limit=MIN_20)
    def t_user_digest(t_tag, **kwargs):
        """User test digest mail send task"""
        TestDigestMail().failed_pattern_test_user_daily_digest(**kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.MailDigests.t_lib_digest',
              soft_time_limit=MIN_10, task_time_limit=MIN_20)
    def t_lib_digest(t_tag, **kwargs):
        """ Team test digest by patt LIBRARY send task"""
        TestDigestMail().all_pattern_test_team_daily_digest(**kwargs)


class PatternTestExecCases:

    @staticmethod
    def patterns_weight_compute(last_days, addm_name):
        """
        Use history tests records to compute average test run time for each.
        :return:
        """
        from run_core.local_operations import LocalDB
        # Select and group history records:
        patterns_weight = LocalDB.history_weight(last_days=last_days, addm_name=addm_name)
        # Insert sorted in TKU Patterns table:
        LocalDB.insert_patt_weight(patterns_weight)


class TaskPrepare:

    def __init__(self, obj):
        # Initial view requests:
        # assert isinstance(obj, dict), 'TaskPrepare obj arg should be a dict!'
        self.view_obj = obj
        if isinstance(obj, dict):
            self.options = self.view_obj.get('context')
            self.request = self.view_obj.get('request')
            # Assign generated context for further usage:
            self.selector = self.options.get('selector', {})
            self.user_name = self.view_obj.get('user_name')
            self.user_email = self.view_obj.get('user_email')

            # It's only single test run can include wiping for test_function.
            self.test_function = self.request.get('test_function', None)
        else:
            self.request = None
            self.options = {}
            self.user_name = obj.user_name
            self.user_email = obj.user_email

        # Define fake run:
        self.fake_run = False
        self.fake_fun()

        # Get user and mail:
        self.start_time = datetime.datetime.now()
        log.info("<=TaskPrepare=> Prepare tests for user: %s - %s", self.user_name, self.user_email)

        # Internal statuses:
        self.silent = False
        self.silent_run()
        # Exclude tests using predefined cases group:
        self.exclude = False
        self.excluding()

        self.refresh = False
        self.wipe = False

        self.p4_synced = False  # We care about to wait for p4 to finish its work, to be sure we teat actual data.
        self.addm_synced = False  # We could do not care if this, just add addm_sync before any test task.
        self.test_balanced = False

        # Sorted\grouped test set:
        self.tests_grouped = dict()

        self.t_tag = ''

    def fake_fun(self):
        """
        For debug purposes, just run all tasks as fake_task with showing all inputs and outputs: args, kwargs.
        Local NT environment cannot properly work with celery + threading. Tasks cannot be proceeded in usual manner.
        Should always be fake run!
        :return:
        """
        if settings.DEV:  # Always fake run on local test env:
            self.fake_run = True
            log.debug("<=TaskPrepare=> Fake run for DEV LOCAL options: %s", self.options)
            log.debug("<=TaskPrepare=> Fake run for DEV LOCAL request: %s", self.request)

        elif self.options.get('fake_run'):
            self.fake_run = True
        log.debug("<=TaskPrepare=> Fake run = %s", self.fake_run)

    def silent_run(self):
        """
        Indicates when do not send any mails.
        :return:
        """
        if self.options.get('silent'):
            self.silent = True
        if settings.DEV:
            self.silent = True
        log.debug("<=TaskPrepare=> Silent run = %s", self.silent)

    def excluding(self):
        """
        Indicates when to use cases group 'excluded' to exclude mentioned test cases from current test run.
        False by default, only useful case to use when run routines or numerous tests with multiple cases.
        :return:
        """
        if self.options.get('exclude'):
            self.exclude = True
        log.debug("<=TaskPrepare=> Will exclude some tests = %s", self.exclude)

    def run_tku_patterns(self):
        """
        Method to run 'tku_patterns' tests.
        Run preparations and tasks to complete user test.
        :return:
        """
        self.task_tag_generate()

        # 0. Init test mail?
        self.user_test_mail(mode='init')

        # 1. Select cases for test
        cases_to_test = self.case_selection()

        # 2. Filter cases grouped by types/branches:
        self.tests_grouped = self.case_sort(cases_to_test)

        # 3. Fire last for p4 sync if needed.
        self.sync_depot()

        # 4. Balance grouped tests on workers based on test_type, tkn_branch
        self.tests_balance(self.tests_grouped)

        # 8. Start tests mail send:
        log.info("<=TaskPrepare=> HERE: make single mail task to confirm tests were started")

        # 9. Wipe logs when worker is free, if needed
        self.wipe_logs(cases_to_test)

        # 10. Finish all test mail? If we want to show this routine finished, but tests are still run...
        log.info("<=TaskPrepare=> HERE: make single mail task and the end of addm_worker queue")
        return "Finish this run"

    def sync_depot(self):
        """
        Run p4 sync. Do not lock other runs for addm sync.
        If this function called - then surely wipe latest logs for selected tests.

        When this called - we have already a probably outdated list of cases to test,
            because during p4 sync actual dates and change numbers might change.
        Never mind, user wanted to test selected items, so we will test them even if any
            those cases became unsuitable for previous select (by date, user, change or so).

        :return:
        """

        if self.request.get('refresh'):
            self.wipe = True
            self.refresh = True
            self.p4_synced = False  # To be synced
            log.debug("<=TaskPrepare=> Will execute p4 sync before run tests")
        else:
            self.p4_synced = True  # Let's think we already synced everything:
            return True

        # Only sync and parse depot, no ADDM Sync here!
        t_tag = f'tag=t_p4_sync;user_name={self.user_name};fake={self.fake_run};start_time={self.start_time}'
        t_p4_sync = Runner.fire_t(TPatternParse.t_p4_sync,
                                  fake_run=self.fake_run,
                                  t_args=[t_tag],
                                  t_queue='w_parsing@tentacle.dq2',
                                  t_routing_key='parsing.perforce.TaskPrepare.sync_depot.TPatternParse.t_p4_sync')
        if not self.fake_run:
            log.debug("<=TaskPrepare=> Start waiting for t_p4_sync...")
            if TasksOperations().task_wait_success(t_p4_sync, 't_p4_sync'):
                log.debug("<=TaskPrepare=> Wait for p4_sync_task is finished, lock released!")
                self.p4_synced = True
                return True
        else:
            self.p4_synced = True  # On fake run we just show this p4 sync is finished OK
            return True

    def wipe_logs(self, test_items):
        """
        Delete test logs for current tests
        :param test_items:
        :return:
        """
        deleted = []
        if self.request.get('wipe'):
            self.wipe = True

        if self.fake_run:
            return []

        if self.wipe and not settings.DEV:
            for test_item in test_items:
                deleted_log = self.db_logs_wipe(test_item)
                deleted.append(deleted_log)
        return deleted

    def db_logs_wipe(self, test_item):
        """
        Delete previous logs from TestLast table for selected test case(s).
        Check if test_item is dict or queryset.
        :param test_item:
        :return:
        """
        test_item_deleted = 'None'

        if isinstance(test_item, dict):
            test_py_path = test_item['test_py_path']
        elif isinstance(test_item, TestCases):
            test_py_path = test_item.test_py_path
        else:
            return test_item_deleted

        try:
            if self.test_function:
                log.info("<=TaskPrepare=> Wipe logs for only test unit: %s", self.test_function)
                if '+' in self.test_function:
                    test_arg = self.test_function.split('+')
                else:
                    test_arg = self.test_function.split(' ')
                test_item_deleted = TestLast.objects.filter(
                    test_py_path__exact=test_py_path,
                    tst_class__exact=test_arg[0],
                    tst_name__exact=test_arg[1]).delete()
            else:
                test_item_deleted = TestLast.objects.filter(
                    test_py_path__exact=test_py_path).delete()
        except Exception as e:
            log.error("<=TaskPrepare=> db_logs_wipe Error: %s", e)
        return test_item_deleted

    def case_selection(self):
        """
        Select cases to test using different options.
        At the very end of sorting - sort out by branch or test type.
        Most of internal selections is better to do via TeasCases id field! (Because we always know Cases IDs from backend)
        - Only in exceptional cases use words to sort.
        :return:
        """
        if any(value for value in self.selector.values()):
            log.debug(f'self.selector" {self.selector}')
            queryset = TestCases.objects.all()
        else:
            queryset = TestCases.objects.last()

        if self.selector.get('cases_ids'):
            id_list = self.selector['cases_ids'].split(',')
            queryset = queryset.filter(id__in=id_list)
        elif self.selector.get('pattern_folder_names'):
            pattern_folder_names = self.selector['pattern_folder_names']
            if isinstance(pattern_folder_names, str):
                pattern_folder_names.split(',')
            queryset = queryset.filter(pattern_folder_name__in=pattern_folder_names)
        elif self.selector.get('pattern_folder_name') and not self.selector['pattern_library']:
            queryset = queryset.filter(pattern_folder_name__exact=self.selector['pattern_folder_name'])
        elif self.selector.get('pattern_folder_name') and self.selector['pattern_library']:
            queryset = queryset.filter(
                pattern_folder_name__exact=self.selector['pattern_folder_name'],
                pattern_library__exact=self.selector['pattern_library'])
        elif self.selector.get('change'):
            queryset = queryset.filter(change__exact=self.selector['change'])
        elif self.selector.get('change_user'):
            queryset = queryset.filter(change_user__exact=self.selector['change_user'])
        elif self.selector.get('change_review'):
            queryset = queryset.filter(change_review__exact=self.selector['change_review'])
        elif self.selector.get('change_ticket'):
            queryset = queryset.filter(change_ticket__exact=self.selector['change_ticket'])
        elif self.selector.get('test_py_path'):
            queryset = queryset.filter(test_py_path__exact=self.selector['test_py_path'])
        else:
            # We won't run any test if not sure how it was selected:
            return None

        if self.selector.get('tkn_branch'):
            queryset = queryset.filter(tkn_branch__exact=self.selector['tkn_branch'])
        if self.selector.get('test_type'):
            queryset = queryset.filter(test_type__exact=self.selector['test_type'])

        return queryset.order_by('tkn_branch')

    def case_exclusion(self, queryset):
        """
        Should check custom groups for option 'exclude=True'
        and then exclude members of those groups from test routine run.
        Or, maybe only exclude when this was executed by CRON and night routine?
        :return:
        """
        if self.exclude:
            log.debug("<=TaskPrepare=> Before exclude: %s", queryset.count())
            excluded_group = TestCasesDetails.objects.get(title__exact='excluded')
            excluded_ids = excluded_group.test_cases.values('id')
            log.debug("Excluded cases are: %s", excluded_ids)
            queryset = queryset.exclude(id__in=excluded_ids)
            log.debug("<=TaskPrepare=> After exclude: %s", queryset.count())
        return queryset

    def case_sort(self, to_test_queryset):
        """
        If user select case(s) to test:
        - split selected on groups by:
        -- test type: tku_patterns/main_python/octo_tests(TBA)
        -- then on groups (for tku_patterns) by branches: tkn_main/tkn_ship

        Later this dict will be used to assign ADDM group for each.
        :return:
        """

        if self.exclude:
            to_test_queryset = self.case_exclusion(to_test_queryset)

        grouped = dict(
            tku_patterns=dict(
                tkn_main=to_test_queryset.filter(tkn_branch__exact='tkn_main'),  # .values()
                tkn_ship=to_test_queryset.filter(tkn_branch__exact='tkn_ship'),  # .values()
            ),
            main_python=to_test_queryset.filter(test_type__exact='main_python'),  # .values()
            octo_tests=to_test_queryset.filter(test_type__exact='octo_tests'),  # .values()
        )
        log.debug("<=TaskPrepare=> grouped: %s", grouped)
        return grouped

    def tests_balance(self, tests_grouped):
        """
        Balance selected and grouped tests between worker groups.

        :param tests_grouped:
        :return:
        """
        assert isinstance(tests_grouped, dict), 'Test tests_grouped should be a dict: %s' % type(tests_grouped)

        tku_patterns_tests = tests_grouped.get('tku_patterns', {})
        log.debug("<=TaskPrepare=> tku_patterns_tests: %s", tku_patterns_tests)
        for branch_k, branch_cases in tku_patterns_tests.items():
            if branch_cases:
                log.debug(f"<=TaskPrepare=> Balancing tests for branch: '{branch_k}': {branch_cases}")
                # 5. Assign free worker for test cases run
                addm_group = self.addm_group_get(tkn_branch=branch_k)
                addm_set = self.addm_set_select(addm_group=addm_group)
                # 6. Sync current ADDM set with actual data from Octopus, after p4 sync finished it's work:
                self.addm_rsync(addm_set)
                # 6.1 Something like prep step? Maybe delete/wipe/kill other tests or ensure ADDM on OK state and so on.
                self.prep_step(addm_set)
                for test_item in branch_cases:
                    log.debug(f'test_item: {test_item} {type(test_item)} {test_item.test_py_path}')
                    # 7.1 Fire task for test starting
                    self.user_test_mail('start', test_item=test_item, addm_set=addm_set)
                    # 7.2 Fire task for test execution
                    self.test_exec(addm_set, test_item)
                    # 7.3 Add mail task after one test, so it show when one test was finished.
                    self.user_test_mail('finish', test_item=test_item, addm_set=addm_set)
                    # 8 Save log when test task finished, disregard any results:
            else:
                log.debug("<=TaskPrepare=> This branch had no selected tests to run: '%s'", branch_k)

    @staticmethod
    def branched_w(branch):
        """
        Select only workers are related to branch
        :type branch: str
        """
        branched_w = Options.objects.get(option_key__exact=f'branch_workers.{branch}')
        branched_w = branched_w.option_value.replace(' ', '').split(',')
        return branched_w

    @staticmethod
    def rabbit_queue_minimal(workers_q):
        workers = [worker + '@tentacle.dq2' for worker in workers_q]
        all_queues_len = RabbitCheck().queue_count_list(workers)
        worker_min = min(all_queues_len, key=all_queues_len.get)
        if '@tentacle' in worker_min:
            worker_min = worker_min.replace('@tentacle.dq2', '')
        return worker_min

    def addm_group_get(self, tkn_branch):
        """
        Check addm groups for available and mininal loaded worker.
        Depends on branch.
            TBA: Later add dependency on test_type, 'main_python' OR 'tku_patterns' OR 'octo_tests'

        :param tkn_branch:
        :return:
        """
        branch_w = self.branched_w(tkn_branch)
        addm_group = self.rabbit_queue_minimal(workers_q=branch_w)  # Ask rabbit mq for less busy queue:
        return addm_group

    def addm_set_select(self, addm_group=None):
        queryset = AddmDev.objects.all()
        if self.options.get('addm_group'):
            log.info("<=TaskPrepare=> ADDM_GROUP from request params: '%s'", self.options.get('addm_group'))
            addm_set = queryset.filter(
                addm_group__exact=self.options.get('addm_group'),
                disables__isnull=True).values()
        else:
            addm_set = queryset.filter(
                addm_group__exact=addm_group,
                disables__isnull=True
            ).values()
        return addm_set

    def addm_rsync(self, addm_set):
        """
        Run task for ADDM rsync command to actualize data on test env from Octopus, after p4 sync finished.
        Task is adding on worker where test would run, so we don't wait this task to finish.

        :param addm_set:
        :return:
        """
        # Only if p4 sync correctly OR we forced it to True:
        addm = addm_set.first()
        if self.p4_synced and self.request.get('refresh'):
            log.debug("<=TaskPrepare=> Adding task to sync addm group: '%s'", addm['addm_group'])
            commands_qs = ADDMStaticOperations.select_operation([
                'rsync.python.testutils',
                'rsync.tideway.utils',
                'rsync.tku.data',
            ])
            for operation_cmd in commands_qs:
                t_tag = f'tag=t_addm_rsync_threads;addm_group={addm["addm_group"]};user_name={self.user_name};' \
                        f'fake={self.fake_run};start_time={self.start_time};command_k={operation_cmd.command_key};'
                addm_grouped_set = addm_set.filter(addm_group__exact=addm["addm_group"])
                t_kwargs = dict(addm_set=addm_grouped_set, operation_cmd=operation_cmd)
                Runner.fire_t(TaskADDMService.t_addm_cmd_thread,
                              fake_run=self.fake_run,
                              t_queue=f'{addm["addm_group"]}@tentacle.dq2',
                              t_args=[t_tag],
                              t_kwargs=t_kwargs,
                              t_routing_key=f'{addm["addm_group"]}.{operation_cmd.command_key}.TaskADDMService.t_addm_cmd_thread')

    def prep_step(self, addm_set):
        """
        Kill any hung tests or scans before test run, to be sure ADDM is ready for actual user test.

        :param addm_set:
        :return:
        """
        addm = addm_set.first()
        commands_qs = ADDMStaticOperations.select_operation([
            'test.kill.term',  # Kill any hanged test before.
            'tw_scan_control.clear',  # Stop any running scan
            'wipe.addm.pool',
            'wipe.addm.record',
            'wipe.tpl.files',
        ])
        for operation_cmd in commands_qs:
            t_tag = f'tag=t_addm_cmd_thread;addm_group={addm["addm_group"]};user_name={self.user_name};' \
                    f'fake={self.fake_run};start_time={self.start_time};command_k={operation_cmd.command_key};'
            addm_grouped_set = addm_set.filter(addm_group__exact=addm["addm_group"])
            t_kwargs = dict(addm_set=addm_grouped_set, operation_cmd=operation_cmd)
            Runner.fire_t(TaskADDMService.t_addm_cmd_thread,
                          fake_run=self.fake_run,
                          t_queue=f'{addm["addm_group"]}@tentacle.dq2',
                          t_args=[t_tag],
                          t_kwargs=t_kwargs,
                          t_routing_key=f'{addm["addm_group"]}.{operation_cmd.command_key}.TaskADDMService.t_addm_cmd_thread')

    def user_test_mail(self, mode, **kwargs):
        """
        Send mails during user test run. Stages: init, start, finish.
        Finish stage will include test results.
        :param mode:
        :return:
        """
        test_item = kwargs.get('test_item', None)  # When test are sorted and prepared
        addm_set = kwargs.get('addm_set', None)
        test_added = loader.get_template('service/emails/statuses/test_added.html')
        addm_group = ''

        cases_ids_l = self.request.get("cases_ids", "").split(',')
        cases_selected = TestCases.objects.filter(id__in=cases_ids_l)
        # Different mode options:
        if mode == 'init':
            init_subject = f'selected cases id: {cases_ids_l}'
            subject = f'[{SITE_SHORT_NAME}] User test init: {init_subject}'
            TaskPrepareLog(subject=subject, user_email=self.user_email).save()
            mail_html = test_added.render(dict(subject=subject, domain=SITE_DOMAIN, mode=mode, cases_selected=cases_selected))

        elif mode == 'start':
            addm = addm_set.first()
            isinstance(addm, dict), "First element from QuerySet should be a dict type!"
            isinstance(test_item, TestCases), "Test item should be TestCases object!"
            addm_group = addm.get('addm_group', None)
            subject_str = f'{test_item.tkn_branch} | {test_item.pattern_library} | {test_item.pattern_folder_name}'
            subject = f'[{SITE_SHORT_NAME}] User test started: {subject_str}'
            mail_html = test_added.render(dict(subject=subject, domain=SITE_DOMAIN, mode=mode, cases_selected=cases_selected, addm_set=addm_set))

        elif mode == 'finish':
            addm = addm_set.first()
            isinstance(addm, dict), "First element from QuerySet should be a dict type!"
            isinstance(test_item, TestCases), "Test item should be TestCases object!"
            addm_group = addm.get('addm_group', None)
            subject_str = f'{test_item.tkn_branch} | {test_item.pattern_library} | {test_item.pattern_folder_name}'
            subject = f'[{SITE_SHORT_NAME}] User test finished: {subject_str}'
            mail_html = None  # Later fill in task, when start or finish - with test digest!

        else:
            subject = f'[{SITE_SHORT_NAME}] User test failed: : {cases_ids_l}'
            log.debug("Unusual mail mode!")
            TaskPrepareLog(subject=subject, user_email=self.user_email,
                           details=f'test_item: {test_item.values()}, addm_set: {addm_set.values()}').save()
            mail_html = test_added.render(dict(subject=subject, domain=SITE_DOMAIN, mode=mode))


        if mode == 'start' or mode == 'finish':
            mail_r_key = f'{addm_group}.TaskPrepare.t_short_mail.{mode}'
            t_tag = f'tag=t_user_mail;mode={mode};{addm_group};{self.user_name};{test_item.test_py_path}'
            Runner.fire_t(self.mail_s,
                          fake_run=self.fake_run,
                          t_args=[t_tag],
                          t_kwargs={'mode': mode, 'test_item': test_item,
                                    'mail_html': mail_html,  # If none - fill in task
                                    'subject': subject,
                                    'user_email': self.user_email},
                          t_queue=addm_group + '@tentacle.dq2',
                          t_routing_key=mail_r_key)
        else:
            Mails.short(subject=subject,
                        send_to=[self.user_email],
                        mail_html=mail_html,
                        )
        return 'User test mail sent!'

    @staticmethod
    @app.task(soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def mail_s(tag, **kwargs):
        mode = kwargs.get('mode')
        test_item = kwargs.get('test_item')
        mail_html = kwargs.get('mail_html', None)
        user_email = kwargs.get('user_email')
        subject = kwargs.get('subject')


        log_html = ''
        tests_digest = ''

        time_stamp = datetime.datetime.now(tz=timezone.utc).strftime('%Y-%m-%d_%H-%M')
        isinstance(test_item, TestCases), "Test item should be TestCases object!"

        if mode == 'finish':
            # Again render new start-finish email body
            test_added = loader.get_template('service/emails/statuses/test_added.html')
            # Render attachment log
            test_log_html = loader.get_template('digests/tables_details/test_details_table_email.html')

            tests_digest = TestLatestDigestAll.objects.filter(test_py_path__exact=test_item.test_py_path).order_by('-addm_name')
            test_logs = TestLast.objects.filter(test_py_path__exact=test_item.test_py_path).order_by('-addm_name').distinct()

            log.debug(f"test_logs: {test_logs}")
            log.debug(f"tests_digest: {tests_digest}")

            mail_html = test_added.render(dict(subject=subject, domain=SITE_DOMAIN, mode=mode, tests_digest=tests_digest))
            log_html = test_log_html.render(dict(test_detail=test_logs, domain=SITE_DOMAIN, ))

        subject_str = f'{test_item.tkn_branch}_{test_item.pattern_library}_{test_item.pattern_folder_name}'
        Mails.short(subject=subject,
                    send_to=[user_email],
                    mail_html=mail_html,
                    attach_content=log_html if log_html else None,
                    attach_content_name=f'{subject_str}_test_{time_stamp}.html',
                    )
        if tests_digest:
            tests_digest = JSONRenderer().render(TestLatestDigestAllSerializer(tests_digest, many=True).data).decode(
                'utf-8')
        else:
            tests_digest = 'Empty'
        TaskPrepareLog(subject=subject, user_email=user_email, details=tests_digest).save()
        return f'Mail sent {subject}'

    def test_exec(self, addm_set, test_item):
        """
        Fire task of test execution.
        :param addm_set:
        :param test_item:
        :return:
        """
        assert isinstance(test_item, TestCases), 'Test item should be a QuerySet: %s' % type(test_item)
        assert isinstance(addm_set, QuerySet), "Addm set should be a QuerySet: %s" % type(addm_set)

        addm = addm_set.first()
        task_r_key = '{}.TExecTest.t_test_exec_threads.{}'.format(addm['addm_group'], test_item.pattern_folder_name)
        t_tag = f'tag=t_test_exec_threads;type=user_routine;branch={test_item.tkn_branch};' \
                f'addm_group={addm["addm_group"]};user_name={self.user_name};' \
                f'refresh={self.refresh};t_ETA={test_item.test_time_weight};test_case_path={test_item.test_case_depot_path}'
        if test_item.test_time_weight:
            test_t_w = round(float(test_item.test_time_weight))
        else:
            test_t_w = 60 * 15

        # Test task exec:
        Runner.fire_t(TPatternExecTest.t_test_exec_threads,
                      fake_run=self.fake_run,
                      t_queue=addm['addm_group'] + '@tentacle.dq2', t_args=[t_tag],
                      t_kwargs=dict(user_email=self.user_email,
                                    user_name=self.user_name,
                                    addm_items=addm_set,
                                    test_item=test_item,
                                    test_function=self.test_function),
                      t_routing_key=task_r_key,
                      t_soft_time_limit=test_t_w + 60 * 20,
                      t_task_time_limit=test_t_w + 60 * 30)

    def task_tag_generate(self):
        """Just make a task tag for this routine"""
        task_string = 'tag=t_TackPrepare_user_tests;type=routine;branch={tkn_branch};' \
                      'addm_group={addm_group};user_name={user_name};refresh={refresh};{pattern_library}/{pattern_folder_name}'
        t_tag_d = task_string.format(
            tkn_branch=self.selector.get('tkn_branch'),
            addm_group=self.selector.get('addm_group'),
            pattern_library=self.selector.get('pattern_library'),
            pattern_folder_name=self.selector.get('pattern_folder_name'),
            user_name=self.user_name,
            refresh=self.request.get('refresh'),
        )
        log.debug("<=TaskPrepare=> User test user_test_add: \n%s", t_tag_d)
        self.t_tag = t_tag_d
