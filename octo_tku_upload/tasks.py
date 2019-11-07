from __future__ import absolute_import, unicode_literals
import os
import datetime
import logging
# noinspection PyUnresolvedReferences
from typing import Dict, List, Any
from django.db.models import Max
# Celery
from octo.octo_celery import app

from octo_tku_upload.test_executor import UploadTestExec

from run_core.local_operations import LocalDownloads
from run_core.models import AddmDev
from run_core.addm_operations import ADDMOperations

from octo_tku_upload.models import TkuPackagesNew as TkuPackages

from octo.helpers.tasks_oper import TasksOperations
from octo.helpers.tasks_helpers import TMail
from octo.helpers.tasks_helpers import exception

from octo.helpers.tasks_run import Runner
from octo.tasks import TSupport

log = logging.getLogger("octo.octologger")

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
class TUploadRoutine:

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TRoutine.t_routine_tku_upload_test_new',
              soft_time_limit=MIN_90, task_time_limit=HOURS_2)
    @exception
    def t_routine_tku_upload(t_tag, **kwargs):
        return UploadCases.tku_upload(**kwargs)


# noinspection PyUnusedLocal,PyUnusedLocal
class TUploadExec:

    @staticmethod
    @app.task(routing_key='worker_tentacle.TExecTest.t_tku_sync.addm_group',
              queue='w_parsing@tentacle.dq2', soft_time_limit=MIN_20, task_time_limit=MIN_40)
    @exception
    def t_tku_sync(t_tag, **kwargs):
        return LocalDownloads().wget_tku_build_hub_option(**kwargs)

    @staticmethod
    @app.task(routing_key='worker_tentacle.TExecTest.t_upload_exec_threads.addm_group',
              soft_time_limit=MIN_90, task_time_limit=HOURS_2)
    @exception
    def t_upload_exec_threads(t_tag, **kwargs):
        return UploadTestExec().upload_run_threads(**kwargs)

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
    def t_upload_addm_prep(t_tag, **kwargs):
        log.debug("t_upload_addm_prep - add here addm preparation routine in threads or vCenter actions?")

    @staticmethod
    @app.task(soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_upload_unzip(t_tag, **kwargs):
        UploadTestExec.upload_unzip_threads(**kwargs)


class UploadCases:

    @staticmethod
    def tku_upload(**kwargs):
        """
        Routine case for following operations:
        1. Download/Renew CONTINUOUS TKU zips on Octopus FS from buildhub FTP.
        2. Parse and collect all CONTINUOUS stored zips and args for them. Insert in DB.
        3. Run simple TKU install and parse results. No extra steps required!

        :return:
        """
        # user_name  = kwargs['user_name']
        user_email = kwargs.get('user_email')
        addm_group = kwargs.get('addm_group')
        mode = kwargs.get('mode', None)
        tku_type = kwargs.get('tku_type', None)
        tku_wget = kwargs.get('tku_wget', False)
        fake_run = kwargs.get('fake_run', False)
        tku_downloaded = False
        # Send on init:
        TMail().upload_t(stage='started', mode=mode, tku_type=tku_type, tku_wget=tku_wget, addm_group=addm_group,
                       user_email=user_email, start_time=datetime.datetime.now())

        if tku_wget:
            """ WGET zips and parse locally: """
            tku_download_task = Runner.fire_t(TUploadExec().t_tku_sync, fake_run=fake_run,
                                              t_kwargs=dict(tku_type=tku_type),
                                              t_args=['tag=t_tku_sync;mode={};addm_group={}'.format(mode, addm_group)])
            # Wait until wget task finished successfully:
            if TasksOperations().task_wait_success(tku_download_task, 't_tku_sync_option'):
                tku_downloaded = True
        else:
            # Do not run WGET, just install local zip
            tku_downloaded = True

        if tku_downloaded:
            t_tag = 'tag=upload_t;lock=True;type=routine;tku_type={tku_type};addm_group={addm_group};'.format(
                tku_type=tku_type, addm_group=addm_group)
            Runner.fire_t(TUploadExec().t_upload_exec_threads, fake_run=fake_run,
                          t_queue=addm_group + '@tentacle.dq2',
                          t_args=[t_tag],
                          t_routing_key='routines.TExecTest.t_upload_exec_threads.{}'.format(addm_group),
                          t_kwargs=dict(addm_group=addm_group, tku_type=tku_type, mode=mode, user_email=user_email))
            # Send on start
            TMail().upload_t(stage='tku_install', mode='continuous', tku_type=tku_type, tku_wget=tku_wget,
                           addm_group=addm_group, t_tag=t_tag, start_time=datetime.datetime.now(), )
        else:
            msg = "<=RoutineCases=> t_tku_sync failed to finish. Kwargs: {}".find(**kwargs)
            log.error(msg)
            raise Exception(msg)


class UploadTaskPrepare:

    def __init__(self, obj):
        # Initial view requests:
        self.view_obj = obj
        if isinstance(self.view_obj, dict):
            self.options = self.view_obj.get('context')
            self.request = self.view_obj.get('request')
            # Assign generated context for further usage:
            self.selector = self.options.get('selector', {})
            self.user_name = self.view_obj.get('user_name')
            self.user_email = self.view_obj.get('user_email')
            self.test_mode = self.selector.get('test_mode', None)
            self.tku_type = self.selector.get('tku_type', None)
            self.addm_group = self.selector.get('addm_group', None)
        else:
            self.request = obj.request
            self.options = obj.request
            self.user_name = self.request.get('user_name', 'octopus_super')
            self.user_email = self.request.get('user_email', None)
            self.selector = self.request.get('selector', {})
            self.test_mode = self.selector.get('test_mode', None)
            self.tku_type = self.selector.get('tku_type', None)
            self.addm_group = self.selector.get('addm_group', None)

        # Define fake run:
        self.fake_run = False
        self.fake_fun()

        # Internal statuses:
        self.silent = False
        self.silent_run()

        # Get user and mail:
        self.start_time = datetime.datetime.now()
        log.info("<=UploadTaskPrepare=> Prepare tests for user: %s - %s", self.user_name, self.user_email)

        self.tku_wget = False
        self.packages = dict()
        self.addm_set = dict()

        # Current status args:
        self.tku_downloaded = False
        # NOTE: It can change during process current class!!!!`
        self.t_tag = ''

    def fake_fun(self):
        """
        For debug purposes, just run all tasks as fake_task with showing all inputs and outputs: args, kwargs.
        :return:
        """

        if os.name == "nt":  # Always fake run on local test env:
            self.fake_run = True
            log.debug("<=TaskPrepare=> Fake run self.options: %s", self.options)
            log.debug("<=TaskPrepare=> Fake run self.request: %s", self.request)

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

    def run_tku_upload(self):
        self.task_tag_generate()
        log.warning("<=UploadTaskPrepare=> TASK PSEUDO RUNNING in TaskPrepare.run_tku_upload")
        # 0. Init test mail?
        # self.mail_status(mail_opts=dict(mode='init', view_obj=self.view_obj))

        # 1. Refresh local TKU Packages:
        self.wget_run()

        # 2. Select TKU for test run.
        packages = self.select_packages_modes()
        self.debug_unpack_packages_qs(packages)

        # 3. Select ADDMs for test:
        self.select_addm()

        # 4. For each package&addm version do SOMETHING:
        self.tku_packages_processing_steps()

    def mail_status(self, mail_opts):
        mode = mail_opts.get('mode')

        if not self.silent:
            log.info("<=TaskPrepare=> Mail sending, mode: %s", mode)
            if mail_opts.get('addm_set') and mail_opts.get('test_item'):
                log.debug("<=TaskPrepare=> MAIL when test item and addm set is TRUE")

                addm = mail_opts.get('addm_set').first()
                test_item = mail_opts.get('test_item')

                mail_r_key = f'{addm["addm_group"]}.TSupport.t_user_mail.{mode}'
                t_tag = f'tag=t_user_mail;mode={mode};addm_group={addm["addm_group"]};user_name={self.user_name};' \
                        f'test_py_path={test_item["test_py_path"]}'

                Runner.fire_t(TSupport.t_user_test, fake_run=self.fake_run, t_args=[t_tag],
                              t_kwargs=dict(mail_opts=mail_opts),
                              t_queue=addm['addm_group']+'@tentacle.dq2', t_routing_key=mail_r_key)

            elif mode == 'init':
                log.debug("<=TaskPrepare=> MAIL when INIT")
                TMail().user_test(mail_opts)
            else:
                log.debug("<=TaskPrepare=> MAIL when ELSE")
                TMail().user_test(mail_opts)
        else:
            log.info("<=TaskPrepare=> Mail silent mode. Do not send massages. Current stage: %s", mode)

    def task_tag_generate(self):
        """Just make a task tag for this routine"""
        self.t_tag = f'tag=upload_routine;lock=True;type=routine;user_name={self.user_name};tku_type={self.tku_type}' \
                     f' | on: "{self.addm_group}" by: {self.user_name}'

    def wget_run(self):
        if self.tku_wget:
            log.info("Run WGET: ")
            task = Runner.fire_t(TUploadExec.t_tku_sync, fake_run=self.fake_run,
                                 t_kwargs=dict(tku_type=self.tku_type),
                                 t_args=['tag=t_tku_sync;'])
            if TasksOperations().task_wait_success(task, 't_tku_sync_option'):
                self.tku_downloaded = True
            # Wait for task to finish?
            # OR, assign this task to the worker of ADDM selected group and then when it finish - upload test will run next?
        else:
            self.tku_downloaded = True

    def select_packages_modes(self):
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
        log.info("Selector: %s", self.selector)

        if self.tku_type:
            assert isinstance(self.tku_type, str)
        if self.selector['package_types']:
            assert isinstance(self.selector['package_types'], list)

        packages = dict()
        if self.test_mode == 'update':
            log.info("<=UploadTaskPrepare=> Will install TKU in UPDATE mode.")

            released_tkn = TkuPackages.objects.filter(tku_type__exact='released_tkn').aggregate(Max('package_type'))
            package = TkuPackages.objects.filter(tku_type__exact='released_tkn', package_type__exact=released_tkn['package_type__max'])
            packages.update(step_1=package)

            ga_candidate = TkuPackages.objects.filter(tku_type__exact='ga_candidate').aggregate(Max('package_type'))
            package = TkuPackages.objects.filter(tku_type__exact='ga_candidate', package_type__exact=ga_candidate['package_type__max'])
            packages.update(step_2=package)

        elif self.test_mode == 'step' or self.test_mode == 'fresh':
            log.info("<=UploadTaskPrepare=> Will install TKU in %s one by one mode.", self.test_mode)
            step = 0
            for package_type in self.selector['package_types']:
                step += 1
                package = TkuPackages.objects.filter(package_type__exact=package_type)
                # If query return anything other (probably old GA) with released_tkn - prefer last option.
                package_dis = package.filter(tku_type__exact='released_tkn')
                if package_dis:
                    package = package_dis
                packages.update({f'step_{step}': package})

        else:
            log.info("<=UploadTaskPrepare=> Will install TKU in Custom mode.")
            step = 0
            for package_type in self.selector['package_types']:
                step += 1
                package = TkuPackages.objects.filter(package_type__exact=package_type)
                package_dis = package.filter(tku_type__exact='released_tkn')
                if package_dis:
                    package = package_dis
                packages.update({f'step_{step}': package})
        # log.info("<=UploadTaskPrepare=> Selected packages for test in mode: %s %s", self.test_mode, packages)
        self.packages = packages
        return packages

    def select_addm(self):
        if not self.addm_group:
            self.addm_group = 'alpha'  # Should be a dedicated group for only upload test routines.
        addm_set = AddmDev.objects.filter(addm_group__exact=self.addm_group, disables__isnull=True).values()
        self.addm_set = addm_set
        return addm_set

    def tku_packages_processing_steps(self):
        for step_k, packages_v in self.packages.items():
            log.info("<=UploadTaskPrepare=> Processing packages step by step: %s", step_k)
            # Task for upload test prep if needed (remove older TKU, prod content, etc)
            self.addm_prepare(step_k=step_k)
            # Task for unzip packages on selected each ADDM from ADDM Group
            self.package_unzip(packages_from_step=packages_v)
            # Task for install TKU from unzipped packages for each ADDM from selected ADDM group
            self.tku_install()

    def addm_prepare(self, step_k):
        if self.test_mode == 'fresh' and step_k == 'step_1':
            log.info("<=UploadTaskPrepare=> Fresh install: (%s), 1st step (%s) - require TKU wipe and prod content delete!", self.test_mode, step_k)
            log.debug("<=UploadTaskPrepare=> We may run vCenter revert snapshot here, later.")
            # TODO: Taskify:
            UploadTestExec().upload_preparations_threads(addm_items=self.addm_set, mode='fresh')

        elif self.test_mode == 'update' and step_k == 'step_1':
            log.info("<=UploadTaskPrepare=> Update install: (%s), 1st step (%s) - require TKU wipe and prod content delete!", self.test_mode, step_k)
            log.debug("<=UploadTaskPrepare=> We may run vCenter revert snapshot here, later.")
            # TODO: Taskify:
            UploadTestExec().upload_preparations_threads(addm_items=self.addm_set, mode='update')

        elif self.test_mode == 'step' and step_k == 'step_1':
            log.info("<=UploadTaskPrepare=> Step install: (%s), 1st step (%s) - require TKU wipe and prod content delete!", self.test_mode, step_k)
            log.debug("<=UploadTaskPrepare=> We may run vCenter revert snapshot here, later.")
            # TODO: Taskify:
            UploadTestExec().upload_preparations_threads(addm_items=self.addm_set, mode='step')

        else:
            log.debug("Other modes do not require preparations. Only fresh and update at 1st step require!")

    def package_unzip(self, packages_from_step):
        """
        Make task with threading for each ADDM in selected group.
        Task run addm unzip routine selecting zips for each addm version and saving files in /usr/tideway/TEMP.
        It will remove all content before!
        :param packages_from_step:
        :return:
        """
        log.info("<=UploadTaskPrepare=> Unzip packages for selected ADDMs from group %s", self.addm_group)
        # TODO: use task!
        UploadTestExec().upload_unzip_threads(addm_items=self.addm_set, packages=packages_from_step)

        # t_tag = f"TKU_Unzip_task;addm_group={self.addm_group}"
        # task_r_key = f"{self.addm_group}.TUploadExec.t_upload_unzip"
        # Runner.fire_t(TUploadExec.t_upload_unzip, fake_run=self.fake_run, to_sleep=20, debug_me=True,
        #               t_queue=f"{self.addm_group}@tentacle.dq2", t_args=[t_tag],
        #               t_kwargs=dict(addm_items=self.addm_set, packages=packages_from_step),
        #               t_routing_key=task_r_key)

    def tku_install(self):
        log.info("<=UploadTaskPrepare=> Run TKU install for unzipped packages %s", self.addm_group)
        UploadTestExec().install_tku_threads(addm_items=self.addm_set)

        # t_tag = f"TKU_Unzip_task;addm_group={self.addm_group}"
        # task_r_key = f"{self.addm_group}.TUploadExec.t_upload_unzip"
        # Runner.fire_t(TUploadExec.t_upload_unzip, fake_run=self.fake_run, to_sleep=20, debug_me=True,
        #               t_queue=f"{self.addm_group}@tentacle.dq2", t_args=[t_tag],
        #               t_kwargs=dict(addm_items=self.addm_set, packages='packages_from_step'),
        #               t_routing_key=task_r_key)


    def debug_unpack_packages_qs(self, packages):
        for step_k, step_package in packages.items():
            for pack in step_package:
                msg = f'{step_k} package: {pack.tku_type} -> {pack.package_type} addm: {pack.addm_version} zip: {pack.zip_file_name} '
                log.info(msg)
