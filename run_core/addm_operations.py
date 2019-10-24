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

# noinspection PyCompatibility
import paramiko
from paramiko import SSHClient

from run_core.models import AddmDev

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
                cmd='rsync -a --progress '
                    '--log-file=/usr/tideway/sync_prod_cont_python.log '
                    '--include "*" --include "*/" '
                    '/usr/tideway/TKU/addm/tkn_main/product_content/r1_0/code/python/ '
                    '/usr/tideway/python',
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
                if addm_group == 'use_all':
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

        # UTILS SYNC
        from_utils = "/usr/tideway/TKU/utils/ "
        to_utils = "/usr/tideway/utils/ "
        rsync_utils = rsync_cmd + rsync_log + from_utils + to_utils

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
    def upload_unzip(ssh, addm_item, tku_zip_list):
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

        # DELETE any TKU zips BEFORE unzip anything new:
        cmd_list = ['rm -f /usr/tideway/TEMP/*']
        TKU_temp = '/usr/tideway/TEMP'
        outputs_l = []

        for zip_item in tku_zip_list:
            log.debug("<=ADDM Oper=> TKU ZIP item: (%s)", zip_item['zip_file_name'])
            path_to_zip = zip_item['zip_file_path'].replace('/home/user/TH_Octopus', '/usr/tideway')
            cmd_list.append('unzip -o {} -d {}'.format(path_to_zip, TKU_temp))

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
                msg = '<=ADDM Oper=> Error during "upload_unzip" for: {} {} {} ON "'.format(
                    cmd, e, addm_item['addm_name'], addm_item['addm_host'])
                log.error(msg)
                raise Exception(msg)
        return outputs_l


