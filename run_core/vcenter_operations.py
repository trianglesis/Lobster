import os
import logging
import atexit
import ssl
# noinspection PyUnresolvedReferences
from pyVim import connect
# noinspection PyUnresolvedReferences
from pyVmomi import vim

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


if __name__ == "__main__":
    import django
    django.setup()
    from run_core.models import AddmDev, OctopusVM
    vc = VCenterOperations()
    all_vms = vc.list_vms(model=AddmDev, vm_model=OctopusVM)