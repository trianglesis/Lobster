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

import datetime
# Python logger
import logging
import os
import re
from time import sleep
from time import time
from django.db.models.query import QuerySet

# noinspection PyCompatibility
import paramiko
from paramiko import SSHClient

from octo.config_cred import mails
from octo.helpers.tasks_run import Runner
from octo.helpers.tasks_mail_send import Mails
from run_core.models import AddmDev, ADDMCommands

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
            operations = operations.filter(command_key__exact='show_addm_version')
        log.info("All selected operations count: %s by command_key %s", operations.count(), command_key)
        return operations

    def threaded_exec_cmd(self, **kwargs):
        from queue import Queue
        from threading import Thread

        addm_set = kwargs.get('addm_set', None)
        operation_cmd = kwargs.get('operation_cmd', None)
        fake_run = kwargs.get('fake_run', False)

        log.debug("addm_set: %s %s", addm_set, type(addm_set))
        log.debug("FAKE_RUN: %s", fake_run)

        assert isinstance(addm_set, QuerySet), 'Should be AddmDev QuerySet'
        assert isinstance(operation_cmd, ADDMCommands), 'Should be ADDMCommands QuerySet'
        cmd_k = operation_cmd.command_key
        th_list = []
        th_out = []
        ts = time()
        out_q = Queue()
        addm_set = addm_set.values()
        for addm_item in addm_set:
            log.debug("addm_item: %s %s", addm_item, type(addm_item))

            # TODO: Remove for not home env
            if not fake_run:
                ssh = ADDMOperations().ssh_c(addm_item=addm_item, where="Executed from threading_exec")
            else:
                ssh = True

            if ssh:
                th_name = f'ADDMStaticOperations.threaded_exec_cmd: {addm_item["addm_group"]} - {addm_item["addm_host"]} {addm_item["addm_ip"]}'
                args_d = dict(out_q=out_q, addm_item=addm_item, operation_cmd=operation_cmd, ssh=ssh, fake_run=fake_run)
                try:
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
        return {cmd_k: th_out, 'time': time() - ts}

    @staticmethod
    def run_static_cmd(out_q, addm_item, operation_cmd, ssh, fake_run=None):
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
                # TODO: Remove for not home env
                if not fake_run:
                    _, stdout, stderr = ssh.exec_command(cmd)
                    output_d = {cmd_k: dict(out=stdout.readlines(),
                                            err=stderr.readlines(),
                                            addm=addm_instance,
                                            cmd_item=cmd,
                                            timest=time() - ts)}
                    log.debug("addm_exec_cmd: %s ADDM: %s", output_d, addm_instance)
                    out_q.put(output_d)
                else:
                    out_q.put(f'Fake run of cmd: {cmd_k} - "{cmd}" on: {addm_item["addm_name"]}')

            except Exception as e:
                log.error("<=ADDM Oper=> Error during operation for: %s %s", cmd, e)
                return {cmd_k: dict(out='Traceback', err=e, addm=addm_instance)}
        else:
            msg = '<=CMD=> Skipped for "{}" {}'.format(cmd_k, addm_instance)
            log.info(msg)
            return {cmd_k: dict(out='Skipped', msg=msg, addm=addm_instance)}

    def run_operation_cmd(self, **kwargs):
        """
        Run one of more operation cmd
        :return:
        """
        from octo_adm.tasks import TaskADDMService

        command_key = kwargs.get('command_key', None)
        fake_run = kwargs.get('fake_run', False)

        tasks_ids = dict()
        addm_set = self.addm_set_selections(**kwargs)
        addm_group_l = self.addm_groups_distinct_validate(addm_set, fake_run)
        log.info("<=ADDMStaticOperations=> Validated list of ADDM groups: %s", addm_group_l)
        commands_set = self.select_operation(command_key)
        # Run new instance of task+threaded for each command:
        for operation_cmd in commands_set:
            # Assign each task on related worker based on ADDM group name:
            for addm_ in addm_group_l:
                # Get only one current addm group from iter step
                addm_grouped_set = addm_set.filter(addm_group__exact=addm_)
                log.debug("addm_grouped_set: %s", addm_grouped_set)

                t_tag = f'tag=t_addm_cmd_thread;type=task;command_k={operation_cmd.command_key};'
                t_kwargs = dict(addm_set=addm_grouped_set, operation_cmd=operation_cmd, fake_run=True)
                task = TaskADDMService.t_addm_cmd_thread.apply_async(
                    queue=f'{addm_}@tentacle.dq2',
                    args=[t_tag],
                    kwargs=t_kwargs,
                    routing_key=f'{addm_}.addm_custom_cmd'
                )
                # task = Runner.fire_t(TaskADDMService.t_addm_cmd_thread, fake_run=fake_run,
                #                      t_queue=f'{addm_}@tentacle.dq2',
                #                      t_args=[t_tag],
                #                      t_kwargs=t_kwargs,
                #                      t_routing_key=f'{addm_}.addm_custom_cmd'
                #                      )
                log.debug("<=_old_addm_cmd=> Added task: %s", task)
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
        addm_branch = kwargs.get('addm_branch', [])
        # Initially query for all enabled:
        all_addms = AddmDev.objects.filter(disables__isnull=True)
        if addm_id:
            if isinstance(addm_id, str):
                addm_id = addm_id.split(',')
            log.debug("<=ADDMStaticOperations=> ADDM selected by: %s", addm_id)
            all_addms = all_addms.filter(id__in=addm_id)
        if addm_group:
            if isinstance(addm_group, str):
                addm_group = addm_group.split(',')
            log.debug("<=ADDMStaticOperations=> ADDM selected by: %s", addm_group)
            all_addms = all_addms.filter(addm_group__in=addm_group)
        if addm_host:
            if isinstance(addm_host, str):
                addm_host = addm_host.split(',')
            log.debug("<=ADDMStaticOperations=> ADDM selected by: %s", addm_host)
            all_addms = all_addms.filter(addm_host__in=addm_host)
        if addm_branch:
            if isinstance(addm_branch, str):
                addm_branch = addm_branch.split(',')
            log.debug("<=ADDMStaticOperations=> ADDM selected by: %s", addm_branch)
            all_addms = all_addms.filter(branch_lock__in=addm_branch)
        log.info("<=ADDMStaticOperations=> ADDM selected count: %s", all_addms.count())
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

        t_tag = f'tag=_old_addm_groups_validate;type=routine;user_name={user_name}'
        if not isinstance(addm_group_l, list):
            addm_group_l = addm_group_l.split(',')

        # TODO: Remove for not home env
        if fake_run:
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
                body = f'Found some workers are DOWN while run (_old_addm_groups_validate) List: {worker_up}'
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


