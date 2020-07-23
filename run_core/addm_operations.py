"""
ADDM operations execute here:
- SSH connections


addm_name:          addm_ip:          addm_host:      addm_ver:     owner:
custard_cream       172.25.144.118    vl-aus-tkudev-38    ADDM_11_2     Alex D
bobblehat           172.25.144.119    vl-aus-tkudev-39    ADDM_11_1     Alex D
aardvark            172.25.144.120    vl-aus-tkudev-40    ADDM_11_0     Alex D
zythum              172.25.144.121    vl-aus-tkudev-41    ADDM_10_2     Alex D
double_decker                 172.25.144.122    vl-aus-tkudev-42    ADDM_10_1     Alex D

"""

# Python logger
import logging
import os
from queue import Queue
from time import sleep
from time import time

# noinspection PyCompatibility
import paramiko
from django.db.models.query import QuerySet
from paramiko import SSHClient

from django.conf import settings
from octo.helpers.tasks_mail_send import Mails
from octo.helpers.tasks_run import Runner
from run_core.models import AddmDev, ADDMCommands

from octo.config_cred import mails

log = logging.getLogger("octo.octologger")
place = os.path.dirname(os.path.abspath(__file__))


# Service functions:
def out_err_read(**kwargs):
    """
    Read everything and warn if something in.
    If needed - return outputs.

    Mode for operating:
    verbose - show all outputs from all pipes
    error - show only STDERR
    stdout - show only STDOUT
    silent - show nothing

    :return:
    """
    stdout = kwargs['out']
    stderr = kwargs['err']

    std_output = ""
    stderr_output = ""

    if kwargs['name']:
        name = kwargs['name']
    else:
        name = "undefined cmd"

    if kwargs['cmd']:
        cmd = kwargs['cmd']
    else:
        cmd = "CMD:"

    if kwargs['mode']:
        mode = kwargs['mode']
    else:
        mode = "error"

    if stdout:
        output = stdout.readlines()
        raw_out = "".join(output).replace('\n', " ")
        if raw_out:
            std_output = raw_out
            if mode == "verbose":
                log.debug(name + " cmd: '%s' - STDOUT: \n%s", cmd, raw_out)
            elif mode == "stdout":
                log.debug(name + " cmd: '%s' - STDOUT: \n%s", cmd, raw_out)
            elif mode == "error" or mode == "silent":
                pass

    if stderr:
        output = stderr.readlines()
        raw_out = "".join(output).replace('\n', " ")
        if raw_out:
            stderr_output = raw_out
            if mode == "verbose":
                log.debug(name + " cmd: '%s' - STDERR: \n%s", cmd, raw_out)
            elif mode == "error":
                log.debug(name + " cmd: '%s' - STDERR: \n%s", cmd, raw_out)
            elif mode == "stdout" or mode == "silent":
                pass

    return std_output, stderr_output


