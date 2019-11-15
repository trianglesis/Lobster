from time import sleep
import unittest
import logging
from celery.result import AsyncResult

from octo_tku_upload.tasks import UploadTaskPrepare

# DEBUG TOOLS
import json
from collections import OrderedDict
from pprint import pformat

log = logging.getLogger("octo.octologger")


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

    def check_tasks(self, tasks):
        tasks_res = dict()
        for task in tasks:
            res = AsyncResult(task.id)
            tasks_res.update({task.id: dict(status=res.status, result=res.result, state=res.state, args=res.args)})

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
