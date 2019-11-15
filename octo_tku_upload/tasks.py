from __future__ import absolute_import, unicode_literals
import ast
import datetime
import logging
import os
import unittest
# noinspection PyUnresolvedReferences
from typing import Dict, List, Any

from django.db.models import Max

from octo.helpers.tasks_helpers import exception
from octo.helpers.tasks_oper import TasksOperations
from octo.helpers.tasks_run import Runner
# Celery
from octo.octo_celery import app
from octo.tasks import TSupport
from octo_tku_upload.models import TkuPackagesNew as TkuPackages
from octo_tku_upload.test_executor import UploadTestExec
from run_core.local_operations import LocalDownloads
from run_core.models import AddmDev


from celery.utils.log import get_task_logger

log = logging.getLogger("octo.octologger")
logger = get_task_logger(__name__)

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


# noinspection PyUnusedLocal,PyUnusedLocal
class TUploadExec:

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TRoutine.t_upload_routines',
              soft_time_limit=MIN_90, task_time_limit=HOURS_2)
    def t_upload_routines(t_tag, **kwargs):
        log.info("<=t_upload_routines=> Running task %s", kwargs)
        return TestRunnerLoc().run_tests(**kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TRoutine.t_routine_tku_upload_test_new',
              soft_time_limit=MIN_90, task_time_limit=HOURS_2)
    @exception
    def t_upload_test(t_tag, **kwargs):
        return UploadTaskPrepare(kwargs['obj']).run_tku_upload()

    @staticmethod
    @app.task(queue='w_parsing@tentacle.dq2', soft_time_limit=MIN_20, task_time_limit=MIN_40)
    @exception
    def t_tku_sync(t_tag, **kwargs):
        return LocalDownloads().wget_tku_build_hub_option(**kwargs)

    @staticmethod
    @app.task(queue='w_parsing@tentacle.dq2', routing_key='parsing.TUploadExec.t_parse_tku',
              soft_time_limit=MIN_40, task_time_limit=MIN_90)
    @exception
    def t_parse_tku(t_tag, **kwargs):
        log.debug("Tag: %s, kwargs %s", t_tag, kwargs)
        return LocalDownloads().only_parse_tku(**kwargs)

    @staticmethod
    @app.task(soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_upload_prep(t_tag, **kwargs):
        return UploadTestExec().upload_preparations_threads(**kwargs)

    @staticmethod
    @app.task(soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_upload_unzip(t_tag, **kwargs):
        return UploadTestExec().upload_unzip_threads(**kwargs)

    @staticmethod
    @app.task(soft_time_limit=HOURS_1, task_time_limit=HOURS_2)
    @exception
    def t_tku_install(t_tag, **kwargs):
        return UploadTestExec().install_tku_threads(**kwargs)


class UploadTaskPrepare:
    """
    From REST:
    "obj": {
      "request": {
        "test_mode": "fresh",
        "package_types": "TKN_release_2019-10-2-282",
        "operation_key": "tku_install_test"
      },
      "user_name": "octopus_super",
      "user_email": "oleksandr_danylchenko_cw@bmc.com"
    }

    """

    def __init__(self, obj):
        # Initial view requests:
        self.view_obj = obj
        if isinstance(self.view_obj, dict):
            log.debug("From REST View?")
            self.request = self.view_obj.get('request')

            # Assign generated context for further usage:
            self.user_name = self.view_obj.get('user_name')
            self.user_email = self.view_obj.get('user_email')

            self.tku_wget = self.request.get('tku_wget', None)
            self.test_mode = self.request.get('test_mode', 'custom')
            self.tku_type = self.request.get('tku_type', None)
            self.addm_group = self.request.get('addm_group', None)
            self.package_detail = self.request.get('package_detail', None)
        else:
            log.debug("From Test class?")
            self.request = obj.request

            self.user_name = self.request.get('user_name', 'octopus_super')
            self.user_email = self.request.get('user_email', None)

            self.tku_wget = self.request.get('tku_wget', None)
            self.test_mode = self.request.get('test_mode', 'custom')
            self.tku_type = self.request.get('tku_type', None)
            self.addm_group = self.request.get('addm_group', None)
            self.package_detail = self.request.get('package_detail', None)

        # Define fake run:
        self.fake_run = False
        self.fake_fun()

        # Internal statuses:
        self.silent = False
        self.silent_run()

        # Get user and mail:
        self.start_time = datetime.datetime.now()
        log.info("<=UploadTaskPrepare=> Prepare tests for user: %s - %s", self.user_name, self.user_email)

        self.package_types = ''
        self.packages = dict()
        self.addm_set = dict()

        # Current status args:
        self.tku_downloaded = False
        # NOTE: It can change during process current class!!!!`
        self.t_tag = ''
        self.tasks_added = []

    def fake_fun(self):
        """
        For debug purposes, just run all tasks as fake_task with showing all inputs and outputs: args, kwargs.
        :return:
        """

        if os.name == "nt":  # Always fake run on local test env:
            self.fake_run = False
            log.debug("<=UploadTaskPrepare=> Fake run for NT request: %s", self.request)

        elif self.request.get('fake_run'):
            self.fake_run = True
            log.debug("<=UploadTaskPrepare=> Fake run = %s", self.fake_run)

    def silent_run(self):
        """
        Indicates when do not send any mails.
        :return:
        """
        if self.request.get('silent'):
            self.silent = True
        log.debug("<=UploadTaskPrepare=> Silent run = %s", self.silent)

    def run_tku_upload(self):
        self.task_tag()
        log.warning("<=UploadTaskPrepare=> TASK PSEUDO RUNNING in TaskPrepare.run_tku_upload")
        # 0. Init test mail?
        # self.mail_status(mail_opts=dict(mode='init', view_obj=self.view_obj))

        # 1. Refresh local TKU Packages:
        self.wget_run()

        # 2. Select TKU for test run.
        packages = self.select_pack_modes()
        self.debug_unpack_qs(packages)

        # 3. Select ADDMs for test:
        self.select_addm()

        # 4. For each package&addm version do SOMETHING:
        self.tku_run_steps()
        return self.tasks_added

    def task_tag(self):
        """Just make a task tag for this routine"""
        self.t_tag = f'tag=upload_routine;lock=True;type=routine;user_name={self.user_name};tku_type={self.tku_type}' \
                     f' | on: "{self.addm_group}" by: {self.user_name}'

    def wget_run(self):
        if self.tku_wget:
            subject = f"TKU_Upload_routines | wget_run | {self.test_mode} | {self.addm_group}"
            body = f"ADDM group: {self.addm_group}, test mode: {self.test_mode}, tku_type: {self.tku_type}, user: {self.user_name}"
            task = Runner.fire_t(TSupport.t_short_mail,
                                 fake_run=self.fake_run, to_sleep=20, to_debug=True,
                                 t_queue=f'{self.addm_group}@tentacle.dq2',
                                 t_args=[f"TKU_Upload_routines.wget_run;task=t_short_mail;test_mode={self.test_mode};"
                                         f"addm_group={self.addm_group};user={self.user_name}"],
                                 t_kwargs=dict(subject=subject, body=body, send_to=[self.user_email]),
                                 t_routing_key=f"{self.addm_group}.TUploadExec.t_upload_prep")
            self.tasks_added.append(task)

            task = Runner.fire_t(TUploadExec.t_tku_sync, fake_run=self.fake_run,
                                 t_kwargs=dict(tku_type=self.tku_type), t_args=['tag=t_tku_sync;'])
            self.tasks_added.append(task)
            if TasksOperations().task_wait_success(task, 't_tku_sync_option'):
                self.tku_downloaded = True
            # Wait for task to finish?
            # OR, assign this task to the worker of ADDM selected group and then when it finish - upload test will run next?
        else:
            self.tku_downloaded = True

    def packages_assign(self):
        if self.tku_type:
            assert isinstance(self.tku_type, str)
        if self.request.get('package_types'):
            # String comes from REST POST Request - split on list
            if isinstance(self.request.get('package_types'), str):
                _packages = self.request.get('package_types')
                log.debug("Splitting package_types: %s", _packages)
                self.package_types = _packages.split(',')
                log.debug("List package_types: %s", self.package_types)
            # List comes from octo test:
            elif isinstance(self.request.get('package_types'), list):
                self.package_types = self.request.get('package_types')
            else:
                log.warning("Unsupported type of package_types!")

    def select_pack_modes(self):
        """
        If mode selected - choose tku packages based on mode:
        update:
            - select latest TKN released for step_1 install
            - select latest GA TNK for step_2 install
        step or fresh: can have one or multiple packages
            - select packages passed one by one, if multiple
        else
            - select one provided type TKN package of latest

        :return:
        """
        self.packages_assign()
        packages = dict()
        if self.test_mode == 'update':
            log.info("<=UploadTaskPrepare=> Will install TKU in UPDATE mode.")

            released_tkn = TkuPackages.objects.filter(tku_type__exact='released_tkn').aggregate(Max('package_type'))
            package = TkuPackages.objects.filter(tku_type__exact='released_tkn',
                                                 package_type__exact=released_tkn['package_type__max'])
            packages.update(step_1=package)

            ga_candidate = TkuPackages.objects.filter(tku_type__exact='ga_candidate').aggregate(Max('package_type'))
            package = TkuPackages.objects.filter(tku_type__exact='ga_candidate',
                                                 package_type__exact=ga_candidate['package_type__max'])
            packages.update(step_2=package)

        elif self.test_mode == 'step' or self.test_mode == 'fresh':
            log.info("<=UploadTaskPrepare=> Install TKU in (%s) mode, package_types (%s)", self.test_mode,
                     self.package_types)
            step = 0
            for package_type in self.package_types:
                step += 1
                package = TkuPackages.objects.filter(package_type__exact=package_type)
                # If query return anything other (probably old GA) with released_tkn - prefer last option.
                package_dis = package.filter(tku_type__exact='released_tkn')

                # log.debug("package: %s", package.values())
                # log.debug("package_dis: %s", package_dis.values())

                if package_dis:
                    package = package_dis
                packages.update({f'step_{step}': package})
        else:
            log.info("<=UploadTaskPrepare=> Will install TKU in Custom mode.")
            step = 0
            for package_type in self.package_types:
                step += 1
                package = TkuPackages.objects.filter(package_type__exact=package_type)
                package_dis = package.filter(tku_type__exact='released_tkn')
                if package_dis:
                    package = package_dis
                packages.update({f'step_{step}': package})

        log.info("<=UploadTaskPrepare=> Selected packages for test in mode: %s", self.test_mode)

        self.packages = packages
        return packages

    def select_addm(self):
        if not self.addm_group:
            self.addm_group = 'golf'  # Should be a dedicated group for only upload test routines.
        addm_set = AddmDev.objects.filter(addm_group__exact=self.addm_group, disables__isnull=True).values()
        self.addm_set = addm_set
        return addm_set

    def tku_run_steps(self):
        for step_k, packages_v in self.packages.items():
            log.info("<=UploadTaskPrepare=> Processing packages step by step: %s", step_k)
            # Task for upload test prep if needed (remove older TKU, prod content, etc)
            self.addm_prepare(step_k=step_k)
            # Task for unzip packages on selected each ADDM from ADDM Group
            self.package_unzip(step_k=step_k, packages_from_step=packages_v)
            # Task for install TKU from unzipped packages for each ADDM from selected ADDM group
            self.tku_install(step_k=step_k, packages_from_step=packages_v)

    def addm_prepare(self, step_k):
        """
        Upload test initial step, prepare ADDM before install TKU.
        It could be - removing old TKU, product content, restart services.
        TBA: Add vCenter operations for: power on, snapshot revert.
        :param step_k:
        :return:
        """
        t_kwargs = ''
        if self.test_mode == 'fresh' and step_k == 'step_1':
            log.info(
                "<=UploadTaskPrepare=> Fresh install: (%s), 1st step (%s) - require TKU wipe and prod content delete!",
                self.test_mode, step_k)
            t_kwargs = dict(addm_items=self.addm_set, step_k=step_k, test_mode='fresh', user_email=self.user_email)

        elif self.test_mode == 'update' and step_k == 'step_1':
            log.info(
                "<=UploadTaskPrepare=> Update install: (%s), 1st step (%s) - require TKU wipe and prod content delete!",
                self.test_mode, step_k)
            t_kwargs = dict(addm_items=self.addm_set, step_k=step_k, test_mode='update', user_email=self.user_email)

        elif self.test_mode == 'step' and step_k == 'step_1':
            log.info(
                "<=UploadTaskPrepare=> Step install: (%s), 1st step (%s) - require TKU wipe and prod content delete!",
                self.test_mode, step_k)
            t_kwargs = dict(addm_items=self.addm_set, step_k=step_k, test_mode='step', user_email=self.user_email)

        else:
            log.debug("Other modes do not require preparations. Only fresh and update at 1st step require!")

        if t_kwargs:
            subject = f"TKU_Upload_routines | addm_prepare | {self.test_mode} | {self.addm_group} | {step_k}"
            body = f"ADDM group: {self.addm_group}, test mode: {self.test_mode}, user: {self.user_name}, step_k: {step_k}, "
            task = Runner.fire_t(TSupport.t_short_mail,
                                 fake_run=self.fake_run, to_sleep=20, to_debug=True,
                                 t_queue=f'{self.addm_group}@tentacle.dq2',
                                 t_args=[
                                     f"TKU_Upload_routines.addm_prepare;task=t_short_mail;test_mode={self.test_mode};"
                                     f"addm_group={self.addm_group};user={self.user_name}"],
                                 t_kwargs=dict(subject=subject, body=body, send_to=[self.user_email]),
                                 t_routing_key=f"{self.addm_group}.TUploadExec.t_upload_prep")
            self.tasks_added.append(task)
            # UploadTestExec().upload_preparations_threads(addm_items=self.addm_set, mode='fresh')
            task = Runner.fire_t(TUploadExec.t_upload_prep,
                                 fake_run=self.fake_run, to_sleep=60, to_debug=True,
                                 t_queue=f'{self.addm_group}@tentacle.dq2',
                                 t_args=[
                                     f"TKU_Upload_routines.addm_prepare;task=addm_prepare;test_mode={self.test_mode};"
                                     f"addm_group={self.addm_group};user={self.user_name}"],
                                 t_kwargs=t_kwargs,
                                 t_routing_key=f"{self.addm_group}.TUploadExec.t_upload_prep")
            self.tasks_added.append(task)

    def package_unzip(self, step_k, packages_from_step):
        """
        Make task with threading for each ADDM in selected group.
        Task run addm unzip routine selecting zips for each addm version and saving files in /usr/tideway/TEMP.
        It will remove all content before!
        :param step_k:
        :param packages_from_step:
        :return:
        """
        subject = f"TKU_Upload_routines | t_upload_unzip | {self.test_mode} | {self.addm_group} | {step_k}"
        packs = packages_from_step.values('tku_type', 'package_type', 'zip_file_name', 'zip_file_path')
        body = f"ADDM group: {self.addm_group}, test mode: {self.test_mode}, user: {self.user_name}, step_k: {step_k}, packages: {list(packs)}"
        task = Runner.fire_t(TSupport.t_short_mail,
                             fake_run=self.fake_run, to_sleep=20, to_debug=True,
                             t_queue=f'{self.addm_group}@tentacle.dq2',
                             t_args=[f"TKU_Upload_routines.package_unzip;task=t_short_mail;test_mode={self.test_mode};"
                                     f"addm_group={self.addm_group};user={self.user_name}"],
                             t_kwargs=dict(subject=subject, body=body, send_to=[self.user_email]),
                             t_routing_key=f"{self.addm_group}.TUploadExec.t_upload_prep")
        self.tasks_added.append(task)
        # UploadTestExec().upload_unzip_threads(addm_items=self.addm_set, packages=packages_from_step)
        task = Runner.fire_t(TUploadExec.t_upload_unzip,
                             fake_run=self.fake_run, to_sleep=60, to_debug=True,
                             t_queue=f"{self.addm_group}@tentacle.dq2",
                             t_args=[
                                 f"TKU_Upload_routines;task=t_upload_unzip;test_mode={self.test_mode};addm_group={self.addm_group};user={self.user_name}"],
                             t_kwargs=dict(addm_items=self.addm_set, test_mode=self.test_mode, step_k=step_k,
                                           packages=packages_from_step, user_email=self.user_email),
                             t_routing_key=f"{self.addm_group}.TUploadExec.t_upload_unzip")
        self.tasks_added.append(task)

    def tku_install(self, step_k, packages_from_step):
        """
        Install previously unzipped TKU from /usr/tideway/TEMP/*.zip
        :return:
        """
        subject = f"TKU_Upload_routines | t_tku_install | {self.test_mode} | {self.addm_group} | {step_k}"
        packs = packages_from_step.values('tku_type', 'package_type', 'zip_file_name', 'zip_file_path')
        body = f"ADDM group: {self.addm_group}, test mode: {self.test_mode}, user: {self.user_name}, step_k: {step_k}, " \
               f"packages: {list(packs)}, package_detail: {self.package_detail}"
        task = Runner.fire_t(TSupport.t_short_mail,
                             fake_run=self.fake_run, to_sleep=20, to_debug=True,
                             t_queue=f'{self.addm_group}@tentacle.dq2',
                             t_args=[f"TKU_Upload_routines.tku_install;task=t_short_mail;test_mode={self.test_mode};"
                                     f"addm_group={self.addm_group};user={self.user_name}"],
                             t_kwargs=dict(subject=subject, body=body, send_to=[self.user_email]),
                             t_routing_key=f"{self.addm_group}.TUploadExec.t_upload_prep")
        self.tasks_added.append(task)
        # UploadTestExec().install_tku_threads(addm_items=self.addm_set)
        task = Runner.fire_t(TUploadExec.t_tku_install,
                             fake_run=self.fake_run, to_sleep=20, to_debug=True,
                             t_queue=f"{self.addm_group}@tentacle.dq2",
                             t_args=[
                                 f"TKU_Upload_routines;task=t_tku_install;test_mode={self.test_mode};addm_group={self.addm_group};user={self.user_name}"],
                             t_kwargs=dict(addm_items=self.addm_set, test_mode=self.test_mode, step_k=step_k,
                                           packages=packages_from_step, package_detail=self.package_detail,
                                           user_email=self.user_email),
                             t_routing_key=f"{self.addm_group}.TUploadExec.t_tku_install")
        self.tasks_added.append(task)

    @staticmethod
    def debug_unpack_qs(packages):
        for step_k, step_package in packages.items():
            for pack in step_package:
                msg = f'{step_k} package: {pack.tku_type} -> {pack.package_type} addm: {pack.addm_version} zip: {pack.zip_file_name} '
                log.info(msg)


class TestRunnerLoc:

    if os.name == 'nt':
        sep = '\\'
    else:
        sep = '/'

    def run_th(self, **kwargs):
        from queue import Queue
        from threading import Thread
        test_method = kwargs.get('test_method')

        thread_outputs = []
        thread_list = []
        th_name = f'Upload_Test_case-{test_method}'
        test_q = Queue()
        th_kwargs = dict(test_method=test_method, test_q=test_q)
        try:
            log.info("Running thread test for: %s", th_name)
            prep_th = Thread(target=self.run_tests, name=th_name, kwargs=th_kwargs)
            prep_th.start()
            thread_list.append(prep_th)
        except Exception as e:
            log.error("TestRunnerLoc thread error: %s", e)

        for test_th in thread_list:
            test_th.join()
            th_out = test_q.get()
            thread_outputs.append(th_out)
        return thread_outputs

    def run_cased(self, **kwargs):
        from queue import Queue
        test_q = Queue()
        cased_func = TestRunnerLoc().run_tests
        test_method = kwargs.get('test_method')
        kw_args = dict(test_q=test_q, test_method=test_method)
        cased_func(**kw_args)

    def get_tests_from_py(self):
        import py_compile
        loader = unittest.TestLoader()

        test_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                 f'..{self.sep}run_core{self.sep}octotest_upload_tku.py'))
        compiled = py_compile.compile(test_file)

        log.debug("test_file: %s", test_file)
        with open(test_file, "r", encoding="utf8") as f:
            read_file = f.read()
            test_tree = ast.parse(read_file)

        code = compile(read_file, 'octotest_upload_tku.py', 'exec')
        log.debug("code: %s", code)

        ast_code = compile(test_tree, 'octotest_upload_tku.py', 'exec')
        log.debug("ast_code: %s", ast_code)

        # OctoTestCaseUpload_eval = eval(code)
        # log.info("OctoTestCaseUpload: eval %s %s", type(OctoTestCaseUpload_eval), OctoTestCaseUpload_eval)

        OctoTestCaseUpload = exec(ast_code)
        log.info("OctoTestCaseUpload: exec %s %s", type(OctoTestCaseUpload), OctoTestCaseUpload)

        # tests_1 = loader.loadTestsFromTestCase(OctoTestCaseUpload_eval)
        # log.debug("tests_1: %s", tests_1)
        tests = loader.discover(
            'D:\\perforce\\addm\\tkn_sandbox\\o.danylchenko\\projects\\PycharmProjects\\lobster\\run_core\\__pycache__',
            pattern='octotest_upload_tku.cpython-36.pyc')
        log.debug("tests: %s", tests)

        # tests_2 = loader.loadTestsFromTestCase(OctoTestCaseUpload)
        # log.debug("tests_2: %s", tests_2)

        return tests

    def get_tests_from_module(self, test_method=None, module=None):
        """
        Importable module load and sort out the test method if any.
        :param test_method:
        :param module:
        :return:
        """
        if not module:
            from run_core import __octotest_upload_tku
            module = __octotest_upload_tku.OctoTestCaseUpload

        loader = unittest.TestLoader()
        tests = loader.loadTestsFromName(test_method, module=module)
        return tests

    def get_tests_from_case(self, test_method=None, case=None):
        """
        Get all test cases from TestCases Class, also sort single test if test_method provided.
        :param test_method:
        :param case:
        :return:
        """
        if not case:
            from run_core.__octotest_upload_tku import OctoTestCaseUpload
            case = OctoTestCaseUpload
        loader = unittest.TestLoader()
        tests = loader.loadTestsFromTestCase(case)
        log.info("All tests in loadTestsFromTestCase: %s", tests)
        if test_method:
            for test in tests:
                if test_method == test._testMethodName:
                    return [test]
        return tests

    def compile_test(self, test_file):
        import py_compile
        compiled = py_compile.compile(test_file)
        log.debug("Compiled tests file: %s", compiled)

    def re_write_test_file(self, test_file, rotate_file_path):

        rotatable = os.path.join(rotate_file_path, '__octo_test_rotate.py')
        if os.path.exists(rotatable):
            log.debug("Deleting rotatable file: %s", rotatable)
            os.remove(rotatable)
            pycache = os.path.join(rotate_file_path, '__pycache__', '__octo_test_rotate.cpython-36.pyc')
            if os.path.exists(pycache):
                os.remove(pycache)

        with open(test_file, "r", encoding="utf8") as f:
            read_file = f.read()
        with open(rotatable, 'w') as test_f:
            test_f.write(read_file)
        return rotatable

    def get_tests_from_discover(self, test_method=None, test_dir=None):
        """
        https://stackoverflow.com/a/37724523
        :param test_method:
        :param test_dir:
        :return:
        """
        loader = unittest.TestLoader()
        # D:\\perforce\\addm\\tkn_sandbox\\o.danylchenko\\projects\\PycharmProjects\\lobster\\z_DEV\\octo_tests
        log.debug("test_dir: %s", test_dir)
        rotatable = self.re_write_test_file(os.path.abspath(os.path.join(test_dir, 'octotest_upload_tku.py')), test_dir)
        log.debug("rotatable: %s", rotatable)

        tests = loader.discover(test_dir, pattern='__octo_test_rotate.py')

        if test_method:
            for test in tests:
                log.info("<=get_tests_from_discover> One test from discover: %s %s", test, type(test))
                if test:
                    log.debug("\ttest iter: %s", test)
                    if isinstance(test, unittest.TestSuite):
                        log.debug("\ttest instance: TestSuite")
                        for item in test:
                            log.debug("\t\ttest item: %s", item)
                            if isinstance(item, unittest.TestSuite):
                                for case in item:
                                    if case and hasattr(case, '_testMethodName'):
                                        log.info("\t\t<=get_tests_from_discover> Test items has attr: %s", case)
                                        if test_method == case._testMethodName:
                                            log.info("\t\t\t<=get_tests_from_discover> Test test._testMethodName: %s", case._testMethodName)
                                            return [case], rotatable
                                else:
                                    log.debug("\t\tThis test case is not %", test_method)
                            else:
                                log.debug("\t\tItem have no attribute _testMethodName")
                    else:
                        log.debug("\tNot a testSuite instance")
                else:
                    log.debug("\tNo test in this suite")
        else:
            log.debug("No test method, run all tests!")

    def run_tests(self, **kwargs):
        # from run_core import octotest_upload_tku
        test_q = kwargs.get('test_q')
        test_method = kwargs.get('test_method')
        test_dir = kwargs.get('test_dir')

        # all_case_names = unittest.TestLoader().getTestCaseNames(octotest_upload_tku.OctoTestCaseUpload)
        # log.debug("all_case_names: %s", all_case_names)

        suite = unittest.TestSuite()
        runner = unittest.TextTestRunner(verbosity=3)
        # tests = self.get_tests_from_module(test_method, module=octotest_upload_tku.OctoTestCaseUpload)
        # tests = self.get_tests_from_case(test_method, case=OctoTestCaseUpload)
        tests, rotatable = self.get_tests_from_discover(test_method, test_dir)
        # tests = self.get_tests_from_py()

        log.info("<=TestRunnerLoc=> tests: %s", tests)
        for test in tests:
            result = runner.run(test)
            log.debug("result: %s", result)
            # return str(result)
            # # test_q.put(str(result))

        # else:
        #     suite.addTests(tests)
        #     result = runner.run(suite)
        #     log.info("<=TestRunnerLoc=> suite: %s", suite)
        # return str(result)
        # test_q.put(str(result))
