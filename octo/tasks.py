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
import logging, os, unittest, importlib
from unittest import TestSuite
from time import sleep

from octo.octo_celery import app
from django.conf import settings

from octo.helpers.tasks_mail_send import Mails

from octo.helpers.tasks_oper import WorkerOperations, TasksOperations
from octo.helpers.tasks_helpers import exception

from octo.win_settings import BASE_DIR

log = logging.getLogger("octo.octologger")
curr_hostname = getattr(settings, 'CURR_HOSTNAME', None)

"""Initialize only if reset!
app.conf.beat_schedule = {
    # Run MAIN for each working day till 20th:
    'tkn_main_workday_routine': {
        'task': 'cases.tasks_shelf.routine_tasks.tasks.night_test_executor',
        'schedule': crontab(hour=17, minute=0, day_of_week='1,2,3,4,5', day_of_month='1-19,28-31'),
        'options': {'queue': 'routines'},
        'args': ('tkn_main',),
        'kwargs': {'send_mail': True, 'sync_tku': True, 'user_name': 'cron_user'},
    },
}
"""

DAY_LIMIT = 172800
HOURS_2 = 7200
HOURS_1 = 3600
MIN_90 = 5400
MIN_40 = 2400
MIN_20 = 1200
MIN_10 = 600
MIN_1 = 60
SEC_10 = 10
SEC_1 = 1


