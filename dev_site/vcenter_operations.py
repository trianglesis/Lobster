

if __name__ == "__main__":
    import os
    import logging
    import atexit
    import ssl
    import requests
    from pyVim import connect
    from pyVim.task import WaitForTask, WaitForTasks
    # noinspection PyUnresolvedReferences
    from pyVmomi import vim
    from datetime import datetime

    from octo.config_cred import v_center_cred

    host_1 = v_center_cred['host_1']
    host_2 = v_center_cred['host_2']
    host_vc = v_center_cred['host_vc']
    LOC_USER = v_center_cred['LOC_USER']
    LOC_PWD = v_center_cred['LOC_PWD']
    VC_USER = v_center_cred['VC_USER']
    VC_PWD = v_center_cred['VC_PWD']
    LOBSTER_USER = v_center_cred['LOBSTER_USER']
    LOBSTER_PWD = v_center_cred['LOBSTER_PWD']
    OCTOPUS_USER = v_center_cred['OCTOPUS_USER']
    OCTOPUS_PWD = v_center_cred['OCTOPUS_PWD']

    log = logging.getLogger("octo.octologger")
    place = os.path.dirname(os.path.abspath(__file__))

    # noinspection PyShadowingNames,PyShadowingNames,PyShadowingNames,PyShadowingNames,PyShadowingNames
    class VCenterOper:
        """

        """

        @staticmethod
        def vconnect(host, user, pwd):
            s = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            s.verify_mode = ssl.CERT_NONE  # disable our certificate checking for lab

            service_instance = connect.SmartConnect(host=host,  # build python connection to vSphere
                                                    user=user,
                                                    pwd=pwd,
                                                    sslContext=s)

            atexit.register(connect.Disconnect, service_instance)  # build disconnect logic

            # Find VM by UUID
            search_index = service_instance.content.searchIndex

            # vl-aus-btk-qa10
            vm = search_index.FindByUuid(None, "5023e317-3750-fc87-f834-32cefd2244bd", True, True)
            details = {'name': vm.summary.config.name,
                       'instance UUID': vm.summary.config.instanceUuid,
                       'bios UUID': vm.summary.config.uuid,
                       'path to VM': vm.summary.config.vmPathName,
                       'guest OS id': vm.summary.config.guestId,
                       'guest OS name': vm.summary.config.guestFullName,
                       'host name': vm.runtime.host.name,
                       'last booted timestamp': vm.runtime.bootTime,
                       }
            print("VM by UUID: {}".format(details))

            # Create snapshot CreateSnapshot_Task:
            task = vm.CreateSnapshot_Task(name='This is snapshot from python',
                                          description="We will create such snapshots automatically!",
                                          memory=True,
                                          quiesce=False)
            WaitForTask(task)
            snapshot = task.info.result
            print("Snapshot created: {}".format(snapshot))

            # List snapshots:
            print("currentSnapshot:             {}".format(vm.snapshot.currentSnapshot))
            print("rootSnapshotList:            {}".format(vm.snapshot.rootSnapshotList))
            # Revert to child snapshot:
            for snapshot_item in vm.snapshot.rootSnapshotList:
                print("snapshot_item.childSnapshotList {}".format(snapshot_item.childSnapshotList))
                for snap in snapshot_item.childSnapshotList:
                    if 'type=tku_upload_ready;' in snap.name:
                        print("This is snap we looking for: {}".format(snap))
                        snap_obj = snap.snapshot
                        print("Reverting snapshot {}".format(snap.name))
                        task = [snap_obj.RevertToSnapshot_Task()]
                        WaitForTasks(task, service_instance)
                        print("Renaming snapshot after revert {}".format(snap.name))
                        snap_obj.RenameSnapshot(
                            name='type=tku_upload_ready;last_reverted_date={}'.format(datetime.now().strftime('%Y-%m-%d')),
                            description='type=tku_upload_ready;last_reverted_timestamp={}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                        )
                        print("Reverted snapshot renamed {}".format(snap.name))

            # Revert latest snapshot RevertToCurrentSnapshot_Task:
            task = vm.RevertToCurrentSnapshot_Task()
            WaitForTask(task)
            snapshot = task.info.result
            print("Snapshot reverted: {}".format(snapshot))

        # noinspection PyUnusedLocal,PyUnusedLocal
        @staticmethod
        def conn(host, user, password, port):
            service_instance = None
            sslContext = None
            verify_cert = None

            try:
                service_instance = connect.SmartConnect(host=host,
                                                        user=user,
                                                        pwd=password,
                                                        port=int(port),
                                                        sslContext=sslContext)
            except IOError as e:
                pass
            if not service_instance:
                print("Could not connect to the specified host using specified "
                      "username and password")
                raise SystemExit(-1)

            # Ensure that we cleanly disconnect in case our code dies
            atexit.register(connect.Disconnect, service_instance)

            content = service_instance.RetrieveContent()
            session_manager = content.sessionManager
            return content, session_manager, service_instance

        @staticmethod
        def make_connection(host, user, pwd):
            s = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            s.verify_mode = ssl.CERT_NONE  # disable our certificate checking for lab

            sslContext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            sslContext.verify_mode = ssl.CERT_NONE

            service_instance = connect.SmartConnect(host=host,  # build python connection to vSphere
                                                    user=user,
                                                    pwd=pwd,
                                                    sslContext=sslContext)

            # service_instance = connect.SmartConnectNoSSL(host="HOST",
            #                                              user="USER",
            #                                              pwd="PWD")

            atexit.register(connect.Disconnect, service_instance)  # build disconnect logic
            content = service_instance.RetrieveContent()
            session_manager = content.sessionManager

            return content, session_manager, service_instance

        @staticmethod
        def list_vms(content, vm_names_list=[]):

            # https://VCENT/mob/?group=group-d1
            container = content.rootFolder  # starting point to look into
            viewType = [vim.VirtualMachine]  # object types to look for

            print("container {}".format(container))
            print("viewType {}".format(viewType))

            recursive = True  # whether we should look into it recursively
            containerView = content.viewManager.CreateContainerView(container, viewType, recursive)  # create container view
            children = containerView.view

            print("containerView {}".format(containerView))
            print("children len: {} all: {}".format(len(children), children))

            for child in children:  # for each statement to iterate all names of VMs in the environment
                summary = child.summary
                if child.name in vm_names_list:
                    # VM VM id:                    'vim.VirtualMachine:vm-105'
                    print("VM name:                     {}".format(child.name))
                    print("VM Parent:                   {}".format(child.parent.name))
                    print("VM resourcePool:             {}".format(child.resourcePool.name))
                    print("VM VM id:                    {}".format(summary.vm))
                    print("Virtual Machine Name:        {}".format(summary.config.name))
                    print("Virtual Machine OS:          {}".format(summary.config.guestFullName))
                    print("Virtual instanceUuid:        {}".format(summary.config.instanceUuid))
                    print("uptimeSeconds:               {}".format(summary.quickStats.uptimeSeconds))
                    print("bootTime:                    {}".format(child.runtime.bootTime))
                    if child.snapshot:
                        print("currentSnapshot:             {}".format(child.snapshot.currentSnapshot))
                        print("rootSnapshotList:            {}".format(child.snapshot.rootSnapshotList))
                    else:
                        print("This VM has no snapshots: {}".format(child.name))
                    print("")
                else:
                    # VM VM id:                    'vim.VirtualMachine:vm-105'
                    print("VM name:                     {}".format(child.name))
                    # print("VM Parent:                   {}".format(child.parent.name))
                    # print("VM resourcePool:             {}".format(child.resourcePool.name))
                    # print("VM VM id:                    {}".format(summary.vm))
                    # print("Virtual Machine Name:        {}".format(summary.config.name))
                    # print("Virtual Machine OS:          {}".format(summary.config.guestFullName))
                    # print("Virtual instanceUuid:        {}".format(summary.config.instanceUuid))
                    # print("uptimeSeconds:               {}".format(summary.quickStats.uptimeSeconds))
                    # print("bootTime:                    {}".format(child.runtime.bootTime))
                    # if child.snapshot:
                    #     print("currentSnapshot:             {}".format(child.snapshot.currentSnapshot))
                    #     print("rootSnapshotList:            {}".format(child.snapshot.rootSnapshotList))
                    # else:
                    #     print("This VM has no snapshots: {}".format(child.name))
                    # print("")

        @staticmethod
        def vm_find_by_uuid(content, uuid):
            # Find VM by UUID
            search_index = content.searchIndex

            # vl-aus-btk-qa10
            vm = search_index.FindByUuid(None, uuid, True, True)
            details = {'name': vm.summary.config.name,
                       'instance UUID': vm.summary.config.instanceUuid,
                       'bios UUID': vm.summary.config.uuid,
                       'path to VM': vm.summary.config.vmPathName,
                       'guest OS id': vm.summary.config.guestId,
                       'guest OS name': vm.summary.config.guestFullName,
                       'host name': vm.runtime.host.name,
                       'last booted timestamp': vm.runtime.bootTime,
                       }
            print("VM by UUID: {}".format(details))
            return vm

        @staticmethod
        def vm_create_snapshot(vm):
            # Create snapshot CreateSnapshot_Task:
            task = vm.CreateSnapshot_Task(name='This is snapshot from python',
                                          description="We will create such snapshots automatically!",
                                          memory=True,
                                          quiesce=False)
            WaitForTask(task)
            snapshot = task.info.result
            print("Snapshot created: {}".format(snapshot))
            return snapshot

        @staticmethod
        def vm_list_snapshots(vm):
            # List snapshots:
            print("currentSnapshot:             {}".format(vm.snapshot.currentSnapshot))
            print("rootSnapshotList:            {}".format(vm.snapshot.rootSnapshotList))

        @staticmethod
        def vm_revert_to_snapshot(si, vm, snap_type):
            # 'type=tku_upload_ready;'
            print(snap_type)
            # Revert to child snapshot:
            for snapshot_item in vm.snapshot.rootSnapshotList:
                print("snapshot_item.childSnapshotList {}".format(snapshot_item.childSnapshotList))
                for snap in snapshot_item.childSnapshotList:
                    if snap_type in snap.name:
                        print("This is snap we looking for: {}".format(snap))
                        snap_obj = snap.snapshot
                        print("Reverting snapshot {}".format(snap.name))
                        task = [snap_obj.RevertToSnapshot_Task()]
                        WaitForTasks(task, si)
                        print("Renaming snapshot after revert {}".format(snap.name))
                        snap_obj.RenameSnapshot(
                            name='type=tku_upload_ready;last_reverted_date={}'.format(datetime.now().strftime('%Y-%m-%d')),
                            description='type=tku_upload_ready;last_reverted_timestamp={}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                        )
                        print("Reverted snapshot renamed {}".format(snap.name))

        @staticmethod
        def vm_revert_to_current_snapshot(vm):
            # Revert latest snapshot RevertToCurrentSnapshot_Task:
            task = vm.RevertToCurrentSnapshot_Task()
            WaitForTask(task)
            snapshot = task.info.result
            print("Snapshot reverted: {}".format(snapshot))

        @staticmethod
        def vm_from_vmdk_register(content):
            host = content.searchIndex.FindByDnsName(None, "host1.myesxhost.com", False)
            folder = content.searchIndex.FindByInventoryPath('')
            task = folder.RegisterVM_Task(path="[Local1] 1001-web1.myhost.com/1001-web1.myhost.com.vmx",
                                          name="new vm name",
                                          asTemplate=False, pool=None, host=host)
            return task

        @staticmethod
        def datacenter_find(content):
            # Get the list of all datacenters we have available to us
            datacenters_object_view = content.viewManager.CreateContainerView(
                content.rootFolder,
                [vim.Datacenter],
                True)
            return datacenters_object_view

        @staticmethod
        def datastore_find(dc_obj, content, ds_item):
            """
            :param dc_obj: datacenters_object_view
            :param content: content
            :param ds_item: Datastore name
            :return:
            """
            # Find the datastore and datacenter we are using
            datacenter = None
            datastore = None
            for dc in dc_obj.view:
                datastores_object_view = content.viewManager.CreateContainerView(
                    dc,
                    [vim.Datastore],
                    True)
                for ds in datastores_object_view.view:
                    if ds.info.name == ds_item:
                        datacenter = dc
                        datastore = ds
            if not datacenter or not datastore:
                print("Could not find the datastore specified")
                raise SystemExit(-1)
            # Clean up the views now that we have what we need
            # noinspection PyUnboundLocalVariable
            datastores_object_view.Destroy()
            dc_obj.Destroy()

            return datacenter, datastore

        @staticmethod
        def url_to_put(remote_file, datastore, datacenter, host):
            # Build the url to put the file - https://hostname:port/resource?params
            if not remote_file.startswith("/"):
                remote_file = "/" + remote_file
            else:
                remote_file = remote_file
            resource = "/folder" + remote_file

            params = {"dsName": datastore.info.name, "dcPath": datacenter.name}
            print("<=url_to_put=> datastore.info.name {}".format(datastore.info.name))
            print("<=url_to_put=> datacenter.name {}".format(datacenter.name))

            http_url = "https://" + host + ":443" + resource

            print("<=url_to_put=> resource, params, http_url {}{}{}".format(resource, params, http_url))

            return http_url, params

        @staticmethod
        def cookie_headers(si):
            # Get the cookie built from the current session
            # noinspection PyProtectedMember
            client_cookie = si._stub.cookie
            # Break apart the cookie into it's component parts - This is more than
            # is needed, but a good example of how to break apart the cookie
            # anyways. The verbosity makes it clear what is happening.
            cookie_name = client_cookie.split("=", 1)[0]
            cookie_value = client_cookie.split("=", 1)[1].split(";", 1)[0]
            cookie_path = client_cookie.split("=", 1)[1].split(";", 1)[1].split(
                ";", 1)[0].lstrip()
            cookie_text = " " + cookie_value + "; $" + cookie_path
            # Make a cookie
            cookie = dict()
            cookie[cookie_name] = cookie_text

            # Get the request headers set up
            headers = {'Content-Type': 'application/octet-stream'}
            return headers, cookie

        # noinspection PyUnusedLocal
        @staticmethod
        def upload_to_datastore(local_file, http_url, params, headers, cookie, verify_cert=None):
            # Get the file to upload ready, extra protection by using with against
            # leaving open threads

            with open(local_file, "rb") as f:
                # Connect and upload the file
                request = requests.put(http_url,
                                       params=params,
                                       data=f,
                                       headers=headers,
                                       cookies=cookie,
                                       verify=False,
                                       )
            return request

        @staticmethod
        def datastore_image_load_trying():
            """
            datacenter-2 "AUS-TKU-DC"
            datastore-87
            name "vmfs-Aus-HDSG15-01-32:8E"
            url "ds:///vmfs/volumes/5b5aaf57-03069dac-8077-20474797ca28/"

            datastoreBrowser-datastore-87
            ManagedObjectReference:HostDatastoreBrowser
            HostDatastoreBrowserSearchResults	SearchDatastore_Task
            HostDatastoreBrowserSearchResults[]	SearchDatastoreSubFolders_Task
            """
            # VCenterOper().vm_from_vmdk_register()

            content, session_manager, service_instance = VCenterOper().make_connection(
                host=v_center_cred['host_2'],
                user=v_center_cred['LOC_USER'],
                pwd=v_center_cred['LOC_PWD'],
            )
            print("1. content, session_manager, service_instance {}{}{}".format(content, session_manager, service_instance))

            datacenters_object_view = VCenterOper().datacenter_find(content)
            print("2. datacenters_object_view {}".format(datacenters_object_view))

            ds_item = "vmfs-Aus-HDSG15-01-32:8E"
            datacenter, datastore = VCenterOper().datastore_find(datacenters_object_view, content, ds_item)
            print("3. datacenter, datastore {}{}".format(datacenter, datastore))

            # remote_file = 'ds:///vmfs/volumes/5b5aaf57-03069dac-8077-20474797ca28/'
            # remote_file = '/tku_build_vms'
            remote_file = '/tku_build_vms/'
            # https://HOST/folder?dcPath=ha-datacenter
            # https://HOST/folder/tku_build_vms?dcPath=ha%252ddatacenter&dsName=vmfs%252dAus%252dHDSG15%252d01%252d32%253a8E
            http_url, params = VCenterOper().url_to_put(remote_file, datastore, datacenter, host=v_center_cred['host_2'])
            print("4. http_url, params {}{}".format(http_url, params))

            headers, cookie = VCenterOper().cookie_headers(session_manager)
            print("5. headers, cookie {}{}".format(headers, cookie))

            local_file = '/var/www/octopus/dev_site/test_upload.txt'
            # https://HOST/folder/tku_build_vms/?dsName=vmfs-Aus-HDSG15-01-32:8E&dcPath=ha-datacenter
            request = VCenterOper().upload_to_datastore(local_file, http_url, params, headers, cookie)
            print("6. request {}".format(request))

            """
            ftp://BUILD/hub/RELEASED/11_3_0_5/publish/VAs/unpacked/ADDM_VA_64_11.3.0.5_767189_ga_Full/ADDM_VA_64_11.3.0.5_767189_ga_Full.ovf
            ftp://BUILD/hub/RELEASED/11_3_0_5/publish/VAs/unpacked/ADDM_VA_64_11.3.0.5_767189_ga_Full/ADDM_VA_64_11.3.0.5_767189_ga_Full-disk-0.vmdk
            """


    class DevVmSetup:

        def __init__(self):
            self.content, self.session_manager, self.service_instance = VCenterOper().make_connection(
                host=host_vc,
                user=VC_USER,
                pwd=VC_PWD,
            )

    # RUNNING:

    # VCenterOper().vconnect(
    #     host=host,
    #     user=LOBSTER_USER,
    #     pwd=LOBSTER_PWD,
    # )

    content, session_manager, service_instance = VCenterOper().make_connection(
        host=host_vc,
        user=VC_USER,
        pwd=VC_PWD,
    )

    my_vms_names = v_center_cred['my_vms_names']
    VCenterOper().list_vms(content, vm_names_list=my_vms_names)

