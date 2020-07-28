import datetime
# DEBUG TOOLS
import json
import logging
import unittest
from pprint import pformat

from celery.result import AsyncResult
from django.utils import timezone

from octo.config_cred import mails
from octo.helpers.tasks_run import Runner
from octo_adm.tasks import TaskADDMService
from octo_tku_patterns.model_views import TestLatestDigestFailed
from octo_tku_patterns.models import TestCases, TestCasesDetails, TestLast
from octo_tku_patterns.night_test_balancer import BalanceNightTests
from octo_tku_patterns.table_oper import PatternsDjangoTableOper
from octo_tku_patterns.tasks import TPatternExecTest, MailDigests
from octo_tku_patterns.tasks import TaskPrepare
from octo_tku_upload.models import TkuPackagesNew as TkuPackages
from octo_tku_upload.tasks import UploadTaskPrepare
from run_core.addm_operations import ADDMOperations, ADDMStaticOperations
from run_core.models import AddmDev

log = logging.getLogger("octo.octologger")


class PatternTestUtils(unittest.TestCase):
    """
    - check life execution
    - check how logs saved with new TestCases model values
    - check how task time limit works with test_weight
    - think about to add some more preparations before run tests
    - refactor unused logs, vars
    - add docs to methods
    - add assertions for sensitive data, vars and types

    Optional:
    - review mails, make shorter, more informative
    Global:
    - finally make method for task_time_limit work
    - use one task to fire TestCase for Upload, TestCases and so on.

    When ready:
    - remove old routine and task

    """

    def __init__(self, *args, **kwargs):
        super(PatternTestUtils, self).__init__(*args, **kwargs)
        self.now = datetime.datetime.now(tz=timezone.utc)
        self.tomorrow = self.now + datetime.timedelta(days=1)

        self.user_name = None
        self.user_email = None
        self.fake_run = False
        self.silent = False

        self.branch = None
        self.queryset = TestCases.objects.all()

        self.addm_group_l = []
        self.addm_set = AddmDev.objects.filter(disables__isnull=True).values()

        self.mail_task_arg = ''
        self.mail_kwargs = dict()
        self.test_output_mode = False

        self.all_tests_w = 0

    def setUp(self) -> None:
        self.user_and_mail()

    def run_case(self):
        log.debug("Making test jobs...")
        # Select addm:
        self.select_addm_set()
        # Sort test over selected ADDM groups:
        self.balance_tests_on_workers()
        # FINISH STEP:
        self.put_test_cases()

    def tearDown(self) -> None:
        log.debug("<=PatternTestUtils=> Test finished")

    def check_tasks(self, tasks):
        tasks_res = dict()
        if not tasks:
            msg = 'No tasks returned from case execution!'
            raise Exception(msg)

        for task in tasks:
            res = AsyncResult(task.id)
            # tasks_res.update({task.id: dict(status=res.status, result=res.result, state=res.state, args=res.args, kwargs=res.kwargs)})
            tasks_res.update({task.id: dict(status=res.status, result=res.result, state=res.state)})
            if res.status == 'FAILURE' or res.state == 'FAILURE':
                msg = f'Task execution finished with failure status: \n\t{task.id}\n\t"{res.result}"'
                raise Exception(msg)
        self.debug_output(tasks_res)
        return tasks_res

    def debug_output(self, tasks_res):
        if self.debug:
            tasks_json = json.dumps(tasks_res, indent=2, ensure_ascii=False, default=pformat)
            print(tasks_json)

    def user_and_mail(self, user_name=None, user_email=None):
        """
        Allow Octopus to send confirmation and status emails for developer of the test.
        Username and email should always be set up as default to indicate cron-automated tasks.
        :param user_name: str
        :param user_email: str
        :return:
        """
        if user_name and user_email:
            self.user_name = user_name
            self.user_email = user_email
        else:
            self.user_name = 'OctoTests'
            self.user_email = mails['admin']

    def fake_run_on(self, fake):
        """
        For debug purposes only, fill fire tasks with fake mode, showing all args, kwargs.
        Fake task will be executed on selected worker if any, or on first possible one.
        :param fake:
        :return:
        """
        if fake:
            self.fake_run = True
            log.debug("<=PatternTestUtils=> Fake Run test tasks")
        else:
            log.debug("<=PatternTestUtils=> Real Run test tasks")

    def silent_on(self, silent):
        """
        Do not send any emails.
        :param silent:
        :return:
        """
        if silent:
            self.silent = True
        else:
            log.debug("<=PatternTestUtils=> Will send confirmation and step emails.")

    def debug_on(self, debug):
        if debug:
            self.debug = True
        else:
            log.debug("<=PatternTestUtils=> Will send confirmation and step emails.")

    def wipe_logs_on(self, wipe_logs):
        if wipe_logs and not self.fake_run:
            log.debug("<=PatternTestUtils=> Will wipe logs. Branch %s", self.branch)
            self.wipe_logs = True
            TestLast.objects.filter(tkn_branch__exact=self.branch).delete()

    def wipe_case_logs(self, test_py_path):
        """Delete latest logs for selected test cases if they're were selected to run."""
        if not self.fake_run:
            log.debug("<=PatternTestUtils=> Will wipe logs of selected patterns.")
            if isinstance(test_py_path, list):
                to_delete = TestLast.objects.filter(test_py_path__in=test_py_path)
                # log.warning(f"About to delete test logs: {to_delete.count()}\n{to_delete.query}\n{to_delete}")
                to_delete.delete()
            elif isinstance(test_py_path, str):
                to_delete = TestLast.objects.filter(test_py_path__exact=test_py_path)
                # log.warning(f"About to delete test logs: {to_delete.count()}\n{to_delete.query}\n{to_delete}")
                to_delete.delete()
            else:
                log.warning("Do not wipe logs is test_py_path is not a list or str!")

    def select_test_cases(self, **sel_opts):
        self.queryset = PatternsDjangoTableOper.sel_dynamical(TestCases, sel_opts=sel_opts)

    def select_latest_failed(self):
        """Select latest test cases logs with failed status"""
        failed_test_py = []
        failed_q = TestLatestDigestFailed.objects.filter(tkn_branch__exact=self.branch).values('test_py_path')
        log.info(f"Selected failed cases from latest: {failed_q.count()}")
        for item in failed_q:
            if item['test_py_path'] not in failed_test_py:
                failed_test_py.append(item['test_py_path'])
        log.info(f"Sorted test_py from latest: {len(failed_test_py)}")
        return failed_test_py

    def select_failed_cases(self, test_py_list):
        return TestCases.objects.filter(test_py_path__in=test_py_list).values()

    def excluded_group(self):
        excluded_group = TestCasesDetails.objects.get(title__exact='excluded')
        excluded_ids = excluded_group.test_cases.values('id')
        self.queryset = self.queryset.exclude(id__in=excluded_ids)

    def key_group(self):
        key_group = TestCasesDetails.objects.get(title__exact='key')
        included = key_group.test_cases.values('id')
        key_cases = TestCases.objects.filter(id__in=included)
        self.queryset = self.queryset | key_cases

    def select_addm_set(self):
        """
        Select ADDM machines by self.addm_group_l = ['hotel', 'india', 'juliett'] like.
        Otherwise we can select any amount by Django query set options.
        :return: list of sets or queryset
        """
        self.addm_set = ADDMOperations.select_addm_set(addm_group=self.addm_group_l)

    def select_addm_group(self):
        """ Select min worker - same as in octo_tku_patterns.tasks.TaskPrepare """
        addm_group = TaskPrepare(self).addm_group_get(tkn_branch=self.branch)
        self.addm_set = TaskPrepare(self).addm_set_select(addm_group=addm_group)

    def balance_tests_on_workers(self):
        """Balance tests between selected ADDM groups each group/queue will be filled
            with tests by overall (weight / groups)"""
        # TODO: Make list of addm_groups based on addm_set.
        self.addm_tests_balanced = BalanceNightTests().test_weight_balancer(
            addm_group=self.addm_group_l, test_items=self.queryset.order_by('-test_time_weight'))

    def put_test_cases(self):
        for addm_item in self.addm_set:
            addm_group = addm_item[0]['addm_group']
            log.debug(f"<=put_test_cases=> Using addm group: {addm_group}")
            addm_coll = self.addm_tests_balanced.get(addm_group)
            addm_tests = addm_coll.get('tests', [])
            if addm_tests:
                self.all_tests_w += addm_coll.get('all_tests_weight')
                self.before_tests()
                self.routine_mail(mode='run', addm_group=addm_group)
                # Sync test data on those addms from group:
                self.sync_test_data_addm_set(addm_item)
                # Start to fill queues with test tasks:
                self.run_cases_router(addm_tests, addm_group, addm_item)
                # End tasks when tests are finished:
                self.routine_mail(mode='fin', addm_group=addm_group)
                self.after_tests()

    def put_test_cases_short(self, test_item):
        _addm_group = self.addm_set[0]['addm_group']
        log.debug(f"<=put_test_cases=> ReRun failed tests - using addm group: {_addm_group}")
        self.routine_mail(mode='re-run', addm_group=_addm_group)
        self.run_cases_router(addm_tests=test_item, _addm_group=_addm_group, addm_item=self.addm_set)
        self.routine_mail(mode='re-fin', addm_group=_addm_group)

    def before_tests(self):
        """

        :param addm_group:
        :return:
        """
        log.debug("<=PatternTestUtils=> ADDM group run some preparations before test run?")
        return True

    def after_tests(self):
        """
        Run after all tests are finished. May be used to generate mail notifications about test results.
        :return:
        """
        # Add finish mail to the queue when it filled with test tasks:
        # TODO: Add some addm cleaning routines and services restart?
        log.debug("<=PatternTestUtils=> ADDM group run some preparations after all tests run?")
        # Make task and it will be added in the end of the queue on each addm group.
        msg = '''Night routine has been executed. Options used:
                 ADDM actual: {addm_act} | 
                 Branch {branch} | 
                 Start at: {start_time} |
                 Overall tests time weight: {tst_w_t} | 
                 Overall tests to run: {queryset_count} | 
                 Tests selected by: {queryset_explain} | 
                 Tests selection query: {queryset_query} | 
                 '''.format(
            addm_act=self.addm_group_l,
            branch=self.branch,
            tst_w_t=self.all_tests_w,
            start_time=self.now,
            queryset_count=self.queryset.count(),
            queryset_explain=self.queryset.explain(),
            queryset_query=self.queryset.query,
        )
        log.info(msg)
        # TODO: Add here a task to save latest possible log
        return True

    def sync_test_data_addm_set(self, addm_item):
        _addm_group = addm_item[0]['addm_group']
        log.debug(f"<=TaskPrepare=> Adding task to sync addm group: {_addm_group} at set: {addm_item}")
        commands_set = ADDMStaticOperations.select_operation([
            'test.kill.term',  # Kill any hanged test before.
            'tw_scan_control.clear',  # Stop any running scan
            'rsync.python.testutils',
            'rsync.tideway.utils',
            'rsync.tku.data',
        ])
        for operation_cmd in commands_set:
            t_tag = f'tag=t_addm_rsync_threads;addm_group={_addm_group};user_name={self.user_name};' \
                    f'fake={self.fake_run};command_k={operation_cmd.command_key};'
            t_kwargs = dict(addm_set=addm_item, operation_cmd=operation_cmd)
            Runner.fire_t(TaskADDMService.t_addm_cmd_thread,
                          fake_run=self.fake_run,
                          t_queue=f'{_addm_group}@tentacle.dq2',
                          t_args=[t_tag],
                          t_kwargs=t_kwargs,
                          t_routing_key=f'PatternTestUtils.{_addm_group}.{operation_cmd}.TaskADDMService.t_addm_cmd_thread')

    def run_cases_router(self, addm_tests, _addm_group, addm_item):
        """ TEST EXECUTION: Init loop for test execution. Each test for each ADDM item. """
        for test_item in addm_tests:
            if test_item.test_time_weight:
                test_t_w = round(float(test_item.test_time_weight))  # TODO: If NoneType - use 0
            else:
                test_t_w = 600

            if test_item.pattern_folder_name:
                case_tag = test_item.pattern_folder_name
            else:
                case_tag = test_item.test_py_path

            tsk_msg = 'tag=night_routine;type=routine {}/{}/{} t:{} on: "{}" by: {}'
            r_key = '{}.TExecTest.nightly_routine_case.{}'.format(_addm_group, case_tag)
            t_tag = tsk_msg.format(test_item.tkn_branch, test_item.pattern_library,
                                   test_item.pattern_folder_name, test_t_w, _addm_group, self.user_name)
            # LIVE:
            Runner.fire_t(TPatternExecTest().t_test_exec_threads,
                          fake_run=True,
                          t_queue=_addm_group + '@tentacle.dq2',
                          t_args=[t_tag],
                          t_kwargs=dict(addm_items=addm_item, test_item=test_item,
                                        test_output_mode=self.test_output_mode),
                          t_routing_key=r_key,
                          t_soft_time_limit=test_t_w + 60 * 20,
                          t_task_time_limit=test_t_w + 60 * 30)
        return True

    def routine_mail(self, **mail_kwargs):
        """
        Send email with task status and details:
        - what task, name, args;
        - when started, added to queue, finished
        - which status have
        - etc.

        :return:
        """
        mode = mail_kwargs.get('mode')
        send = mail_kwargs.get('send', True)
        addm_group = mail_kwargs.get('addm_group')

        addm_coll = self.addm_tests_balanced.get(addm_group)

        if not send:
            return 'Do not send emails.'

        mail_kwargs.update(
            branch=self.branch,
            addm_coll=addm_coll,
            addm_groups=self.addm_group_l,
            addm_tests=addm_coll.get('tests', []),
            addm_test_pairs=self.addm_tests_balanced,
            all_tests=self.queryset,
            addm_set=self.addm_set,
            addm_tests_weight=addm_coll.get('all_tests_weight'),
            tent_avg=addm_coll.get('tent_avg'),
            start_time=self.now,
        )

        # Send mail
        tag = 'tag=night_routine;lvl=auto;type=send_mail'
        Runner.fire_t(MailDigests.routine_mail,
                      fake_run=self.fake_run, to_sleep=2, to_debug=True,
                      t_queue=f'{addm_group}@tentacle.dq2',
                      t_args=[tag],
                      t_kwargs=mail_kwargs,
                      t_routing_key=f'z_{addm_group}.night_routine_mail.{mode}', )
        return True


