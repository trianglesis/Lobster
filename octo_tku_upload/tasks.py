from __future__ import absolute_import, unicode_literals

import datetime
import logging
from itertools import groupby
from operator import itemgetter
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
from octotests.tests_discover_run import TestRunnerLoc
from run_core.local_operations import LocalDownloads
from run_core.models import AddmDev
from octo_tku_upload.digests import TKUEmailDigest


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

_LH_ = '<=UploadTaskPrepare=>'


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
        log.info(f"<=t_upload_routines=> Running task {t_tag} {kwargs}")
        TestRunnerLoc().run_subprocess(**kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TRoutine.t_routine_tku_upload_test_new',
              soft_time_limit=MIN_90, task_time_limit=HOURS_2)
    @exception
    def t_upload_test(t_tag, **kwargs):
        return UploadTaskPrepare(**kwargs).run_tku_upload()

    @staticmethod
    @app.task(queue='w_parsing@tentacle.dq2',
              soft_time_limit=MIN_40, task_time_limit=MIN_90)
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
    def t_upload_unzip(t_tag, **kwargs):
        return UploadTestExec().upload_unzip_threads(**kwargs)

    @staticmethod
    @app.task(soft_time_limit=MIN_90, task_time_limit=HOURS_2)
    @exception
    def t_tku_install(t_tag, **kwargs):
        return UploadTestExec().install_tku_threads(**kwargs)

class MailDigests:

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.MailDigests.t_upload_digest',
              soft_time_limit=MIN_10, task_time_limit=MIN_20)
    def t_upload_digest(t_tag, **kwargs):
        TKUEmailDigest().upload_daily_fails_warnings(**kwargs)