# noinspection SpellCheckingInspection
class ADDMOperations:

    def __init__(self):
        # log.debug("Init ADDMOperations class")
        # noinspection PyUnresolvedReferences
        self.host_keys = os.path.join(place, 'addms')

        # TODO: This may be moved to database?
        self.cmd_d = dict(
            show_v=dict(
                name='Show ADDM vesrion',
                cmd='/usr/tideway/bin/tw_disco_control -v',
            ),
            wipe_tpl=dict(
                name='Wipe tpl after preproc',
                cmd='find /usr/tideway/SYNC/addm/tkn_main/tku_patterns/ -type d -name "tpl*[0-9]" -exec rm -rf {} +',
            ),
            wipe_log=dict(
                name='Wipe preproc and other logs',
                cmd='find /usr/tideway/SYNC/ -name "*.log" -type f -mtime +7 -delete',
            ),
            wipe_sync_log=dict(
                name='Wipe rsync logs',
                cmd='sudo find /usr/tideway/ -maxdepth 1 -name "sync_*.log" -type f -mtime +7 -delete',
            ),
            wipe_syslog=dict(
                name='Wipe addm syslogs old',
                cmd='sudo find /usr/tideway/log/ -name "*.gz" -type f -delete'
                # Do not want to delete...
                # cmd='sudo find /usr/tideway/log/ -type f -name "*.gz" -o -name "*.log.[0-9][0-9][0-9][0-9]*" -delete',
            ),
            wipe_pool=dict(
                name='Wipe pool data leftowers',
                cmd="find /usr/tideway/var/pool/ -maxdepth 1 -type d -not -name 'pool' -exec rm -rf {} +",
            ),
            wipe_record=dict(
                name='Wipe record data leftowers',
                cmd="find /usr/tideway/var/record/ -maxdepth 1 -type d -not -name 'record' -exec rm -rf {} +",
            ),
            wipe_temp=dict(
                name='Wipe /usr/tideway/TEMP',
                cmd="rm -f /usr/tideway/TEMP/*",
            ),
            wipe_data_installed_product_content=dict(
                name='Wipe: /usr/tideway/data/installed/tpl/product_content',
                addm_exceptions=['zythum', 'aardvark', 'bobblehat'],
                cmd='rm -rf /usr/tideway/data/installed/tpl/product_content/*',
            ),
            tw_pattern_management=dict(
                name='Wipe all installed TKU',
                cmd='/usr/tideway/bin/tw_pattern_management -p system --remove-all -f',
            ),
            _upload_unzip=dict(
                name='in DEV: Unzip selected TKU package',
                cmd='mkdir /usr/tideway/TEMP > /dev/null 2>&1',
            ),
            product_content=dict(
                name='Delete product_content rpm',
                addm_exceptions=['zythum', 'aardvark', 'bobblehat'],
                # cmd='sudo rpm -ev tideway-content-1.0*',
                cmd='''DEV_PROD_CONT=`rpm -qa | gawk 'match($0, /(tideway-content-1.0.+)/, a) {print a[1]}'` && sudo rpm -ev ${DEV_PROD_CONT}
                ''',
            ),
            tideway_devices=dict(
                name='Delete tideway_devices rpm',
                addm_exceptions=['zythum', 'aardvark', 'bobblehat'],
                # cmd='sudo rpm -ev tideway-content-1.0*',
                cmd='''DEV_TIDEWAY_DEVICES=`rpm -qa | gawk 'match($0, /(tideway-devices-.+)/, a) {print a[1]}'` && sudo rpm -ev $DEV_TIDEWAY_DEVICES
                ''',
            ),
            delete_rpm=dict(
                name='Delete installed rpm',
                addm_exceptions=['zythum', 'aardvark', 'bobblehat'],
                cmd='sudo rpm -ev {rpm}',
            ),
            tw_model_wipe=dict(
                name='Wipe addm model DB',
                interactive=True,
                interactive_shell=self.tw_model_wipe,
                cmd='/usr/tideway/bin/tw_model_wipe -p system --force',
            ),
            tw_tax_import=dict(
                name='Import latest taxonomy',
                addm_exceptions=['zythum', ],
                cmd='/usr/tideway/bin/tw_tax_import -p system --clear --verbose /usr/tideway/SYNC/addm/tkn_main/product_content/r1_0/code/data/installed/taxonomy/00taxonomy.xml',
                cmd_alt='/usr/tideway/bin/tw_tax_import -p system --clear --verbose /usr/tideway/data/installed/taxonomy/00taxonomy.xml',
            ),
            sync_prod_cont_python=dict(
                name='Sync product content',
                addm_exceptions=['zythum', 'aardvark', 'bobblehat', 'custard_cream'],
                cmd='rsync -a --progress -log-file=/usr/tideway/sync_prod_cont_python.log --include "*" --include "*/" /usr/tideway/TKU/addm/tkn_main/product_content/r1_0/code/python/ /usr/tideway/python',
                cmd_alt='sync back?',
            ),
            sync_prod_cont_data=dict(
                name='Sync product content',
                addm_exceptions=['zythum', 'aardvark', 'bobblehat', 'custard_cream'],
                cmd='rsync -a --progress '
                    '--log-file=/usr/tideway/sync_prod_cont_data.log '
                    '--include "*" --include "*/" '
                    '/usr/tideway/TKU/addm/tkn_main/product_content/r1_0/code/data/installed/ '
                    '/usr/tideway/data/installed',
                cmd_alt='sync back?',
            ),
            test_kill=dict(
                name='Kill test.py process',
                cmd="kill $(ps aux | grep '/usr/tideway/bin/python -u .*/tests/test.py --verbose' | awk '{print $2}')",
            ),
            tku_install_kill=dict(
                name='Kill pattern_management',
                cmd="kill $(ps aux | grep 'pattern_management.pyc -p system --install-activate' | awk '{print $2}')",
            ),
            tw_scan_control=dict(
                name='Discard curent discovery scan',
                cmd='/usr/tideway/bin/tw_scan_control -p system --clear',
            ),
            tideway_restart=dict(
                name='Restart tideway services on RedHat appliance and CentOS',
                cmd='sudo service tideway restart',
                # cmd_alt='/usr/tideway/startup/tideway restart',
                cmd_alt='/usr/tideway/bin/tw_service_control --restart',
                addm_exceptions=['double_decker'],
                interactive=True,
                interactive_shell=self.restart_tideway,
                # interactive_shell_alt = 'Place here: Interactive shell with CentOS',
            ),
            tw_restart_service=dict(
                name='Restart tideway service',
                addm_exceptions=['double_decker'],
                cmd='sudo service tideway restart {service}',
                interactive=True,
                format_arg=True,
                interactive_shell=self.restart_tideway,
                # For example;
                cmd_alt='/usr/tideway/bin/tw_service_control --restart {service}',
            )
        )

    @staticmethod
    def select_addm_set(addm_group=None, addm_set=None):
        """
        When addm set was selected BEFORE this step - just return itself.
        When addm set was not selected BUT addm group is present - select addm set
            based on it's group name.
        When NO addm set and NO addm group - select ALL addms from database.

        When addm_group is a list - return list of querysets for selected addm groups

        Be carefull!

        :param addm_group:
        :param addm_set:
        :return:
        """
        selected_addms_l = []
        if not addm_set:
            if addm_group:
                if addm_group == 'all':
                    addm_set = AddmDev.objects.filter(disables__isnull=True).values()
                elif isinstance(addm_group, list):
                    for addm_group_item in addm_group:
                        if '@tentacle' in addm_group_item:
                            addm_group_item = addm_group_item.replace('@tentacle', '')

                        addm_set = AddmDev.objects.filter(addm_group__exact=addm_group_item, disables__isnull=True).values()
                        selected_addms_l.append(addm_set)
                    return selected_addms_l
                else:
                    addm_set = AddmDev.objects.filter(addm_group__exact=addm_group, disables__isnull=True).values()
                    log.debug("<=ADDMOperations=> Use select_addm_set. ADDM group used: (%s)", addm_group)
            else:
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
        where = kwargs.get('where', None)
        addm_item = kwargs.get('addm_item')

        addm_ip = addm_item.get('addm_ip')
        tideway_user = addm_item.get('tideway_user')
        tideway_pdw = addm_item.get('tideway_pdw')

        addm_str = 'ADDM: "{}" {} - {} = ({})'.format(
            addm_item['addm_group'],
            addm_item['addm_name'],
            addm_item['addm_host'],
            addm_item['addm_ip'],
        )

        ssh = self.addm_ssh_connect(addm_ip, tideway_user, tideway_pdw, where)
        # If opened connection is Up and alive:
        if ssh and ssh.get_transport().is_active():
            # NOTE: Do not handle error here: later decide what to do in thread initialize or so.
            msg = '<=ADDMOperations SSH=> SUCCESS: {} From: {} '.format(addm_str, where)
            log.debug(msg)
        # When SSH is not active - skip thread for this ADDM and show log error (later could raise an exception?)
        else:
            msg = '<=ADDMOperations SSH=> ERROR: {} From: {} '.format(addm_str, where)
            log.error(msg)
            # NOTE: Do not handle error here: later decide what to do in thread initialize or so.
            ssh = None
        return ssh

    def addm_ssh_connect(self, addm_ip, tideway_user, tideway_pdw, where=None):
        """
        Check if can SSH to selected ADDM.

        No existing session:
        - https://stackoverflow.com/questions/6832248/paramiko-no-existing-session-exception

        :param where:
        :param tideway_pdw: str
        :param tideway_user: str
        :param addm_ip: str
        :rtype type: SSHClient
        """
        addm_instance = "ADDM: {} {} {}".format(addm_ip, tideway_user, tideway_pdw)
        ssh = paramiko.SSHClient()  # type: SSHClient

        if not where:
            where = 'PARAMIKO SSH Executed from itself!'
        log.info("<= Paramiko => %s", where)

        if addm_ip and tideway_user and tideway_pdw:

            # noinspection PyUnresolvedReferences
            ssh.get_host_keys().save(self.host_keys + os.sep + "keys_" + str(addm_ip) + ".key")
            # noinspection PyUnresolvedReferences
            ssh.save_host_keys(self.host_keys + os.sep + "keys_" + str(addm_ip) + ".key")
            # ssh.load_system_host_keys(self.host_keys + os.sep + "keys_" + str(addm_ip) + ".key")
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # noinspection PyBroadException
            try:
                ssh.connect(hostname=addm_ip, username=tideway_user, password=tideway_pdw,
                            timeout=60,  # Let connection live forever?
                            banner_timeout=60,
                            allow_agent=False, look_for_keys=False, compress=True)
                transport = ssh.get_transport()
                transport.set_keepalive(20)

            except paramiko.ssh_exception.AuthenticationException as e:
                m = "Authentication failed \n{}\nError: -->{}<--".format(addm_instance, e)
                log.error(m)
                return None
                # raise Exception(m)
            except TimeoutError as e:
                m = "TimeoutError: Connection failed. Host or IP of ADDM is not set or incorrect! " \
                    "\n{}\nError: --> s{} <--".format(addm_instance, e)
                log.error(m)
                return None
                # raise Exception(m)
            except paramiko.ssh_exception.BadHostKeyException as e:
                m = "BadHostKeyException: which I do not know: \n{}\nError: --> s{} <--".format(addm_instance, e)
                log.error(m)
                return None
                # raise Exception(m)
            except paramiko.ssh_exception.SSHException as e:
                m = "SSHException: \n{}\nError: --> {} <--".format(addm_instance, e)
                log.error(m)
                return None
                # raise Exception(m)
            # Paramiko SSHException which I do not know: No existing session
            except Exception as e:
                if 'No existing session' in e:
                    m = "1. Catching  'No existing session' Trying to reconnect again. {}\nError: -->{}<--".format(
                        addm_instance, e)
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
                        m = "2. No luck with this error. " \
                            "Try not raise to allow thread reconnect it later. " \
                            "Exception: \n{}\nError: --> {} <--".format(addm_instance, e)
                        log.error(m)
                        raise Exception(m)
        return ssh

    # noinspection PyCompatibility
    def make_addm_sync_threads(self, **kwargs):
        """
        Run each test in pair of connected ADDM instance separately from each other.
        Each this instance is an instance of SSH console of active ADDM + added
        test args to test_exec(). Execute each test.
        """
        from queue import Queue
        from threading import Thread

        addm_items = kwargs.get('addm_items')

        thread_list = []
        sync_out = []
        ts = time()
        sync_q = Queue()
        for addm_item in addm_items:
            # Open SSH connection:
            ssh = ADDMOperations().ssh_c(addm_item=addm_item, where="Executed from make_addm_sync_threads in ADDMOperations")
            # If opened connection is Up and alive:
            if ssh:
                kwargs_d = dict(ssh=ssh, addm_item=addm_item, sync_q=sync_q)
                th_name = 'Sync thread: addm {}'.format(addm_item['addm_ip'])
                try:
                    test_thread = Thread(target=self.sync_addm, name=th_name, kwargs=kwargs_d)
                    test_thread.start()
                    thread_list.append(test_thread)
                except Exception as e:
                    msg = "Thread test fail with error: {}".format(e)
                    log.error(msg)
                    raise Exception(msg)
            # When SSH is not active - skip thread for this ADDM and show log error (later could raise an exception?)
            else:
                msg = '<=make_addm_sync_threads=> SSH Connection could not be established, ' \
                      'thread skipping for ADDM: {} - {} in {}'.format(addm_item['addm_ip'], addm_item['addm_host'],
                                                                       addm_item['addm_group'])
                log.error(msg)
                sync_out.append(msg)
                # Send mail with this error? BUT not for the multiple tasks!!!

        for test_th in thread_list:
            test_th.join()
            sync_out.append(sync_q.get())
        return 'All addm sync Took {} Out {}'.format(time() - ts, sync_out)

    def sync_addm(self, **kwargs):
        """
        Construct threading for each addm and tests.
        Freeze addm with tests for threading.
        {'root_pwd': 'tidewayroot',
         'addm_v_int': '11.2',
         'is_synced': 1,
         'check_bashrc': 1,
         'fstab_check': 0,
         'nfs_helper_moved': 0,
         'new_fstab': 0,
         'check_fs_tree': 0,
         'tideway_user': 'tideway',
         'addm_branch': 'r11_2_0_x',
         'nfs_helper': 0,
         'root_user': 'root',
         'pass_ok': 1,
         'addm_is_dev': 1,
         'BAK_fstab': 0,
         'addm_v_code': 'ADDM_11_2',
         'addm_name': 'custard_cream',
         'check_mounts': 1,
         'mount_success': 0,
         'tideway_pdw': 'S0m3w@y',
         'addm_owner': 'Alex D',
         'addm_ip': '172.25.144.118',
         'check_fstab': 1,
         'addm_host': 'vl-aus-tkudev-38'}


        :return:
        """
        ssh = kwargs.get('ssh')
        sync_q = kwargs.get('sync_q')
        addm = kwargs.get('addm_item')

        addm_name = addm.get('addm_name')
        addm_host = addm.get('addm_host')
        addm_group = addm.get('addm_group')
        ts = time()

        tku_sync = self.rsync_tku_data(ssh=ssh, addm_item=addm)
        utils_sync = self.rsync_testutils(ssh=ssh, addm_item=addm)
        log.info("<=ADDMOperations=> make_addm_sync_single %s - %s %s", addm_name, addm_host, addm_group)

        all_syncs_dict = dict(
            sync_addm='{} {} {}'.format(addm_group, addm_name, addm_host),
            sync_status=dict(tku_sync=tku_sync, utils_sync=utils_sync, timest=time() - ts))
        # Close previously opened SSH:
        ssh.close()
        # Put test results into a thread queue output:
        sync_q.put(all_syncs_dict)

    @staticmethod
    def rsync_tku_data(ssh, addm_item):
        """
        Use set of ssh connections and execute sync for each.

        It does not sync tkn_main/python and tkn_main/buildscripts -
        because they should be used from NFS places.

        If fails - add sync for tkn_main/python and tkn_main/buildscripts!
        And update bashrc to point new directions!

        When OK:
            [tideway@vl-aus-tkudev-38 ~]$ rsync -a --progress --prune-empty-dirs
                    --log-file=/usr/tideway/rsync_test.log
                    --include "*/" --include="*.tplpre" --include="TEST" --include="*.py"
                    --include="*.dml" --include="*.model" --exclude="*"
                    /usr/tideway/TKU/addm/tkn_main/buildscripts/ ///addm/tkn_main/buildscripts/
            building file list ...
            24 files to consider

            sent 588 bytes  received 12 bytes  1200.00 bytes/sec
            total size is 397897  speedup is 663.16

        BAD Place FROM:
            building file list ...
            rsync: link_stat "/usr/tideway/TKU/addm/tkn_main/buildscripts/ERR" failed: No such file or directory (2)
            0 files to consider

            sent 18 bytes  received 12 bytes  60.00 bytes/sec
            total size is 0  speedup is 0.00
            rsync error: some files/attrs were not transferred
            (see previous errors) (code 23) at main.c(1039) [sender=3.0.6]

        Do not exclude:
        rsync_includes = '--include "*" --include "*/" ' \
                         '--include="*.tplpre" ' \
                         '--include="TEST" ' \
                         '--include="*.py" ' \
                         '--include="*.dml" ' \
                         '--include="*.model" '


        :return:
        """
        addm_name = addm_item.get('addm_name', "None")
        addm_host = addm_item.get('addm_host', "None")

        sync_error_re = re.compile(r"^0\sfiles\sto\sconsider")
        start_time = datetime.datetime.now()
        start_time_format = start_time.strftime('%Y-%m-%d_%H-%M-%S')

        # DO NOT EXCLUDE!
        rsync_cmd = "rsync -a --progress --prune-empty-dirs "
        rsync_log = "--log-file=/usr/tideway/sync_tkn_main_" + str(start_time_format) + "_.log "
        rsync_includes_all = '--include "*" --include "*/" '
        path_from = "/usr/tideway/TKU/addm/ "
        path_to = "/usr/tideway/SYNC/addm/ "
        rsync_command = rsync_cmd + rsync_log + rsync_includes_all + path_from + path_to

        log.debug("rsync_command: %s", rsync_command)

        # noinspection PyBroadException
        try:
            _, stdout, stderr = ssh.exec_command(rsync_command)
            raw_out, raw_err = out_err_read(out=stdout, err=stderr, name='Sync TKU', cmd=rsync_command,
                                            mode='error')
            if re.match(sync_error_re, raw_out):
                out_msg = "<= SYNC ADDM => raw_out: {} raw_err: {} | ON: {} | HOST {} ".format(
                    raw_out, raw_err, addm_name, addm_host)
                log.error(out_msg)
                raise Exception('Sync TKU failed: {} - {}'.format(addm_name, addm_host))
            else:
                success_msg = "<=SYNC ADDM=> from {} to {}. \nnfs '{}-{}'".format(
                    path_from, path_to, addm_name, addm_host)
                log.info(success_msg)
                return 'Synced TKU: {} - {}'.format(addm_name, addm_host)
        except Exception as e:
            msg = "<=SYNC ADDM=> Error addm_rsync_all: | CMD {} Host {} Ex: {}".format(rsync_command, addm_host, e)
            log.error(msg)
            raise Exception(msg)

    @staticmethod
    def rsync_testutils(ssh, addm_item):
        """
        Sync utils and testutils

        rsync -a --progress --prune-empty-dirs --log-file=/usr/tideway/sync_2017-10-05_20-23-23_.log
        /usr/tideway/TKU/utils/ /usr/tideway/utils/

        :param addm_item:
        :param ssh:
        :return:
        """
        addm_name = addm_item.get('addm_name', "None")
        addm_host = addm_item.get('addm_host', "None")

        start_time_format = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        rsync_log = "--log-file=/usr/tideway/sync_utils_" + str(start_time_format) + "_.log "

        sync_error_re = re.compile(r"^0\sfiles\sto\sconsider")
        rsync_cmd = "rsync -a --progress --prune-empty-dirs "
        # TESTUTILS SYNC
        from_testutils = "/usr/tideway/TKU/python/testutils/ "
        to_testutils = "/usr/tideway/python/testutils/ "
        rsync_testutils = rsync_cmd + rsync_log + from_testutils + to_testutils

        log.debug("rsync_testutils: %s", rsync_testutils)

        # UTILS SYNC
        from_utils = "/usr/tideway/TKU/utils/ "
        to_utils = "/usr/tideway/utils/ "
        rsync_utils = rsync_cmd + rsync_log + from_utils + to_utils

        log.debug("rsync_utils: %s", rsync_utils)

        cmd_t = rsync_testutils, rsync_utils
        for cmd in cmd_t:
            try:
                _, stdout, stderr = ssh.exec_command(cmd)
                raw_out, raw_err = out_err_read(out=stdout, err=stderr, name='utils/testutils', cmd=cmd, mode='error')
                if re.match(sync_error_re, raw_out):
                    out_msg = "<=SYNC ADDM=> out: {} err: {} on '{} {}'".format(raw_out, raw_err, addm_name, addm_host)
                    log.error(out_msg)
                    raise Exception('Sync utils/testutils failed: {} - {}'.format(addm_name, addm_host))
                else:
                    ok_msg = "<=SYNC ADDM=> CMD {} on '{} {}'".format(cmd, addm_name, addm_host)
                    log.info(ok_msg)
                    return 'Synced utils/testutils: {} - {}'.format(addm_name, addm_host)
            except Exception as e:
                msg = "<=SYNC ADDM=> Error utils/testutils: | Host {} Exception: {}".format(addm_item, e)
                log.error(msg)
                raise Exception(msg)

    def addm_exec_cmd(self, ssh, addm_item, cmd_k, service=None, rpm=None):
        cmd_item = self.cmd_d.get(cmd_k)
        addm_instance = "ADDM: {0} - {1}".format(addm_item['addm_name'], addm_item['addm_host'])
        ts = time()

        if cmd_k == 'tw_restart_service' and service:
            cmd_item.update(cmd=cmd_item['cmd'].format(service=service))
            cmd_item.update(cmd_alt=cmd_item['cmd_alt'].format(service=service))

        if cmd_k == 'delete_rpm' and rpm:
            cmd_item.update(cmd=cmd_item['cmd'].format(rpm=rpm))

        if addm_item['addm_name'] in cmd_item.get('addm_exceptions', []):
            cmd = cmd_item.get('cmd_alt', False)
            if cmd_k in ['tideway_restart', 'tw_restart_service']:
                cmd_item.pop('interactive_shell')  # Set to false for alt cmd
        else:
            cmd = cmd_item.get('cmd', False)

        log.debug("<=CMD=> Run cmd %s on %s CMD: '%s'", cmd_k, addm_instance, cmd)
        if cmd:
            if cmd_item.get('interactive_shell', False):
                cmd_shell = cmd_item['interactive_shell']
                # noinspection PyBroadException
                try:
                    # noinspection PyCallingNonCallable
                    interactive_run = cmd_shell(ssh, addm_item)
                    output_d = {cmd_k: interactive_run, 'timest': time() - ts}
                    log.debug("addm_exec_cmd: %s ADDM: %s", output_d, addm_instance)
                    return output_d
                except Exception as e:
                    log.error("<=ADDM Oper=> Error during operation for: %s %s", cmd, e)
                    return {cmd_k: dict(out='Traceback', err=e, addm=addm_instance)}
            else:
                # noinspection PyBroadException
                try:
                    _, stdout, stderr = ssh.exec_command(cmd)
                    output_d = {cmd_k: dict(out=stdout.readlines(),
                                            err=stderr.readlines(),
                                            addm=addm_instance,
                                            cmd_item=cmd,
                                            timest=time() - ts)}
                    log.debug("addm_exec_cmd: %s ADDM: %s", output_d, addm_instance)
                    return output_d
                except Exception as e:
                    log.error("<=ADDM Oper=> Error during operation for: %s %s", cmd, e)
                    return {cmd_k: dict(out='Traceback', err=e, addm=addm_instance)}
        else:
            msg = '<=CMD=> Skipped for "{}" {}'.format(cmd_k, addm_instance)
            log.info(msg)
            return {cmd_k: dict(out='Skipped', msg=msg, addm=addm_instance)}

    @staticmethod
    def tw_model_wipe(ssh, addm_item):
        """
        Execute addm_tw_model_wipe / tw_model_init
        https://docs.bmc.com/docs/display/DISCO90/tw_model_init

        [tideway@vl-aus-tkudev-38 ~]$ du -h /usr/tideway/var/localdisk/ | sort -hr | head -n 20
        1.3G    /usr/tideway/var/localdisk/tideway.db
        1.3G    /usr/tideway/var/localdisk/
        1.1G    /usr/tideway/var/localdisk/tideway.db/logs
        156M    /usr/tideway/var/localdisk/tideway.db/data/datadir
        156M    /usr/tideway/var/localdisk/tideway.db/data
        4.0K    /usr/tideway/var/localdisk/backup

        :return:
        """
        cmd = '/usr/tideway/bin/tw_model_wipe -p system --force'
        addm_instance = "ADDM: {0} - {1}".format(addm_item['addm_name'], addm_item['addm_host'])
        log.debug("<=ADDM Oper=> addm_tw_model_wipe -> wipe addm datastore! %s", addm_instance)
        # noinspection PyBroadException
        try:
            resp = ADDMConfigurations().addm_cmd_shell_model_wipe(ssh, cmd, addm_instance, addm_item['addm_name'])
            # ssh.close()
            if "CORBA.TRANSIENT" in resp:
                msg = "CORBA ERROR on: {} Output {}".format(addm_instance, resp)
                log.error(msg)
                return dict(tideway_restart=msg, addm=addm_instance)
            else:
                return dict(tideway_restart=resp, addm=addm_instance)
        except Exception as e:
            log.error("<=ADDM Oper=> Error on %s during: %s Exception: %s", addm_instance, cmd, e)
            return dict(tideway_model_wipe=e, addm=addm_instance)

    @staticmethod
    def restart_tideway(ssh, addm_item, service=None):
        """
        Execute sudo service tideway restart

        :return:
        """

        if service:
            cmd = 'sudo service tideway restart {}'.format(service)
        else:
            cmd = 'sudo service tideway restart'

        addm_instance = "ADDM: {0} - {1}".format(addm_item['addm_name'], addm_item['addm_host'])
        log.debug("<=ADDM Oper=> addm_restart_tideway -> '%s' %s", cmd, addm_instance)
        # noinspection PyBroadException
        try:
            resp = ADDMConfigurations().addm_cmd_shell_tideway_restart(ssh, cmd, addm_instance, addm_item['addm_name'])
            # ssh.close()
            if "CORBA.TRANSIENT" in resp:
                msg = "CORBA ERROR on: {} Output {}".format(addm_instance, resp)
                log.error(msg)
                return dict(tideway_restart=msg, addm=addm_instance)
            else:
                return dict(tideway_restart=resp, addm=addm_instance)
        except Exception as e:
            log.error("<=ADDM Oper=> Error on %s during: %s Exception: %s", addm_instance, cmd, e)
            return dict(tideway_restart=e, addm=addm_instance)

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
        test_q = kwargs.get('test_q')
        ssh = kwargs.get('ssh')
        addm_item = kwargs.get('addm_item')
        tku_zip_list = kwargs.get('tku_zip_list')

        # DELETE any TKU zips BEFORE unzip anything new:
        # TODO: create dir of not exist
        cmd_list = ['rm -f /usr/tideway/TEMP/*']
        TKU_temp = '/usr/tideway/TEMP'
        outputs_l = []

        for zip_item in tku_zip_list:
            log.debug("<=ADDM Oper=> TKU ZIP item: (%s)", zip_item)
            path_to_zip = zip_item.replace('/home/user/TH_Octopus', '/usr/tideway')
            cmd_list.append(f'unzip -o {path_to_zip} -d {TKU_temp}')

        cmd_list.append('rm -f /usr/tideway/TEMP/release.txt')

        log.debug("<=ADDM Oper=> CMD LIST %s", cmd_list)
        # noinspection PyBroadException
        for cmd in cmd_list:
            try:
                log.debug("Try execute: '%s' | on %s - %s ", cmd, addm_item['addm_host'], addm_item['addm_name'])
                _, stdout, stderr = ssh.exec_command(cmd)
                std_output, stderr_output = out_err_read(
                    out=stdout, err=stderr, cmd=cmd, mode='error',
                    name='upload_unzip on {}'.format(addm_item['addm_name']))
                # log.debug("<=ADDM Oper=> upload_unzip: \n\tstd_output: %s \n\tstderr_output: %s", std_output, stderr_output)
                if stderr_output:
                    log.error("<=ADDM Oper=> upload_unzip -> stderr_output: %s", stderr_output)
                outputs_l.append(dict(cmd=cmd, stdout=std_output, stderr=stderr_output))
            except Exception as e:
                msg = f'<=ADDM Oper=> Error during upload_unzip for: {cmd} {e} {addm_item["addm_name"]} ON {addm_item["addm_host"]}'
                log.error(msg)
                raise Exception(msg)
        test_q.put(outputs_l)
        return True