class UploadTaskUtils(unittest.TestCase, UploadTaskPrepare):

    def __init__(self, *args, **kwargs):
        super(UploadTaskUtils, self).__init__(*args, **kwargs)
        self.user_name = 'OctoTests'
        self.user_email = 'OctoTests'

        self.silent = False
        self.fake_run = False
        self.tku_wget = False
        self.test_mode = ''
        self.tku_type = None
        self.addm_group = None
        self.package_types = None
        self.package_detail = None
        # To ignore filter packages by ADDM version during unzip func
        self.development = False

        self.packages = TkuPackages.objects.all()
        if not self.addm_group:
            self.addm_set = AddmDev.objects.all()

        self.data = dict()
        self.tasks_added = []

    def setUp(self) -> None:
        self.user_and_mail()
        log.debug("<=UploadTaskUtils=> SetUp data %s", self.data)

    def run_case(self):
        log.info("<=UploadTaskUtils=> Running case!")
        tasks = self.run_tku_upload()
        log.info(f"tasks: {tasks}")

    def tearDown(self) -> None:
        log.debug("<=UploadTaskUtils=> Test finished, data: %s", self.data)

    def check_tasks(self, tasks):
        tasks_res = dict()
        if not tasks:
            msg = 'No tasks returned from case execution!'
            raise Exception(msg)
        for task in tasks:
            res = AsyncResult(task.id)
            # tasks_res.update({task.id: dict(status=res.status, result=res.result, state=res.state, args=res.args, kwargs=res.kwargs)})
            tasks_res.update({task.id: dict(status=res.status, result=res.result, state=res.state)})
            if res.status == 'FAILURE' or res.state == 'FAILURE':
                msg = f'Task execution finished with failure status: \n\t{task.id}\n\t"{res.result}"'
                raise Exception(msg)
        self.debug_output(tasks_res)
        return tasks_res

    def debug_output(self, tasks_res):
        if self.data.get('debug') or self.debug:
            tasks_json = json.dumps(tasks_res, indent=2, ensure_ascii=False, default=pformat)
            print(tasks_json)

    def user_and_mail(self, user_name=None, user_email=None):
        """
        Allow Octopus to send confirmation and status emails for developer of the test.
        Username and email should always be set up as default to indicate cron-automated tasks.
        :param user_name: str
        :param user_email: str
        :return:
        """
        if user_name and user_email:
            self.user_name = user_name
            self.user_email = user_email

    def select_addm(self):
        if self.addm_group:
            addm_set = AddmDev.objects.all()
            self.addm_set = addm_set.filter(addm_group__exact=self.addm_group, disables__isnull=True).values()
        else:
            log.debug("Using addm set from test call.")

    @staticmethod
    def select_latest_continuous(tkn_branch):
        pass

    @staticmethod
    def select_latest_ga():
        pass

    @staticmethod
    def select_latest_released():
        pass

    @staticmethod
    def select_any_amount_of_packages():
        pass

    @staticmethod
    def preparation_step():
        pass
