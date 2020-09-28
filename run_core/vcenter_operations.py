import os
import logging
import atexit
import ssl
# noinspection PyUnresolvedReferences
from django.db.models import QuerySet
from pyVim import connect
# noinspection PyUnresolvedReferences
from pyVmomi import vim
from pyVim.task import WaitForTask

from time import sleep
from time import time
from queue import Queue

from octo.config_cred import v_center_cred
from django.core.exceptions import ObjectDoesNotExist

from run_core.models import AddmDev

log = logging.getLogger("octo.octologger")
place = os.path.dirname(os.path.abspath(__file__))


class VCenterOperations:
    """

    """

    def __init__(self):
        # s = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        s = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        s.verify_mode = ssl.CERT_NONE  # disable our certificate checking for lab
        self.ssl = s
        self.service_instance = None
        self.content = None
        self.containerView = None
        self.container = None
        self.session_manager = None

        # Store connection here:
        self.vconnect()

        self.operations = dict(
            list_vms_update_db=self.list_vms_update_db,
            vm_create_snapshot=self.vm_create_snapshot,
            vm_revert_snapshot=self.vm_revert_snapshot,
            vm_power_on=self.vm_power_on,
            vm_power_off=self.vm_power_off,
            vm_shutdown_guest=self.vm_shutdown_guest,
            vm_soft_reboot=self.vm_soft_reboot,
            vm_reset=self.vm_reset,
            vm_config=self.vm_config,
        )

    def vconnect(self):
        """
        Connect VCenter and save connection:
        :return:
        """
        self.service_instance = connect.SmartConnect(
            host=v_center_cred['host_vc'],
            user=v_center_cred['VC_USER'],
            pwd=v_center_cred['VC_PWD'],
            sslContext=self.ssl)
        atexit.register(connect.Disconnect, self.service_instance)  # build disconnect logic

    def retrieve_content(self):
        """
        Get initial content
        :return:
        """
        self.content = self.service_instance.RetrieveContent()
        self.session_manager = self.content.sessionManager

    def root_container(self):
        """
        Get root
        :return:
        """
        self.retrieve_content()
        self.container = self.content.rootFolder  # starting point to look into
        log.info(f"container {self.container}")

    def get_content_vms(self):
        self.root_container()
        self.retrieve_content()

        recursive = True  # whether we should look into it recursively
        viewType = [vim.VirtualMachine]  # object types to look for
        log.info(f"viewType {viewType}")

        containerView = self.content.viewManager.CreateContainerView(self.container, viewType,
                                                                     recursive)  # create container view
        return containerView

    def threaded_operations(self, **kwargs):
        """
        Power On is always a default operation_k, if no key provided!
        :param kwargs:
        :return:
        """
        from threading import Thread
        addm_set = kwargs.get('addm_set')
        operation_k = kwargs.get('operation_k', None)
        t_sleep = kwargs.get('t_sleep', 60 * 10)
        vm_kwargs = kwargs.get('vm_kwargs', None)

        th_list = []
        th_out = []
        txt_out = ''
        ts = time()
        out_q = Queue()

        if not addm_set:
            return 'No ADDM set provided!'
        # if not isinstance(addm_set, QuerySet) and not isinstance(addm_set, AddmDev):
        #     raise Exception('ADDM set should be a QS of AddmDev model for VM operations!')

        for addm_item in addm_set:
            if self.service_instance:
                th_name = f'VCenterOperations.threaded_operations: {addm_item.addm_group} - {addm_item.addm_host} {addm_item.addm_ip}'
                args_d = dict(out_q=out_q, vm_obj=addm_item.octopusvm, vm_kwargs=vm_kwargs)
                try:
                    log.info(f"<=threaded_operations=> Run {operation_k}.")
                    cmd_th = Thread(target=self.operations[operation_k], name=th_name, kwargs=args_d)
                    cmd_th.start()
                    th_list.append(cmd_th)
                except Exception as e:
                    msg = f'Thread {th_name} fail with error: \n{e}'
                    log.error(msg)
                    raise Exception(msg)
            else:
                msg = f'VCenter Connection died! There is no service_instance!'
                log.error(msg)
                raise Exception(msg)

        for test_th in th_list:
            test_th.join()
            thread_out = out_q.get()
            th_out.append(thread_out)
            txt_out += f'\n\t{thread_out}'

        # Some times we need to sleep not occupying worker.
        # [{'vl-aus-tkudev-19': 'poweredOn'}, ]
        # [{'vl-aus-tkudev-39': 'skipped'}, ]
        if any('poweredOn' in vm.values() for vm in th_out):
            log.info(f'Any VM was powered On, will wait for {t_sleep} for services to start.')
            if t_sleep:
                sleep(t_sleep)

        if any('rebooted' in vm.values() for vm in th_out):
            log.info(f'Any VM was rebooted, will wait for {t_sleep} for services to start.')
            if t_sleep:
                sleep(t_sleep)

        if all('skipped' in vm.values() for vm in th_out):
            log.info('All VMs are skipping power ON! No sleep required.')

        output = {operation_k: th_out, 'time': time() - ts}
        # Do not show CMD out with too big data in it:
        txt_output = f'CMD:{operation_k}\nOutput:{txt_out}\nEST: {time() - ts}'
        log.info(f"VM Operation Output txt: {txt_output}")
        return output

    def list_vms_update_db(self, model=None, vm_model=None):
        containerView = self.get_content_vms()
        children = containerView.view
        all_vms = []
        for child in children:  # for each statement to iterate all names of VMs in the environment
            summary = child.summary
            if child.name:
                vm_info_all = dict(
                    vm_name=child.name,
                    parent_name=child.parent.name,
                    vm_id=summary.vm,
                    vm_name_str=summary.config.name,
                    vm_os=summary.config.guestFullName,
                    instanceUuid=summary.config.instanceUuid,
                    uptimeSeconds=summary.quickStats.uptimeSeconds,
                    bootTime=child.runtime.bootTime,
                )
                if child.snapshot:
                    vm_info_all.update(
                        currentSnapshot=child.snapshot.currentSnapshot,
                        rootSnapshotList=child.snapshot.rootSnapshotList,
                    )
                if child.resourcePool and hasattr(child.resourcePool, 'name'):
                    vm_info_all.update(pool_name=child.resourcePool.name, )
                all_vms.append(vm_info_all)

                if model and vm_model:
                    self.insert_update_addm_vm(vm=vm_info_all, model=model, vm_model=vm_model)

                log.info(f"VM Info: {vm_info_all}")
            else:
                log.info(f"Has no name: {child}")
        return all_vms

    @staticmethod
    def insert_update_addm_vm(vm, model, vm_model):
        related_addm = None
        try:
            related_addm = model.objects.get(addm_host__exact=vm['vm_name'])
        except ObjectDoesNotExist as e:
            log.info(f'VM is not in ADDM VMs, skip {vm["vm_name"]} {e}')
        if related_addm:
            log.info(f"Found ADDM VM! {related_addm}")
            octo_vm = vm_model(
                addm_name=related_addm,
                vm_name=vm['vm_name'],
                parent_name=vm.get('parent_name', None),
                vm_id=vm['vm_id'],
                vm_name_str=vm['vm_name_str'],
                vm_os=vm.get('vm_os', None),
                instanceUuid=vm.get('instanceUuid'),
                uptimeSeconds=vm.get('uptimeSeconds', None),
                bootTime=vm.get('bootTime', None),
                currentSnapshot=vm.get('currentSnapshot', None),
                rootSnapshotList=vm.get('rootSnapshotList', None),
                pool_name=vm.get('pool_name', None),
            )
            octo_vm.save()

    def search_vm(self, vm_uuid, instance_search=True):
        self.retrieve_content()
        vm = self.service_instance.content.searchIndex.FindByUuid(None, vm_uuid, True, instance_search)
        log.info(f'Find VM: {vm}')
        return vm

    def vm_create_snapshot(self, vm_obj, out_q, **vm_kwargs):
        log.info(f"Creating snapshot for VM: {vm_obj.vm_name}")
        vm = self.search_vm(vm_obj.instanceUuid)
        if vm:
            name = vm_kwargs.get('name', 'Default snapshot')
            description = vm_kwargs.get('description', 'Automated default snapshot.')
            memory = vm_kwargs.get('memory', False)
            quiesce = vm_kwargs.get('quiesce', False)
            # Create snapshot CreateSnapshot_Task:
            task = vm.CreateSnapshot_Task(name=name,
                                          description=description,
                                          memory=memory,
                                          quiesce=quiesce)
            vim.WaitForTask(task)
            snapshot = task.info.result
            log.info(f"Snapshot created: {snapshot}")
            out_q.put({vm_obj.vm_name: snapshot})
        else:
            log.info(f"there is no such vm: {vm_obj.vm_name} id: {vm_obj.instanceUuid}")
            out_q.put({vm_obj.vm_name: 'no_snapshot'})

    def vm_revert_snapshot(self, vm_obj, out_q, **vm_kwargs):
        log.info(f"Reverting latest snapshot for VM: {vm_obj.vm_name}")
        vm = self.search_vm(vm_obj.instanceUuid)
        if vm:
            # Revert latest snapshot RevertToCurrentSnapshot_Task:
            task = vm.RevertToCurrentSnapshot_Task()
            WaitForTask(task)
            snapshot = task.info.result
            log.info(f"Snapshot reverted: {snapshot}")
            out_q.put({vm_obj.vm_name: snapshot})
        else:
            log.info(f"there is no such vm: {vm_obj.vm_name} id: {vm_obj.instanceUuid}")
            out_q.put({vm_obj.vm_name: 'no_snapshot'})

    def vm_power_on(self, vm_obj, out_q, **vm_kwargs):
        """
        Power on vm. If not powered off state - skip
        :param vm_obj:
        :return:
        """
        log.info(f"Power ON VM: {vm_obj.vm_name}")
        vm = self.search_vm(vm_obj.instanceUuid)
        if vm:
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOff:
                task = vm.PowerOn()
                log.info(f"Powering on task: {task}")
                WaitForTask(task)
                out_q.put({vm_obj.vm_name: 'poweredOn'})
            else:
                log.info(f'This machine is not PoweredOff - skipping task! {vm_obj.vm_name}')
                out_q.put({vm_obj.vm_name: 'skipped'})
        else:
            log.info(f"there is no such vm: {vm_obj.vm_name} id: {vm_obj.instanceUuid}")
            out_q.put({vm_obj.vm_name: None})

    def vm_power_off(self, vm_obj, out_q, **vm_kwargs):
        """
        Power off vm. If not powered on state - skip
        :param vm_obj:
        :return:
        """
        log.info(f"Power OFF VM: {vm_obj.vm_name}")
        vm = self.search_vm(vm_obj.instanceUuid)
        if vm:
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                task = vm.PowerOff()
                log.info(f"Powering off task: {task}")
                WaitForTask(task)
                out_q.put({vm_obj.vm_name: 'poweredOff'})
            else:
                log.info(f'This machine is poweredOff already - skipping task! {vm_obj.vm_name}')
                out_q.put({vm_obj.vm_name: 'skipped'})
        else:
            log.info(f"there is no such vm: {vm_obj.vm_name} id: {vm_obj.instanceUuid}")
            out_q.put({vm_obj.vm_name: None})

    def vm_shutdown_guest(self, vm_obj, out_q, **vm_kwargs):
        """
        Shutdown VM OS. If not powered on state - skip
        :param vm_obj:
        :return:
        """
        log.info(f"Graceful shutdown VM: {vm_obj.vm_name}")
        vm = self.search_vm(vm_obj.instanceUuid)
        if vm:
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                task = vm.ShutdownGuest()
                log.info(f"Shut down OS task: {task}")
                # Cannot wait for this: 'NoneType' object has no attribute '_stub'
                # WaitForTask(task)
                sleep(60*5)
                out_q.put({vm_obj.vm_name: 'poweredOff'})
            else:
                log.info(f'This machine is poweredOff already - skipping task! {vm_obj.vm_name}')
                out_q.put({vm_obj.vm_name: 'skipped'})
        else:
            log.info(f"there is no such vm: {vm_obj.vm_name} id: {vm_obj.instanceUuid}")
            out_q.put({vm_obj.vm_name: None})

    def vm_soft_reboot(self, vm_obj, out_q, **vm_kwargs):
        log.info(f"Soft REBOOT VM: {vm_obj.vm_name}")
        vm = self.search_vm(vm_obj.instanceUuid)
        if vm:
            task = vm.RebootGuest()()
            log.info(f"Reboot off task: {task}")
            WaitForTask(task)
            out_q.put({vm_obj.vm_name: 'rebooted'})
        else:
            log.info(f"there is no such vm: {vm_obj.vm_name} id: {vm_obj.instanceUuid}")
            out_q.put({vm_obj.vm_name: None})

    def vm_reset(self, vm_obj, out_q, **vm_kwargs):
        log.info(f"RESET VM: {vm_obj.vm_name}")
        vm = self.search_vm(vm_obj.instanceUuid)
        if vm:
            task = vm.ResetVM_Task()()()
            log.info(f"Reset off task: {task}")
            WaitForTask(task)
            out_q.put({vm_obj.vm_name: 'reset'})
        else:
            log.info(f"there is no such vm: {vm_obj.vm_name} id: {vm_obj.instanceUuid}")
            out_q.put({vm_obj.vm_name: None})

    def vm_config(self, vm_obj, out_q=None, **vm_kwargs):
        """
        Should be powered Off before change
        :param vm_obj:
        :param out_q:
        :param kwargs:
        :return:
        """
        vm_conf = vm_kwargs.get('vm_kwargs')
        numCPUs = vm_conf.get('numCPUs', None)
        memoryMB = vm_conf.get('memoryMB', None)
        numCoresPerSocket = vm_conf.get('numCoresPerSocket', None)

        vm = self.search_vm(vm_obj.instanceUuid)
        # PowerOff VM before run reconfigure task
        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
            self.vm_shutdown_guest(vm_obj, out_q)

        cspec = vim.vm.ConfigSpec()

        if numCPUs:
            log.debug(f"Change {vm_obj.vm_name} numCPUs: {numCPUs}")
            cspec.numCPUs = numCPUs
        if numCoresPerSocket:
            log.debug(f"Change {vm_obj.vm_name} numCoresPerSocket: {numCoresPerSocket}")
            cspec.numCoresPerSocket = numCoresPerSocket
        if memoryMB:
            log.debug(f"Change {vm_obj.vm_name} memoryMB: {memoryMB}")
            cspec.memoryMB = memoryMB

        if vm:
            task = vm.Reconfigure(cspec)
            WaitForTask(task)
            log.info(f"Reconfigured VM {vm_obj.vm_name} with: {vm_conf}")
            out_q.put({f'Reconfigure: {vm_obj.vm_name}': f'Options set:{vm_conf}'})
        else:
            out_q.put({f'Not found VM: {vm_obj.vm_name}': f'Options unset:{vm_conf}'})