class ADDMConfigurations:

    @staticmethod
    def addm_cmd_shell_tideway_restart(ssh, cmd, addm_instance, addm_name):
        # resp = "Nothing executed."
        shell = ssh.invoke_shell()
        buff = b''
        iter_n = 0
        while not buff.endswith(b' ~]$ '):
            resp = shell.recv(9999)
            buff += resp
            iter_n += 1
            sleep(0.5)
            # log.debug("ITER: %s | Waiting for shell: %s", iter_n, resp)

        # Ssh and wait for the password prompt.
        log.debug("Send cmd: %s on: %s", cmd, addm_instance)
        shell.send(cmd + '\n')
        # log.debug("CMD Resp: %s", shell.recv(9999))
        # resp = "Shell invoked."
        "Restarting local BMC Discovery application services"
        buff = b''
        iter_n = 0
        while buff.find(b'Restarting local') < 0:
            resp = shell.recv(9999)
            buff += resp
            iter_n += 1
            sleep(0.5)
            # log.debug("ITER: %s | Waiting for 'Restarting local' in output: %s", iter_n, resp.decode('utf-8'))

        resp = "Restart cmd sent."
        buff = b''
        iter_n = 0

        while buff.find(b'Updating baseline') < 0:
            resp = shell.recv(9999)
            buff += resp
            iter_n += 1
            sleep(10)
            # log.debug("ITER: %s %s| TIDEWAY: %s", iter_n, addm_instance, resp.decode('utf-8')
            #           .replace("\x08", "").replace("\x1b", "").replace("[K", "")
            #           .replace("[60G[  [0;32mOK[0;39m  ]", "OK").replace("  ", " "))

            if buff.find(b'ERROR: Failed to start services') > 0:
                log.error("<=TW Restart=> Error while service restarts: on %s Error: \n--> %s \n<-- ",
                          addm_instance, resp.decode('utf-8'))
                msg = 'ERROR: Failed to restart services: {} Out: {}'.format(addm_instance, resp.decode('utf-8'))
                return msg

        log.info("<=ADDM Oper=> Tideway services restart initiated! %s", addm_name)
        return resp.decode('utf-8')

    @staticmethod
    def addm_cmd_shell_model_wipe(ssh, cmd, addm_instance, addm_name):
        """
            [tideway@vl-aus-rem-dv33 ~]$ /usr/tideway/bin/tw_model_wipe -p system --force

            WARNING: tw_model_wipe will delete all data, on all cluster members;
            all BMC Discovery data will be deleted!
              Do you wish to proceed? (y/n) y
            Checking

        :param ssh:
        :param cmd:
        :param addm_instance:
        :param addm_name:
        :return:
        """

        resp = "Nothing executed."
        resp_l = []
        shell = ssh.invoke_shell()
        buff = b''
        iter_n = 0
        while not buff.endswith(b' ~]$ '):
            resp = shell.recv(9999)
            buff += resp
            iter_n += 1
            log.debug("ITER: %s | Waiting for shell: %s", iter_n, resp)
            resp_l.append(resp)
            sleep(2)

        log.debug("Send cmd: %s on: %s", cmd, addm_instance)
        shell.send(cmd + '\n')
        buff = b''
        while not buff.endswith(b'Do you wish to proceed? (y/n) '):
            resp = shell.recv(9999)
            iter_n += 1
            sleep(2)
            # log.debug("ITER: %s | 1st Response %s ", iter_n, resp)
            resp_l.append(resp)
            buff = resp

        log.debug("Sending yes")
        shell.send("y" + '\n')
        buff = b''
        iter_n = 0
        while buff.find(b'Checking') < 0:
            resp = shell.recv(9999)
            iter_n += 1
            buff += resp
            # log.debug("ITER: %s | 2nd Response %s ", iter_n, resp)
            resp_l.append(resp)
            sleep(2)

        buff = b''
        iter_n = 0
        while buff.find(b'Model wipe complete') < 0:
            resp = shell.recv(9999)
            iter_n += 1
            buff += resp
            # log.debug("ITER: %s | 3rd Response %s ", iter_n, resp)
            resp_l.append(resp)
            sleep(10)

            if buff.find(b'ERROR: Failed to start services') > 0:
                log.error("<=Model wipe=> Error while service restarts: on %s Error: \n--> %s \n<-- ",
                          addm_instance, resp.decode('utf-8'))
                msg = 'ERROR: Failed to restart services: {} Out: {}'.format(
                    addm_instance, resp.decode('utf-8'))
                return msg
                # raise Exception('ERROR: Failed to restart services: {} Out: {}'.format(addm_instance, resp.decode('utf-8')))
        log.info("<=ADDM Oper=> Tideway tw_model_wipe finished! %s", addm_name)
        return resp.decode('utf-8'), resp_l