class ADDMStaticOperations:

    @staticmethod
    def select_operation(command_key):
        operations = ADDMCommands.objects.all()
        if isinstance(command_key, str):
            operations = operations.filter(command_key__exact=command_key)
        elif isinstance(command_key, list):
            operations = operations.filter(command_key__in=command_key)
        else:
            # To catch a wrong situation, just select a version command:
            operations = operations.filter(command_key__exact='show.addm.version')
        # log.info("All selected operations count: %s by command_key %s", operations.count(), command_key)
        return operations

    def threaded_exec_cmd(self, **kwargs):
        """ Execute one operation command per addm in addm_set """
        from threading import Thread

        addm_set = kwargs.get('addm_set', None)
        operation_cmd = kwargs.get('operation_cmd', None)
        interactive_mode = kwargs.get('interactive_mode', False)
        fake_run = kwargs.get('fake_run', False)

        if isinstance(addm_set, QuerySet):
            addm_set = addm_set.values()
            log.debug(f'AddmDev QuerySet: {type(addm_set)}')
        else:
            log.info(f'AddmDev set: {type(addm_set)}')

        if isinstance(operation_cmd, ADDMCommands):
            cmd_k = operation_cmd.command_key
            cmd_interactive = operation_cmd.interactive
        elif isinstance(operation_cmd, dict):
            cmd_k = operation_cmd
            cmd_interactive = interactive_mode
        else:
            cmd_interactive, cmd_k = None, None
            log.error("ADDM CMD should be a dict or ADDMCommands object!")
            return {'cmd_error': 'ADDM CMD should be a dict or ADDMCommands object!'}

        th_list = []
        th_out = []
        ts = time()
        out_q = Queue()

        for addm_item in addm_set:
            ssh = ADDMOperations().ssh_c(addm_item=addm_item)
            if ssh:
                th_name = f'ADDMStaticOperations.threaded_exec_cmd: {addm_item["addm_group"]} - {addm_item["addm_host"]} {addm_item["addm_ip"]}'
                args_d = dict(out_q=out_q, addm_item=addm_item, operation_cmd=operation_cmd, ssh=ssh)
                try:
                    if cmd_interactive:
                        log.info("<=threaded_exec_cmd=> Interactive shell CMD mode.")
                        cmd_th = Thread(target=self.run_interactive_cmd, name=th_name, kwargs=args_d)
                    else:
                        log.info("<=threaded_exec_cmd=> Static CMD mode.")
                        cmd_th = Thread(target=self.run_static_cmd, name=th_name, kwargs=args_d)
                    cmd_th.start()
                    th_list.append(cmd_th)
                except Exception as e:
                    msg = f'Thread test fail with error: {e}'
                    log.error(msg)
                    raise Exception(msg)
            else:
                msg = f'SSH Connection died! Addm: {addm_item["addm_host"]}'
                log.error(msg)
                raise Exception(msg)
        for test_th in th_list:
            test_th.join()
            th_out.append(out_q.get())
        output = {cmd_k: th_out, 'time': time() - ts}
        log.info(f"ADDM CMD Output: {output}")
        return output

    @staticmethod
    def run_static_cmd(out_q, addm_item, operation_cmd, ssh):
        assert isinstance(addm_item, dict), 'Should be dict converted from QuerySet.values()'

        if isinstance(operation_cmd, ADDMCommands):
            cmd_k = operation_cmd.command_key
            cmd = operation_cmd.command_value
        elif isinstance(operation_cmd, dict):
            cmd_k = operation_cmd['command_key']
            cmd = operation_cmd['command_value']
        elif isinstance(operation_cmd, list):
            cmd_k = 'cmd_list'
            cmd = operation_cmd
        else:
            cmd, cmd_k = None, None
            log.error("ADDM CMD should be a dict or ADDMCommands object!")
            return {'cmd_error': 'ADDM CMD should be a dict or ADDMCommands object!'}

        addm_instance = f"ADDM: {addm_item['addm_name']} - {addm_item['addm_host']}"
        ts = time()

        log.debug("<=CMD=> Run cmd %s on %s CMD: '%s'", cmd_k, addm_instance, cmd)
        if cmd:
            # noinspection PyBroadException
            try:
                _, stdout, stderr = ssh.exec_command(cmd)
                output_d = {cmd_k: dict(out=stdout.readlines(),
                                        err=stderr.readlines(),
                                        addm=addm_instance,
                                        cmd_item=cmd,
                                        timest=time() - ts)}
                # log.debug("addm_exec_cmd: %s ADDM: %s", output_d, addm_instance)
                out_q.put(output_d)
            except Exception as e:
                log.error("<=ADDM Oper=> Error during operation for: %s %s", cmd, e)
                out_q.put({cmd_k: dict(out='Traceback', err=e, addm=addm_instance)})
        else:
            msg = '<=CMD=> Skipped for "{}" {}'.format(cmd_k, addm_instance)
            log.info(msg)
            out_q.put({cmd_k: dict(out='Skipped', msg=msg, addm=addm_instance)})

    def run_interactive_cmd(self, out_q, addm_item, operation_cmd, ssh):
        assert isinstance(addm_item, dict), 'Should be dict converted from QuerySet.values()'
        assert isinstance(operation_cmd, ADDMCommands), 'Should be ADDMCommands QuerySet'

        cmd_k = operation_cmd.command_key
        cmd = operation_cmd.command_value

        addm_instance = f"ADDM: {addm_item['addm_name']} - {addm_item['addm_host']}"
        ts = time()

        log.debug("<=CMD=> Run cmd %s on %s CMD: '%s'", operation_cmd.command_key, addm_instance, operation_cmd.command_value)
        if cmd:
            # noinspection PyBroadException
            try:
                resp_l = self.invoke_interactive(ssh, cmd, addm_instance)
                output_d = {cmd_k: dict(resp_l=resp_l, addm=addm_instance, cmd_item=cmd, timest=time() - ts)}
                out_q.put(output_d)
            except Exception as e:
                log.error("<=ADDM Oper=> Error during operation for: %s %s", cmd, e)
                out_q.put({cmd_k: dict(out='Traceback', err=e, addm=addm_instance)})
        else:
            msg = '<=CMD=> Skipped for "{}" {}'.format(cmd_k, addm_instance)
            log.info(msg)
            out_q.put({cmd_k: dict(out='Skipped', msg=msg, addm=addm_instance)})

    @staticmethod
    def invoke_interactive(ssh, cmd, addm_instance):
        resp = "Nothing executed."
        resp_l = []

        # Initial run:
        buff = b''
        iter_n = 0
        shell = ssh.invoke_shell()
        while not buff.endswith(b' ~]$ '):
            resp = shell.recv(9999)
            buff += resp
            iter_n += 1
            msg = f"STEP 1 Iter: {iter_n} response: {resp.decode('utf-8').replace(chr(27), ';').replace('[0G', '#').replace('[K', '|').replace('  ', ' ')}"
            # log.debug(msg)
            resp_l.append(msg)
            sleep(2)

        shell.send(cmd + '\n')  # Send CMD, clear Buffer to empty:
        sleep(2)
        shell.recv(9999)  # Get cmd from buffer to make it empty.
        buff = b''  # Wipe buff before wait for new resp

        iter_n = 0
        while buff.find(b'Finished interactive CMD') < 0:
            resp = shell.recv(9999)
            iter_n += 1
            buff += resp
            msg = f"STEP 2 Iter: {iter_n} response: {resp.decode('utf-8').replace(chr(27), ';').replace('[0G', '#').replace('[K', '|').replace('  ', ' ')}"
            log.debug(msg)
            resp_l.append(msg)
            sleep(30)  # Most operations will run longer that 30 sec.

            # Check:
            if b'Finished interactive CMD' in buff:
                msg = f'Finished interactive CMD: {addm_instance} Out: {resp.decode("utf-8")}'
                log.info(msg)
                resp_l.append(f"FINISH: '{msg}' buffer: '{buff}'")
                return resp_l

            elif buff.find(b'ERROR: Failed to start services') > 0:
                msg = f'Failed to restart services: {addm_instance} Out: {resp.decode("utf-8")}'
                log.error(msg)
                resp_l.append(f"ERROR: '{msg}' buffer: '{buff}'")
                return resp_l

            elif buff.find(b'This machine is locked') > 0:
                msg = "Model wipe require unlock!"
                log.error(msg)
                resp_l.append(f"ERROR: '{msg}' buffer: '{buff}'")
                return resp_l

            elif buff.endswith(b' ~]$ '):
                msg = "Interactive CMD finished, shell new line!"
                log.warning(msg)
                resp_l.append(f"FINISH: '{msg}' buffer: '{buff}'")
                return resp_l

        resp_l.append(f"Finish ok: {resp.decode('utf-8')}")
        log.info("<=invoke_interactive=> Interactive CMD run finished! %s resp_l: %s", addm_instance, resp_l)
        return resp_l

    def run_operation_cmd(self, **kwargs):
        """
        Run one of more operation cmd
        :return:
        """
        from octo_adm.tasks import TaskADDMService

        command_key = kwargs.get('command_key', [])
        commands_set = kwargs.get('commands_set', [])
        fake_run = kwargs.get('fake_run', False)

        assert isinstance(command_key, list), "command_key should be a list!"

        tasks_ids = dict()
        addm_set = self.addm_set_selections(**kwargs)
        addm_group_l = self.addm_groups_distinct_validate(addm_set, fake_run)
        # log.info("<=ADDMStaticOperations=> Validated list of ADDM groups: %s", addm_group_l)

        if not commands_set:
            commands_set = self.select_operation(command_key)
        # Run new instance of task+threaded for each command:
        for operation_cmd in commands_set:
            # Assign each task on related worker based on ADDM group name:FAKE_RUN:
            for addm_ in addm_group_l:
                # Get only one current addm group from iter step
                addm_grouped_set = addm_set.filter(addm_group__exact=addm_)
                t_tag = f'tag=t_addm_cmd_thread;type=task;command_k={operation_cmd.command_key};'
                t_kwargs = dict(addm_set=addm_grouped_set, operation_cmd=operation_cmd, fake_run=fake_run)
                task = Runner.fire_t(TaskADDMService.t_addm_cmd_thread, fake_run=fake_run,
                                     t_queue=f'{addm_}@tentacle.dq2',
                                     t_args=[t_tag],
                                     t_kwargs=t_kwargs,
                                     t_routing_key=f'{addm_}.run_operation_cmd.TaskADDMService.t_addm_cmd_thread'
                                     )
                tasks_ids.update({addm_: task.id})
        return tasks_ids

    @staticmethod
    def addm_set_selections(**kwargs):
        """
        Select any amount of ADDM machines by:
        - addm row id
        - addm group
        - addm hostname
        - addm branch
        Sort by group as default option.

        :param kwargs:
        :return:
        """
        addm_id = kwargs.get('addm_id', [])
        addm_group = kwargs.get('addm_group', [])
        addm_host = kwargs.get('addm_host', [])
        # Initially query for all enabled:
        all_addms = AddmDev.objects.filter(disables__isnull=True)
        if addm_id:
            if isinstance(addm_id, str):
                addm_id = addm_id.split(',')
            log.debug("<=ADDMStaticOperations=> ADDM selected by addm_id: %s", addm_id)
            all_addms = all_addms.filter(id__in=addm_id)
        if addm_group:
            if isinstance(addm_group, str):
                addm_group = addm_group.split(',')
            log.debug("<=ADDMStaticOperations=> ADDM selected by addm_group: %s", addm_group)
            all_addms = all_addms.filter(addm_group__in=addm_group)
        if addm_host:
            if isinstance(addm_host, str):
                addm_host = addm_host.split(',')
            log.debug("<=ADDMStaticOperations=> ADDM selected by addm_host: %s", addm_host)
            all_addms = all_addms.filter(addm_host__in=addm_host)
        # log.info("<=ADDMStaticOperations=> ADDM branch sel query: %s", all_addms.query)
        # log.info("<=ADDMStaticOperations=> ADDM selected count: %s", all_addms.count())
        # log.debug("<=ADDMStaticOperations=> ADDM selected: %s", all_addms)
        # log.debug("<=ADDMStaticOperations=> ADDM selected query: %s", all_addms.query)
        # is this is not too danger to return all enabled addms?
        return all_addms.order_by('addm_group')

    def addm_groups_distinct_validate(self, addm_set, fake_run=None):
        """
        Make list of unique addm_groups values, then add a sleep task for each related worker after
        successful ping of all workers.
        :param fake_run:
        :param addm_set:
        :return: list of addm groups.
        """
        _addm_groups = []
        for addm_ in addm_set.values('addm_group').distinct():
            _addm_groups.append(addm_.get('addm_group'))
        addm_group_l = self.addm_groups_validate(addm_group=_addm_groups, occupy_sec=1,
                                                 fake_run=fake_run)  # type: list
        return addm_group_l

    @staticmethod
    def addm_groups_validate(**kwargs):
        """
        Complete initial checks of workers health and availability and exec busy tasks.
        :param kwargs:
        :return:
        """
        from octo.tasks import TSupport
        from octo.helpers.tasks_oper import WorkerOperations

        addm_group_l = kwargs.get('addm_group', [])
        user_name = kwargs.get('user_name', 'cron')
        occupy_sec = kwargs.get('occupy_sec', 40)
        fake_run = kwargs.get('fake_run', False)

        t_tag = f'tag=addm_groups_validate;type=routine;user_name={user_name}'
        if not isinstance(addm_group_l, list):
            addm_group_l = addm_group_l.split(',')

        # TODO: Return simply the group without ping, verification and occupy.
        if fake_run:
            return addm_group_l
        if settings.DEV:
            return addm_group_l

        if isinstance(addm_group_l, list):
            ping_list = WorkerOperations().service_workers_list[:]
            for _worker in addm_group_l:
                if "@tentacle" not in _worker:
                    _worker = f"{_worker}@tentacle"
                ping_list.append(_worker)
            worker_up = WorkerOperations().worker_heartbeat(worker_list=ping_list)
            if worker_up.get('down'):
                log.error("Some workers may be down: %s - sending email!", worker_up)
                subject = f'Worker is down, cannot run all other tasks. W: {worker_up}'
                body = f'Found some workers are DOWN while run (addm_groups_validate) List: {worker_up}'
                admin = mails['admin']
                Mails.short(subject=subject, body=body, send_to=[admin])
                # Nothing else to do here.
                raise Exception(subject)
            else:
                for addm_group in addm_group_l:
                    occupy_sec += 1
                    t_tag_busy = f"{t_tag} | sleep {occupy_sec} Check addm group."
                    addm_val_kw = dict(occupy_sec=occupy_sec, addm_group=addm_group,
                                       ping_list=ping_list, user_name=user_name)
                    Runner.fire_t(TSupport.t_occupy_w, fake_run=fake_run,
                                  t_args=[t_tag_busy, occupy_sec],
                                  t_kwargs=addm_val_kw,
                                  t_queue=f'{addm_group}@tentacle.dq2',
                                  t_routing_key = f'{addm_group}.t_occupy_w')
                return addm_group_l


