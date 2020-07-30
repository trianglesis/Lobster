import os
import logging
import atexit
import ssl
# noinspection PyUnresolvedReferences
from pyVim import connect
# noinspection PyUnresolvedReferences
from pyVmomi import vim
from pyVim.task import WaitForTask



from octo.config_cred import v_center_cred
from django.core.exceptions import ObjectDoesNotExist

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
        self.content =None
        self.containerView = None
        self.container = None

        # Store connection here:
        self.vconnect()

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
        print("container {}".format(self.container))

    def get_content_vms(self):
        self.root_container()
        self.retrieve_content()

        recursive = True  # whether we should look into it recursively
        viewType = [vim.VirtualMachine]  # object types to look for
        print("viewType {}".format(viewType))

        containerView = self.content.viewManager.CreateContainerView(self.container, viewType, recursive)  # create container view
        return containerView

    def list_vms(self, model=None, vm_model=None):
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
                    vm_info_all.update(pool_name=child.resourcePool.name,)
                all_vms.append(vm_info_all)

                if model and vm_model:
                    self.insert_update_addm_vm(vm=vm_info_all, model=model, vm_model=vm_model)

                print(f"VM Info: {vm_info_all}")
            else:
                print(f"Has no name: {child}")
        return all_vms

    def insert_update_addm_vm(self, vm, model, vm_model):
        related_addm = None
        try:
            related_addm = model.objects.get(addm_host__exact=vm['vm_name'])
        except ObjectDoesNotExist as e:
            print(f'VM is not in ADDM VMs, skip {vm["vm_name"]} {e}')
        if related_addm:
            print(f"Found ADDM VM! {related_addm}")
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
        print(f'Find VM: {vm}')
        return vm

    def vm_create_snapshot(self, vm_obj, **kwargs):
        print(f"Creating snapshot for VM: {vm_obj.vm_name}")
        vm = self.search_vm(vm_obj.instanceUuid)
        if vm:
            name = kwargs.get('name', 'Default snapshot')
            description = kwargs.get('description', 'Automated default snapshot.')
            memory = kwargs.get('memory', False)
            quiesce = kwargs.get('quiesce', False)
            # Create snapshot CreateSnapshot_Task:
            task = vm.CreateSnapshot_Task(name=name,
                                          description=description,
                                          memory=memory,
                                          quiesce=quiesce)
            vim.WaitForTask(task)
            snapshot = task.info.result
            print("Snapshot created: {}".format(snapshot))
            return snapshot
        else:
            print(f"there is no such vm: {vm_obj.vm_name} id: {vm_obj.instanceUuid}")
            return None

    def vm_revert_snapshot(self, vm_obj):
        print(f"Reverting latest snapshot for VM: {vm_obj.vm_name}")
        vm = self.search_vm(vm_obj.instanceUuid)
        if vm:
            # Revert latest snapshot RevertToCurrentSnapshot_Task:
            task = vm.RevertToCurrentSnapshot_Task()
            WaitForTask(task)
            snapshot = task.info.result
            print("Snapshot reverted: {}".format(snapshot))
            return snapshot
        else:
            print(f"there is no such vm: {vm_obj.vm_name} id: {vm_obj.instanceUuid}")
            return None

    def vm_power_on(self, vm_obj):
        """
        Power on vm. If not powered off state - skip
        :param vm_obj:
        :return:
        """
        print(f"Power ON VM: {vm_obj.vm_name}")
        vm = self.search_vm(vm_obj.instanceUuid)
        if vm:
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOff:
                task = vm.PowerOn()
                print(f"Powering on task: {task}")
                WaitForTask(task)
            else:
                print(f'This machine is not PoweredOff - skipping task! {vm_obj.vm_name}')
        else:
            print(f"there is no such vm: {vm_obj.vm_name} id: {vm_obj.instanceUuid}")
            return None

    def vm_power_off(self, vm_obj):
        """
        Power off vm. If not powered on state - skip
        :param vm_obj:
        :return:
        """
        print(f"Power OFF VM: {vm_obj.vm_name}")
        vm = self.search_vm(vm_obj.instanceUuid)
        if vm:
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                task = vm.PowerOff()
                print(f"Powering off task: {task}")
                WaitForTask(task)
            else:
                print(f'This machine is poweredOn already - skipping task! {vm_obj.vm_name}')
        else:
            print(f"there is no such vm: {vm_obj.vm_name} id: {vm_obj.instanceUuid}")
            return None

    def vm_soft_reboot(self, vm_obj):
        print(f"Soft REBOOT VM: {vm_obj.vm_name}")
        vm = self.search_vm(vm_obj.instanceUuid)
        if vm:
            task = vm.RebootGuest()()
            print(f"Reboot off task: {task}")
            WaitForTask(task)
        else:
            print(f"there is no such vm: {vm_obj.vm_name} id: {vm_obj.instanceUuid}")
            return None

    def vm_reset(self, vm_obj):
        print(f"RESET VM: {vm_obj.vm_name}")
        vm = self.search_vm(vm_obj.instanceUuid)
        if vm:
            task = vm.ResetVM_Task()()()
            print(f"Reset off task: {task}")
            WaitForTask(task)
        else:
            print(f"there is no such vm: {vm_obj.vm_name} id: {vm_obj.instanceUuid}")
            return None


if __name__ == "__main__":
    import django
    django.setup()
    from run_core.models import AddmDev, OctopusVM
    vc = VCenterOperations()
    # all_vms = vc.list_vms(model=AddmDev, vm_model=OctopusVM)

    alpha_addms = AddmDev.objects.filter(addm_group__exact='alpha')
    for addm in alpha_addms:
        print(f"addm {addm.octopusvm.vm_name}, {addm.octopusvm.instanceUuid}")
        vc.vm_revert_snapshot(vm_obj=addm.octopusvm)
        # vc.vm_power_off(vm_obj=addm.octopusvm)
        vc.vm_power_on(vm_obj=addm.octopusvm)