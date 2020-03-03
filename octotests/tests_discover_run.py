import importlib
import logging
import os
import unittest
import subprocess
from unittest import TestSuite

from octo.win_settings import BASE_DIR
import octo.config_cred as conf_cred
from octo import settings

log = logging.getLogger("octo.octologger")


class TestRunnerLoc:
    """
    Use this class to run cases, tests and routines internally, based on unittest logic.
    They will be executed reflecting all dynamical changes without need to restart/reload any services or tasks.
    Could be executed as usual task + user selected args from like table of available unit test class and metdods.
    Unit test classed and methods could be discovered with DiscoverLocalTests, but testsuited could not be executable
    without additional celery worker restart.
    """

    def run_subprocess(self, **kwargs):
        test_py_path = kwargs.get('test_py_path', None)  # full path to octotest_upload_tku.py
        test_method = kwargs.get('test_method', None)  # test001_product_content_update_tkn_main
        test_class = kwargs.get('test_class', None)  # OctoTestCaseUpload
        test_module = kwargs.get('test_module', None)  # run_core.tests.octotest_upload_tku
        log.info(f"<=TestRunnerLoc=> Getting test method {test_method} from: {test_module}.{test_class}")

        # Set the ENV:
        my_env = os.environ.copy()
        my_env['DJANGO_SETTINGS_MODULE'] = 'octo.win_settings'

        # Save results here:
        run_results = []
        cmd_list = []

        # DEV: Set paths to test and working dir:
        if conf_cred.DEV_HOST in settings.CURR_HOSTNAME:
            if "KBP1" in settings.CURR_HOSTNAME:
                wsl_path = '/mnt/d/Projects/PycharmProjects/lobster'
                octo_core = wsl_path
            else:
                wsl_path = '/mnt/d/Projects/PycharmProjects/lobster'
                octo_core = wsl_path
            activate = 'bash -c "source {WSL_PATH}venv/bin/activate"'.format(WSL_PATH=wsl_path)
            deactivate = 'bash -c "source {WSL_PATH}venv/bin/deactivate"'.format(WSL_PATH=wsl_path)
        else:
            octo_core = '/var/www/octopus/'
            activate = 'source venv/bin/activate'
            deactivate = 'deactivate'

        # Set unit test cmd:
        if test_module and test_class and test_method:
            test_cmd = f'python -m unittest {test_module}.{test_class}.{test_method}'
        elif test_module and test_class and not test_method:
            test_cmd = f'python -m unittest {test_module}.{test_class}'
        elif test_module and not test_class and not test_method:
            test_cmd = f'python -m unittest {test_module}'
        else:
            test_cmd = f'python -m unittest {test_py_path}'

        cmd_list.append(activate)
        cmd_list.append(test_cmd)
        cmd_list.append(deactivate)

        log.info(f"<=TestRunnerLoc=> Composed commands to execute: {cmd_list}")
        for cmd in cmd_list:
            try:
                log.debug("<=TEST=> Run: %s", cmd)
                run_cmd = subprocess.Popen(cmd,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           cwd=octo_core,
                                           env=my_env,
                                           shell=True,
                                           )
                # Timeout for 10 min, usually this takes few minutes
                stdout, stderr = run_cmd.communicate(timeout=600)
                stdout, stderr = stdout.decode('utf-8'), stderr.decode('utf-8')
                run_cmd.wait(timeout=300)  # wait until command finished
                run_results.append({'stdout': stdout, 'stderr': stderr})
                log.debug('<=TEST=> stdout %s', stdout)
                log.debug('<=TEST=> stderr %s', stderr)
            except Exception as e:
                log.error("<=run_subprocess=> Error during operation for: %s %s", cmd, e)
        log.debug("<=run_subprocess=> run_results: %s", run_results)
        return run_results


class DiscoverLocalTests:
    """
    Use this class with methods to discover new test methods from internal 'octotests' and save it to table
    or show on UI part of Octopus where they could be used as executable (only by TestRunnerLoc) tasks and routines.
    But do not use test suites to run tests, because without prorer restart celery tasks wouldn't run any of them
    and could not reflect any changes.

    NOTE: DO not run this as task! Task wouldn't reflect local-external changes from test files!

    """

    def get_all_tests_dev(self, **kwargs):
        test_method = kwargs.get('test_method', None)
        test_class = kwargs.get('test_class', None)
        test_module = kwargs.get('test_module', None)

        runner = unittest.TextTestRunner(verbosity=3)
        test_suite = TestSuite()

        tst_class = ''
        tst_module = ''
        if test_module:
            tst_module = importlib.import_module(test_module)
        if test_class and tst_module:
            tst_class = getattr(tst_module, test_class)

        log.info("Test class id: %s, module id: %s", id(tst_module), id(tst_class))
        log.info("Test test_suite id: %s", id(test_suite))

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
        test_suite.addTest(tst_class(test_method))
        log.info("Test suite: %s", test_suite)
        # runner.run(test_suite)

    @staticmethod
    def unittests_discover(test_dir=None, pattern=None):
        if not test_dir:
            test_dir = BASE_DIR
            log.info("Getting all tests from dir: %s", test_dir)
        if not pattern:
            pattern = 'octotest_*.py'
        tests = unittest.TestLoader().discover(test_dir, pattern=pattern)
        return tests

    @staticmethod
    def unittests_name_from_module_names(names, tst_module):
        if isinstance(names, str):
            tests = unittest.TestLoader().loadTestsFromName(names, module=tst_module)
        elif isinstance(names, list):
            tests = unittest.TestLoader().loadTestsFromNames(names, module=tst_module)
        else:
            raise Exception('Test cases names is not a list or str')
        return tests

    @staticmethod
    def unittests_from_case(tst_class):
        tests = unittest.TestLoader().loadTestsFromTestCase(tst_class)
        return tests

    @staticmethod
    def unittests_from_module(tst_module, pattern=None):
        if not pattern:
            pattern = 'octotest_*.py'
        tests = unittest.TestLoader().loadTestsFromModule(module=tst_module, pattern=pattern)
        return tests

    @staticmethod
    def get_unittest_names(tst_class):
        names = unittest.TestLoader().getTestCaseNames(tst_class)
        return names