class UploadTaskPrepare:

    def __init__(self, **kwargs):
        # Initial view requests:
        self.data = kwargs.get('data')

        # Assign generated context for further usage:
        self.user_name = kwargs.get('user_name')
        self.user_email = kwargs.get('user_email')

        self.tku_wget = self.data.get('tku_wget', None)
        self.test_mode = self.data.get('test_mode', 'custom')
        self.tku_type = self.data.get('tku_type', None)
        self.addm_group = self.data.get('addm_group', None)
        self.package_detail = self.data.get('package_detail', None)

        # Define fake run:
        self.fake_run = False
        self.fake_run_f()

        # Internal statuses:
        self.silent = False
        self.silent_run()

        # Get user and mail:
        self.start_time = datetime.datetime.now()
        log.info(f"{_LH_} Prepare tests for user: {self.user_name} - {self.user_email}")

        self.package_types = ''
        self.packages = dict()
        self.addm_set = ''
        # To ignore filter packages by ADDM version during unzip func
        self.development = False

        # Current status args:
        self.tku_downloaded = False
        # NOTE: It can change during process current class!!!!`
        self.tasks_added = []

    def fake_run_f(self):
        """For debug purposes, just run all tasks as fake_task with showing all inputs and outputs: args, kwargs."""
        if self.data.get('fake_run'):
            self.fake_run = True
            log.debug(f"{_LH_} Fake run = {self.fake_run}")

    def silent_run(self):
        """Indicates when do not send any mails. """
        if self.data.get('silent'):
            self.silent = True
        log.debug(f"{_LH_} Silent run = {self.silent}")

    def run_tku_upload(self):
        # 0. Init test mail?
        subject = f"UploadTaskPrepare | Routine start | {self.test_mode} "
        body = f"Upload test routine started! test mode: {self.test_mode}, tku_type: {self.tku_type}, user: {self.user_name}"
        self.mail(t_args=[f"UploadTaskPrepare.run_tku_upload"],
                  t_kwargs=dict(subject=subject, body=body, send_to=[self.user_email]),
                  t_queue='w_parsing@tentacle.dq2')
        # 1. Refresh local TKU Packages:
        self.wget_run()
        # 2. Select TKU for test run.
        self.select_pack_modes()
        # 3. Select ADDMs for test:
        self.select_addm()
        # 4. For each package&addm version do SOMETHING:
        self.tku_run_steps()
        return self.tasks_added

    def wget_run(self):
        if self.tku_wget:
            subject = f"UploadTaskPrepare | wget_run | {self.test_mode} "
            body = f"WGET Run! test mode: {self.test_mode}, tku_type: {self.tku_type}, user: {self.user_name}"
            self.mail(t_args=[f"UploadTaskPrepare.wget_run"],
                      t_kwargs=dict(subject=subject, body=body, send_to=[self.user_email]),
                      t_queue='w_parsing@tentacle.dq2')
            task = Runner.fire_t(TUploadExec.t_tku_sync,
                                 fake_run=self.fake_run, to_sleep=2, to_debug=True,
                                 t_kwargs=dict(tku_type=self.tku_type), t_args=['tag=t_tku_sync;'],
                                 t_queue='w_parsing@tentacle.dq2')
            self.tasks_added.append(task)
            if TasksOperations().task_wait_success(task, 't_tku_sync_option'):
                self.tku_downloaded = True
            # Wait for task to finish!
        else:
            self.tku_downloaded = True

    def packages_assign(self):
        """
        Check args for packages:
        - 'tku_type' should be a string, to use as query detail.
        - 'package_types' - can be a str or list of str, indicates model 'package_type' field accordingly
        Packages should not be selected in other way, because it could select duplicates or not supported versions if
            query is more dynamic than static.
        """
        if self.tku_type:
            assert isinstance(self.tku_type, str)
        if self.data.get('package_types'):
            # String comes from REST POST Request - split on list
            if isinstance(self.data.get('package_types'), str):
                _packages = self.data.get('package_types')
                log.debug(f"Splitting package_types: {_packages}")
                self.package_types = _packages.split(',')
                log.debug(f"List package_types: {self.package_types}")
            # List comes from octo test:
            elif isinstance(self.data.get('package_types'), list):
                self.package_types = self.data.get('package_types')
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
        Processing packages make a dict, where each package is assigned to one step, from n=1 to n+1.
        Additionally avoid to select GA Candidates with the same 'package_type' as already published release.
        """
        self.packages_assign()
        packages = dict()
        # Mode to install Released TKU and then GA over it:
        if self.test_mode == 'update':
            log.info(f"{_LH_} Will install TKU in UPDATE mode.")
            # 1st step - use previously released package:
            released_tkn = TkuPackages.objects.filter(
                tku_type__exact='released_tkn').aggregate(Max('package_type'))
            package = TkuPackages.objects.filter(
                tku_type__exact='released_tkn',
                package_type__exact=released_tkn['package_type__max'])
            packages.update(step_1=package)
            # 2nd step - use GA candidate package:
            ga_candidate = TkuPackages.objects.filter(
                tku_type__exact='ga_candidate').aggregate(Max('package_type'))
            package = TkuPackages.objects.filter(
                tku_type__exact='ga_candidate',
                package_type__exact=ga_candidate['package_type__max'])
            packages.update(step_2=package)
        # Mode to install any TKU as fresh or step, one by one.
        elif self.test_mode == 'step' or self.test_mode == 'fresh':
            log.info(f"{_LH_}Install TKU in {self.test_mode} mode - {self.package_types}")
            step = 0
            for package_type in self.package_types:
                step += 1
                package = TkuPackages.objects.filter(package_type__exact=package_type)
                # If query return anything other (probably old GA, where pack type could be same)
                # with released_tkn - prefer last option.
                package_dis = package.filter(tku_type__exact='released_tkn')
                if package_dis:
                    package = package_dis
                packages.update({f'step_{step}': package})
        # Mode to install TKU simply.
        else:
            log.info(f"{_LH_} Will install TKU in Custom mode self.package_types: {self.package_types}")
            step = 0
            for package_type in self.package_types:
                step += 1
                package = TkuPackages.objects.filter(package_type__exact=package_type)
                # If query return anything other (probably old GA, where pack type could be same)
                # with released_tkn - prefer last option.
                # TODO: Add development way
                if self.development:
                    pass
                else:
                    package_dis = package.filter(tku_type__exact='released_tkn')
                    if package_dis:
                        package = package_dis
                packages.update({f'step_{step}': package})

        log.info(f"{_LH_}Selected packages for test in mode: {self.test_mode}")

        self.packages = packages
        return packages

    def select_addm(self):
        """
        Select addm set to install TKU or single package by group name.
        If there is no 'addm_group' provided, then it probably a test override.
        Otherwise we don't select anything and fail the routine.
        """
        if self.addm_group:
            addm_set = AddmDev.objects.all()
            self.addm_set = addm_set.filter(addm_group__exact=self.addm_group, disables__isnull=True).values()
        else:
            log.debug("Using addm set from test call.")
        if self.addm_set:
            self.addm_set = self.addm_set.order_by('addm_group').values()
        else:
            msg = "Addm set has not selected. It should be selected by passing addm_group argument, " \
                  "or in octotest overriding the query" \
                  "Stop the routine now."
            log.error(msg)
            subject = f"UploadTaskPrepare | select_addm | Fail!"
            body = f"ADDM group: {self.addm_group}, test mode: {self.test_mode}, user: {self.user_name}, {msg}"
            self.mail(t_kwargs=dict(subject=subject, body=body, send_to=[self.user_email]))
            raise Exception(msg)

    def tku_run_steps(self):
        """ Previously composed dict of 'step_n = TKU' now initiates runs
            Each 'step = package' instance initiate one iteration:
        """
        for step_k, packages_v in self.packages.items():
            log.info(f"{_LH_}Processing packages step by step: {step_k}")
            # Power on machines for upload test or check online:
            self.vcenter_prepare(mode='powerOn')
            # Task for upload test prep if needed (remove older TKU, prod content, etc)
            self.addm_prepare(step_k=step_k)
            # Task for unzip packages on selected each ADDM from ADDM Group
            self.package_unzip(step_k=step_k, packages_from_step=packages_v)
            # Task for install TKU from unzipped packages for each ADDM from selected ADDM group
            self.tku_install(step_k=step_k, packages_from_step=packages_v)

    def vcenter_prepare(self, mode):
        """
        TBA: Add vCenter operations for: power on, snapshot revert.
        But do not mess with addm prep function, as this is only for each addm host itself.
        Wait until this task is finished or just stack next tasks to addm_group worker.
        """
        # log.debug(f'Using addm set: {self.addm_set} to run vCenter procedures based on VM ids.')
        modes = {
            'powerOn': 'pathToPowerOnProcedure',
            'snapRevert': 'pathToSnapshotReveringProcedure',
            'powerOff': 'pathToPowerOffProcedure'
        }

    def addm_prepare(self, step_k):
        """
        Upload test initial step, prepare ADDM before install TKU.
        It could be - removing old TKU, product content, restart services.
        """
        options = ''

        # TODO: Maybe move this to upload_preparations? OR to test utils?
        if self.test_mode == 'fresh' and step_k == 'step_1':
            self.vcenter_prepare(mode='snapRevert')
            options = dict(test_mode='fresh')  # 1st step is always fresh
            log.info(f"{_LH_} TKU Mode: {self.test_mode}, {step_k} - TKU wipe and prod content delete!")

        elif self.test_mode == 'update' and step_k == 'step_1':
            options = dict(test_mode='fresh')  # 1st step is always fresh
            log.info(f"{_LH_} TKU Mode: {self.test_mode}, {step_k} - TKU wipe and prod content delete!")

        elif self.test_mode == 'step' and step_k == 'step_1':
            options = dict(test_mode='step')  # It can be not fresh, because we install one by one
            log.info(f"{_LH_} TKU Mode: {self.test_mode}, {step_k} - will install over previous TKU !")

        elif self.test_mode == 'tideway_content' or self.test_mode == 'tideway_devices':
            options = dict(test_mode=self.test_mode)
            log.info(f"{_LH_} TKU Mode: {self.test_mode}, {step_k} - Will delete '{self.test_mode}'!")

        else:
            log.debug(f"{_LH_} TKU Mode: {self.test_mode}, {step_k} - no preparations.")

        if options:
            for addm_group, addm_items in groupby(self.addm_set, itemgetter('addm_group')):
                options.update(addm_items=addm_items, addm_group=addm_group, step_k=step_k, user_email=self.user_email,
                               fake_run=self.fake_run)
                subject = f"UploadTaskPrepare | addm_prepare | {self.test_mode} | {addm_group} | {step_k}"
                log.info(f"<=addm_prepare=> Actually start task: {subject}")
                body = f"ADDM group: {addm_group}, test mode: {self.test_mode}, user: {self.user_name}, step_k: {step_k}, "
                self.mail(t_args=[f"UploadTaskPrepare.addm_prepare"],
                          t_kwargs=dict(subject=subject, body=body, send_to=[self.user_email]),
                          t_routing_key=f"{addm_group}.UploadTaskPrepare.TSupport.t_short_mail",
                          t_queue=f'{addm_group}@tentacle.dq2')
                # New approach:
                results = UploadTestExec().upload_preparations(**options)
                self.tasks_added.append(results)

    def package_unzip(self, step_k, packages_from_step):
        """
        Make task with threading for each ADDM in selected group.
        Task run addm unzip routine selecting zips for each addm version and saving files in /usr/tideway/TEMP.
        It will remove all content before!
        :param step_k:
        :param packages_from_step:
        :return:
        """
        for addm_group, addm_items in groupby(self.addm_set, itemgetter('addm_group')):
            packs = packages_from_step.values('tku_type', 'package_type', 'zip_file_name', 'zip_file_path')
            subject = f"UploadTaskPrepare | t_upload_unzip | {self.test_mode} | {addm_group} | {step_k}"
            log.info(f"<=package_unzip=> Actually start task: {subject}")
            body = f"ADDM group: {addm_group}, test mode: {self.test_mode}, user: {self.user_name}, step_k: {step_k}, " \
                   f"packages: {list(packs)}"
            self.mail(t_args=[f"UploadTaskPrepare.package_unzip"],
                      t_kwargs=dict(subject=subject, body=body, send_to=[self.user_email]),
                      t_routing_key=f"{addm_group}.UploadTaskPrepare.TSupport.t_short_mail",
                      t_queue=f'{addm_group}@tentacle.dq2')
            task = Runner.fire_t(TUploadExec.t_upload_unzip,
                                 fake_run=self.fake_run, to_sleep=2, to_debug=True,
                                 t_queue=f"{addm_group}@tentacle.dq2",
                                 t_args=[f"UploadTaskPrepare;task=t_upload_unzip;test_mode={self.test_mode};"
                                         f"addm_group={addm_group};user={self.user_name}"],
                                 t_kwargs=dict(addm_items=addm_items, addm_group=addm_group,
                                               test_mode=self.test_mode, step_k=step_k,
                                               packages=packages_from_step, user_email=self.user_email, development=self.development),
                                 t_routing_key=f"{addm_group}.TUploadExec.package_unzip.TUploadExec.t_upload_unzip")
            self.tasks_added.append(task)

    def tku_install(self, step_k, packages_from_step):
        """ Install previously unzipped TKU from /usr/tideway/TEMP/*.zip """
        for addm_group, addm_items in groupby(self.addm_set, itemgetter('addm_group')):
            packs = packages_from_step.values('tku_type', 'package_type', 'zip_file_name', 'zip_file_path')
            subject = f"UploadTaskPrepare | t_tku_install | {self.test_mode} | {addm_group} | {step_k}"
            log.info(f"<=tku_install=> Actually start task: {subject}")
            body = f"ADDM group: {addm_group}, test mode: {self.test_mode}, user: {self.user_name}, step_k: {step_k}, " \
                   f"packages: {list(packs)}, package_detail: {self.package_detail}"
            self.mail(t_args=[f"UploadTaskPrepare.tku_install"],
                      t_kwargs=dict(subject=subject, body=body, send_to=[self.user_email]),
                      t_routing_key=f"{addm_group}.UploadTaskPrepare.TSupport.t_short_mail",
                      t_queue=f'{addm_group}@tentacle.dq2')
            task = Runner.fire_t(TUploadExec.t_tku_install,
                                 fake_run=self.fake_run, to_sleep=2, to_debug=True,
                                 t_queue=f"{addm_group}@tentacle.dq2",
                                 t_args=[f"UploadTaskPrepare;task=t_tku_install;test_mode={self.test_mode};"
                                         f"addm_group={addm_group};user={self.user_name}"],
                                 t_kwargs=dict(addm_items=addm_items, addm_group=addm_group,
                                               test_mode=self.test_mode, step_k=step_k,
                                               packages=packages_from_step, package_detail=self.package_detail,
                                               user_email=self.user_email),
                                 t_routing_key=f"{addm_group}.TUploadExec.t_tku_install.TUploadExec.t_tku_install")
            self.tasks_added.append(task)

            # When finished - last task for upload status update:
            if self.tku_type == 'ga_candidate':
                log.info(f"Send email of upload result for {self.tku_type}")
                # digests.TKUEmailDigest.upload_daily_fails_warnings
                task = Runner.fire_t(MailDigests.t_upload_digest,
                                     fake_run=self.fake_run, to_sleep=2, to_debug=True,
                                     t_queue=f"{addm_group}@tentacle.dq2",
                                     t_args=[f"MailDigests.t_upload_digest;task=t_tku_install;test_mode={self.test_mode};"
                                             f"addm_group={addm_group};user={self.user_name}"],
                                     t_kwargs=dict(status='everything',
                                                   tku_type=self.tku_type,
                                                   fake_run=self.fake_run),
                                     t_routing_key=f"{addm_group}.TUploadExec.t_tku_install.MailDigests.t_upload_digest")
                self.tasks_added.append(task)

            elif self.tku_type == 'tkn_main_continuous' or self.tku_type == 'tkn_ship_continuous':
                log.info(f"Send email of upload result for {self.tku_type}")
                # digests.TKUEmailDigest.upload_daily_fails_warnings
                task = Runner.fire_t(MailDigests.t_upload_digest,
                                     fake_run=self.fake_run, to_sleep=2, to_debug=True,
                                     t_queue=f"{addm_group}@tentacle.dq2",
                                     t_args=[f"MailDigests.t_upload_digest;task=t_tku_install;test_mode={self.test_mode};"
                                             f"addm_group={addm_group};user={self.user_name}"],
                                     t_kwargs=dict(status='status',
                                                   tku_type=self.tku_type,
                                                   fake_run=self.fake_run),
                                     t_routing_key=f"{addm_group}.TUploadExec.t_tku_install.MailDigests.t_upload_digest")
                self.tasks_added.append(task)


    def mail(self, t_kwargs, t_queue=None, t_args=None, t_routing_key=None):
        if not t_args:
            t_args = 'UploadTaskPrepare.mail'
        if not t_routing_key:
            t_routing_key = 'UploadTaskPrepare.TSupport.t_short_mail'
        if not t_queue:
            t_queue = 'w_routines@tentacle.dq2'
        if not self.silent:
            task = Runner.fire_t(TSupport.t_short_mail,
                                 fake_run=self.fake_run, to_sleep=2, to_debug=True,
                                 t_queue=t_queue, t_args=[t_args], t_kwargs=t_kwargs, t_routing_key=t_routing_key)
            self.tasks_added.append(task)
        log.debug(f"Silent mode, mail don't sending: {t_kwargs.get('subject', 'subject')}")

    @staticmethod
    def debug_unpack_qs(packages):
        for step_k, step_package in packages.items():
            for pack in step_package:
                log.info(f'{step_k} package: {pack.tku_type} -> {pack.package_type} addm: {pack.addm_version} zip: {pack.zip_file_name} ')
