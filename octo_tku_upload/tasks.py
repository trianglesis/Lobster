from __future__ import absolute_import, unicode_literals

import datetime
import logging
import os
# noinspection PyUnresolvedReferences
from typing import Dict, List, Any

from celery.utils.log import get_task_logger
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

from octotests.tests_discover_run import TestRunnerLoc

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
        """
        Can run routines tasks as test methods from unit test case class.
        Reflects external changes to to test file without reload/restart.
        :param t_tag:
        :param kwargs: dict(test_method, test_class, test_module)
        :return:
        """
        log.info("<=t_upload_routines=> Running task %s", kwargs)
        return TestRunnerLoc().run_subprocess(**kwargs)

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

    # TODO: Simplify this, we no longer require view\requests, just use same as for patterns
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