class ADDMOperations:

    def __init__(self):
        self.host_keys = os.path.join(place, 'addms')
        self.private_key = os.path.join(self.host_keys, 'private_key', 'Octo_ssh_key')

    @staticmethod
    def select_addm_set(addm_group=None, addm_set=None):
        """
        When addm set was selected BEFORE this step - just return itself.
        When addm set was not selected BUT addm group is present - select addm set
            based on it's group name.
        When NO addm set and NO addm group - select ALL addms from database.

        When addm_group is a list - return list of querysets for selected addm groups

        Be careful!

        :param addm_group:
        :param addm_set:
        :return:
        """
        selected_addms_l = []
        if not addm_set:
            log.info("<=ADDMOperations=> Selecting addm set.")
            if addm_group:
                log.info(f"<=ADDMOperations=> Selecting addm set by addm_group: {addm_group}")
                if addm_group == 'all':
                    addm_set = AddmDev.objects.filter(disables__isnull=True).values()
                elif isinstance(addm_group, list):
                    log.info(f"<=ADDMOperations=> Selecting addm set by addm_group list: {addm_group}")
                    for addm_group_item in addm_group:
                        if '@tentacle' in addm_group_item:
                            addm_group_item = addm_group_item.replace('@tentacle', '')

                        addm_set = AddmDev.objects.filter(addm_group__exact=addm_group_item, disables__isnull=True).values()
                        selected_addms_l.append(addm_set)
                    return selected_addms_l
                else:
                    log.info(f"<=ADDMOperations=> Selecting addm set by addm_group not a list and not 'all': {addm_group}")
                    addm_set = AddmDev.objects.filter(addm_group__exact=addm_group, disables__isnull=True).values()
                    log.debug("<=ADDMOperations=> Use select_addm_set. ADDM group used: (%s)", addm_group)
            else:
                log.info(f"<=ADDMOperations=> Selecting everything!")
                addm_set = AddmDev.objects.filter(disables__isnull=True).values()
                log.debug("<=ADDMOperations=> Use select_addm_set. Use all ADDMs!")
        return addm_set

    def ssh_c(self, **kwargs):
        """
        Create active SSH connection, then validate and show SUCCESS or ERROR.
        Return SSH connection obj.
        Raise errors where this function were called, not here!

        :param kwargs:
        :return:
        """
        addm_item = kwargs.get('addm_item')
        addm_ip = addm_item.get('addm_ip')
        tideway_user = addm_item.get('tideway_user')
        tideway_pdw = addm_item.get('tideway_pdw')

        addm_str = f'ADDM: "{addm_item["addm_group"]}" {addm_item["addm_name"]} - {addm_item["addm_host"]}'
        ssh = self.addm_ssh_connect(addm_ip, tideway_user, tideway_pdw)
        # If opened connection is Up and alive:
        if ssh and ssh.get_transport().is_active():
            # NOTE: Do not handle error here: later decide what to do in thread initialize or so.
            msg = '<=SSH=> SUCCESS: {}'.format(addm_str)
            log.debug(msg)
        # When SSH is not active - skip thread for this ADDM and show log error (later could raise an exception?)
        else:
            msg = '<=SSH=> ERROR: {}'.format(addm_str)
            log.error(msg)
            # NOTE: Do not handle error here: later decide what to do in thread initialize or so.
            ssh = None
        return ssh

    def addm_ssh_connect(self, addm_ip, tideway_user, tideway_pdw):
        """
        Check if can SSH to selected ADDM.
        :param tideway_pdw: str
        :param tideway_user: str
        :param addm_ip: str
        :rtype type: SSHClient
        """
        addm_instance = f"ADDM: {addm_ip} {tideway_user}"
        ssh = paramiko.SSHClient()  # type: SSHClient
        if addm_ip and tideway_user and tideway_pdw:
            private_key = paramiko.RSAKey.from_private_key_file(self.private_key)
            ssh.get_host_keys().save(self.host_keys + os.sep + "keys_" + str(addm_ip) + ".key")
            ssh.save_host_keys(self.host_keys + os.sep + "keys_" + str(addm_ip) + ".key")
            # ssh.load_system_host_keys(self.host_keys + os.sep + "keys_" + str(addm_ip) + ".key")
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # noinspection PyBroadException
            try:
                ssh.connect(hostname=addm_ip, username=tideway_user, pkey=private_key,
                            timeout=60,  # Let connection live forever?
                            banner_timeout=60,
                            allow_agent=False, look_for_keys=False, compress=True)
                transport = ssh.get_transport()
                transport.set_keepalive(20)

            except paramiko.ssh_exception.AuthenticationException as e:
                m = f"Authentication failed \n{addm_instance}\nError: -->{e}<--"
                log.error(m)
                return None
                # raise Exception(m)
            except TimeoutError as e:
                m = f"TimeoutError: Connection failed. Host or IP of ADDM is not set or incorrect! " \
                    "\n{addm_instance}\nError: --> s{e} <--"
                log.error(m)
                return None
                # raise Exception(m)
            except paramiko.ssh_exception.BadHostKeyException as e:
                m = f"BadHostKeyException: which I do not know: \n{addm_instance}\nError: --> s{e} <--"
                log.error(m)
                return None
                # raise Exception(m)
            except paramiko.ssh_exception.SSHException as e:
                m = f"SSHException: \n{addm_instance}\nError: --> {e} <--"
                log.error(m)
                return None
                # raise Exception(m)
            # Paramiko SSHException which I do not know: No existing session
            except Exception as e:
                if 'No existing session' in e:
                    m = f"1. Catching  'No existing session' Trying to reconnect again. {addm_instance}\nError: -->{e}<--"
                    log.error(m)
                    # Try reconnect:
                    try:
                        ssh.connect(hostname=addm_ip, username=tideway_user, password=tideway_pdw,
                                    timeout=60,  # Let connection live forever?
                                    banner_timeout=60,
                                    allow_agent=False, look_for_keys=False, compress=True)
                        transport = ssh.get_transport()
                        transport.set_keepalive(20)
                    except Exception as e:
                        # TODO: This may be a reason for another deadlock?
                        m = f"2. No luck with this error. Try not raise to allow thread reconnect it later. " \
                            f"Exception: \n{addm_instance}\nError: --> {e} <--"
                        log.error(m)
                        raise Exception(m)
        return ssh

    @staticmethod
    def upload_unzip(**kwargs):
        """
        Execute ADDM command tw_pattern_management with install-activate key
        and execute upload testing saving STD outputs to Database

        Zips:
        /usr/tideway/UPLOAD/edp/Extended-Data-Pack-2068-04-1-ADDM-11.3+.zip
        /usr/tideway/UPLOAD/tku/Technology-Knowledge-Update-2068-04-1-ADDM-11.3+.zip
        /usr/tideway/UPLOAD/tku/Technology-Knowledge-Update-Storage-2068-04-1-ADDM-11.3+.zip

        Unzip


        :param ssh:
        :param addm_item:
        :param tku_zip_list:
        :return:
        """
        # TODO: Abort an further execution if zip fails to load
        test_q = kwargs.get('test_q')
        ssh = kwargs.get('ssh')
        addm_item = kwargs.get('addm_item')
        packages = kwargs.get('packages')
        development = kwargs.get('development', False)

        outputs_l = []
        tku_zip_cmd_l = []
        # Prepare zip commands with paths for each addm version:
        clean_tku_TEMP = ADDMStaticOperations.select_operation(['wipe.tideway.TEMP', 'mkdir.tideway.TEMP']).order_by('-command_value')

        # TODO: Save release.txt output
        # catZipRelease = ADDMStaticOperations.select_operation('cat.tku_zip.release').first()

        unzipTkuTemp = ADDMStaticOperations.select_operation('unzip.tku.TEMP').first()
        rmTidewayTempRelease = ADDMStaticOperations.select_operation('rm.tideway.TEMP.release').first()

        # Compose commands for single ADDM:
        # TODO: Think to set newer addm package for dev apl like 12.0 when addm is 11.90
        log.debug(f"Using packages: {packages}")
        log.debug(f"Development: {development}")
        if development:
            package_ = packages
            for p in package_:
                log.debug(f"Development packages will be used: {p}")
        else:
            package_ = packages.filter(addm_version__exact=addm_item['addm_v_int'])

        zip_path = [package.zip_file_path.replace('/home/user/TH_Octopus', '/usr/tideway') for package in package_]
        clean_cmd_l = [cmd.command_value for cmd in clean_tku_TEMP]
        tku_zip_cmd_l.extend(clean_cmd_l)

        tku_zip_cmd_l.extend([unzipTkuTemp.command_value.format(path_to_zip=zip_) for zip_ in zip_path])
        tku_zip_cmd_l.append(rmTidewayTempRelease.command_value)
        log.info(f"{addm_item['addm_name']} upload_unzip commands: {tku_zip_cmd_l}")

        # noinspection PyBroadException
        for cmd in tku_zip_cmd_l:
            try:
                _, stdout, stderr = ssh.exec_command(cmd)
                std_output, stderr_output = out_err_read(
                    out=stdout, err=stderr, cmd=cmd, mode='error',
                    name='upload_unzip on {}'.format(addm_item['addm_name']))
                if stderr_output:
                    log.error("<=ADDM Oper=> upload_unzip -> stderr_output: %s", stderr_output)
                outputs_l.append(dict(cmd=cmd, stdout=std_output, stderr=stderr_output))
            except Exception as e:
                log.debug(f"<=ADDM Oper=> CMD LIST {tku_zip_cmd_l}")
                msg = f'<=ADDM Oper=> Error during upload_unzip for: {cmd} {e} {addm_item["addm_name"]} ON {addm_item["addm_host"]}'
                log.error(msg)
                raise Exception(msg)
        test_q.put(outputs_l)
