import importlib
import logging
import os
import unittest
import subprocess
from unittest import TestSuite

from octo.settings import BASE_DIR
from django.conf import settings

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
        test_py_path = kwargs.get('test_py_path', None)  # full path to
        test_method = kwargs.get('test_method', None)  # test001_product_content_update_tkn_main
        test_class = kwargs.get('test_class', None)  # OctoTestCaseUpload
        test_module = kwargs.get('test_module', None)  # run_core.tests.octotest_upload_tku
        log.info(f"<=TestRunnerLoc=> Getting test method {test_method} from: {test_module}.{test_class}")

        # Set the ENV:
        my_env = os.environ.copy()
        my_env['DJANGO_SETTINGS_MODULE'] = 'octo.settings'

        # Save results here:
        run_results = []
        cmd_list = []

        # DEV: Set paths to test and working dir:
        if settings.DEV:
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

