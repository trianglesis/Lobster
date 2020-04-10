"""
Celery tasks.
All celery tasks should be collected here.
- Task should execute only separate case or case_routine.
- Task should not execute any code itself.
- Task should have exception handler which output useful data or send mail.

Note:
    - Be careful with recursive import.
    - Do not import case routines which import tasks from here.
"""
from __future__ import absolute_import, unicode_literals

import datetime
import logging
import os

from django.db.models.query import QuerySet

import octo.config_cred as conf_cred
from octo import settings

from octo.helpers.tasks_helpers import TMail
from octo.helpers.tasks_helpers import exception
from octo.helpers.tasks_oper import TasksOperations
from octo.helpers.tasks_run import Runner
from octo.octo_celery import app
from octo.tasks import TSupport
from octo_adm.tasks import TaskADDMService
from octo_tku_patterns.models import TestLast, TestCases, TestCasesDetails
from octo_tku_patterns.test_executor import TestExecutor
from octotests.tests_discover_run import TestRunnerLoc
from run_core.addm_operations import ADDMStaticOperations
from run_core.local_operations import LocalPatternsP4Parse
from run_core.models import AddmDev
from run_core.p4_operations import PerforceOperations

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
    def t_patt_routines(t_tag, **kwargs):
        """
        Can run routines tasks as test methods from unit test case class.
        Reflects external changes to to test file without reload/restart.
        :param t_tag:
        :param kwargs: dict(test_method, test_class, test_module)
        :return:
        """
        log.info("<=t_upload_routines=> Running task %s", kwargs)
        TestRunnerLoc().run_subprocess(**kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TRoutine.t_test_prep',
              soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_test_prep(t_tag, **kwargs):
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
        log.debug("t_tag: %s", t_tag)
        return PerforceOperations().sync_force(depot_path)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.t_pattern_weight_index',
              soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_pattern_weight_index(t_tag, last_days=30, addm_name='custard_cream'):
        log.debug("t_tag: %s", t_tag)
        PatternTestExecCases.patterns_weight_compute(last_days, addm_name)


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

        # NOTE: It can change during process current class!!!!`
        self.t_tag = ''

    def fake_fun(self):
        """
        For debug purposes, just run all tasks as fake_task with showing all inputs and outputs: args, kwargs.
        Local NT environment cannot properly work with celery + threading. Tasks cannot be proceeded in usual manner.
        Should always be fake run!
        :return:
        """
        if conf_cred.DEV_HOST in settings.CURR_HOSTNAME:  # Always fake run on local test env:
            # self.fake_run = True
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
        :return:
        """
        self.task_tag_generate()

        # 0. Init test mail?
        self.mail_status(mail_opts=dict(mode='init'))

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
            return self.p4_synced

        # Only sync and parse depot, no ADDM Sync here!
        # TODO: Add task for sync to the same routine worker so it only can start next tests after sync was finished?
        t_tag = f'tag=t_p4_sync;user_name={self.user_name};fake={self.fake_run};start_time={self.start_time}'
        t_p4_sync = Runner.fire_t(TPatternParse.t_p4_sync,
                                  fake_run=self.fake_run, t_args=[t_tag], t_queue='w_parsing@tentacle.dq2',
                                  t_routing_key='parsing.perforce.TaskPrepare.sync_depot.TPatternParse.t_p4_sync')
        if not self.fake_run:
            log.debug("<=TaskPrepare=> Start waiting for t_p4_sync...")
            if TasksOperations().task_wait_success(t_p4_sync, 't_p4_sync'):
                log.debug("<=TaskPrepare=> Wait for p4_sync_task is finished, lock released!")
                self.p4_synced = True
                # return self.p4_synced
        else:
            # On fake run we just show this p4 sync is finished OK
            self.p4_synced = True
            return self.p4_synced

    def wipe_logs(self, test_items):
        if self.test_balanced:
            log.info("<=TaskPrepare=> All tests are balanced and assigned to workers, we now can wipe logs?")

        deleted = []
        if self.request.get('wipe'):
            self.wipe = True
            log.info("<=TaskPrepare=> Will wipe old logs for selected case(s)")
        elif self.wipe and self.refresh:
            log.info("<=TaskPrepare=> Forced: Will wipe old logs for selected case(s). By: self.refresh = %s", self.refresh)

        if self.fake_run:
            return []

        if self.wipe:
            for test_item in test_items:
                deleted_log = self.db_logs_wipe(test_item)
                deleted.append(deleted_log)
        else:
            log.info("<=TaskPrepare=> Not wiping previous logs.")
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
                log.debug("<=TaskPrepare=> Wipe logs for only test unit: %s", self.test_function)
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

        # TODO: Not actually select ALL if we don't get/understand request args?
        # TODO: Sort only pattern test cases?
        if any(value for value in self.selector.values()):
            queryset = TestCases.objects.all()
        else:
            queryset = TestCases.objects.last()

        # # Most common and usual way to select cases for tests:
        # log.debug("self.selector: %s", self.selector)
        # for key, value in self.selector.items():
        #     if value:
        #         log.debug("True val for key: %s val: %s", key, value)
        #     else:
        #         log.debug("False val for key: %s val: %s", key, value)
        # log.debug("self.selector value: %s", any(value for value in self.selector.values()))

        if self.selector.get('cases_ids'):
            id_list = self.selector['cases_ids'].split(',')
            log.debug("<=TaskPrepare=> Selecting cases by id: %s", id_list)
            queryset = queryset.filter(id__in=id_list)
        # Older but useful from search perspectives???
        elif self.selector.get('pattern_folder_names'):
            pattern_folder_names = self.selector['pattern_folder_names']
            if isinstance(pattern_folder_names, str):
                pattern_folder_names.split(',')
            log.debug("<=TaskPrepare=> Selecting cases by 'pattern_folder_names: %s", pattern_folder_names)
            queryset = queryset.filter(pattern_folder_name__in=pattern_folder_names)
        # Not sure this is the best solution to sort out
        elif self.selector.get('pattern_folder_name') and not self.selector['pattern_library']:
            log.debug("<=TaskPrepare=> Selecting cases by 'pattern_folder_name': %s", self.selector['pattern_folder_name'])
            queryset = queryset.filter(pattern_folder_name__exact=self.selector['pattern_folder_name'])
        # Current implemented way, but remove it later?
        elif self.selector.get('pattern_folder_name') and self.selector['pattern_library']:
            log.debug("<=TaskPrepare=> Selecting cases by 'pattern_library' AND 'pattern_folder_name': %s", self.selector['pattern_folder_name'])
            queryset = queryset.filter(
                pattern_folder_name__exact=self.selector['pattern_folder_name'],
                pattern_library__exact=self.selector['pattern_library'])
        # Test all cases related to p4 change:
        elif self.selector.get('change'):
            log.debug("<=TaskPrepare=> Selecting cases by 'change': %s", self.selector['change'])
            queryset = queryset.filter(change__exact=self.selector['change'])
        # Test all cases related to p4 change user:
        elif self.selector.get('change_user'):
            log.debug("<=TaskPrepare=> Selecting cases by 'change_user': %s", self.selector['change_user'])
            queryset = queryset.filter(change_user__exact=self.selector['change_user'])
        # Test all cases related to change review if any:
        elif self.selector.get('change_review'):
            log.debug("<=TaskPrepare=> Selecting cases by 'change_review': %s", self.selector['change_review'])
            queryset = queryset.filter(change_review__exact=self.selector['change_review'])
        # Test all cases related to change ticket if any:
        elif self.selector.get('change_ticket'):
            log.debug("<=TaskPrepare=> Selecting cases by 'change_ticket': %s", self.selector['change_ticket'])
            queryset = queryset.filter(change_ticket__exact=self.selector['change_ticket'])
        # Test case with selected test_py - to be removed maybe later?:
        elif self.selector.get('test_py_path'):
            log.debug("<=TaskPrepare=> Selecting cases by 'test_py_path': %s", self.selector['test_py_path'])
            queryset = queryset.filter(test_py_path__exact=self.selector['test_py_path'])
        else:
            # Ignore any unused options:
            pass

        # Queryset strict by branch if needed:
        if self.selector.get('tkn_branch'):
            log.debug("<=TaskPrepare=> Selecting cases by 'tkn_branch': %s", self.selector['tkn_branch'])
            queryset = queryset.filter(tkn_branch__exact=self.selector['tkn_branch'])
        # Queryset strict by test_type:
        if self.selector.get('test_type'):
            log.debug("<=TaskPrepare=> Selecting cases by 'test_type': %s", self.selector['test_type'])
            queryset = queryset.filter(test_type__exact=self.selector['test_type'])

        # log.debug("<=TaskPrepare=> queryset: %s", queryset.query)
        log.debug("<=TaskPrepare=> cases_to_test: %s", queryset.count())
        # log.debug("<=TaskPrepare=> Items: %s", queryset)
        return queryset.order_by('tkn_branch')

    def case_exclusion(self, queryset):
        """
        Should check custom groups for option 'exclude=True'
        and then exclude members of those groups from test routine run.
        Or, maybe only exclude when this was executed by CRON and night routine?
        :return:
        """
        if self.exclude:
            log.info("<=TaskPrepare=> About to exclude some tests which are added to group exclude!")
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

        Note: "octo_tests" should never run in this class!
        :return:
        """

        if self.exclude:
            to_test_queryset = self.case_exclusion(to_test_queryset)

        grouped = dict(
            tku_patterns=dict(
                tkn_main=to_test_queryset.filter(tkn_branch__exact='tkn_main').values(),
                tkn_ship=to_test_queryset.filter(tkn_branch__exact='tkn_ship').values(),
            ),
            main_python=to_test_queryset.filter(test_type__exact='main_python').values(),
            octo_tests=to_test_queryset.filter(test_type__exact='octo_tests').values(),
        )
        # log.debug("<=TaskPrepare=> grouped: %s", grouped)
        return grouped

    def tests_balance(self, tests_grouped):
        """
        Balance selected and grouped tests between worker groups.

        :param tests_grouped:
        :return:
        """
        assert isinstance(tests_grouped, dict), 'Test tests_grouped should be a dict: %s' % type(tests_grouped)

        tku_patterns_tests = tests_grouped.get('tku_patterns', {})
        # log.debug("<=TaskPrepare=> tku_patterns_tests: %s", tku_patterns_tests)

        for branch_k, branch_cases in tku_patterns_tests.items():
            if branch_cases:
                log.debug("<=TaskPrepare=> Balancing tests for branch: '%s'", branch_k)
                # 5. Assign free worker for test cases run
                addm_group = self.addm_group_get(tkn_branch=branch_k)
                addm_set = self.addm_set_select(addm_group=addm_group)

                # 6. Sync current ADDM set with actual data from Octopus, after p4 sync finished it's work:
                self.addm_rsync(addm_set)

                # 6.1 Something like prep step? Maybe delete/wipe/kill other tests or ensure ADDM on OK state and so on.
                self.prep_step(addm_set)

                for test_item in branch_cases:
                    # 7.1 Fire task for test starting
                    self.mail_status(mail_opts=dict(mode='start', test_item=test_item, addm_set=addm_set))
                    # 7.2 Fire task for test execution
                    self.test_exec(addm_set, test_item)
                    # 7.3 Add mail task after one test, so it show when one test was finished.
                    self.mail_status(mail_opts=dict(mode='finish', test_item=test_item, addm_set=addm_set))
            else:
                log.debug("<=TaskPrepare=> This branch had no selected tests to run: '%s'", branch_k)

    def addm_group_get(self, tkn_branch):
        """
        Check addm groups for available and mininal loaded worker.
        Depends on branch.
            TBA: Later add dependency on test_type, 'main_python' OR 'tku_patterns' OR 'octo_tests'

        :param tkn_branch:
        :return:
        """

        """DEBUG:"""
        from octo_tku_patterns.user_test_balancer import WorkerGetAvailable
        branch_w = WorkerGetAvailable.branched_w(tkn_branch)
        addm_group = branch_w[0]

        if not self.fake_run:
            addm_group = WorkerGetAvailable().user_test_available_w(branch=tkn_branch, user_mail=self.user_email)
        log.debug("<=TaskPrepare=> Get available addm_group: '%s'", addm_group)
        return addm_group

    def addm_set_select(self, addm_group=None):
        # TODO: Return only JSON-friendly and required for test run values (passwords could not be excluded =( )
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
        # log.info("<=TaskPrepare=> Will use selected addm_set to run test: %s",  addm_set)
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
            commands_set = ADDMStaticOperations.select_operation([
                'rsync.python.testutils',
                'rsync.tideway.utils',
                'rsync.tku.data',
            ])
            for operation_cmd in commands_set:
                t_tag = f'tag=t_addm_rsync_threads;addm_group={addm["addm_group"]};user_name={self.user_name};' \
                        f'fake={self.fake_run};start_time={self.start_time};command_k={operation_cmd.command_key};'
                addm_grouped_set = addm_set.filter(addm_group__exact=addm["addm_group"])
                t_kwargs = dict(addm_set=addm_grouped_set, operation_cmd=operation_cmd)
                Runner.fire_t(TaskADDMService.t_addm_cmd_thread,
                              t_queue=f'{addm["addm_group"]}@tentacle.dq2',
                              t_args=[t_tag],
                              t_kwargs=t_kwargs,
                              t_routing_key=f'{addm["addm_group"]}.addm_rsync.TaskADDMService.t_addm_cmd_thread')

    def prep_step(self, addm_set):
        log.info("<=TaskPrepare=> Preparing step before test run!")
        addm = addm_set.first()
        # TODO: Here we can kill test.py, wipe old data, run cmd and so on.

    def mail_status(self, mail_opts):
        mode = mail_opts.get('mode')
        mail_opts.update(request=self.request)
        mail_opts.update(user_email=self.user_email)

        if not self.silent:
            log.info("<=TaskPrepare=> Mail sending, mode: %s", mode)
            if mail_opts.get('test_item') and mail_opts.get('addm_set'):
                addm = mail_opts.get('addm_set').first()
                test_item = mail_opts.get('test_item')

                mail_r_key = f'{addm["addm_group"]}.TSupport.t_user_mail.{mode}.TSupport.t_user_test'
                t_tag = f'tag=t_user_mail;mode={mode};addm_group={addm["addm_group"]};user_name={self.user_name};' \
                        f'test_py_path={test_item["test_py_path"]}'

                Runner.fire_t(TSupport.t_user_test, fake_run=self.fake_run, t_args=[t_tag],
                              t_kwargs=dict(mail_opts=mail_opts),
                              t_queue=addm['addm_group']+'@tentacle.dq2', t_routing_key=mail_r_key)
            elif mode == 'init':
                TMail().user_test(mail_opts)
            else:
                TMail().user_test(mail_opts)
        else:
            log.info("<=TaskPrepare=> Mail silent mode. Do not send massages. Current stage: %s", mode)

    def test_exec(self, addm_set, test_item):
        """
        Fire task of test execution.
        :param addm_set:
        :param test_item:
        :return:
        """
        assert isinstance(test_item, dict), 'Test item should be a dict: %s' % type(test_item)
        assert isinstance(addm_set, QuerySet), "Addm set should be a QuerySet: %s" % type(addm_set)

        addm = addm_set.first()
        task_r_key = '{}.TExecTest.t_test_exec_threads.{}'.format(addm['addm_group'], test_item["pattern_folder_name"])
        t_tag = f'tag=t_test_exec_threads;type=user_routine;branch={test_item["tkn_branch"]};' \
                f'addm_group={addm["addm_group"]};user_name={self.user_name};' \
                f'refresh={self.refresh};t_ETA={test_item["test_time_weight"]};test_case_path={test_item["test_case_depot_path"]}'
        if test_item['test_time_weight']:
            test_t_w = round(float(test_item['test_time_weight']))  # TODO: If NoneType - use 0
        else:
            test_t_w = 300

        # Test task exec:
        Runner.fire_t(TPatternExecTest.t_test_exec_threads, fake_run=self.fake_run, to_sleep=10, debug_me=True,
                      t_queue=addm['addm_group'] + '@tentacle.dq2', t_args=[t_tag],
                      t_kwargs=dict(user_email=self.user_email, user_name=self.user_name, addm_items=list(addm_set), test_item=test_item,
                                    test_function=self.test_function),
                      t_routing_key=task_r_key,
                      t_soft_time_limit=test_t_w+900,
                      t_task_time_limit=test_t_w+1200)

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
        # log.debug("<=TaskPrepare=> User test user_test_add: \n%s", t_tag_d)
        self.t_tag = t_tag_d

    def test_and_addm_check(self, addm_set, test_item):
        if not addm_set or not test_item:
            self.mail_status(mail_opts=dict(mode='fail', test_item=test_item))