# noinspection PyPep8Naming,PyPep8
class ADDMConfigurations:
    """
    Uses configuration functions to setup test environments for newly added addms:
    - change standard passwords
    - create folders
    - copy NFS helper
    - create fstab recordings (etc/fstab)
    - create bashrc files for branches
    - mount all NFS
    etc

    """

    def __init__(self):
        """
        Class should be init with active SSH function.
        If no SSH - no work will done here.

        """
        # noinspection PyUnresolvedReferences
        self.host_keys = os.path.join(place, 'addms')
        # Choose correct branch:
        self.branches = {
            'double_decker': 'r11_3_x_x',
            'zythum': 'r10_2_0_x',
            'aardvark': 'r11_0_0_x',
            'bobblehat': 'r11_1_0_x',
            'custard_cream': 'r11_2_0_x'
        }

        self.password_change_txt_re = re.compile(r"Password change required but no TTY available\.")
        self.password_expired_txt_re = re.compile(r"WARNING: Your password has expired\.")
        self.whoami_tideway_re = re.compile(r"\btideway")

        # NFS ADDM folder shares check_ide
        self.MOUNT_TKN_MAIN_re = re.compile(r"172\.25\.144\.117:/home/user/TH_Octopus/perforce/addm/tkn_main")
        self.MOUNT_TKN_SHIP_re = re.compile(r"172\.25\.144\.117:/home/user/TH_Octopus/perforce/addm/tkn_ship")

        self.vm_tkn_path_re = re.compile(r"(?P<tkn_path>\S+)/addm/tkn_main/tku_patterns/")

        # BASH profile check for exports:
        self.TKN_MAIN_re = re.compile(r"export\sTKN_MAIN=/usr/tideway/SYNC/addm/tkn_main/")
        self.TKN_SHIP_re = re.compile(r"export\sTKN_MAIN=/usr/tideway/SYNC/addm/tkn_ship/")
        self.TKN_CORE_re = re.compile(r"export\sTKN_CORE=\$TKN_MAIN/tku_patterns/CORE")
        self.PYTHONPATH_re = re.compile(r"export\sPYTHONPATH=\$PYTHONPATH:\$TKN_MAIN/python")

        # MOUNTS CHECK:
        # Check if paths in mount points is recent:
        self.MOUNT_UTILS_str = "172\.25\.144\.117:/home/user/TH_Octopus/perforce/addm/rel/branches" \
                               "/{}/{}/code/utils"
        self.MOUNT_TESTUTILS_str = "172\.25\.144\.117:/home/user/TH_Octopus/perforce/addm/rel/branches" \
                                   "/{}/{}/code/python/testutils/"

        self.upload_activated_check = re.compile(r'(\d+\sknowledge\supload\sactivated)')
        self.upload_num_item = re.compile(r'Uploaded\s+\S+\s+as\s\"([^"]+)\"')

        # Init class with list of already connected ADDM:
        # self.connected_addm_list_d = self.addm_list_dict_exec(addm_host_list)
        # log.debug("List of addm ssh: " + str(self.connected_addm_list_d))
        # log.debug("Init ADDM Config class")

    # @staticmethod
    # def addm_list_dict_exec(addm_hosts):
    #     """
    #     Check list of ADDMs for its DEV details.
    #
    #     :param addm_hosts: tuple
    #     :return:
    #     """
    #     dict_of_connected_addm = dict()
    #     new_password = "S0m3w@y"
    #     if isinstance(addm_hosts, tuple):
    #         for addm_tuple in addm_hosts:
    #
    #             addm_host = addm_tuple[0]
    #             addm_name = addm_tuple[1]
    #             tideway_user = addm_tuple[2]
    #             password = addm_tuple[3]
    #             addm_ip = addm_tuple[6]
    #             # TODO: Dict make
    #             # addm_host     = addm['addm_host']
    #             # addm_name = addm['addm_name']
    #             # tideway_user  = addm['tideway_user']
    #             # tideway_pdw   = addm['tideway_pdw']
    #             # addm_ip       = addm['addm_ip']
    #             where = "Executed from addm_list_dict_exec in ADDMConfig"
    #             ssh_cons = ADDMOperations().addm_ssh_connect(
    #                 addm_ip=addm_ip,
    #                 tideway_user=tideway_user,
    #                 tideway_pdw=password,
    #                 where=where)
    #             if ssh_cons:
    #                 if ssh_cons.get_transport().is_active():
    #                     dict_of_connected_addm.update({addm_host: dict(ssh_cons=ssh_cons,
    #                                                                    addm_host=addm_host,
    #                                                                    addm_ip=addm_ip,
    #                                                                    addm_name=addm_name,
    #                                                                    tideway_user=tideway_user,
    #                                                                    tideway_password=password)})
    #                 else:
    #                     log.debug("SSH Connection closed!")
    #             else:
    #                 log.debug("This addm cannot be connected via SSH: %s via SSH as user: %s password: %s",
    #                           addm_host, tideway_user, password)
    #                 log.debug("In case if password was changed to new - try new now.")
    #                 where = 'PARAMIKO SSH addm_list_dict_exec'
    #                 ssh_cons = ADDMOperations().addm_ssh_connect(addm_ip=addm_ip, tideway_user=tideway_user,
    #                                                              tideway_pdw=new_password, where=where)
    #                 if ssh_cons:
    #                     if ssh_cons.get_transport().is_active():
    #                         dict_of_connected_addm.update({addm_host: dict(ssh_cons=ssh_cons,
    #                                                                        addm_host=addm_host,
    #                                                                        addm_ip=addm_ip,
    #                                                                        addm_name=addm_name,
    #                                                                        tideway_user=tideway_user,
    #                                                                        tideway_password=password)})
    #                     else:
    #                         log.debug("SSH Connection closed!")
    #
    #     return dict_of_connected_addm

    # Check ADDM status if DEV:
    # TODO: Make dicts
    # noinspection PyPep8Naming
    # def addm_cond(self, addm_host_list):
    #     """
    #     Execute standard functions to check:
    #
    #     - if SSH to ADDM not successful:
    #     -- log.debug if not
    #
    #     - if password change not required:
    #     -- change password
    #
    #     - if ADDM has no DEV check:
    #         - check dev conf in tideway
    #             -- run df -h - parse
    #             -- run nfs check - parse
    #             -- run rsync check - parse
    #         - if not dev conf - create
    #         - if not df -h and nfs and fstab:
    #             -- execute config
    #             -- save dev conf to tideway
    #     :return:
    #     """
    #     log.debug("Start ADDM dev checking procedure.")
    #
    #     list_addm_dev_to_db = dict()
    #     tuple_addm_dev_to_db = dict()
    #     # connected_addm_list_d = self.addm_list_dict_exec(addm_host_list)
    #     # noinspection PyShadowingBuiltins
    #     round = 1
    #     for addm_item in addm_host_list:
    #
    #         # check_bashrc     = 0
    #         check_fstab = 0
    #         check_fs_tree = 0
    #         check_mounts = 0
    #         is_synced = 0
    #         fstab_check = 0
    #         nfs_helper = 0
    #         nfs_helper_moved = 0
    #         BAK_fstab = 0
    #         new_fstab = 0
    #         mount_success = 0
    #
    #         addm_host = addm_item[0]
    #         addm_name = addm_item[1]
    #         tideway_user = addm_item[2]
    #         tideway_pdw = addm_item[3]
    #         root_user = addm_item[4]
    #         root_pwd = addm_item[5]
    #         addm_ip = addm_item[6]
    #         addm_v_code = addm_item[7]
    #         addm_v_int = addm_item[8]
    #         addm_owner = addm_item[9]
    #         addm_is_dev = addm_item[10]
    #
    #         where = 'PARAMIKO SSH addm_cond'
    #
    #         addm_ssh = ADDMOperations().addm_ssh_connect(
    #             addm_ip=addm_ip,
    #             tideway_user=tideway_user,
    #             tideway_pdw=tideway_pdw,
    #             where=where)
    #         if addm_ssh:
    #             if addm_ssh.get_transport().is_active():
    #                 log.debug("-====== Start testing ADDM status for: %s IP: %s host: %s",
    #                           addm_name, addm_ip, addm_host)
    #                 pass_ok = self.pass_check(ssh=addm_ssh)
    #
    #                 # TODO: Assign later with checks.
    #                 if addm_name in self.branches:
    #                     addm_branch = self.branches[addm_name]
    #                     log.debug("ADDM Branch is set to: " + addm_branch)
    #
    #                     # Check ADDM dev status:
    #                     if pass_ok:
    #                         log.debug("ADDM can connect as tideway and password is recent.")
    #                         dev_d = self.addm_status(ssh=addm_ssh,
    #                                                  addm_name=addm_name,
    #                                                  branch=addm_branch)
    #
    #                         if dev_d['check_mounts'] and dev_d['check_fstab']:
    #                             log.debug("Current ADDM have DEV footlog.debugs in it's filesystem.")
    #                             check_mounts = dev_d['check_mounts']
    #                             check_fstab = dev_d['check_fstab']
    #                             # check_bashrc = dev_d['check_bashrc']  # Not needed now, just export for each.
    #                             addm_is_dev = 1
    #
    #                         else:
    #                             log.debug("NOT DEV - Current ADDM have NOT DEV "
    #                                       "footlog.debugs in it's filesystem try to setup.")
    #                             # Try to configure this ADDM
    #                             addm_dev_options = self.addm_setup(ssh=addm_ssh,
    #                                                                addm_ip=addm_ip,
    #                                                                addm_branch=addm_branch,
    #                                                                addm_name=addm_name,
    #                                                                addm_root_pass=root_pwd)
    #                             log.debug("ADDM config process is shown in this dict: " + str(addm_dev_options))
    #
    #                             if addm_dev_options['bash_updated'] and addm_dev_options['mounts']:
    #                                 fstab_check = addm_dev_options['fstab_check']
    #                                 nfs_helper = addm_dev_options['nfs_helper']
    #                                 nfs_helper_moved = addm_dev_options['nfs_helper_moved']
    #                                 BAK_fstab = addm_dev_options['BAK_fstab']
    #                                 new_fstab = addm_dev_options['new_fstab']
    #                                 mount_success = addm_dev_options['mount_success']
    #                                 log.debug("Current ADDM setup process was executed. Check results.")
    #                                 # Re-run check for all dev statutes:
    #                                 dev_d = self.addm_status(ssh=addm_ssh,
    #                                                          addm_name=addm_name,
    #                                                          branch=addm_branch)
    #
    #                                 if dev_d['check_mounts'] and dev_d['check_fstab']:
    #                                     log.debug("Current ADDM setup process was executed. And dev setup is on place.")
    #                                     check_mounts = dev_d['check_mounts']
    #                                     check_fstab = dev_d['check_fstab']
    #                                     # check_bashrc = dev_d['check_bashrc']  # Not needed now, just export for each.
    #                                     addm_is_dev = 1
    #
    #                                 else:
    #                                     log.debug("Current ADDM setup process was executed. "
    #                                               "But setup wasn't successful.")
    #                             else:
    #                                 log.debug("Checked machine wasn't configured to DEV and its config process failed!")
    #                     else:
    #                         log.debug("ADDM password wrong or connection cannot be established.")
    #
    #                     tuple_addm_dev_to_db.update({addm_host: (addm_host, addm_name, tideway_user, tideway_pdw,
    #                                                              root_user, root_pwd, addm_ip, addm_v_code, addm_v_int,
    #                                                              addm_branch, addm_owner, addm_is_dev, check_fstab,
    #                                                              check_fs_tree, check_mounts, fstab_check,
    #                                                              nfs_helper, nfs_helper_moved, BAK_fstab, new_fstab,
    #                                                              mount_success, is_synced, pass_ok)})
    #                     list_addm_dev_to_db.update({addm_host: dict(addm_host=addm_host,
    #                                                                 addm_name=addm_name,
    #                                                                 addm_user=tideway_user,
    #                                                                 addm_password=tideway_pdw,
    #                                                                 addm_root_user=root_user,
    #                                                                 addm_root_password=root_pwd,
    #                                                                 addm_ip=addm_ip,
    #                                                                 addm_ver=addm_v_code,
    #                                                                 addm_num=addm_v_int,
    #                                                                 addm_branch=addm_branch,
    #                                                                 owner=addm_owner,
    #                                                                 addm_dev=addm_is_dev,
    #                                                                 check_fstab=check_fstab,
    #                                                                 check_fs_tree=check_fs_tree,
    #                                                                 check_mounts=check_mounts,
    #                                                                 fstab_check=fstab_check,
    #                                                                 nfs_helper=nfs_helper,
    #                                                                 nfs_helper_moved=nfs_helper_moved,
    #                                                                 BAK_fstab=BAK_fstab,
    #                                                                 new_fstab=new_fstab,
    #                                                                 mount_success=mount_success,
    #                                                                 is_synced=is_synced,
    #                                                                 pass_ok=pass_ok)})
    #                     # Try to sort processed addms into logical groups and save them locally. For now.
    #                     log.debug("-====== END of testing ADDM status for: %s IP: %s host: %s | Round:%s",
    #                               addm_name, addm_ip, addm_host, round)
    #                     # noinspection PyShadowingBuiltins
    #                     round = round + 1
    #                 else:
    #                     log.debug("This ADDM codename %s is not found in my dict: %s ", addm_name, self.branches)
    #             else:
    #                 log.debug("SSH Connection closed!")
    #
    #     return list_addm_dev_to_db, tuple_addm_dev_to_db

    def pass_check(self, ssh):
        """
        Check if password expired of should be change in initial connect.
        Change password to my password.

        :return:
        """
        pass_ok = False
        who_am_i = "whoami"
        new_password = "S0m3w@y"
        old_password = "tidewayuser"

        initial_ssh_stdout = ''
        initial_ssh_stderr = ''

        log.debug("Octopus will check if this ADDM require password change at first logon.")
        if ssh:
            # noinspection PyBroadException
            try:
                _, stdout, stderr = ssh.exec_command(who_am_i)
                if stdout:
                    output = stdout.readlines()
                    raw_out = "".join(output).replace('\n', " ")
                    if raw_out:
                        initial_ssh_stdout = raw_out
                if stderr:
                    output = stderr.readlines()
                    raw_out = "".join(output).replace('\n', " ")
                    if raw_out:
                        initial_ssh_stderr = raw_out
            except Exception as e:
                log.debug("Cannot exec_command ls. %s", e)

            if initial_ssh_stderr:
                log.debug("initial_ssh_stderr: " + str(initial_ssh_stderr))
                pass_change_check = self.password_change_txt_re.search(initial_ssh_stderr)
                pass_expire_check = self.password_expired_txt_re.search(initial_ssh_stderr)

                if pass_change_check or pass_expire_check:
                    log.debug("Password will be changed from standard to usual Alex D password.")
                    log.debug("Password changing procedure starting...")
                    message = self.pass_change(ssh_conn=ssh, old_pass=old_password, new_pass=new_password)
                    log.debug("Password changing procedure has been finished. See log for results." + str(message))

                    """
                    Password changing procedure has been finished. See log for results.
                    [b'passwd: all authentication tokens updated successfully.\r']
                    Maybe password was't changed or I do not know content in 'message' - 
                    [b'passwd: all authentication tokens updated successfully.\r']
                    """

                    if "all authentication tokens updated successfully." in message:
                        pass_ok = True
                    else:
                        log.debug(
                            "Maybe password was't changed or I do not know content in 'message' - " + str(message))

                # pass_actual = self.whoami_tideway_re.search(initial_ssh_stderr)
                # if pass_actual:
                #     log.debug("Im ok, password ok.")
                #     pass_ok = True

            if initial_ssh_stdout:
                log.debug("initial_ssh_stdout: " + str(initial_ssh_stdout))
                pass_actual = self.whoami_tideway_re.search(initial_ssh_stdout)
                if pass_actual:
                    log.debug("Im ok, password ok.")
                    pass_ok = True
                else:
                    log.debug("Cannot run whoami command or got an unexpected output: " + str(initial_ssh_stdout))

        return pass_ok

    @staticmethod
    def pass_change(ssh_conn, old_pass, new_pass):
        """
        If got error on login then set with interactive mode.

        shutdown(how)
            Shut down one or both halves of the connection.
            If how is 0, further receives are disallowed. If how is 1,
            further sends are disallowed.
            If how is 2, further sends and receives are disallowed.
            This closes the stream in one or both directions.

        invoke_shell(*args, **kwargs)
            Request an interactive shell session on this channel.
            If the server allows it, the channel will then be directly
            connected to the stdin, stdout, and stderr of the shell.
            Normally you would call get_pty before this, in which case the shell will operate through the pty,
            and the channel will be connected to the stdin and stdout of the pty.
            When the shell exits, the channel will be closed and can’t be reused.
            You must open a new channel if you wish to
            open another shell
            Raises:	SSHException – if the request was rejected or the channel was closed

        finish msg =         L:156   LST b'passwd: all authentication tokens updated successfully.\r':

        """
        result_out = []
        log.debug("Start password changing: old_password = '%s' | new_password = '%s' ", old_pass, new_pass)
        log.debug("Start interact SHELL invoke_shell()")

        interact = ssh_conn.invoke_shell()
        buff = b''

        while not buff.endswith(b'UNIX password: '):
            resp = interact.recv(9999)  # b'Changing password for user tideway.\r\n'
            """
            b'\r\nBMC Discovery application software, and system configuration. 
            It is not a\r\ngeneral purpose system and should not be treated as such. 
            Any customizations\r\nmade to the system that are undocumented and not explicitly requested by 
            BMC\r\nCustomer Support will void support for the appliance.\r\n\r\nDocumentation regarding 
            supported configuration changes and additional software\r\nthat can be installed on the appliance can 
            be found at:\r\n  https://docs.bmc.com/docs/display/ADDM/Documentation+Home\r\n\r\n
            For additional information, please contact BMC Customer Support.\r\n'
            """
            sleep(0.1)
            buff = resp

        interact.send(old_pass + '\n')  # Interact old_pass response: b'\r\n'
        buff = b''
        while not buff.endswith(b'New password: '):
            resp = interact.recv(9999)  # Response from : --> b'New password: '
            sleep(0.1)
            buff = resp

        interact.send(new_pass + '\n')  # Sending password: S0m3w@y
        buff = b''
        while not buff.endswith(b'Retype new password: '):
            resp = interact.recv(9999)  # Response from : --> b'Retype new password: '
            sleep(0.1)
            buff = resp

        interact.send(new_pass + '\n')  # Sending password: S0m3w@y
        interact.shutdown(2)
        if interact.exit_status_ready():
            log.debug("Interact exiting: --> %s", interact.recv_exit_status())

        finish_message = interact.recv(-1)  # b'passwd: all authentication tokens updated successfully.\r':
        result_out.append(finish_message)

        log.debug("Last Password %s:", interact.recv(-1))

        return result_out

    # noinspection PyPep8Naming
    def addm_status(self, ssh, addm_name, branch):
        """
        Run ssh connection and see if this addm configured or need to be configured.

        Future way to check all patterns: /usr/tideway/TKU/addm/tkn_main/tku_patterns/CORE/**/*.tplpre

        :return:
        """

        dev_statuses = dict(check_mounts=False,
                            check_fstab=False,
                            check_fs_tree=False)

        # Check if files are really propagated via share:
        path_to_tkn_mains = "/usr/tideway/TKU/addm/tkn_main/"
        path_to_tkn_ships = "/usr/tideway/TKU/addm/tkn_ship/"
        preproc_re = re.compile(r"TPLPreprocessor\.py")
        tpl_tests_re = re.compile(r"tpl_tests\.py")

        # path_to_testutils_sync = "/usr/tideway/python/testutils"
        path_to_testutils_nfs = "/usr/tideway/TKU/python/testutils"
        dml_test_utils_re = re.compile(r"dml_test_utils\.py")

        # Later Add this to check, now this is not needed.
        # path_to_utils_nfs = "/usr/tideway/TKU/utils"
        # utils_re = re.compile(r"(start_manual_tests|stop_manual_tests)")

        path_to_tplpre_tst = "/usr/tideway/TKU/addm/tkn_main/tku_patterns/CORE/Zones/"
        path_to_ship_tplpre_tst = "/usr/tideway/TKU/addm/tkn_ship/tku_patterns/CORE/Zones/"
        tplpre_tst_re = re.compile(r"tests/(dml|test.py)")

        # Initial check for fstab content and active mounts.
        MOUNT_UTILS_re = re.compile(self.MOUNT_UTILS_str.format(addm_name, branch))
        MOUNT_TESTUTILS_re = re.compile(self.MOUNT_TESTUTILS_str.format(addm_name, branch))
        mounts_check, df_cmd_out = self.check_mounts(ssh,
                                                     utils=MOUNT_UTILS_re,
                                                     testutils=MOUNT_TESTUTILS_re)
        fstab_check, cat_fstab_out = self.check_fstab(ssh,
                                                      utils=MOUNT_UTILS_re,
                                                      testutils=MOUNT_TESTUTILS_re)

        # There is no reason to check if mount was not found. And files can be old.
        if mounts_check and fstab_check:

            dev_statuses['check_mounts'] = True
            dev_statuses['check_fstab'] = True

            # Not needed now, just export for each.
            # export_check, bash_out = self.check_bashrc(ssh)

            # TODO: Later make dict with keys for needed paths and check them in loop.
            preproc_check, preproc_out = self.check_tree(ssh=ssh,
                                                         check_path=path_to_tkn_mains,
                                                         regex=preproc_re)

            preproc_ship_check, preproc_ship_out = self.check_tree(ssh=ssh,
                                                                   check_path=path_to_tkn_ships,
                                                                   regex=preproc_re)

            tpl_tests_check, tpl_tests_out = self.check_tree(ssh=ssh,
                                                             check_path=path_to_tkn_mains,
                                                             regex=tpl_tests_re)

            dml_test_utils_check, dml_test_utils_out = self.check_tree(ssh=ssh,
                                                                       check_path=path_to_testutils_nfs,
                                                                       regex=dml_test_utils_re)
            pattern_tests, pattern_tests_out = self.check_tree(ssh=ssh,
                                                               check_path=path_to_tplpre_tst,
                                                               regex=tplpre_tst_re)
            pattern_ship_tests, pattern_ship_tests_out = self.check_tree(ssh=ssh,
                                                                         check_path=path_to_ship_tplpre_tst,
                                                                         regex=tplpre_tst_re)

            # TODO: Test SYNC folders before test start or run SYNC.

            if preproc_check and tpl_tests_check and dml_test_utils_check and pattern_tests \
                    and pattern_ship_tests and preproc_ship_check:
                dev_statuses['check_fs_tree'] = True
            else:
                log.debug("While checking files tree for NFS mount - not found needed files and places! "
                          "Stdout in debug.")
                log.debug("STDOUT's for file tree checks: "
                          "preproc_check - %s | "
                          "preproc_ship_check - %s | "
                          "tpl_tests_check - %s | "
                          "dml_test_utils_check - %s | "
                          "pattern_tests - %s ",
                          "pattern_ship_tests - %s ",
                          preproc_check, preproc_ship_check,
                          tpl_tests_check, dml_test_utils_check, pattern_tests, pattern_ship_tests)
            # if export_check:
            #     dev_statuses['check_bashrc'] = True
            # else:
            #     log.debug("Check bashrc cannot find export variables for testing in.")

        elif mounts_check and not fstab_check:
            log.debug("FS is mounted in df -s option but mount point was not found in /etc/fstab!")
        elif fstab_check and not mounts_check:
            log.debug("FS is mounted in /etc/fstab option but mount point was not found in df -h!")
        else:
            log.debug("FS is not mounted in system and fstab, please check: 'df -h' and: cat '/etc/fstab'")

        return dev_statuses

    # noinspection PyBroadException
    def check_mounts(self, ssh, **regexps):
        """
        Check if ADDM VM is using mount FS

        172.25.144.117:/home/user/TH_Octopus/perforce/addm/tkn_ship

        172.25.144.117:/home/user/TH_Octopus/perforce/addm/tkn_main
                               76G  6.9G   70G  10% /usr/tideway/TKU/addm/tkn_main
        172.25.144.117:/home/user/TH_Octopus/perforce/addm/rel/branches/bobblehat/r11_1_0_x/code/utils/
                               76G  6.9G   70G  10% /usr/tideway/utils
        172.25.144.117:/home/user/TH_Octopus/perforce/addm/rel/branches/bobblehat/r11_1_0_x/code/python/testutils/
                               76G  6.9G   70G  10% /usr/tideway/python/testutils

        :return:
        """
        # TODO: MOUNT ONLY addm/../ no need later to use separate ships!

        mounts_check = False
        # raw_err = ''
        raw_out = ''
        MOUNT_UTILS_re = regexps['utils']
        MOUNT_TESTUTILS_re = regexps['testutils']

        # Check if paths in mount points is recent:
        cmd = "df -h"
        try:
            _, stdout, stderr = ssh.exec_command(cmd)
            raw_out, raw_err = out_err_read(out=stdout,
                                            err=stderr,
                                            name='check_nfs',
                                            cmd=cmd,
                                            mode='error')
            TKN_MAIN_MOUNT = self.MOUNT_TKN_MAIN_re.search(raw_out)
            TKN_SHIP_MOUNT = self.MOUNT_TKN_SHIP_re.search(raw_out)
            UTILS_MOUNT = MOUNT_UTILS_re.search(raw_out)
            TESTUTILS_MOUNT = MOUNT_TESTUTILS_re.search(raw_out)
            if TKN_MAIN_MOUNT and UTILS_MOUNT and TESTUTILS_MOUNT and TKN_SHIP_MOUNT:
                mounts_check = True
        except Exception as e:
            log.debug("ADDM VM command 'df -h' %s", e)

        return mounts_check, raw_out

    def check_fstab(self, ssh, **regexps):
        """
        Check if ADDM VM is using mount FS

        # Added by TH Octopus system. Used for test execution.
        172.25.144.117:/home/user/TH_Octopus/perforce/addm/tkn_ship
        172.25.144.117:/home/user/TH_Octopus/perforce/addm/tkn_main
        172.25.144.117:/home/user/TH_Octopus/perforce/addm/rel/branches/bobblehat/r11_1_0_x/code/utils/
        172.25.144.117:/home/user/TH_Octopus/perforce/addm/rel/branches/bobblehat/r11_1_0_x/code/python/testutils/
        # End of block with TH Octopus append.


        :return:
        """
        # TODO: MOUNT ONLY addm/../ no need later to use separate ships!
        fstab_check = False
        # raw_err = ''
        raw_out = ''
        MOUNT_UTILS_re = regexps['utils']
        MOUNT_TESTUTILS_re = regexps['testutils']

        cmd = "cat /etc/fstab"
        # noinspection PyBroadException
        try:
            _, stdout, stderr = ssh.exec_command(cmd)
            raw_out, raw_err = out_err_read(out=stdout,
                                            err=stderr,
                                            name='check_fstab',
                                            cmd=cmd,
                                            mode='error')
            TKN_SHIP_MOUNT = self.MOUNT_TKN_SHIP_re.search(raw_out)
            TKN_MAIN_MOUNT = self.MOUNT_TKN_MAIN_re.search(raw_out)
            UTILS_MOUNT = MOUNT_UTILS_re.search(raw_out)
            TESTUTILS_MOUNT = MOUNT_TESTUTILS_re.search(raw_out)
            if TKN_MAIN_MOUNT and UTILS_MOUNT and TESTUTILS_MOUNT and TKN_SHIP_MOUNT:
                fstab_check = True
        except Exception as e:
            log.debug("ADDM VM command 'cat /etc/fstab %s", e)

        return fstab_check, raw_out

    # TODO: Not needed
    def check_bashrc(self, ssh):
        """
        Check if ADDM VM is using export TKN_MAIN

        [tideway@vl-aus-tkudev-38 ~]$ cat .bashrc | grep "TKN_MAIN"
        export TKN_MAIN=/usr/PerforceCheckout/addm/tkn_main/
        export TKN_CORE=$TKN_MAIN/tku_patterns/CORE
        export PYTHONPATH=$PYTHONPATH:$TKN_MAIN/python
        :return:
        """

        export_check = False

        err = ''
        raw_out = ''

        check_cmd_bashrc = 'cat .bashrc | grep "TKN_MAIN"'
        # noinspection PyBroadException
        try:
            _, stdout, stderr = ssh.exec_command(check_cmd_bashrc)
            raw_out, raw_err = out_err_read(out=stdout,
                                            err=stderr,
                                            name='check_cmd_bashrc',
                                            cmd=check_cmd_bashrc,
                                            mode='error')
            TKN_MAIN_check = self.TKN_MAIN_re.search(raw_out)
            TKN_CORE_check = self.TKN_CORE_re.search(raw_out)
            PYTHONPATH_check = self.PYTHONPATH_re.search(raw_out)
            if TKN_MAIN_check and TKN_CORE_check and PYTHONPATH_check:
                export_check = True
            else:
                log.debug("ADDM tideway user bashrc has no needed lines:\n " + str(raw_out))
        except Exception as e:
            log.error("Exception as :s", e)
            log.debug("ADDM VM command '%s' Error: %s", check_cmd_bashrc, err)

        return export_check, raw_out

    @staticmethod
    def check_tree(ssh, check_path, mode="Content", regex=None):
        """
        Check if files are really situated in paths.

        :param regex:
        :param check_path:
        :param mode:
        :param ssh:
        :return:
        """

        file_tree_check = False
        # raw_err = ''
        raw_out = ''

        cmd = 'ls -d -1 {}**/*'
        if mode == "Path":
            cmd = 'ls -d -1 {}**/'

        file_tree_cmd = cmd.format(check_path)
        # noinspection PyBroadException
        try:
            log.debug("Checking path - " + str(file_tree_cmd))
            _, stdout, stderr = ssh.exec_command(file_tree_cmd)
            raw_out, raw_err = out_err_read(out=stdout,
                                            err=stderr,
                                            name='check_file_tree',
                                            cmd=file_tree_cmd,
                                            mode='error')
            # Check for files:
            if regex:
                PATH_CHECK = regex.search(raw_out)
                if PATH_CHECK:
                    file_tree_check = True
            # Check just if path is there:
            # No such file or directory
            else:
                if "No such file or directory" in raw_err:
                    log.debug("UNIX ls check No such file or directory")
                else:
                    file_tree_check = True
        except Exception as e:
            log.error("Exception as :s", e)
            log.debug("ADDM VM command '%s' Error: %s", file_tree_cmd)

        return file_tree_check, raw_out

    @staticmethod
    def check_file(ssh, check_path):
        """
        Check if files are really situated in paths.

        :param check_path: 
        :param ssh:
        :return:
        """

        single_file = False
        # raw_err = ''
        raw_out = ''

        cmd = 'ls {}'

        check_single_file = cmd.format(check_path)
        log.debug("Checking single file: %s", check_single_file)
        # noinspection PyBroadException
        try:
            _, stdout, stderr = ssh.exec_command(check_single_file)
            raw_out, raw_err = out_err_read(out=stdout,
                                            err=stderr,
                                            name='check_file_tree',
                                            cmd=check_single_file,
                                            mode='error')
            # No such file or directory
            if "No such file or directory" in raw_err:
                log.debug("UNIX ls check No such file or directory")
            else:
                single_file = True
        except Exception as e:
            log.error("Exception as :s", e)
            log.debug("ADDM VM command '%s' Error: %s", check_single_file)

        return single_file, raw_out

    @staticmethod
    def chmod_file(ssh, path, mode="user"):
        """

        :param mode:
        :param ssh:
        :param path:
        :return:
        """
        single_file = False
        # raw_err = ''
        raw_out = ''

        cmd = 'chmod 776 {}'
        if mode == 'sudo':
            cmd = 'sudo chmod 776 {}'

        chmod_file_now = cmd.format(path)
        log.debug("CHMOD file: %s", chmod_file_now)
        # noinspection PyBroadException
        try:
            _, stdout, stderr = ssh.exec_command(chmod_file_now)
            raw_out, raw_err = out_err_read(out=stdout,
                                            err=stderr,
                                            name='check_file_tree',
                                            cmd=chmod_file_now,
                                            mode='error')
            # No such file or directory
            if "No such file or directory" in raw_err:
                log.debug("UNIX ls check No such file or directory")
            else:
                single_file = True
        except Exception as e:
            log.error("Exception as :s", e)
            log.debug("ADDM VM command '%s' Error: %s", chmod_file_now)

        return single_file, raw_out

    # Config ADDM if check failed:
    def addm_setup(self, **options):
        """
        Make addm dev.

        :return:
        """

        ssh = options['ssh']
        # addm_ip = options['addm_ip']
        addm_name = options['addm_name']
        addm_root = options['addm_root_pass']
        addm_branch = options['addm_branch']

        log.debug("Executing addm_setup.")
        addm_dev_options = dict(bash_updated=False, mounts=False)

        # Setup bashrc file. Function will check if it currently set up.
        bash_updated, raw_out = self.bashrc_setup(ssh)

        if bash_updated:
            log.debug("Addm bashrc configured!")
            addm_dev_options['bash_updated'] = True

        # Setup NFS options and shares. Function will check if it currently set up.
        create_mounts_statuses = self.addm_nfs_add(ssh=ssh,
                                                   # addm_ip=addm_ip,
                                                   addm_name=addm_name,
                                                   addm_branch=addm_branch,
                                                   addm_root_pass=addm_root)
        addm_dev_options['mounts'] = create_mounts_statuses

        return addm_dev_options

    # TODO: Not needed
    def bashrc_setup(self, ssh):
        """
        Config all addm environments in bashrc.
        Check file content before add new.

        :return:
        """
        bash_updated = False
        # raw_out = ''
        raw_err = ''

        backup_bashrc = 'cp /usr/tideway/.bashrc /usr/tideway/backup_.bashrc'

        bashrc_block = '\n\n\n' \
                       '# ======== Added by TH Octopus system. Used for test execution. ======== \n' \
                       'export TKN_MAIN=/usr/tideway/SYNC/addm/tkn_main/\n' \
                       'export TKN_CORE=$TKN_MAIN/tku_patterns/CORE\n' \
                       'export PYTHONPATH=$PYTHONPATH:$TKN_MAIN/python\n' \
                       '# ========  End of block with TH Octopus append. ======== \n\n\n'

        bashrc_ship_block = '\n\n\n' \
                            '# ======== Added by TH Octopus system. Used for test execution. ======== \n' \
                            'export TKN_MAIN=/usr/tideway/SYNC/addm/tkn_main/\n' \
                            'export TKN_CORE=$TKN_MAIN/tku_patterns/CORE\n' \
                            'export PYTHONPATH=$PYTHONPATH:$TKN_MAIN/python\n' \
                            '# ========  End of block with TH Octopus append. ======== \n\n\n'

        append_cmd = "echo '{}' >> /usr/tideway/.bashrc".format(bashrc_block)
        ship_bashrc_cmd = "echo '{}' >> /usr/tideway/.ship_bashrc".format(bashrc_ship_block)

        # Check for current version, and if there already added block - ignore new changes.
        export_check, raw_out = self.check_bashrc(ssh)
        # If exports were not found:
        if not export_check:
            # noinspection PyBroadException
            try:
                log.debug("Making backup copy for bashrc: backup_.bashrc. Cmd: " + str(backup_bashrc))

                _, stdout, stderr = ssh.exec_command(backup_bashrc)
                raw_out, raw_err = out_err_read(out=stdout,
                                                err=stderr,
                                                name='addm_bashrc_setup',
                                                cmd=backup_bashrc,
                                                mode='error')
                log.debug("Appending export paths to current bashrc. Cmd: " + str(append_cmd))

                _, stdout, stderr = ssh.exec_command(append_cmd)
                raw_out, raw_err = out_err_read(out=stdout,
                                                err=stderr,
                                                name='addm_bashrc_setup',
                                                cmd=append_cmd,
                                                mode='error')
                log.debug("Creating extra .ship_bashrc only with export vars fot TKN_SHIP")
                _, stdout, stderr = ssh.exec_command(ship_bashrc_cmd)
                raw_out, raw_err = out_err_read(out=stdout,
                                                err=stderr,
                                                name='ship_bashrc_cmd',
                                                cmd=ship_bashrc_cmd,
                                                mode='error')

                log.debug("Check of bashrc was updated.")
                bash_updated, raw_out = self.check_bashrc(ssh)
                if bash_updated:
                    bash_updated = True
                    log.debug("File bashrc successfully updated for testing.")
            except Exception as e:
                log.error("Exception as :s", e)
                log.debug("Error during run command addm_bashrc_setup on ADDM! " + str(raw_err))
        else:
            bash_updated = True
            log.debug("Current version of bashrc have paths for testing already! "
                      "Ignore additional modifications.")

        return bash_updated, raw_out

    # Collecting all NFS functions here and execute one by one checking status of each.
    def addm_nfs_add(self, ssh, addm_name, addm_branch, addm_root_pass):
        """
        Upload nfs helper
        scp /sbin/mount.nfs root@addm-ip:/sbin

        :type ssh: func
        :type addm_branch: str
        :type addm_name: str
        :type addm_root_pass: str
        :return:
        """

        '''
        fstab_check=True - will show that fstab was not modified twice!
        fstab_check=False - that means program made some actions on it.
            Than it means new_fstab=True!
        If self.check_fstab fail - we will be sure the program wouldn't go to edit it.
        '''
        create_mounts_statuses = dict(fstab_check=True,
                                      nfs_helper=False,
                                      nfs_helper_moved=False,
                                      BAK_fstab=False,
                                      new_fstab=False,
                                      mount_success=False
                                      )

        # vars from addm item:
        ADDM_CODENAME = addm_name
        BRANCH_VER = addm_branch
        MOUNT_UTILS_re = re.compile(self.MOUNT_UTILS_str.format(ADDM_CODENAME, BRANCH_VER))
        MOUNT_TESTUTILS_re = re.compile(self.MOUNT_TESTUTILS_str.format(ADDM_CODENAME, BRANCH_VER))

        # Create local folders for all shares:
        create_dirs_status, raw_out = self.make_dirs(ssh, addm_name, addm_branch)
        if create_dirs_status:
            create_mounts_statuses['create_dirs_status'] = True

        # Check fstab before append anything else:
        fstab_check, cat_fstab_out = self.check_fstab(ssh,
                                                      utils=MOUNT_UTILS_re,
                                                      testutils=MOUNT_TESTUTILS_re)
        # Touch fstab file only if there is no NFS mounts found!
        if not fstab_check:
            create_mounts_statuses['fstab_check'] = False
            nfs_helper = self.copy_nfs_mod(ssh)

            if nfs_helper:
                create_mounts_statuses['nfs_helper'] = True
                nfs_helper_moved, raw_out = self.move_nfs_mod(ssh)

                if nfs_helper_moved:
                    create_mounts_statuses['nfs_helper_moved'] = True
                    BAK_fstab, raw_out = self.backup_fstab(ssh)

                    if BAK_fstab:
                        create_mounts_statuses['BAK_fstab'] = True
                        new_fstab, raw_out = self.append_fstab(ssh, addm_name, addm_branch, addm_root_pass)

                        if new_fstab:
                            create_mounts_statuses['new_fstab'] = True
                            mount_success, raw_out = self.mount_all(ssh)
                            if mount_success:
                                create_mounts_statuses['mount_success'] = True
                            else:
                                log.debug("Cannot run function: mount_all and setup ADDM dev.")
                        else:
                            log.debug("Cannot run function: new_fstab and setup ADDM dev.")
                    else:
                        log.debug("Cannot run function: BAK_fstab and setup ADDM dev.")
                else:
                    log.debug("Cannot run function: nfs_helper_moved and setup ADDM dev.")
            else:
                log.debug("Cannot run function: nfs_helper and setup ADDM dev.")
        else:
            log.debug("FSTAB configured, but I'll check if mount.nfs is on place.")
            # Initially check nfs helper:
            nfs_helper_file, raw_out = self.check_file(ssh, "/sbin/mount.nfs")
            log.debug("Second check of nfs_helper_file: " + str(nfs_helper_file))

            if not nfs_helper_file:
                nfs_helper = self.copy_nfs_mod(ssh)
                if nfs_helper:
                    create_mounts_statuses['nfs_helper'] = True
                    nfs_helper_moved, raw_out = self.move_nfs_mod(ssh)

                    if nfs_helper_moved:
                        create_mounts_statuses['nfs_helper_moved'] = True
                        mount_success, raw_out = self.mount_all(ssh)
                        if mount_success:
                            create_mounts_statuses['mount_success'] = True
                        else:
                            log.debug("Cannot run function: mount_all and setup ADDM dev.")
                    else:
                        log.debug("Cannot run function: nfs_helper_moved and setup ADDM dev.")
                else:
                    log.debug("Cannot run function: nfs_helper and setup ADDM dev.")
            else:
                self.chmod_file(ssh, "/sbin/mount.nfs", mode="sudo")
                self.mount_all(ssh)
        return create_mounts_statuses

    def make_dirs(self, ssh, addm_name, addm_branch):
        """
        Create folders needed for NFS share mount and tests.

        :return:
        """
        create_dirs_status = False
        # raw_err = ''
        raw_out = ''

        check_dirs = [
            "/usr/tideway/TKU/python/testutils",
            "/usr/tideway/TKU/addm/tkn_main",
            "/usr/tideway/TKU/utils",
            "/usr/tideway/python/testutils",
            "/usr/tideway/SYNC/addm/tkn_main",
            "/usr/tideway/SYNC/addm/tkn_ship",
            "/usr/tideway/utils",
        ]

        cmd = "mkdir -p {}"

        # NFS options vars:
        nfs_options = "nfs      auto,noatime,nolock,bg,nfsvers=3,intr,tcp,actimeo=1800 0 0"
        nfs_root = "172.25.144.117:/home/user/TH_Octopus/perforce/addm/"
        rel = "rel/branches/"
        usr = "/usr/tideway/TKU"

        warning_txt = 'THIS IS PATH TO NFS SHARE! DO NOT DELETE!\n' \
                      'Shared files will be under /usr/tideway/TKU\n' \
                      'Local copy files will be under /usr/tideway/SYNC, ' \
                      'and /usr/tideway/python/testutils/, /usr/tideway/utils/\n' \
                      'Octopus changed config files on this machine, this is example of content and path to files:\n' \
                      'It also upload nfs helper file /sbin/mount.nfs\n' \
                      'Path to /usr/tideway/.bashrc\n' \
                      '# ======== Added by TH Octopus system. Used for test execution. ======== \n' \
                      'export TKN_MAIN=/usr/tideway/SYNC/addm/tkn_main/\n' \
                      'export TKN_CORE=$TKN_MAIN/tku_patterns/CORE\n' \
                      'export PYTHONPATH=$PYTHONPATH:$TKN_MAIN/python\n' \
                      '# ========  End of block with TH Octopus append. ======== \n' \
                      'Path to /etc/fstab\n' \
                      '# ======== Added by TH Octopus system. Used for test execution. ======== \n' \
                      '# Contents from NFS mounted to /usr/tideway/TKU/.. \n' \
                      '# should be later copied to this ADDM actual places with rsync.\n' \
                      '{0}tkn_ship                     {1}/addm/tkn_ship      {2}\n' \
                      '{0}tkn_main                     {1}/addm/tkn_main      {2}\n' \
                      '{3}/{4}/code/utils/             {1}/utils              {2}\n' \
                      '{3}/{4}/code/python/testutils/  {1}/python/testutils   {2}\n' \
                      '# These files should appear in local ADDM in given paths. \n' \
                      '# ========  End of block with TH Octopus append. ======== \n' \
                      ''.format(nfs_root,
                                usr,
                                nfs_options,
                                nfs_root + rel + addm_name,
                                addm_branch)
        # Check if dirs are present:
        for path in check_dirs:
            tree_test, raw_out = self.check_tree(ssh=ssh, check_path=path, mode="Path")
            if tree_test:
                log.debug("This path is found: %s", path)
                create_dirs_status = True
            else:
                log.debug("This path should be created: %s", path)
                create_path = cmd.format(path)
                # noinspection PyBroadException
                try:
                    log.debug("Creating local paths for NFS shares. Cmd: " + str(create_path))
                    _, stdout, stderr = ssh.exec_command(create_path)
                    raw_out, raw_err = out_err_read(out=stdout,
                                                    err=stderr,
                                                    name='create_dirs',
                                                    cmd=create_path,
                                                    mode='error')
                    if not raw_err and not raw_out:
                        create_dirs_status = True
                        # noinspection PyBroadException
                        try:
                            stub_cmd = "echo '{0}' >> {1}_DO_NOT_DELETE".format(warning_txt, path)
                            # Create file stubs:
                            log.debug("Creating file stubs to "
                                      "indicate local path in NFS share: " + str(create_path))
                            _, stdout, stderr = ssh.exec_command(stub_cmd)
                            raw_out, raw_err = out_err_read(out=stdout,
                                                            err=stderr,
                                                            name='create_dirs',
                                                            cmd=stub_cmd,
                                                            mode='error')
                        except Exception as e:
                            log.error("Exception as :s", e)
                            log.debug("Cannot create stub files to indicate the NFS share path in local FS.")
                except Exception as e:
                    log.error("Exception as :s", e)
                    log.debug("Error during run Creating local paths for NFS shares")

        return create_dirs_status, raw_out

    def copy_nfs_mod(self, ssh):
        """
        Open SFTP from MNG VM to ADDM and put /sbin/mount.nfs to /usr/tideway/mount.nfs

        :return:
        """
        nfs_helper = False

        single_file, raw_out = self.check_file(ssh, "/sbin/mount.nfs")
        log.debug("Want to copy /mount.nfs")
        if not single_file:
            # Open FSTP:
            sftp = ssh.open_sftp()
            # noinspection PyBroadException
            try:
                log.debug("Copy NFS helpers to tideway folder. "
                          "SFTP: /home/user/TH_Octopus/mount.nfs', '/usr/tideway/mount.nfs")
                sftp.put('/home/user/TH_Octopus/mount.nfs', '/usr/tideway/mount.nfs')
                sftp.close()
                nfs_helper = True
            except Exception as e:
                log.error("Exception as :s", e)
                log.debug("Error during run Copy NFS helpers to tideway folder")
        else:
            log.debug("No SFTP requited for nfs helper. I see /sbin/mount.nfs is already in place.")
            nfs_helper = True

        return nfs_helper

    def move_nfs_mod(self, ssh):
        """
        Open SFTP from MNG VM to ADDM and put /sbin/mount.nfs to /usr/tideway/mount.nfs

        :return:
        """
        # raw_err = ''
        # raw_out = ''
        nfs_helper_moved = False
        move_nfs_cmd = "sudo cp /usr/tideway/mount.nfs /sbin/mount.nfs"
        # chmod_nfs_cmd = "sudo chmod 776 /sbin/mount.nfs"

        single_file, raw_out = self.check_file(ssh, "/sbin/mount.nfs")
        log.debug("Want to move: mount.nfs")
        if not single_file:
            # noinspection PyBroadException
            try:
                _, stdout, stderr = ssh.exec_command(move_nfs_cmd)
                raw_out, raw_err = out_err_read(out=stdout,
                                                err=stderr,
                                                name='create_dirs',
                                                cmd=move_nfs_cmd,
                                                mode='error')
                if not raw_err and not raw_out:
                    nfs_helper_moved = True
                    self.chmod_file(ssh, "/sbin/mount.nfs", mode="sudo")
            except Exception as e:
                log.error("Exception as :s", e)
                log.debug("Error during run Move NFS helpers from tideway folder to /sbin")
        else:
            log.debug("No copy required for nfs helper. I see /sbin/mount.nfs is already in place.")
            nfs_helper_moved = True

        return nfs_helper_moved, raw_out

    @staticmethod
    def backup_fstab(ssh):
        """
        Make copy of current /etc/fstab file to /etc/BAK_fstab
        :param ssh:
        :return:
        """
        # raw_err = ''
        raw_out = ''
        BAK_fstab = False

        # Make copy to save:
        backup_fstab_cmd = 'sudo cp /etc/fstab /etc/BAK_fstab'
        # noinspection PyBroadException
        try:
            log.debug("Backup fstab to BAK_fstab. Cmd: " + str(backup_fstab_cmd))
            _, stdout, stderr = ssh.exec_command(backup_fstab_cmd)
            raw_out, raw_err = out_err_read(out=stdout,
                                            err=stderr,
                                            name='backup_fstab',
                                            cmd=backup_fstab_cmd,
                                            mode='error')
            if not raw_err and not raw_out:
                BAK_fstab = True
        except Exception as e:
            log.error("Exception as :s", e)
            log.debug("Error during run backup_fstab")

        return BAK_fstab, raw_out

    @staticmethod
    def append_fstab(ssh, addm_name, addm_branch, addm_root_pass):
        """
        Appending shares block to /etc/fstab

        Mount all shares to /usr/tideway/TKU/
        later sync them to right places.

        :type addm_root_pass: str
        :param addm_branch:
        :param addm_name:
        :param ssh:
        :return:
        """
        # raw_err = ''
        raw_out = ''
        new_fstab = False

        # NFS options vars:
        nfs_options = "nfs      auto,noatime,nolock,bg,nfsvers=3,intr,tcp,actimeo=1800 0 0"
        nfs_root = "172.25.144.117:/home/user/TH_Octopus/perforce/addm/"
        rel = "rel/branches/"
        usr = "/usr/tideway/TKU"

        fstab_block = '\n\n\n' \
                      '# ======== Added by TH Octopus system. Used for test execution. ======== \n' \
                      '# Contents from NFS mounted to /usr/tideway/TKU/.. \n' \
                      '# should be later copied to this ADDM actual places with rsync.\n' \
                      '{0}tkn_main                     {1}/addm/tkn_main      {2}\n' \
                      '{0}tkn_ship                     {1}/addm/tkn_ship      {2}\n' \
                      '{3}/{4}/code/utils/             {1}/utils              {2}\n' \
                      '{3}/{4}/code/python/testutils/  {1}/python/testutils   {2}\n' \
                      '# These files should appear in local ADDM in given paths. \n' \
                      '# ========  End of block with TH Octopus append. ======== \n\n\n'
        append_mnt_fstab = fstab_block.format(nfs_root, usr, nfs_options, nfs_root + rel + addm_name, addm_branch)

        # Adding text block to fstab:
        # append_cmd = "sudo echo '%s' >> /etc/fstab" % append_mnt_fstab
        su_append_cmd = "su -c \"echo '%s' >> /etc/fstab\" -m root" % append_mnt_fstab

        # noinspection PyBroadException
        try:
            log.debug("Appending mounts to fstab.")
            log.debug("Sending cmd: \n" + str(su_append_cmd))
            _, stdout, stderr = ssh.exec_command(su_append_cmd)
            interact = ssh.invoke_shell()

            interact.send(su_append_cmd + '\n')

            resp = interact.recv(9999)
            log.debug("Response from interact.send(su_append_cmd + '\\n'): --> " + str(resp))

            buff = b''
            while not buff.endswith(b'Password: '):
                resp = interact.recv(9999)
                log.debug("Response from : --> " + str(resp))
                sleep(1)
                buff = resp

            log.debug("Sending password: " + addm_root_pass)
            interact.send(addm_root_pass + '\n')
            log.debug("Interact interact.send(addm_root_pass + '\\n') response: " + str(interact.recv(9999)))
            new_fstab = True
        except Exception as e:
            log.error("Exception as :s", e)
            log.debug("Error during run Appending mounts to fstab.")

        return new_fstab, raw_out

    @staticmethod
    def mount_all(ssh):
        """
        Execute cmd mount -a

        :param ssh:
        :return:
        """
        # raw_err = ''
        raw_out = ''
        mount_success = False

        # Mount everything:
        mount_nfs_cmd = "sudo mount -a"
        # noinspection PyBroadException
        try:
            log.debug("Mount NFS shares. Cmd: " + str(mount_nfs_cmd))
            _, stdout, stderr = ssh.exec_command(mount_nfs_cmd)
            raw_out, raw_err = out_err_read(out=stdout,
                                            err=stderr,
                                            name='mount_all',
                                            cmd=mount_nfs_cmd,
                                            mode='error')
            if not raw_err and not raw_out:
                mount_success = True
        except Exception as e:
            log.error("Exception as :s", e)
            log.debug("Error during run mount_all")

        return mount_success, raw_out

    @staticmethod
    def addm_sudo_shell(ssh, addm_root_pass, cmd):
        """
        Invoke shell if sudo wants and send root password:
        :param cmd:
        :param ssh:
        :param addm_root_pass:
        :return:
        """

        interact = ssh.invoke_shell()
        log.debug("Shell logged in resp: %s", interact.recv(9999))

        # Switch user to root:
        interact.send("su root")
        log.debug("Execute su root resp: %s", interact.recv(9999))

        # buff = ''
        # while not buff.endswith(':~# '):
        #     resp = interact.recv(9999)
        #     buff += resp
        #     print(resp)

        buff = b''
        while not buff.endswith(b'Password: '):
            resp = interact.recv(9999)
            log.debug("Response from password resp: %s ", resp)
            sleep(0.5)
            buff = resp

        log.debug("Sending password: " + addm_root_pass)
        interact.send(addm_root_pass + '\n')

        log.debug("Interact send pass resp: %s", interact.recv(9999))

        log.debug("Send cmd: %s", cmd)
        interact.send(cmd + '\n')

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
            Stopping services
            Stopping Application Server service:                        [  OK  ]
            Stopping External API service:                              [  OK  ]
            Stopping Reports service:                                   [  OK  ]
            Stopping Tomcat:                                            [  OK  ]
            Stopping Reasoning service:                                 [  OK  ]
            Stopping CMDB Sync (Transformer) service:                   [  OK  ]
            Stopping CMDB Sync (Exporter) service:                      [  OK  ]
            Stopping SQL Provider service:                              [  OK  ]
            Stopping Mainframe Provider service:                        [  OK  ]
            Stopping Discovery service:                                 [  OK  ]
            Stopping Vault service:                                     [  OK  ]
            Stopping Model service:                                     [  OK  ]
            Stopping Security service:                                  [  OK  ]
            Removing files in the data directory
            Removing files in the logs directory
            Removing reasoning persistence data
            Removing CMDB sync persistence data
            Removing generated code
            Starting services
            Starting Security service:                                  [  OK  ]
            Starting Model service:                                     [  Unknown  ]
            Creating partitions:                                        [  OK  ]
            Importing taxonomy:                                          [  OK  ]
            Importing default data:                                      [  OK  ]
            Starting Vault service:                                     [  OK  ]
            Starting Discovery service:                                 [  OK  ]
            Starting Mainframe Provider service:                        [  OK  ]
            Starting SQL Provider service:                              [  OK  ]
            Starting CMDB Sync (Exporter) service:                      [  OK  ]
            Starting CMDB Sync (Transformer) service:                   [  OK  ]
            Starting Reasoning service:                                 [  Unknown  ]
            Importing TKU packages:                                      [  Unknown  ]
            Validate TKU-BladeEnclosure-2017-08-2-ADDM-11.2+:           [  Unknown  ]
            Validate TKU-Cloud-2017-08-2-ADDM-11.2+:                    [  Unknown  ]
            Validate TKU-Core-2017-08-2-ADDM-11.2+:                     [  Unknown  ]
            Validate TKU-Extended-DB-Discovery-2017-08-2-ADDM-11.2+:    [  Unknown  ]
            Validate TKU-Extended-Middleware-Discovery-2017-08-2-ADDM-11.2+: [  Unknown  ]
            Validate TKU-LoadBalancer-2017-08-2-ADDM-11.2+:             [  Unknown  ]
            Validate TKU-ManagementControllers-2017-08-2-ADDM-11.2+:    [  Unknown  ]
            Validate TKU-System-2017-08-2-ADDM-11.2+:                   [  Unknown  ]
            Activating patterns:



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
