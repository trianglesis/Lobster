from time import sleep
import datetime
from django.utils import timezone
import unittest
import logging
from celery.result import AsyncResult

from run_core.addm_operations import ADDMOperations

from octo_tku_patterns.models import TestCases, TestCasesDetails
from octo_tku_patterns.tasks import TaskPrepare
from octo_tku_patterns.table_oper import PatternsDjangoTableOper
from octo_tku_patterns.night_test_balancer import BalanceNightTests

from octo_tku_upload.tasks import UploadTaskPrepare
from octo_tku_upload.models import TkuPackagesNew as TkuPackages

from octo.helpers.tasks_run import Runner

from octo.tasks import TSupport
from octo_tku_patterns.tasks import TPatternParse, TPatternExecTest

# DEBUG TOOLS
import json
from pprint import pformat

log = logging.getLogger("octo.octologger")


class PatternTestUtils(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(PatternTestUtils, self).__init__(*args, **kwargs)
        self.now = datetime.datetime.now(tz=timezone.utc)
        self.tomorrow = self.now + datetime.timedelta(days=1)

        self.user_name = None
        self.user_email = None
        # TODO: During DEV always True
        self.fake_run = True

        self.date_from = None
        self.date_to = None
        self.branch = None
        self.queryset = TestCases.objects.all()

        self.addm_group_l = []
        self.mail_task_arg = ''
        self.mail_kwargs = dict()
        self.test_output_mode = False

        self.all_tests_w = 0

    def setUp(self) -> None:
        pass

    def run_case(self):
        self.get_branched_addm_groups()
        self.select_addm_set()
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
            self.user_email = 'OctoTests'

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

    def wipe_logs(self, wipe_logs):
        if wipe_logs and not self.fake_run:
            # TODO: Make wipe
            log.debug("<=PatternTestUtils=> Will wipe logs.")

    def select_test_cases(self, **sel_opts):
        self.queryset = PatternsDjangoTableOper.sel_dynamical(TestCases, **sel_opts)

    def excluded_group(self):
        excluded_group = TestCasesDetails.objects.get(title__exact='excluded')
        excluded_ids = excluded_group.test_cases.values('id')
        self.queryset = self.queryset.exclude(id__in=excluded_ids)

    def get_branched_addm_groups(self):
        self.addm_group_l = BalanceNightTests().get_available_addm_groups(
            branch=self.branch, user_name=self.user_name)

    def select_addm_set(self):
        self.addm_set = ADDMOperations.select_addm_set(
            addm_group=self.addm_group_l)

    def balance_tests_on_workers(self):
        select_test_cases = BalanceNightTests().test_weight_balancer(
            addm_group=self.addm_group_l, test_items=self.queryset)
        self.addm_tests_balanced = select_test_cases.order_by('-test_time_weight')

    def put_test_cases(self):
        for addm_item in self.addm_set:
            _addm_group = addm_item[0]['addm_group']
            addm_coll = self.addm_tests_balanced.get(_addm_group)
            addm_tests = addm_coll.get('tests', [])
            if addm_tests:
                addm_tests_weight = addm_coll.get('all_tests_weight')
                tent_avg = addm_coll.get('tent_avg')
                # Start email sending:
                self.start_mail(_addm_group, addm_tests, addm_tests_weight, tent_avg)
                # Any addm preparations here:
                self.prepare_addm_set(addm_item)
                # Sync test data on those addms from group:
                self.sync_test_data_addm_set(_addm_group, addm_item)
                # Start to fill queues with test tasks:
                self.run_cases_router(addm_tests, _addm_group, addm_item)
                # Add finish mail to the queue when it filled with test tasks:
                self.finish_mail(_addm_group)
                self.all_tests_w += addm_tests_weight

        msg = '''Night routine has been executed. Options used:
                 ADDM actual: {addm_act} | 
                 Branch {branch} | 
                 Overall tests to run: {tst_len} | 
                 Overall tests time weight: {tst_w_t} | 
                 Start at: {start_time} |'''.format(
            addm_act=self.addm_group_l,
            branch=self.branch,
            tst_len=self.queryset.count(),
            tst_w_t=self.all_tests_w,
            start_time=self.now,
        )
        return msg

    def prepare_addm_set(self, addm_item):
        log.debug("<=PatternTestUtils=> ADDM group run some preparations before test run?")

    def sync_test_data_addm_set(self, _addm_group, addm_item):
        Runner.fire_t(TPatternParse.t_addm_rsync_threads, fake_run=self.fake_run,
                      t_queue=_addm_group + '@tentacle.dq2',
                      t_args=[self.mail_task_arg],
                      t_kwargs=dict(addm_items=addm_item))

    def start_mail(self, _addm_group, addm_tests, addm_tests_weight, tent_avg):
        self.mail_task_arg = 'tag=night_routine;lock=True;lvl=auto;type=send_mail'
        self.mail_kwargs = dict(
            mode="run",
            r_type='Night',
            branch=self.branch,
            start_time=self.now,
            addm_group=_addm_group,
            addm_group_l=self.addm_group_l,
            addm_test_pairs=len(self.addm_tests_balanced),
            test_items_len=len(addm_tests),
            all_tests=self.queryset.count(),
            addm_used=self.addm_set.count(),
            all_tests_weight=addm_tests_weight,
            tent_avg=tent_avg)
        """ MAIL send mail when routine tests selected: """
        Runner.fire_t(TSupport.t_long_mail, fake_run=self.fake_run,
                      t_queue=_addm_group + '@tentacle.dq2',
                      t_args=[self.mail_task_arg],
                      t_kwargs=self.mail_kwargs,
                      t_routing_key='z_{}.night_routine_mail'.format(_addm_group))

    def run_cases_router(self, addm_tests, _addm_group, addm_item):
        """ TEST EXECUTION: Init loop for test execution. Each test for each ADDM item. """
        for test_item in addm_tests:
            test_t_w = round(float(test_item['test_time_weight']))
            tsk_msg = 'tag=night_routine;lock=True;type=routine {}/{}/{} t:{} on: "{}" by: {}'
            r_key = '{}.TExecTest.nightly_routine_case.{}'.format(_addm_group, test_item['pattern_folder_name'])
            t_tag = tsk_msg.format(test_item['tkn_branch'], test_item['pattern_library'],
                                   test_item['pattern_folder_name'], test_t_w, _addm_group, self.user_name)
            # LIVE:
            Runner.fire_t(TPatternExecTest().t_test_exec_threads, fake_run=self.fake_run,
                          t_queue=_addm_group + '@tentacle.dq2',
                          t_args=[t_tag],
                          t_kwargs=dict(addm_items=addm_item, test_item=test_item,
                                        test_output_mode=self.test_output_mode),
                          t_routing_key=r_key,
                          t_soft_time_limit=test_t_w + 900,
                          t_task_time_limit=test_t_w + 1000)

    def finish_mail(self, _addm_group):
        self.mail_kwargs.update(mode='fin')
        Runner.fire_t(TSupport.t_long_mail, fake_run=self.fake_run,
                      t_queue=_addm_group + '@tentacle.dq2',
                      t_args=[self.mail_task_arg],
                      t_kwargs=self.mail_kwargs,
                      t_routing_key='z_{}.night_routine_mail'.format(_addm_group))


class UploadTaskUtils(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(UploadTaskUtils, self).__init__(*args, **kwargs)
        self.user_name = None
        self.user_email = None
        self.fake_run = None
        self.request = dict()

    def setUp(self) -> None:
        self.user_and_mail()
        log.debug("<=UploadTaskUtils=> SetUp request %s", self.request)

    def run_case(self):
        tasks = UploadTaskPrepare(self).run_tku_upload()
        if tasks:
            self.check_tasks(tasks)

    def tearDown(self) -> None:
        sleep(3)
        log.debug("<=UploadTaskUtils=> Test finished, request: %s", self.request)

    def check_args(self):
        if self.request.get('package_types'):
            package_types = self.request.get('package_types')
            assert isinstance(package_types, list), 'Package types is not a list!'
            for package in package_types:
                package_qa = TkuPackages.objects.filter(tku_type__exact=package)
                if package_qa:
                    assert isinstance(package_qa, TkuPackages), 'Selected package is not a QuerySet of TkuPackages'
                else:
                    raise Exception(f'No package can be found in database with type: {package}, maybe WGET can help')

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
        if self.request.get('debug') or self.debug:
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
            self.request.update(user_name=user_name, user_email=user_email)
        else:
            self.request.update(user_name='OctoTests', user_email='OctoTests')

    def fake_run_on(self, fake):
        """
        For debug purposes only, fill fire tasks with fake mode, showing all args, kwargs.
        Fake task will be executed on selected worker if any, or on first possible one.
        :param fake:
        :return:
        """
        if fake:
            self.request.update(fake_run=True)
            log.debug("<=UploadTaskUtils=> Fake Run test tasks")
        else:
            log.debug("<=UploadTaskUtils=> Real Run test tasks")

    def wget_on(self, wget):
        """
        To run WGET before upload to get most latest packages or use as it now saved in local DB.
        :param wget:
        :return:
        """
        if wget:
            self.request.update(tku_wget=True)
        else:
            log.debug("<=UploadTaskUtils=> No WGET run.")

    def silent_on(self, silent):
        """
        Do not send any emails.
        :param silent:
        :return:
        """
        if silent:
            self.request.update(silent=True)
        else:
            log.debug("<=UploadTaskUtils=> Will send confirmation and step emails.")

    def debug_on(self, debug):
        if debug:
            self.request.update(debug=True)
        else:
            log.debug("<=UploadTaskUtils=> Will send confirmation and step emails.")

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
