from __future__ import absolute_import, unicode_literals

import logging
from itertools import groupby
from operator import itemgetter
# noinspection PyUnresolvedReferences
from typing import Dict, List, Any

from celery.utils.log import get_task_logger
from django.db.models import Max, QuerySet

from octo.helpers.tasks_helpers import exception
from octo.helpers.tasks_oper import TasksOperations
from octo.helpers.tasks_run import Runner
# Celery
from octo.octo_celery import app

from octo_adm.tasks import TaskVMService
from octo.tasks import TSupport

from octo_tku_upload.digests import TKUEmailDigest
from octo_tku_upload.models import TkuPackagesNew as TkuPackages
from octo_tku_upload.test_executor import UploadTestExec
from run_core.local_operations import LocalDownloads
from run_core.models import AddmDev, UploadTaskPrepareLog
from run_core.models import Options

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
              soft_time_limit=HOURS_2, task_time_limit=HOURS_2)
    @exception
    def t_upload_routines(t_tag, **kwargs):
        """
        Can run routines tasks as test methods from unit test case class.
        Reflects external changes to to test file without reload/restart.
        :param t_tag:
        :param kwargs: dict(test_method, test_class, test_module)
        :return:
        """
        log.info(f"<=t_upload_routines=> Running task {t_tag} {kwargs}")
        tsk = TestCases(**kwargs)
        routine = tsk.runner()
        return True

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TRoutine.t_routine_tku_upload_test_new',
              soft_time_limit=HOURS_2, task_time_limit=HOURS_2)
    @exception
    def t_upload_test(t_tag, **kwargs):
        """General task for upload test"""
        return UploadTaskPrepare(**kwargs).run_tku_upload()

    @staticmethod
    @app.task(queue='w_parsing@tentacle.dq2',
              soft_time_limit=HOURS_2, task_time_limit=HOURS_2)
    @exception
    def t_tku_sync(t_tag, **kwargs):
        """Sync TKU Packages with WGET"""
        return LocalDownloads().wget_tku_build_hub_option(**kwargs)

    @staticmethod
    @app.task(queue='w_parsing@tentacle.dq2', routing_key='parsing.TUploadExec.t_parse_tku',
              soft_time_limit=MIN_40, task_time_limit=MIN_90)
    @exception
    def t_parse_tku(t_tag, **kwargs):
        """Parse synced TKU packages in local FS after WGET"""
        log.debug("Tag: %s, kwargs %s", t_tag, kwargs)
        return LocalDownloads().only_parse_tku(**kwargs)

    @staticmethod
    @app.task(soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_upload_unzip(t_tag, **kwargs):
        """Unzip TKU packages on selected ADDMs into TEMP folder"""
        return UploadTestExec().upload_unzip_threads(**kwargs)

    @staticmethod
    @app.task(soft_time_limit=HOURS_2, task_time_limit=HOURS_2)
    @exception
    def t_tku_install(t_tag, **kwargs):
        """ Execute TKU install command after TKU packages were unzipped in TEMP folder."""
        return UploadTestExec().install_tku_threads(**kwargs)

    @staticmethod
    @app.task(soft_time_limit=MIN_10, task_time_limit=MIN_20,
              queue='w_routines@tentacle.dq2', routing_key='routines.MailDigests.t_upload_digest')
    @exception
    def t_upload_digest(t_tag, **kwargs):
        log.info(f"Task send email: {t_tag}")
        return TKUEmailDigest.upload_daily_fails_warnings(**kwargs)


class TKUSignalExecCases:

    @staticmethod
    def test_exec_on_change(sender, instance, created, **kwargs):
        # m_upload = Options.objects.get(option_key__exact='mail_recipients.upload_test')
        # self.m_upload = m_upload.option_value.replace(' ', '').split(',')
        log.info(f"<=Signal=> TKU Save => sender: {sender}; instance: {instance}; created: {created}; kwargs: {kwargs}")
        # Only run ONCE for single TKU Package as trigger:

        if instance.tku_name == 'Extended-Data-Pack' and instance.zip_type == 'edp' and instance.addm_version == '12.0':
            log.info(f"<=Signal=> TKU Trigger for build: {instance.tku_name} and {instance.zip_type} and {instance.addm_version} ")
            if instance.tku_type == 'ga_candidate':
                # If GA - run test009_release_ga_upgrade_and_fresh
                test_key = 'release_ga_upgrade_and_fresh'
                log.info(f"<=Signal=> Running TKU Upload test {test_key} for {instance.tku_type}")
            elif instance.tku_type == 'tkn_main_continuous':
                # If main continuous: run test007_tkn_main_continuous_fresh
                test_key = 'continuous_tkn_main_fresh'
                log.info(f"<=Signal=> Running TKU Upload test {test_key} for {instance.tku_type}")

            # TODO: Add ship_upgrade_and_fresh
            elif instance.tku_type == 'tkn_ship_continuous':
                # If ship continuous: run test008_tkn_ship_continuous_fresh
                test_key = 'continuous_tkn_ship_fresh'
                log.info(f"<=Signal=> Running TKU Upload test {test_key} for {instance.tku_type}")
            else:
                test_key = None
                log.debug(f'<=Signal=> No Automatic Upload tests for {instance.tku_type}')
                return f'No Automatic Upload tests for {instance.tku_type}'

            if instance.tku_type:
                kw_options = dict(
                    test_key=test_key,
                )
                t_tag = f'tag=t_upload_test;user_name=Cron;test_method={test_key}'
                t_queue = 'w_routines@tentacle.dq2'
                t_routing_key = 'TKUSignalExecCases.tku_install_test.TUploadExec.t_upload_routines'
                Runner.fire_t(TUploadExec.t_upload_routines,
                              fake_run=kwargs.get('fake_run', False),
                              args=[t_tag],
                              t_kwargs=kw_options,
                              t_queue=t_queue,
                              t_routing_key=t_routing_key)
            else:
                log.debug(f"<=Signal=> TKU Save - Not an : {instance}")


class UploadTaskPrepare:

    def __init__(self, *args, **kwargs):
        super(UploadTaskPrepare, self).__init__()
        # Initial view requests:
        self.data = kwargs
        # Assign generated context for further usage:
        self.user_name = self.data.get('user_name')
        self.user_email = self.data.get('user_email')
        self.tku_wget = self.data.get('tku_wget', None)
        self.test_mode = self.data.get('test_mode', 'custom')
        self.tku_type = self.data.get('tku_type', None)  # Assign TKU type based on packs.tku_type
        self.addm_group = self.data.get('addm_group', None)
        self.package_detail = self.data.get('package_detail', None)
        self.test_key = self.data.get('test_key', None)
        # Define fake run:
        self.fake_run = False
        # Internal statuses:
        self.silent = False
        # ADDM VM Snapshot:
        self.revert_snapshot = False

        self.package_types = ''
        self.packages = dict()
        self.addm_set = AddmDev.objects.all()
        # To ignore filter packages by ADDM version during unzip func
        self.development = False
        # Current status args:
        self.tku_downloaded = False
        self.addm_group_l = ''

    def run_case(self):
        """
        Simple run case.
        :return:
        """
        log.info("<=UploadTaskPrepare=> Running case!")
        self.fake_run_f()
        self.silent_run()
        self.vm_snap()
        self.run_tku_upload()

    def fake_run_f(self):
        """For debug purposes, just run all tasks as fake_task with showing all inputs and outputs: args, kwargs."""
        if self.data.get('fake_run'):
            self.fake_run = True
        if self.fake_run:
            log.debug(f"'<=UploadTaskPrepare=>' Fake run = {self.fake_run}")

    def silent_run(self):
        """Indicates when do not send any mails. """
        if self.data.get('silent'):
            self.silent = True
        if self.silent:
            log.debug(f"'<=UploadTaskPrepare=>' Silent run = {self.silent}")

    def vm_snap(self):
        """For debug purposes, just run all tasks as fake_task with showing all inputs and outputs: args, kwargs."""
        if self.data.get('revert_snapshot'):
            self.revert_snapshot = True
        if self.revert_snapshot:
            log.debug(f"'<=UploadTaskPrepare=>' revert_snapshot = {self.fake_run}")

    def run_tku_upload(self):
        # 0. Init test mail?
        UploadTaskPrepareLog(subject=f"<=START=> Init routine | {self.test_mode} {self.test_key if self.test_key else ''}",
                             details=f"Upload test routine started! test_key: {self.test_key}, test mode: {self.test_mode}, tku_type: {self.tku_type}, user: {self.user_name}").save()
        # 1. Select ADDMs for test:
        self.select_addm()
        # 1.1 ADDM VM Prepare
        self.vcenter_prepare()
        # 2. Refresh local TKU Packages:
        self.wget_run()
        # 3. Select TKU for test run.
        self.select_pack_modes()
        # 4. For each package&addm version do SOMETHING:
        self.tku_run_steps()

    def wget_run(self):
        if self.tku_wget:
            UploadTaskPrepareLog(subject=f"WGet init task | {self.test_mode} {self.tku_type if self.tku_type else ''}",
                                 details=f"WGET Run! test mode: {self.test_mode}, tku_type: {self.tku_type}, user: {self.user_name}").save()
            task = Runner.fire_t(TUploadExec.t_tku_sync,
                                 fake_run=self.fake_run,
                                 t_kwargs=dict(tku_type=self.tku_type), t_args=['tag=t_tku_sync;'],
                                 t_queue='w_parsing@tentacle.dq2')
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

    @staticmethod
    def select_latest_continuous(tkn_branch):
        package_type = TkuPackages.objects.filter(tku_type__exact=tkn_branch + '_continuous').aggregate(
            Max('package_type'))
        return package_type['package_type__max']

    @staticmethod
    def select_latest_ga():
        package_type = TkuPackages.objects.filter(tku_type__exact='ga_candidate').aggregate(Max('package_type'))
        return package_type['package_type__max']

    @staticmethod
    def select_latest_ship():
        package_type = TkuPackages.objects.filter(tku_type__exact='tkn_ship_continuous').aggregate(Max('package_type'))
        return package_type['package_type__max']

    @staticmethod
    def select_latest_released():
        package_type = TkuPackages.objects.filter(tku_type__exact='released_tkn').aggregate(Max('package_type'))
        return package_type['package_type__max']

    @staticmethod
    def select_any_amount_of_packages():
        package_type = TkuPackages.objects.filter(tku_type__exact='addm_released',
                                                  addm_version__exact='11.3').aggregate(Max('package_type'))
        return package_type['package_type__max']

    @staticmethod
    def select_tku_type(tku_type):
        package_type = TkuPackages.objects.filter(tku_type__exact=tku_type).aggregate(
            Max('package_type'))
        return package_type['package_type__max']

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
            log.info(f"'<=UploadTaskPrepare=>' Will install TKU in UPDATE mode.")

            # 1st step - use previously released package:
            released_tkn = TkuPackages.objects.filter(
                tku_type__exact='released_tkn').aggregate(Max('package_type'))
            package = TkuPackages.objects.filter(
                tku_type__exact='released_tkn',
                package_type__exact=released_tkn['package_type__max'])
            packages.update(step_1=package)

            # TODO: Add get logic for same as GA but for SHIP build
            # 2nd step - use GA candidate package:
            if self.tku_type == 'tkn_ship_continuous':
                ga_candidate = TkuPackages.objects.filter(
                    tku_type__exact='tkn_ship_continuous').aggregate(Max('package_type'))
                package = TkuPackages.objects.filter(
                    tku_type__exact='tkn_ship_continuous',
                    package_type__exact=ga_candidate['package_type__max'])
                packages.update(step_2=package)
            else:
                ga_candidate = TkuPackages.objects.filter(
                    tku_type__exact='ga_candidate').aggregate(Max('package_type'))
                package = TkuPackages.objects.filter(
                    tku_type__exact='ga_candidate',
                    package_type__exact=ga_candidate['package_type__max'])
                packages.update(step_2=package)
        # Mode to install any TKU as fresh or step, one by one.
        elif self.test_mode == 'step' or self.test_mode == 'fresh':
            log.info(f"'<=UploadTaskPrepare=>'Install TKU in {self.test_mode} mode - {self.package_types}")
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
            log.info(f"'<=UploadTaskPrepare=>' Will install TKU in Custom mode self.package_types: {self.package_types}")
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

        log.info(f"'<=UploadTaskPrepare=>'Selected packages for test in mode: {self.test_mode}")

        self.packages = packages
        return packages

    def select_addm(self):
        """
        Select addm set to install TKU or single package by group name.
        If there is no 'addm_group' provided, then it probably a test override.
        Otherwise we don't select anything and fail the routine.
        """
        if self.addm_group:
            self.addm_set = self.addm_set.filter(addm_group__exact=self.addm_group, disables__isnull=True)
        else:
            log.debug("Using addm set from test call.")
        if not self.addm_set:
            msg = "Addm set has not selected. It should be selected by passing addm_group argument, " \
                  "or in octotest overriding the query" \
                  "Stop the routine now."
            log.critical(msg)
            UploadTaskPrepareLog(subject=f"ADDM Assigning init| Fail!",
                                 details=f"ADDM group: {self.addm_group}, test mode: {self.test_mode}, user: {self.user_name}, {msg}").save()
            raise Exception(msg)

    def tku_run_steps(self):
        """ Previously composed dict of 'step_n = TKU' now initiates runs
            Each 'step = package' instance initiate one iteration:
        """
        for step_k, packages_v in self.packages.items():
            log.info(f"'<=UploadTaskPrepare=>'Processing packages step by step: {step_k}")
            # Power on machines for upload test or check online:
            # Task for upload test prep if needed (remove older TKU, prod content, etc)
            self.addm_prepare(step_k=step_k)
            # Task for unzip packages on selected each ADDM from ADDM Group
            self.package_unzip(step_k=step_k, packages_from_step=packages_v)
            # Task for install TKU from unzipped packages for each ADDM from selected ADDM group
            self.tku_install(step_k=step_k, packages_from_step=packages_v)

    def vcenter_prepare(self):
        """
        TBA: Add vCenter operations for: power on, snapshot revert.
        But do not mess with addm prep function, as this is only for each addm host itself.
        Wait until this task is finished or just stack next tasks to addm_group worker.
        """
        # Revert snapshot - usually for alpha and only during GA, and then wait fr VMs to powerOn and start services
        # TODO: Check if each worker GET it's task!
        for addm_group, _ in groupby(self.addm_set.order_by('addm_group').values(), itemgetter('addm_group')):
            # addm_group = self.addm_set.first().addm_group
            addm_items = self.addm_set.filter(addm_group__exact=addm_group)
            if self.revert_snapshot:
                log.debug(f'VM Reverting snapshot, PowerOn VMs and occupy worker for 5 min: \n{self.addm_set}')
                # Taskinization:
                log.info(f"Adding task revert snapshot! Group {addm_group}; sing ADDMs: {addm_items}")
                Runner.fire_t(TaskVMService.t_vm_operation_thread,
                              fake_run=self.fake_run,
                              t_queue=f"{addm_group}@tentacle.dq2",
                              t_args=[f"UploadTaskPrepare;task=t_vm_operation_thread;operation_k=vm_revert_snapshot"],
                              t_kwargs=dict(addm_set=addm_items, operation_k='vm_revert_snapshot'),
                              t_routing_key=f"{addm_group}.UploadTaskPrepare.t_vm_operation_thread.vm_revert_snapshot")
                log.info(f"Adding task power On vms! Group {addm_group}; Using ADDMs: {addm_items}")
                Runner.fire_t(TaskVMService.t_vm_operation_thread,
                              fake_run=self.fake_run,
                              t_queue=f"{addm_group}@tentacle.dq2",
                              t_args=[
                                  f"UploadTaskPrepare.afterSnapshot;task=t_vm_operation_thread;operation_k=vm_power_on"],
                              t_kwargs=dict(addm_set=addm_items, operation_k='vm_power_on', t_sleep=60 * 15),
                              t_routing_key=f"{addm_group}.UploadTaskPrepare.t_vm_operation_thread.vm_power_on")
            # Otherwise check if machines aren't powered off - and power On if so
            else:
                log.info(f"VM Power on tasks, no snapshots reverting = {self.revert_snapshot}")
                log.info(f"Adding task power On vms! Group {addm_group}; Using ADDMs: {addm_items}")
                Runner.fire_t(TaskVMService.t_vm_operation_thread,
                              fake_run=self.fake_run,
                              t_queue=f"{addm_group}@tentacle.dq2",
                              t_args=[f"UploadTaskPrepare;task=t_vm_operation_thread;operation_k=vm_power_on"],
                              t_kwargs=dict(addm_set=addm_items, operation_k='vm_power_on', t_sleep=60 * 15),
                              t_routing_key=f"{addm_group}.UploadTaskPrepare.t_vm_operation_thread.vm_power_on")

    def addm_prepare(self, step_k):
        """
        Upload test initial step, prepare ADDM before install TKU.
        It could be - removing old TKU, product content, restart services.
        """
        options = ''

        if self.test_mode == 'fresh' and step_k == 'step_1':
            options = dict(test_mode='fresh')  # 1st step is always fresh
            log.info(f"'<=UploadTaskPrepare=>' TKU Mode: {self.test_mode}, {step_k} - TKU wipe and prod content delete!")

        elif self.test_mode == 'update' and step_k == 'step_1':
            options = dict(test_mode='fresh')  # 1st step is always fresh
            log.info(f"'<=UploadTaskPrepare=>' TKU Mode: {self.test_mode}, {step_k} - TKU wipe and prod content delete!")

        elif self.test_mode == 'step' and step_k == 'step_1':
            options = dict(test_mode='step')  # It can be not fresh, because we install one by one
            log.info(f"'<=UploadTaskPrepare=>' TKU Mode: {self.test_mode}, {step_k} - will install over previous TKU !")

        elif self.test_mode == 'tideway_content' or self.test_mode == 'tideway_devices':
            options = dict(test_mode=self.test_mode)
            log.info(f"'<=UploadTaskPrepare=>' TKU Mode: {self.test_mode}, {step_k} - Will delete '{self.test_mode}'!")

        else:
            log.debug(f"'<=UploadTaskPrepare=>' TKU Mode: {self.test_mode}, {step_k} - no preparations.")

        if options:
            for addm_group, _ in groupby(self.addm_set.order_by('addm_group').values(), itemgetter('addm_group')):
                addm_items = self.addm_set.filter(addm_group__exact=addm_group)
                assert isinstance(addm_items,
                                  QuerySet), f'ADDM Items should be a QuerySet in UploadTaskPrepare.addm_prepare; type {type(addm_items)}'
                options.update(
                    fake_run=self.fake_run,
                    addm_items=addm_items,
                    addm_group=addm_group,
                    step_k=step_k,
                    user_email=self.user_email
                )
                UploadTaskPrepareLog(
                    subject=f"ADDM Prepare init task | {self.test_mode} | {addm_group} | {step_k}",
                    details=f"ADDM group: {addm_group}, test mode: {self.test_mode}, user: {self.user_name}, step_k: {step_k}, ").save()
                # New approach: not task, because it produce other tasks for each operation:
                UploadTestExec().upload_preparations(**options)

    def package_unzip(self, step_k, packages_from_step):
        """
        Make task with threading for each ADDM in selected group.
        Task run addm unzip routine selecting zips for each addm version and saving files in /usr/tideway/TEMP.
        It will remove all content before!
        :param step_k:
        :param packages_from_step:
        :return:
        """
        for addm_group, _ in groupby(self.addm_set.order_by('addm_group').values(), itemgetter('addm_group')):
            addm_items = self.addm_set.filter(addm_group__exact=addm_group)
            assert isinstance(addm_items,
                              QuerySet), f'ADDM Items should be a QuerySet in UploadTaskPrepare.package_unzip; type {type(addm_items)}'
            packs = packages_from_step.values('tku_type', 'package_type', 'zip_file_name', 'zip_file_path')

            UploadTaskPrepareLog(
                subject=f"TKU Unzip init task | {self.test_mode} | {addm_group} | {step_k}",
                details=f"ADDM group: {addm_group}, test mode: {self.test_mode}, user: {self.user_name}, step_k: {step_k} packages: {list(packs)}").save()
            Runner.fire_t(TUploadExec.t_upload_unzip,
                          fake_run=self.fake_run,
                          t_queue=f"{addm_group}@tentacle.dq2",
                          t_args=[f"UploadTaskPrepare;task=t_upload_unzip;test_mode={self.test_mode};"
                                  f"addm_group={addm_group};user={self.user_name}"],
                          t_kwargs=dict(addm_items=addm_items, addm_group=addm_group,test_mode=self.test_mode,
                                        step_k=step_k, packages=packages_from_step, user_email=self.user_email,
                                        development=self.development),
                          t_routing_key=f"{addm_group}.TUploadExec.package_unzip.TUploadExec.t_upload_unzip")

    def tku_install(self, step_k, packages_from_step):
        """ Install previously unzipped TKU from /usr/tideway/TEMP/*.zip """
        self.tku_type = packages_from_step.first().tku_type
        # addm_set = self.addm_set.order_by('addm_group').values()
        # log.info(f"<=tku_install=> addm_set: {addm_set}")
        for addm_group, _ in groupby(self.addm_set.order_by('addm_group').values(), itemgetter('addm_group')):
            addm_items = self.addm_set.filter(addm_group__exact=addm_group)
            assert isinstance(addm_items,
                              QuerySet), f'ADDM Items should be a QuerySet in UploadTaskPrepare.tku_install; type {type(addm_items)}'
            packs = packages_from_step.values('tku_type', 'package_type', 'zip_file_name', 'zip_file_path', 'release',
                                              'zip_file_md5_digest')
            UploadTaskPrepareLog(
                subject=f"TKU Install init task | {self.test_mode} | {addm_group} | {step_k}",
                details=f"ADDM group: {addm_group}, test mode: {self.test_mode}, user: {self.user_name}, "
                        f"tku_type: {self.tku_type} step_k: {step_k} packages: {list(packs)}, "
                        f"package_detail: {self.package_detail}").save()
            Runner.fire_t(TUploadExec.t_tku_install,
                          fake_run=self.fake_run,
                          t_queue=f"{addm_group}@tentacle.dq2",
                          t_args=[f"UploadTaskPrepare;task=t_tku_install;test_mode={self.test_mode};"
                                  f"addm_group={addm_group};user={self.user_name}"],
                          t_kwargs=dict(addm_items=addm_items, addm_group=addm_group,
                                        test_mode=self.test_mode, step_k=step_k,
                                        packages=packages_from_step, package_detail=self.package_detail,
                                        silent=self.silent, user_email=self.user_email),
                          t_routing_key=f"{addm_group}.TUploadExec.t_tku_install.TUploadExec.t_tku_install")

            # When finished - last task for upload status update:
            """
            Send email if following conditions are True:
            if test_mode: fresh AND step_k: step_1 OR  test_mode: update AND step_k: step_2
            if 'tku_type': 'ga_candidate' - get it from current packages_from_step - first any package from step
            if 'tku_type': 'tkn_main_continuous' or 'tkn_ship_continuous' - get it from current packages_from_step - first any package from step
            """
            log.info(f"Options before mail send \n test_mode: {self.test_mode} \ntku_type: {self.tku_type}"
                     f"\nstep_k: {step_k} \npackage_detail: {self.package_detail}")
            if self.tku_type == 'ga_candidate':
                log.info(f"Send email of upload result for {self.tku_type}")
                # digests.TKUEmailDigest.upload_daily_fails_warnings
                Runner.fire_t(TUploadExec.t_upload_digest,
                              fake_run=self.fake_run,
                              t_queue=f"{addm_group}@tentacle.dq2",
                              t_args=[
                                  f"MailDigests.t_upload_digest;task=t_tku_install;test_mode={self.test_mode};"
                                  f"addm_group={addm_group};user={self.user_name}"],
                              t_kwargs=dict(
                                  tku_type=self.tku_type,
                                  fake_run=self.fake_run
                              ),
                              t_routing_key=f"{addm_group}.TUploadExec.t_tku_install.MailDigests.t_upload_digest")

            elif self.tku_type == 'tkn_main_continuous' or self.tku_type == 'tkn_ship_continuous':
                # Do not send email during small install of prod cont or devices
                if not self.package_detail:
                    log.info(f"Send email of upload result for {self.tku_type}")
                    # digests.TKUEmailDigest.upload_daily_fails_warnings`
                    Runner.fire_t(TUploadExec.t_upload_digest,
                                  fake_run=self.fake_run,
                                  t_queue=f"{addm_group}@tentacle.dq2",
                                  t_args=[
                                      f"MailDigests.t_upload_digest;task=t_tku_install;test_mode={self.test_mode};"
                                      f"addm_group={addm_group};user={self.user_name}"],
                                  t_kwargs=dict(
                                      tku_type=self.tku_type,
                                      fake_run=self.fake_run
                                  ),
                                  t_routing_key=f"{addm_group}.TUploadExec.t_tku_install.MailDigests.t_upload_digest")
                else:
                    log.info("<=UploadTaskPrepare=> Do not send test result email during package/device install")
            else:
                log.info(
                    f"<=UploadTaskPrepare=> Do not send test result email tku_type {self.tku_type} package_detail {self.package_detail}")

            """
            Power Off ADDM VMs after latest step reached: ga tku and fresh test mode should be always the last step!
            """
            if self.tku_type == 'ga_candidate' and self.test_mode == 'fresh':
                log.info("Adding task occupy worker, for 15 min! before power Off vms!")
                Runner.fire_t(TSupport.t_occupy_w,
                              fake_run=self.fake_run,
                              t_queue=f"{addm_group}@tentacle.dq2",
                              t_args=[f"UploadTaskPrepare;task=t_occupy_w;WaitBeforePowerOffVMs", 60 * 30],
                              t_kwargs=dict(addm_set=self.addm_set, addm_group=addm_group),
                              t_routing_key=f"{addm_group}.TUploadExec.t_tku_install.TUploadExec.t_tku_install")
                log.info("Adding task Power off VMs")
                Runner.fire_t(TaskVMService.t_vm_operation_thread,
                              fake_run=self.fake_run,
                              t_queue=f"{addm_group}@tentacle.dq2",
                              t_args=[f"UploadTaskPrepare;task=t_vm_operation_thread;operation_k=vm_shutdown_guest"],
                              t_kwargs=dict(addm_set=self.addm_set, operation_k='vm_shutdown_guest', t_sleep=60 * 5),
                              t_routing_key=f"{addm_group}.UploadTaskPrepare.t_vm_operation_thread.vm_shutdown_guest")
            else:
                log.info(f"<=UploadTaskPrepare=> Do not power Off VMs, when it's not a GA install.")

    @staticmethod
    def _debug_unpack_qs(packages):
        for step_k, step_package in packages.items():
            for pack in step_package:
                log.info(
                    f'{step_k} package: {pack.tku_type} -> {pack.package_type} addm: {pack.addm_version} zip: {pack.zip_file_name} ')


class TestCases(UploadTaskPrepare):

    def __init__(self, *args, **kwargs):
        super(TestCases, self).__init__()
        self.assign_variables(*args, **kwargs)

    def assign_variables(self, *args, **kwargs):
        log.debug(f"TestCases assign_variables args: {args}")
        log.debug(f"TestCases assign_variables kwargs: {kwargs}")
        # Assign generated context for further usage:
        self.user_name = kwargs.get('user_name')
        self.user_email = kwargs.get('user_email')

        self.tku_wget = kwargs.get('tku_wget', None)
        self.test_mode = kwargs.get('test_mode', 'custom')
        self.tku_type = kwargs.get('tku_type', None)  # Assign TKU type based on packs.tku_type
        self.addm_group = kwargs.get('addm_group', None)
        self.package_detail = kwargs.get('package_detail', None)
        self.test_key = kwargs.get('test_key', None)

    def test_keys(self):
        """
        Execute task operations or return task operation status.
        If no args passed - return operations dict to show user all possible variants.

        :return:
        """
        operations = dict(
            product_content_tkn_main_update=self.test001_product_content_update_tkn_main,
            product_content_tkn_ship_update=self.test002_product_content_update_tkn_ship,
            tideway_devices_tkn_main_update=self.test003_tideway_devices_update_tkn_main,
            tideway_devices_tkn_ship_update=self.test004_tideway_devices_update_tkn_ship,

            release_ga_upgrade_and_fresh=self.test009_release_ga_upgrade_and_fresh,
            release_ga_upgrade=self.test005_release_ga_upgrade,
            release_ga_fresh=self.test006_release_ga_fresh,

            ship_upgrade_and_fresh=self.test020_ship_upgrade_and_fresh,
            ship_upgrade=self.test018_ship_cont_upgrade,
            ship_fresh=self.test019_ship_cont_fresh,

            continuous_tkn_main_fresh=self.test007_tkn_main_continuous_fresh,
            continuous_tkn_ship_fresh=self.test008_tkn_ship_continuous_fresh,

            product_content_tkn_main_update_beta=self.test010_product_content_update_tkn_main_beta,
            product_content_tkn_ship_update_echo=self.test011_product_content_update_tkn_ship_echo,
            product_content_main_options_addm_update=self.test012_product_content_update_main_options_addm,
            product_content_ship_options_addm_update=self.test013_product_content_update_ship_options_addm,
            product_content_main_continuous_update=self.test014_product_content_update_main_continuous,
            product_content_main_latest_update=self.test015_product_content_update_main_latest,

            tku_install_main_continuous=self.test016_tku_install_main_continuous,
            tku_install_main_latest=self.test017_tku_install_main_latest,

            TEST_tkn_main_continuous_fresh=self.test999_tkn_main_continuous_fresh,
            jenkins_ship_cont=self.test1000_jenkins_tkn_ship_cont,
        )
        if self.test_key:
            log.info(f"The test_key were provided - will run case based on key :{self.test_key}!")
            actions = operations.get(self.test_key, 'No such operation key')
        else:
            # If no test key provided - use kwargs to run test:
            log.warning("No test_key were provided - will run case based on args, kwargs!")
            actions = self.run_case
        return actions

    def runner(self):
        # Get user and mail:
        log.info(f"<=TestCases=> Prepare tests for user: {self.user_name} - {self.user_email}")
        run_test = self.test_keys()
        log.info(f"About to run: {run_test}")
        run_test()
        return True

    def test001_product_content_update_tkn_main(self):
        """
        Product Content Update tkn_main
        Install tideway_content, except ADDM where continuous build installs
        """
        self.addm_group_l = Options.objects.get(option_key__exact='night_workers.tkn_main').option_value.replace(' ', '').split(',')
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=self.addm_group_l,
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test002_product_content_update_tkn_ship(self):
        """
        Product Content Update tkn_ship
        Install tideway_content, except ADDM where continuous build installs
        """
        self.addm_group_l = Options.objects.get(option_key__exact='night_workers.tkn_ship').option_value.replace(' ', '').split(',')
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=self.addm_group_l,
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test003_tideway_devices_update_tkn_main(self):
        """
        Tideway Devices Update tkn_main
        Update tideway devices rpm for branch main, for all listed ADDMs: ['beta']
        :return:
        """
        self.addm_group_l = Options.objects.get(option_key__exact='night_workers.tkn_main').option_value.replace(' ', '').split(',')
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_devices'
        self.package_detail = 'tideway-devices'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=self.addm_group_l,
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test004_tideway_devices_update_tkn_ship(self):
        """
        Tideway Devices Update tkn_ship
        Update tideway devices RPMs for branch ship, for all listed ADDMs: ['echo']
        :return:
        """
        self.addm_group_l = Options.objects.get(option_key__exact='night_workers.tkn_ship').option_value.replace(' ', '').split(',')
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_devices'
        self.package_detail = 'tideway-devices'
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=self.addm_group_l,
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test005_release_ga_upgrade(self):
        """
        RELEASE GA Upgrade mode
        Install TKU release GA in UPGRADE mode. Run BEFORE fresh routine! ADDM: ['alpha'].
        This group is locked only for upload tests! Cron 24-30 days.
        :return:
        """
        # self.tku_wget = True
        self.test_mode = 'update'
        self.revert_snapshot = True
        # Update mode will select packages for upgrade test by itself
        # previous = self.select_latest_released()
        # current_ga = self.select_latest_ga()
        # Update mode will select packages for upgrade test by itself
        # package_types=[previous, current_ga],
        self.addm_set = self.addm_set.filter(
            addm_group__in=['alpha'],
            # addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test006_release_ga_fresh(self):
        """
        RELEASE GA Fresh mode
        Install TKU release GA in FRESH mode. Run BEFORE fresh routine! ADDM: ['alpha'].
        This group is locked only for upload tests! Cron 24-30 days.
        :return:
        """
        package_type = self.select_latest_ga()
        # self.tku_wget = True
        self.test_mode = 'fresh'
        self.revert_snapshot = True
        self.addm_set = self.addm_set.filter(
            addm_group__in=['alpha'],
            # addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.package_types = [package_type]
        self.run_case()

    def test007_tkn_main_continuous_fresh(self):
        """
        Continuous fresh tkn_main
        Install TKU from the continuous build for the main branch, on assigned ADDM ['beta'].
        Can be any ADDM group, but not the reserved for upload test.
        :return:
        """
        # TODO: Run this when WGET routine detects a new tkn_main_cont package by md5
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'fresh'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['beta'],
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test008_tkn_ship_continuous_fresh(self):
        """
        Continuous fresh tkn_ship
        Install TKU from the continuous build for the main branch, on assigned ADDM ['echo'].
        Can be any ADDM group, but not the reserved for upload test.
        Run 1-24 days - do not run during release rush, as there is no builds for this.
        :return:
        """
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'fresh'
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['echo'],
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test009_release_ga_upgrade_and_fresh(self):
        # self.tku_wget = True
        self.test005_release_ga_upgrade()
        self.test006_release_ga_fresh()

    def test010_product_content_update_tkn_main_beta(self):
        """
        Product Content Update tkn_main
        Install tideway_content, except ADDM where continuous build installs
        """
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['beta'],
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test011_product_content_update_tkn_ship_echo(self):
        """
        Product Content Update tkn_ship
        Install tideway_content, except ADDM where continuous build installs
        """
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['echo'],
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test012_product_content_update_main_options_addm(self):
        """
        Product Content Update tkn_main
        Install tideway_content, except ADDM where continuous build installs
        """
        self.addm_group_l = Options.objects.get(option_key__exact='night_workers.tkn_main').option_value.replace(' ', '').split(',')
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=self.addm_group_l,
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test013_product_content_update_ship_options_addm(self):
        """
        Product Content Update tkn_ship
        Install tideway_content, except ADDM where continuous build installs
        """
        self.addm_group_l = Options.objects.get(option_key__exact='night_workers.tkn_ship').option_value.replace(' ', '').split(',')
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=self.addm_group_l,
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test014_product_content_update_main_continuous(self):
        """ Usual branch is tkn_main, no ship alowed because there should be only released packages and VMs
        Install dev TKU packages for latest addm. (12.0 for example)"""
        self.addm_group_l = Options.objects.get(option_key__exact='night_workers.tkn_main').option_value.replace(' ', '').split(',')
        self.silent = True
        self.development = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_tku_type(tku_type='main_continuous')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=self.addm_group_l,
            # addm_group__in=['beta'],
            addm_v_int__in=['11.90'],
            disables__isnull=True).order_by('addm_group')
        print(self.addm_set)
        self.run_case()

    def test015_product_content_update_main_latest(self):
        """ Usual branch is tkn_main, no ship alowed because there should be only released packages and VMs
        Install dev TKU packages for latest addm. (12.0 for example)"""
        self.addm_group_l = Options.objects.get(option_key__exact='night_workers.tkn_main').option_value.replace(' ', '').split(',')
        self.silent = True
        self.development = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_tku_type(tku_type='main_latest')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=self.addm_group_l,
            # addm_group__in=['beta'],
            addm_v_int__in=['11.90'],
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test016_tku_install_main_continuous(self):
        """ Usual branch is tkn_main, no ship alowed because there should be only released packages and VMs
        Install dev TKU packages for latest addm. (12.0 for example)"""
        self.silent = True
        self.development = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'fresh'
        package_type = self.select_tku_type(tku_type='main_continuous')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['beta'],
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['fish_finger'],
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test017_tku_install_main_latest(self):
        """ Usual branch is tkn_main, no ship alowed because there should be only released packages and VMs
        Install dev TKU packages for latest addm. (12.0 for example)"""
        self.silent = True
        self.development = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'fresh'
        package_type = self.select_tku_type(tku_type='main_latest')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['beta'],
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['fish_finger'],
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test018_ship_cont_upgrade(self):
        """
        Ship Upgrade mode
        :return:
        """
        self.tku_type = 'tkn_ship_continuous'
        self.test_mode = 'update'
        self.revert_snapshot = True
        self.addm_set = self.addm_set.filter(
            addm_group__in=['alpha'],
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test019_ship_cont_fresh(self):
        """
        SHIP Fresh mode
        :return:
        """
        package_type = self.select_latest_ship()
        self.test_mode = 'fresh'
        self.revert_snapshot = True
        self.addm_set = self.addm_set.filter(
            addm_group__in=['alpha'],
            disables__isnull=True).order_by('addm_group')
        self.package_types = [package_type]
        self.run_case()

    def test020_ship_upgrade_and_fresh(self):
        self.test018_ship_cont_upgrade()
        self.test019_ship_cont_fresh()

    def test999_tkn_main_continuous_fresh(self):
        """
        test999_tkn_main_continuous_fresh

        :return:
        """
        self.fake_run = True
        self.silent = False
        self.revert_snapshot = True
        self.tku_wget = True
        self.test_mode = 'fresh'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['golf'],
            # addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['bobblehat'],
            disables__isnull=True).order_by('addm_group')
        log.debug("Kind a run case!")
        self.run_case()

    def test1000_jenkins_tkn_ship_cont(self):
        self.fake_run = True
        self.silent = True
        self.tku_wget = True
        self.test_mode = 'fresh'
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['golf'],
            # addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['bobblehat'],
            disables__isnull=True).order_by('addm_group')
        self.run_case()