# noinspection PyUnusedLocal
class TSupport:
    """
    Sending mails for example
    """

    @staticmethod
    @app.task(soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_short_mail(t_tag, **mail_kwargs):
        return Mails().short(**mail_kwargs)

    @staticmethod
    @app.task(soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_long_mail(t_tag, **mail_kwargs):
        from octo.helpers.tasks_helpers import TMail
        TMail().long_r(**mail_kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='TSupport.t_user_mail',
              soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_user_mail(t_tag, **mail_kwargs):
        from octo.helpers.tasks_helpers import TMail
        TMail().user_t(**mail_kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='TSupport.t_user_mail',
              soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_user_test(t_tag, **mail_opts):
        from octo.helpers.tasks_helpers import TMail
        TMail().user_test(**mail_opts)

    @staticmethod
    @app.task(soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_occupy_w(t_tag, sleep_t, **kwargs):
        """
        Just keep worker busy when user change it.
        :return:
        """
        sleep(sleep_t)

    @app.task(soft_time_limit=HOURS_2, task_time_limit=HOURS_2+900)
    @exception
    def fake_task(t_tag, sleep_t, **kwargs):
        """
        Just keep worker busy when user change it.

        :param t_tag:
        :param sleep_t:
        :return:
        """
        debug_me = kwargs.get('debug_me', None)
        debug_str = "tag={};sleep_t={};kwargs={}".format(t_tag, sleep_t, kwargs)
        if debug_me:
            log.info("This task\\worker has been occupied: %s sleep_t %s", t_tag, sleep_t)
            log.info("Task can also return all args\\kwargs items for debug purposes.")
        sleep(sleep_t)
        return debug_str


class TInternal:

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.test_task_heartbeat_ping_workers',
              soft_time_limit=MIN_1, task_time_limit=MIN_10)
    @exception
    def test_task_heartbeat_ping_workers(t_tag, **kwargs):
        """
        Send heartbeat and ping to all workers in system to keep them up and ready to use.
        This is necessary routine to catch the bug when worker goes down.

        :return:
        """
        log.info("t_tag: %s", t_tag)

        w_up = WorkerOperations().worker_heartbeat()

        # If result dict have a 'down' key:
        if w_up.get('down'):
            msg = '<=test_task_heartbeat_ping_workers=> Worker down: "{}"' \
                  '\nworkers_passed: {}\nworkers_resolved: {}'.format(w_up.get('down'),
                                                                      w_up.get('workers_passed'),
                                                                      w_up.get('workers_resolved'))
            raise Exception(msg)
        else:
            return 'Having workers up and running: {}'.format(w_up)

    # noinspection PyUnusedLocal,PyUnusedLocal
    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.test_task_get_worker_minimal',
              soft_time_limit=MIN_1, task_time_limit=MIN_10)
    @exception
    def test_task_get_worker_minimal(t_tag, **kwargs):
        """
        Testing and catching bug when excluded worker still present in available free workers list.
        Should be ONE free worker.
        We can compare returned worker over list of NOT excluded workers and raise when diff.

        expected_w = 'alpha,beta,charlie'
        worker_min = 'beta'

        :return:
        """
        from octo_adm.request_service import SelectorRequestsHelpers

        expected_w = kwargs.get('expected_w')
        mail_send = kwargs.get('mail_send', False)

        log.info("t_tag: %s", t_tag)
        expected_w_list = expected_w.split(",")

        # Get one minimal loaded worker:
        # worker_min_free = SelectorRequestsHelpers.get_free_included_w()
        worker_min_task = SelectorRequestsHelpers.get_free_included_w_task()
        all_workers_status = TasksOperations().check_active_reserved_short()
        log.debug("<=test_task_get_worker_minimal=> Free min worker: %s", worker_min_task)

        if worker_min_task:
            if worker_min_task not in expected_w_list:
                msg = '<=test_task_get_worker_minimal=> Returned worker "{}" is not in expected list of workers - "{}" on {}'.format(
                    worker_min_task, expected_w_list, curr_hostname)
                # Mails.short(subject='Task fail', body="{} All: {}".format(msg, all_workers_status))
                raise Exception(msg)
            else:
                return "Excluded minimum busy worker expected - OK: {}={}".format(worker_min_task, expected_w_list)
        else:
            msg = "WARNING: Excluded minimum busy worker - EMPTY: {}={}. It may be busy." \
                   "Host {}" \
                  "All workers status: {}".format(worker_min_task, expected_w_list, curr_hostname, all_workers_status)
            # if mail_send:
            #     Mails.short(subject='Expected worker could be busy:', body=msg)
            return msg

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TInternal.internal_test_routine',
              soft_time_limit=MIN_90, task_time_limit=HOURS_2)
    def internal_test_routine(t_tag, **kwargs):
        log.info("<=internal_test_routine=> Running task %s %s", t_tag, kwargs)
        return TestRunnerLoc.run_subprocess(**kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TInternal.internal_test_get',
              soft_time_limit=MIN_10, task_time_limit=MIN_20)
    def internal_test_get(t_tag, **kwargs):
        log.info("<=get_all_tests_dev=> Running task %s %s", t_tag, kwargs)
        return DiscoverLocalTests.get_all_tests_dev(**kwargs)


class TestRunnerLoc:

    def run_subprocess(self, **kwargs):
        import subprocess

        test_py_path = kwargs.get('test_py_path', None)  # full path to octotest_upload_tku.py
        test_method = kwargs.get('test_method', None)  # test001_product_content_update_tkn_main
        test_class = kwargs.get('test_class', None)  # OctoTestCaseUpload
        test_module = kwargs.get('test_module', None)  # run_core.tests.octotest_upload_tku

        # Set the ENV:
        my_env = os.environ.copy()
        my_env['DJANGO_SETTINGS_MODULE'] = 'octo.win_settings'

        # Save results here:
        run_results = []
        cmd_list = []

        # DEV: Set paths to test and working dir:
        if os.name == 'nt':
            test_env = 'D:\\perforce\\addm\\tkn_sandbox\\o.danylchenko\\projects\\PycharmProjects\\lobster\\venv\\Scripts\\'
            octo_core = 'D:\\perforce\\addm\\tkn_sandbox\\o.danylchenko\\projects\\PycharmProjects\\lobster'
            activate = 'activate.bat'
            deactivate = 'deactivate.bat'
        else:
            test_env = '/var/www/octopus/'
            octo_core = '/var/www/octopus/'
            activate = 'venv/bin/activate/activate'
            deactivate = 'venv/bin/activate/deactivate'

        # Set unit test cmd:
        if test_module and test_class and test_method:
            test_cmd = f'python -m unittest {test_module}.{test_class}.{test_method}'
        elif test_module and test_class and not test_method:
            test_cmd = f'python -m unittest {test_module}.{test_class}'
        elif test_module and not test_class and not test_method:
            test_cmd = f'python -m unittest {test_module}'
        else:
            test_cmd = f'python -m unittest {test_py_path}'

        # Compose CMD run:
        cmd_list.append(f'{test_env}{activate}')
        cmd_list.append(test_cmd)
        cmd_list.append(f'{test_env}{deactivate}')

        for cmd in cmd_list:
            try:
                # log.debug("<=TEST=> Run: %s", cmd)
                run_cmd = subprocess.Popen(cmd,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           cwd=octo_core,
                                           env=my_env,
                                           )
                run_cmd.communicate()
                stdout, stderr = run_cmd.communicate()
                stdout, stderr = stdout.decode('utf-8'), stderr.decode('utf-8')
                run_cmd.wait()
                run_results.append({'stdout': stdout, 'stderr': stderr})
                # log.debug('<=TEST=> stdout %s', stdout)
                # log.debug('<=TEST=> stderr %s', stderr)

            except Exception as e:
                log.error("<=run_subprocess=> Error during operation for: %s %s", cmd, e)
        log.debug("<=run_subprocess=> run_results: %s", run_results)
        return run_results


class DiscoverLocalTests:

    suite = TestSuite()
    loader = unittest.TestLoader()
    runner = unittest.TextTestRunner(verbosity=3)

    if os.name == 'nt':
        sep = '\\'
    else:
        sep = '/'

    def get_all_tests_dev(self, **kwargs):
        test_method = kwargs.get('test_method', None)
        test_class = kwargs.get('test_class', None)
        test_module = kwargs.get('test_module', None)

        tst_class = ''
        tst_module = ''
        if test_module:
            tst_module = importlib.import_module(test_module)
        if test_class and tst_module:
            tst_class = getattr(tst_module, test_class)

        tests_from_discover = self.unittests_discover(test_dir=None)
        log.debug("<=tests_from_discover=> %s", tests_from_discover)

        tests_names_from_mod = self.unittests_name_from_module_names(names=test_method, tst_module=tst_module)
        log.debug("<=tests_names_from_mod=> %s", tests_names_from_mod)

        tests_from_case = self.unittests_from_case(tst_class)
        log.debug("<=tests_from_case=> %s", tests_from_case)

        tests_from_mod = self.unittests_from_module(tst_module=tst_module, pattern=None)
        log.debug("<=tests_from_mod=> %s", tests_from_mod)

        test_names = self.get_unittest_names(tst_class)
        log.debug("<=test_names=> %s", test_names)

        # self.suite.addTests(tests_from_discover)
        # Or customize:
        self.suite.addTest(tst_class(test_method))
        log.info("Test suite: %s", self.suite)
        self.runner.run(self.suite)

    def unittests_discover(self, test_dir=None, pattern=None):
        if not test_dir:
            test_dir = BASE_DIR
            log.info("Getting all tests from dir: %s", test_dir)
        if not pattern:
            pattern = 'octotest_*.py'
        tests = self.loader.discover(test_dir, pattern=pattern)
        return tests

    def unittests_name_from_module_names(self, names, tst_module):
        if isinstance(names, str):
            tests = self.loader.loadTestsFromName(names, module=tst_module)
        elif isinstance(names, list):
            tests = self.loader.loadTestsFromNames(names, module=tst_module)
        else:
            raise Exception('Test cases names is not a list or str')
        return tests

    def unittests_from_case(self, tst_class):
        tests = self.loader.loadTestsFromTestCase(tst_class)
        return tests

    def unittests_from_module(self, tst_module, pattern=None):
        if not pattern:
            pattern = 'octotest_*.py'
        tests = self.loader.loadTestsFromModule(module=tst_module, pattern=pattern)
        return tests

    def get_unittest_names(self, tst_class):
        names = self.loader.getTestCaseNames(tst_class)
        return names
