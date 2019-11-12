"""
Tests execute here.
WIll use same logic from TPL IDE Automation.

"""

import re, os
from time import time
from time import sleep
from datetime import datetime

from queue import Queue
from threading import Thread

from django.db.models import Max
from run_core.addm_operations import ADDMOperations
from run_core.models import AddmDev
from octo_tku_upload.models import TkuPackagesNew as TkuPackages
from octo_tku_upload.models import UploadTestsNew as UploadTests

from octo.helpers.tasks_mail_send import Mails
from octo_tku_upload.table_oper import UploadTKUTableOper

from octo.helpers.tasks_helpers import TMail

# Python logger
import logging

log = logging.getLogger("octo.octologger")


class UploadTestExec:
    """
    Manage Upload test tasks.

    """

    def __init__(self):
        """
        Initialize some useful items.

        """
        self.addm_op = ADDMOperations()

        # (ssh, addm_item, 'product_content')
        # (ssh, addm_item, 'tw_pattern_management')
        self.mode_cases = dict(
            fresh=dict(
                test_kill=self.addm_op.addm_exec_cmd,
                tku_install_kill=self.addm_op.addm_exec_cmd,
                tideway_restart=self.addm_op.addm_exec_cmd,
                # Ideally we don't want to delete previous installed prod cont, but it its version is higher than actual installable?
                # wipe_data_installed_product_content=self.addm_op.addm_exec_cmd,
                tw_pattern_management=self.addm_op.addm_exec_cmd,
                product_content=self.addm_op.addm_exec_cmd,
            ),
            update=dict(
                product_content=False,
                tw_pattern_management=False,
            ),
            step=dict(
                product_content=False,
                tw_pattern_management=False,
            ),
        )

        self.out_clear_re = re.compile(r';#.*;\n')
        self.upload_packages_status_re = re.compile(
            r'Uploaded\s(?P<zip_file>\S+)\s(?:as|adding\sto)\s(?P<tku_package>\S+)\"\s')
        self.upload_packages_skipped_re = re.compile(r"Skipping\s(?P<tku_name>.+(?=\s-))\s-\s(?P<reason>.+)")
        self.product_content_re = re.compile(
            r"(?P<cause>(?<!Product\sContent)\w+|(?:\s))\s+Product\sContent\s+(?P<reason>.+)")
        self.warnings_re = re.compile(r"Pattern\smodule\s(?P<module>\S+)\s+Warnings:\s+(?P<error>.+)")
        self.errors_re = re.compile(r"Pattern\smodule\s(?P<module>\S+)\s+Errors:\s+(?P<error>.+)")

    def upload_preparations_threads(self, **kwargs):
        """
        Run sequence of commands on each ADDM to prepare it for TKU Install.
        Usually just delete older TKU (to install released one later), restart services and so on.
        :param kwargs:
        :return:
        """
        user_email = kwargs.get('user_email', None)
        addm_items = kwargs.get('addm_items', None)
        test_mode = kwargs.get('test_mode', None)
        step_k = kwargs.get('step_k', None)
        addm_group = addm_items.first().get('addm_group')

        thread_list = []
        thread_outputs = []
        ts = time()
        test_q = Queue()
        start_time = datetime.now()

        for addm_item in addm_items:
            msg = f"<=Upload Preparation Thread=> {addm_item['addm_name']}:{addm_item['addm_v_int']};mode={test_mode};step_k={step_k}"
            log.debug(msg)
            # TODO: TEMP for win local runs
            if not os.name == 'nt':
                # Open SSH connection:
                ssh = ADDMOperations().ssh_c(addm_item=addm_item, where="Executed from upload_run_threads in UploadTestExec")
                if ssh and ssh.get_transport().is_active():
                    m = f"<=upload_preparations_threads=> OK: SSH Is active - continue... ADDM: {addm_item['addm_name']} {addm_item['addm_host']} {addm_item['addm_group']}"
                    log.info(m)
                    kwargs = dict(ssh=ssh, addm_item=addm_item, start_time=start_time,  test_mode=test_mode, test_q=test_q)
                    th_name = f"Upload unzip TKU: addm {addm_item['addm_name']}"
                    try:
                        test_thread = Thread(target=self.upload_preparations, name=th_name, kwargs=kwargs)
                        test_thread.start()
                        thread_list.append(test_thread)
                    except Exception as e:
                        msg = f"Thread test fail with error: {e}"
                        log.error(msg)
                        # raise Exception(msg)
                        return msg
                # When SSH is not active - skip thread for this ADDM and show log error (later could raise an exception?)
                else:
                    msg = f"<=upload_preparations_threads=> SSH Connection could not be established thread skipping for ADDM: " \
                          f"{addm_item['addm_ip']} - {addm_item['addm_host']} in {addm_item['addm_group']}"
                    log.error(msg)
                    thread_outputs.append(msg)
                    # Send mail with this error? BUT not for the multiple tasks!!!
        # TODO: TEMP for win local runs
        if not os.name == 'nt':
            for test_th in thread_list:
                test_th.join()
                log.debug("<=upload_preparations_threads=> Thread finished, test_q.get: %s", test_q.get())
                thread_outputs.append(test_q.get())
            log.debug("<=upload_preparations_threads=> All thread_outputs: %s", thread_outputs)

        # Email confirmation when execution was finished:
        subject = f"TKU_Upload_routines | upload_preparations_threads | {step_k} |  {addm_group} | Finished!"
        body = f"ADDM group: {addm_group}, test_mode: {test_mode}, step_k: {step_k}, start_time: {start_time}, time spent: {time() - ts}"
        Mails.short(subject=subject, body=body, send_to=[user_email])
        return f'upload_preparations_threads Took {time() - ts} {body}'

    def upload_unzip_threads(self, **kwargs):
        """
        Unzip TKU packs from the queryset of packages for each ADDM version.
        Selects zips only related to one ADDM version.
        :param kwargs:
        :return:
        """
        user_email = kwargs.get('user_email', None)
        addm_items = kwargs.get('addm_items', None)
        packages = kwargs.get('packages', None)
        test_mode = kwargs.get('test_mode', None)
        step_k = kwargs.get('step_k', None)
        addm_group = addm_items.first().get('addm_group')
        pack = packages.first()

        thread_list = []
        thread_outputs = []
        ts = time()
        test_q = Queue()
        start_time = datetime.now()

        for addm_item in addm_items:
            # Get ADDM related package zip list from packages:
            package_ = packages.filter(addm_version__exact=addm_item['addm_v_int'])
            tku_zip_list = [package.zip_file_path for package in package_]
            msg = f"<=Upload Unzip Thread=> {addm_item['addm_name']}:{addm_item['addm_v_int']}zip={len(tku_zip_list)} - {tku_zip_list};step_k={step_k}"
            log.debug(msg)
            # TODO: TEMP for win local runs
            if not os.name == 'nt':
                # Open SSH connection:
                ssh = ADDMOperations().ssh_c(addm_item=addm_item, where="Executed from upload_run_threads in UploadTestExec")
                if ssh and ssh.get_transport().is_active():
                    m = f"<=upload_unzip_threads=> OK: SSH Is active - continue... ADDM: {addm_item['addm_name']} {addm_item['addm_host']} {addm_item['addm_group']}"
                    log.info(m)
                    kwargs = dict(ssh=ssh, addm_item=addm_item, tku_zip_list=tku_zip_list, test_q=test_q)
                    th_name = f"Upload unzip TKU: addm {addm_item['addm_name']}"
                    try:
                        test_thread = Thread(target=self.addm_op.upload_unzip, name=th_name, kwargs=kwargs)
                        test_thread.start()
                        thread_list.append(test_thread)
                    except Exception as e:
                        msg = f"Thread test fail with error: {e}"
                        log.error(msg)
                        # raise Exception(msg)
                        return msg
                # When SSH is not active - skip thread for this ADDM and show log error (later could raise an exception?)
                else:
                    msg = f"<=upload_unzip_threads=> SSH Connection could not be established thread skipping for ADDM: " \
                          f"{addm_item['addm_ip']} - {addm_item['addm_host']} in {addm_item['addm_group']}"
                    log.error(msg)
                    thread_outputs.append(msg)
                    # Send mail with this error? BUT not for the multiple tasks!!!
        # TODO: TEMP for win local runs
        if not os.name == 'nt':
            for test_th in thread_list:
                test_th.join()
                log.debug("<=upload_unzip_threads=> Thread finished, test_q.get: %s", test_q.get())
                thread_outputs.append(test_q.get())
            log.debug("<=upload_unzip_threads=> All thread_outputs: %s", thread_outputs)

        # Email confirmation when execution was finished:
        subject = f"TKU_Upload_routines | upload_unzip_threads | {step_k} |  {addm_group} | Finished!"
        body = f"ADDM group: {addm_group}, test_mode: {test_mode}, step_k: {step_k}, tku_type: {pack.tku_type}, " \
               f"package_type: {pack.package_type}, start_time: {start_time}, time spent: {time() - ts}"
        Mails.short(subject=subject, body=body, send_to=[user_email])
        return f'upload_unzip_threads Took {time() - ts} {body}'

    def install_tku_threads(self, **kwargs):
        """
        Simple TKU Install process, runs for each ADDM om set, with tw_pattern_management utility.
        Return Outputs which need to be saved into DB!
        :param kwargs:
        :return:
        """
        user_email = kwargs.get('user_email', None)
        addm_items = kwargs.get('addm_items', None)
        packages = kwargs.get('packages', None)
        test_mode = kwargs.get('test_mode')
        step_k = kwargs.get('step_k')
        addm_group = addm_items.first().get('addm_group')
        pack = packages.first()

        thread_outputs = []
        test_outputs = []
        ts = time()
        test_q = Queue()
        start_time = datetime.now()

        for addm_item in addm_items:
            # Get ADDM related package zip list from packages:
            package_ = packages.filter(addm_version__exact=addm_item['addm_v_int'])
            tku_zip_list = [package.zip_file_path for package in package_]
            msg = f"<=Upload TKU Install Thread=> {addm_item['addm_name']}:{addm_item['addm_v_int']}zip={len(tku_zip_list)} - {tku_zip_list};step_k={step_k}"
            log.debug(msg)
            # TODO: TEMP for win local runs
            if not os.name == 'nt':
                # Open SSH connection:
                ssh = ADDMOperations().ssh_c(addm_item=addm_item, where="Executed from upload_run_threads in UploadTestExec")
                if ssh and ssh.get_transport().is_active():
                    m = f"<=install_tku_threads=> OK: SSH Is active - continue... ADDM: {addm_item['addm_name']} {addm_item['addm_host']} {addm_item['addm_group']}"
                    log.info(m)
                    kwargs = dict(ssh=ssh, addm_item=addm_item, test_q=test_q)
                    th_name = f"Upload unzip TKU: addm {addm_item['addm_name']}"
                    try:
                        test_thread = Thread(target=self.install_activate, name=th_name, kwargs=kwargs)
                        test_thread.start()
                        thread_outputs.append(test_thread)
                    except Exception as e:
                        msg = f"Thread test fail with error: {e}"
                        log.error(msg)
                        # raise Exception(msg)
                        return msg
                # When SSH is not active - skip thread for this ADDM and show log error (later could raise an exception?)
                else:
                    msg = f"<=install_tku_threads=> SSH Connection could not be established thread skipping for ADDM: " \
                          f"{addm_item['addm_ip']} - {addm_item['addm_host']} in {addm_item['addm_group']}"
                    log.error(msg)
                    test_outputs.append(msg)
        # TODO: TEMP for win local runs
        if not os.name == 'nt':
            for test_th in thread_outputs:
                test_th.join()
                test_outputs.append(test_q.get())
                log.debug("<=upload_preparations_threads=> Thread finished, test_q.get: %s", test_q.get())
                thread_outputs.append(test_q.get())
                # Get thread output and insert results in upload test table:
                msg = f'tku_type={packages[0].tku_type};package_type={packages[0].package_type};test_mode={test_mode}:step_k={step_k},'
                log.debug("Package installed: %s", msg)
                # upload_results_d = self.parse_upload_result(upload_outputs_d)
                # self.model_save_insert(test_mode, mode_key, ts, addm_item, zip_values, upload_results_d, upload_outputs_d)
                # return upload_outputs_d
            log.debug("<=upload_preparations_threads=> All thread_outputs: %s", thread_outputs)

        # Email confirmation when execution was finished:
        subject = f"TKU_Upload_routines | install_tku_threads | {test_mode} | {step_k} | {addm_group} | Finished!"
        body = f"ADDM group: {addm_group}, test_mode: {test_mode}, step_k: {step_k}, tku_type: {pack.tku_type}, " \
               f"package_type: {pack.package_type}, start_time: {start_time}, time spent: {time() - ts} "
        Mails.short(subject=subject, body=body, send_to=[user_email])
        return f'install_tku_threads Took {time() - ts} {body}'

    # noinspection PyCompatibility
    def upload_run_threads(self, **kwargs):
        """
        Run each test in pair of connected ADDM instance separately from each other.
        Each this instance is an instance of SSH console of active ADDM + added
        test args to test_exec(). Execute each test.

        """
        thread_list = []
        test_outputs = []
        ts = time()
        test_q = Queue()
        start_time = datetime.now()

        addm_group = kwargs['addm_group']
        mode = kwargs.get('mode', None)
        tku_type = kwargs.get('tku_type', None)
        user_email = kwargs.get('user_email', None)

        addm_set = AddmDev.objects.filter(addm_group__exact=addm_group, disables__isnull=True).values()
        for addm_item in addm_set:
            # Open SSH connection:
            ssh = ADDMOperations().ssh_c(addm_item=addm_item,
                                         where="Executed from upload_run_threads in UploadTestExec")
            # If opened connection is Up and alive:
            if ssh and ssh.get_transport().is_active():
                m = '<=upload_run_threads=> OK: SSH Is active - continue... ADDM: {} {} {}'.format(
                    addm_item['addm_name'], addm_item['addm_host'], addm_item['addm_group'])
                log.debug(m)

                kwargs = dict(ssh=ssh, addm_item=addm_item, mode=mode, tku_type=tku_type, user_email=user_email,
                              start_time=start_time, test_q=test_q)
                th_name = 'Upload test thread: addm {} mode {} tku {}'.format(
                    addm_item['addm_ip'], mode, tku_type)  # type: str

                try:
                    test_thread = Thread(target=self.upload_test_exec, name=th_name, kwargs=kwargs)
                    test_thread.start()
                    thread_list.append(test_thread)
                except Exception as e:
                    msg = "Thread test fail with error: {}".format(e)
                    log.error(msg)
                    # raise Exception(msg)
                    return msg
            # When SSH is not active - skip thread for this ADDM and show log error (later could raise an exception?)
            else:
                msg = '<=upload_run_threads=> SSH Connection could not be established, ' \
                      'thread skipping for ADDM: {} - {} in {}'.format(addm_item['addm_ip'], addm_item['addm_host'],
                                                                       addm_item['addm_group'])
                log.error(msg)
                test_outputs.append(msg)
                # Send mail with this error? BUT not for the multiple tasks!!!

        for test_th in thread_list:
            test_th.join()
            test_outputs.append(test_q.get())

        TMail().upload_t(  # finished
            stage='finished', start_time=start_time, addm_group=addm_group, mode=mode, tku_type=tku_type,
            user_email=user_email, outputs='test_outputs'
        )
        return 'All tests Took {} Out {}'.format(time() - ts, 'is too long, disabled for now')

    def upload_test_exec(self, **kwargs):
        # noinspection SpellCheckingInspection
        """
        Here execute three ways
            - install fresh TKU package, it's release candidate by default
                and install previuos released TKU - then upgrade to release candidate TKU.
            - install one TKU pack and do nothing before (only rm TEMP!) and after
            - install TKU package freshly with wiping old TKU before


        mode: update, step and 'default'
        tku_type: ga_candidate, addm_released, released_tkn, tkn_main_continuous, tkn_ship_continuous

        :param kwargs:
        :return:
        """
        start_time = kwargs.get('start_time')
        ssh = kwargs.get('ssh')
        test_q = kwargs.get('test_q')
        mode = kwargs.get('mode', None)
        tku_type = kwargs.get('tku_type', None)
        user_email = kwargs.get('user_email')
        addm_item = kwargs.get('addm_item')

        addm_name = addm_item.get('addm_name')
        ts = time()

        if ssh and ssh.get_transport().is_active():
            log.info("<=upload_test_exec=> PASSED: SSH Is active")

        install_statuses = dict(mode=mode, tku_type=tku_type)
        log.info("<=RoutineCases=> Upload test mode %s", mode)
        if mode == 'update':

            # STEP 1 - Install RELEASED TKN
            zip_values = UploadTKUTableOper.select_packages_narrow(addm_item, 'released_tkn')
            log.debug("OPTIONS: package_type %s %s", addm_item['addm_full_version'], zip_values[0]['package_type'])
            self.addm_op.upload_unzip(ssh=ssh, addm_item=addm_item, tku_zip_list=zip_values)
            kwargs.update(mode='fresh')
            outputs_tkn = self.run_upload_test_case('released_tkn_install_step_1', zip_values, **kwargs)
            install_statuses.update(released_tkn_install=outputs_tkn)

            log.debug("Need to sleep just to wait some processes to finish and full stop.")
            sleep(60)

            # STEP 2 - Install CANDIDATE GA
            zip_values = UploadTKUTableOper.select_packages_narrow(addm_item, 'ga_candidate')
            log.debug("OPTIONS: package_type %s %s", addm_item['addm_full_version'], zip_values[0]['package_type'])
            self.addm_op.upload_unzip(ssh=ssh, addm_item=addm_item, tku_zip_list=zip_values)
            kwargs.update(mode='update')
            outputs_ga = self.run_upload_test_case('ga_candidate_install_step_2', zip_values, **kwargs)
            install_statuses.update(ga_candidate_install=outputs_ga)

        # Only install TKU - no wiping (rm TEMP anyway!)
        elif mode == 'step':
            zip_values = UploadTKUTableOper.select_packages_narrow(addm_item, tku_type)
            log.debug("OPTIONS: package_type %s %s", addm_item['addm_full_version'], zip_values[0]['package_type'])
            self.addm_op.upload_unzip(ssh=ssh, addm_item=addm_item, tku_zip_list=zip_values)
            outputs = self.run_upload_test_case(tku_type + '_install', zip_values, **kwargs)
            install_statuses.update(step_install=outputs)

        # Fresh install TKU - wiping older TKU and product cont (rm TEMP anyway!)
        else:
            zip_values = UploadTKUTableOper.select_packages_narrow(addm_item, tku_type)
            log.debug("OPTIONS: package_type %s %s", addm_item['addm_full_version'], zip_values[0]['package_type'])
            self.addm_op.upload_unzip(ssh=ssh, addm_item=addm_item, tku_zip_list=zip_values)
            kwargs.update(mode='fresh')
            outputs = self.run_upload_test_case(tku_type + '_install', zip_values, **kwargs)
            install_statuses.update(fresh_install=outputs)

        # TODO: Add link to test results and link to ADDM UI TKU Page from mail body
        TMail().upload_t(stage='running', start_time=start_time, t_spent=time() - ts, addm_item=addm_item,
                         tku_type=tku_type,
                         mode=mode if mode else "Fresh", user_email=user_email, outputs={addm_name: install_statuses},
                         kwargs=kwargs)
        # Close previously opened SSH:
        ssh.close()
        # Put test results into a thread queue output:
        test_q.put(install_statuses)

    def upload_preparations(self, **kwargs):
        """
        Run preparations before or after TKU zip upload install.
        Executes after TKU zips are on places and right before install.

        :return:
        """
        test_q = kwargs.get('test_q')
        ssh = kwargs.get('ssh')
        mode = kwargs.get('test_mode')
        addm_item = kwargs.get('addm_item')  # test mode change the level of preparations.

        if ssh and ssh.get_transport().is_active():
            log.info("<=upload_preparations=> PASSED: SSH Is active")

        preps = self.mode_cases[mode]
        for func_key, func_obj in preps.items():
            if func_obj:
                log.debug("<=upload_preparations=> MAKE SOME PREPARATION... %s %s %s", mode, func_key, addm_item['addm_name'])
                # if func_key == 'tw_restart_service':
                #     func_run = func_obj(ssh, addm_item, func_key, 'reasoning')
                # else:
                #     func_run = func_obj(ssh, addm_item, func_key)
                # log.info("<=upload_preparations=> TKU Upload preparations: %s %s", func_key, func_run)
            else:
                log.info("<=upload_preparations=> No preparations will run of current mode: %s %s=%s", mode, func_key, func_obj)
        return True

    def run_upload_test_case(self, mode_key, zip_values, **kwargs):
        """
        Run selected upload tests for chosen zip files in mode.

        addm_item and zip_values are query sets from django DB.
        mode - is switch to execute upload test in one of modes - update or fresh
        mode_key - is unique for one execution run, will be used to indicate upload scenario in db
        wipe_product_content - is a switch to execute or not a command to delete product content BEFORE
            run upload test.
        wipe_tku - same as above for TKU, can be deleted before run or after.

        :param mode_key: used for DB record
        :param zip_values: list of zips
        :return:
        """
        # import json
        # from pprint import pformat, pprint
        # from collections import OrderedDict
        # ssh = kwargs.get('ssh')
        mode = kwargs.get('mode')
        addm_item = kwargs.get('addm_item')
        ts = time()

        if zip_values:
            # Install TKU:
            try:
                # self.upload_preparations(ssh, mode, addm_item)
                self.upload_preparations(**kwargs)
            except Exception as e:
                msg = "<=UploadTestExecutor=> Error upload_preparations - {}\n" \
                      "mode_key={}\nzip_values={}\nkwargs={}".format(e, mode_key, zip_values, kwargs)
                log.error(msg)
                return msg
                # raise Exception(msg)

            try:
                # upload_outputs_d = self.install_activate(ssh, **kwargs)
                upload_outputs_d = self.install_activate(**kwargs)
            except Exception as e:
                msg = "<=UploadTestExecutor=> Error install_activate - {}\n" \
                      "mode_key={}\nzip_values={}\nkwargs={}".format(e, mode_key, zip_values, kwargs)
                log.error(msg)
                return msg
                # raise Exception(msg)

            try:
                upload_results_d = self.parse_upload_result(upload_outputs_d)
            except Exception as e:
                msg = "<=UploadTestExecutor=> Error parse_upload_result - {}\n" \
                      "mode_key={}\nzip_values={}\nkwargs={}".format(e, mode_key, zip_values, kwargs)
                log.error(msg)
                return msg
                # raise Exception(msg)

            self.model_save_insert(mode, mode_key, ts, addm_item, zip_values, upload_results_d, upload_outputs_d)
            return {addm_item['addm_name']: dict(mode=mode, mode_key=mode_key, composed_results=upload_results_d)}

        else:
            msg = '<=UploadTestExecutor=> run_upload_test_case no test zip were passed! {} {}\n' \
                  'mode_key={}\nzip_values={}\nkwargs={}'.format(addm_item['addm_name'], addm_item['addm_host'],
                                                                 mode_key, zip_values, kwargs)
            log.error(msg)
            return msg

    def install_activate(self, **kwargs):
        """
        Run ADDM remote CMD to install TKU:

        /usr/tideway/bin/tw_pattern_management -p system
            --install-activate
            --allow-restart
            --show-progress
            --loglevel=debug /usr/tideway/TEMP/*zip'

        Uploaded TKU-Storage-2068-04-1-ADDM-11.3+.zip as "TKU-Storage-2068-04-1-ADDM-11.3+"
        Compiled 30 of 44 pattern modules


        :return:
        """
        test_q = kwargs.get('test_q')
        ssh = kwargs.get('ssh')
        addm_item = kwargs.get('addm_item')

        if ssh and ssh.get_transport().is_active():
            log.info("<=install_activate=> PASSED: SSH Is active")

        # TODO: Run for all files, not zip only?
        if float(addm_item['addm_v_int']) > 11.1:
            # noinspection SpellCheckingInspection
            cmd = ('/usr/tideway/bin/tw_pattern_management -p system  '
                   '--install-activate '
                   '--allow-restart '
                   '--show-progress '
                   '--loglevel=debug /usr/tideway/TEMP/*.zip')
        else:
            # noinspection SpellCheckingInspection
            cmd = ('/usr/tideway/bin/tw_pattern_management -p system  '
                   '--install-activate '
                   '--show-progress '
                   '--loglevel=debug /usr/tideway/TEMP/*.zip')
        # noinspection PyBroadException
        try:
            # TODO: Run fake command.
            cmd = 'ls -lh'
            log.debug("Try CMD: (%s) | on %s - %s ", cmd, addm_item['addm_host'], addm_item['addm_name'])
            _, stdout, stderr = ssh.exec_command(cmd)
            upload_outputs_d = self.std_read(out=stdout, err=stderr)
            test_q.put(upload_outputs_d)

        except Exception as e:
            msg = "<=UploadTestExecutor=> Error during 'install_activate' for: {} {}".format(cmd, e)
            log.error(msg)
            raise Exception(msg)

    def parse_upload_result(self, upload_outputs_d):
        """
        Replace all term symbols and leave output clean and ready to parse and add in DB

        If ERROR: A knowledge upload is already in progress
        Try to kill and restart?

        Failed to activate 3 knowledge uploads
        Pattern module AbInitio.CoOperatingSystem
        <TAB>Errors:
        <TAB><TAB>Unknown string qualifier 'typo' at line 15


        :param upload_outputs_d:
        :return:
        """
        upload_warnings = []
        upload_errors = []
        product_content = []

        # TODO: Simplify - parse only when cleared symbols in raw output.
        # TODO: Can parse 'important' output for words 'error', 'warning', etc.

        # str_stdout = upload_outputs_d['std_output']  # formatted output
        str_stdout = upload_outputs_d['clean_std']  # important output
        str_stderr = upload_outputs_d['stderr_output']  # Usual stderr output, works from 11.2+
        # log.debug("<=UploadTestExecutor=> RAW OUTPUT str_stdout %s", str_stdout)

        upload_packages_status = self.upload_packages_status_re.findall(str_stdout)
        upload_packages_skipped = self.upload_packages_skipped_re.findall(str_stdout)
        product_content_status = self.product_content_re.findall(str_stdout)
        if product_content_status:
            for status in product_content_status:
                product_content.append(dict(cause=status[0] if status[0] else 'None', reason=status[1]))

        tku_statuses = dict(statuses=upload_packages_status,
                            skipped=upload_packages_skipped,
                            product_content=product_content)

        try:
            # Check if TKU upload activated:
            # check_upload = self.upload_activated_re.search(str_stdout)
            # log.debug("<=UploadTestExecutor=> check_upload %s", check_upload)
            # Collect all errors in STDOUT:
            all_warnings = self.warnings_re.findall(str_stdout)
            if all_warnings:
                log.error("<=UploadTestExecutor=> STDOUT len %s all_warnings: %s", len(all_warnings), all_warnings)
                for warning in all_warnings:
                    log.warning("<=UploadTestExecutor=> STDOUT warning: %s", warning)
                    upload_warnings.append(warning)
            # Collect all warnings in STDERR if STDOUT is empty:
            else:
                all_warnings = self.warnings_re.findall(str_stderr)
                if all_warnings:
                    log.error("<=UploadTestExecutor=> STDERR len %s all_warnings: %s", len(all_warnings), all_warnings)
                    for warning in all_warnings:
                        log.warning("<=UploadTestExecutor=> STDERR warning: %s", warning)
                        upload_warnings.append(warning)

            # Collect all errors in STDOUT:
            all_errors = self.errors_re.findall(str_stdout)
            if all_errors:
                log.error("<=UploadTestExecutor=> STDOUT len %s all_errors: %s", len(all_errors), all_errors)
                for error in all_errors:
                    log.error("<=UploadTestExecutor=> STDOUT error: %s", error)
                    upload_errors.append(error)
            # Collect all errors in STDERR if STDOUT is empty:
            else:
                all_errors = self.errors_re.findall(str_stderr)
                if all_errors:
                    log.error("<=UploadTestExecutor=> STDERR len %s all_errors: %s", len(all_errors), all_errors)
                    for error in all_errors:
                        log.error("<=UploadTestExecutor=> STDERR error: %s", error)
                        upload_errors.append(error)

            if not upload_errors and not all_errors:
                upload_status = 'passed'
            else:
                upload_status = 'failed'

            upload_results_d = dict(
                upload_status=upload_status,
                str_stdout=str_stdout,
                str_stderr=str_stderr,
                all_errors=len(upload_errors),
                all_warnings=len(upload_warnings),
                upload_warnings=upload_warnings,
                upload_errors=upload_errors,
                tku_statuses=tku_statuses,
            )
            return upload_results_d
        except Exception as e:
            log.error("Error during action - %s", e)
            raise Exception(e)

    @staticmethod
    def model_save_insert(mode, mode_key, ts, addm_item, test_zip, upload_results_d, upload_outputs_d):
        """
        Get all data into the right places

        :param mode:
        :param mode_key:
        :param upload_results_d: parsed upload test results
        :param test_zip: list  of tested zips
        :param addm_item: set of addms
        :param ts: time start obj
        :param upload_outputs_d:
        :return:
        """
        time_spent_test = time() - ts

        # PPRINT
        import json
        from pprint import pformat

        zip_tested_md5sum = []
        for zip_item in test_zip:
            zip_tested_md5sum.append(zip_item['zip_file_md5_digest'])

        # TODO: Re-test this, rewrite and run on local ADDM to verify. Save usual outputs as reference?
        upload_test = dict(
            # Used mode and mode key:
            test_mode=mode,  # What package to install;
            mode_key=mode_key,  # In which order or case to install package;
            # TKU zip details:
            tku_type=test_zip[0]['tku_type'],  # ga_candidate, ..
            package_type=test_zip[0]['package_type'],  # TKN_release_2019-01-1-131, ..
            tku_build=test_zip[0]['tku_build'],  # 2019, ..
            tku_date=test_zip[0]['tku_date'],  # means TKU build count
            tku_month=test_zip[0]['tku_month'],  # 01-12
            # Clean outputs for debug:
            upload_test_status=upload_results_d['upload_status'],
            upload_test_str_stdout=upload_outputs_d['std_output'],
            upload_test_str_stderr=upload_outputs_d['stderr_output'],
            # parsed and cleaned output (without extra console and repeated symbols)
            important_out=upload_outputs_d['clean_std'],
            # COUNT of all errors and warnings:
            all_errors=upload_results_d['all_errors'],
            all_warnings=upload_results_d['all_warnings'],
            # Clear warnings and errors during TKU install:
            upload_warnings=upload_results_d['upload_warnings'],
            upload_errors=upload_results_d['upload_errors'],
            # TKU zips and packages installed: list and statuses, like 'skipped'
            tku_statuses=upload_results_d['tku_statuses'],
            # List of md5sum indexes of TKU zips were used for test
            tested_zips=zip_tested_md5sum,
            # Addm item details:
            addm_name=addm_item['addm_name'],
            addm_v_int=addm_item['addm_v_int'],
            addm_host=addm_item['addm_host'],
            addm_ip=addm_item['addm_ip'],
            addm_version=addm_item['addm_full_version'],
            # Test lasts
            time_spent_test=str(time_spent_test),
        )

        item_sort = json.dumps(upload_test, indent=2, ensure_ascii=False, default=pformat)
        log.debug("<=UploadTestExecutor=> SORTED composed_results_d: %s", item_sort)

        try:
            upload_tst = UploadTests(**upload_test)
            upload_tst.save(force_insert=True)
            if upload_tst.id:
                # NOTE: Return short description of test, not the full output:
                # NOTE: 2 We already have most of these args in task body!
                return dict(saved_id=upload_tst.id)
            else:
                msg = "Test result not saved! Result: {}".format(upload_test)
                log.error(msg)
                return dict(saved_id=False, msg=msg)
        except Exception as e:
            msg = "<=TEST=> _model_save_insert: Error: {}\n-->\t db_model: {}\n-->\t details: {} ".format(
                e, UploadTests, upload_test)
            log.error(msg)
            return dict(saved_id=False, error=e)

    def std_read(self, **kwargs):
        """
        Input args as outputs from STDOUT and STDERR
        Compose messages, logs for pipes
        Output raw output for each pipe, if needed.

        output = out.readlines()  # <class 'list'>
        raw_out = "".join(output)  # <class 'str'> binary
        std_output = raw_out.encode('utf-8')  # <class 'bytes'>


        :param kwargs:
        :return:
        """
        out = kwargs['out']  # <class 'paramiko.channel.ChannelFile'>
        err = kwargs['err']

        std_output = b''
        stderr_output = b''
        important_output = ''

        if out:
            output = out.readlines()  # <class 'list'>
            raw_out = "".join(output)  # <class 'str'> binary
            if raw_out:
                std_output = raw_out.encode('utf-8')  # <class 'bytes'> a bytes-like object
        # This pipe of for unittest output only:
        if err:
            output = err.readlines()
            raw_out = "".join(output)
            if raw_out:
                stderr_output = raw_out.encode('utf-8')  # a bytes-like object

        try:
            formatted_stdout = std_output.decode('utf-8').replace(chr(27), ';').replace('[0G', '#').replace('[K', '\n')
            important_output = self.out_clear_re.sub('', formatted_stdout)
            # log.debug("IMPORTANT OUT: \n%s", important_output)
        except Exception as e:
            log.error("STDOUT Cannot decode and replace for clear log: %s", e)
            formatted_stdout = std_output

        try:
            formatted_stderr = stderr_output.decode('utf-8').replace(chr(27), ';').replace('[0G', '#').replace('[K', '\n')
        except Exception as e:
            log.error("STDERR Cannot decode and replace for clear log: %s", e)
            formatted_stderr = stderr_output

        try:
            raw_out = std_output + stderr_output
        except Exception as e:
            raw_out = "Cannot concatenate stdout+stderr: {}".format(e)
            log.error(raw_out)

        upload_outputs_d = dict(
            std_output=formatted_stdout,
            stderr_output=formatted_stderr,
            clean_std=important_output,
            # clean_err=stderr_output,  # Should be clean anyway
            raw_out=raw_out,
        )
        return upload_outputs_d

    @staticmethod
    def _choose_packages(mode, tku_type, addm_item):
        """
            ga_candidate_max {'package_type__max': 'TKN_release_2018-05-1-97'},
            released_tkn_max {'package_type__max': 'TKN_release_2018-06-1-104'}

        tku_type: ga_candidate, addm_released, released_tkn, tkn_main_continuous

        :param mode:
        :param tku_type:
        :param addm_item:
        :return:
        """
        ga_candidate_max = TkuPackages.objects.filter(tku_type__exact='ga_candidate').aggregate(Max('package_type'))
        released_tkn_max = TkuPackages.objects.filter(tku_type__exact='released_tkn').aggregate(Max('package_type'))
        tkn_main_continuous_max = TkuPackages.objects.filter(tku_type__exact='tkn_main_continuous').aggregate(
            Max('package_type'))

        tku_zip_ga = TkuPackages.objects.filter(
            tku_type__exact='ga_candidate',
            addm_version__exact=addm_item['addm_v_int'],
            package_type__exact=ga_candidate_max['package_type__max']).values()
        tku_zip_release = TkuPackages.objects.filter(
            tku_type__exact='released_tkn',
            addm_version__exact=addm_item['addm_v_int'],
            package_type__exact=released_tkn_max['package_type__max']).values()

        if mode == 'fresh':
            # When options install order is required:
            if tku_type == 'ga_candidate':
                tku_zip_d = dict(fresh=tku_zip_ga, upgrade=None)
            elif tku_type == 'released_tkn':
                tku_zip_d = dict(fresh=tku_zip_release, upgrade=None)
            elif tku_type == 'tkn_main_continuous':
                tkn_main_continuous = TkuPackages.objects.filter(
                    tku_type__exact='tkn_main_continuous',
                    addm_version__exact=addm_item['addm_v_int'],
                    package_type__exact=tkn_main_continuous_max['package_type__max']).values()
                tku_zip_d = dict(fresh=tkn_main_continuous, upgrade=None)
            else:
                log.info("<=RoutineCases=> mode is not set, can not choose any package to install!")
                raise Exception(
                    "<=RoutineCases=> mode is not set, can not choose any package to install! {} {} {}".format(mode,
                                                                                                               tku_type,
                                                                                                               addm_item))
        elif mode == "update":
            tku_zip_d = dict(fresh=tku_zip_release, upgrade=tku_zip_ga)
        else:
            msg = "<=RoutineCases=> I can't choose package based on current mode and args: {} {} {}".format(mode,
                                                                                                            tku_type,
                                                                                                            addm_item)
            log.warning(msg)
            raise Exception(msg)

        return tku_zip_d

    @staticmethod
    def _model_save_insert(mode, mode_key, composed_results_d, upload_outputs_d):
        """

        :param upload_outputs_d:
        :param mode_key:
        :param mode:
        :param composed_results_d:
        :return:
        """
        # PPRINT
        # log.debug("<=UploadTestExecutor=> _model_save_insert composed_results_d %s ", composed_results_d)
        # item_sort = json.dumps(composed_results_d, indent=2, ensure_ascii=False, default=pformat)
        # log.debug("<=UploadTestExecutor=> SORTED composed_results_d: %s", item_sort)
        from octo_tku_upload.models import UploadTests as UploadTestsOld
        upload_test = dict(
            # Current mode:
            test_mode=mode,
            mode_key=mode_key,
            # Clean outputs for debug:
            upload_test_str_stdout=upload_outputs_d['std_output'],
            upload_test_str_stderr=upload_outputs_d['stderr_output'],
            # Add important output:
            important_out=upload_outputs_d['clean_std'],
            # No need to add raw, which is raw_out = std_output + stderr_output
            # Composed and parsed:
            test_case_key=composed_results_d['test_case_key'],
            test_date=composed_results_d['test_date'],
            test_time=composed_results_d['test_time'],
            upload_test_status=composed_results_d['upload_test_status'],
            all_errors=composed_results_d['all_errors'],
            all_warnings=composed_results_d['all_warnings'],
            upload_warnings=composed_results_d['upload_warnings'],
            upload_errors=composed_results_d['upload_errors'],
            tku_statuses=composed_results_d['tku_statuses'],
            time_spent_test=composed_results_d['time_spent_test'],
            tested_zips=composed_results_d['tested_zips'],
            addm_name=composed_results_d['addm_name'],
            addm_v_int=composed_results_d['addm_v_int'],
            addm_host=composed_results_d['addm_host'],
            addm_ip=composed_results_d['addm_ip'],
            addm_version=composed_results_d['addm_version'],
            tku_type=composed_results_d['tku_type'],
            package_type=composed_results_d['package_type'],
            tku_build=composed_results_d['tku_build'],
            tku_date=composed_results_d['tku_date'],
            tku_month=composed_results_d['tku_month'],
        )
        try:
            upload_tst = UploadTestsOld(**upload_test)
            upload_tst.save(force_insert=True)
            if upload_tst.id:
                # NOTE: Return short description of test, not the full output:
                # NOTE: 2 We already have most of these args in task body!
                return dict(saved_id=upload_tst.id)
            else:
                msg = "Test result not saved! Result: {}".format(upload_test)
                log.error(msg)
                return dict(saved_id=False, msg=msg)
        except Exception as e:
            msg = "<=TEST=> _model_save_insert: Error: {}\n-->\t db_model: {}\n-->\t details: {} ".format(
                e, UploadTestsOld, upload_test)
            log.error(msg)
            return dict(saved_id=False, error=e)

    @staticmethod
    def _compose_test_results(addm_item, test_zip, upload_results_d, time_spent_test, mode_key):
        """

        :param mode_key:
        :param time_spent_test:
        :param addm_item:
        :param test_zip:
        :param upload_results_d:
        :return:
        """
        # log.debug("<=UploadTestExecutor=> _compose_test_results %s %s %s", addm_item, test_zip, time_spent_test)
        try:
            zip_tested = []
            zip_tested_md5sum = []
            time_now = datetime.now()
            test_date = time_now.strftime('%Y-%m-%d')
            test_time = time_now.strftime('%H-%M-%S')

            single_zip = test_zip[0]
            test_case_key = '{}_{}_{}_{}'.format(
                single_zip['tku_type'],
                single_zip['package_type'],
                addm_item['addm_name'],
                mode_key, )

            for zip_item in test_zip:
                zip_item_d = dict(
                    zip_file_path=zip_item['zip_file_path'],
                    zip_file_name=zip_item['zip_file_name'],
                    package_type=zip_item['package_type'],
                    tku_type=zip_item['tku_type'],
                    zip_type=zip_item['zip_type'],
                    addm_version=zip_item['addm_version'],
                    tku_name=zip_item['tku_name'],
                    tku_addm_version=zip_item['tku_addm_version'],
                    tku_build=zip_item['tku_build'],
                    tku_date=zip_item['tku_date'],
                    tku_month=zip_item['tku_month'],
                    tku_pack=zip_item['tku_pack'],
                )
                zip_tested.append(zip_item_d)
                zip_tested_md5sum.append(zip_item['zip_file_md5_digest'])

            composed_results_d = dict(
                test_case_key=test_case_key,
                test_date=str(test_date),
                test_time=str(test_time),
                upload_test_status=upload_results_d['upload_status'],
                all_errors=upload_results_d['all_errors'],
                all_warnings=upload_results_d['all_warnings'],
                upload_warnings=upload_results_d['upload_warnings'],
                upload_errors=upload_results_d['upload_errors'],
                tku_statuses=upload_results_d['tku_statuses'],
                time_spent_test=str(time_spent_test),

                # TODO: Change to md5sum list:
                tested_zips=zip_tested,
                zip_tested_md5sum=zip_tested_md5sum,

                addm_name=addm_item['addm_name'],
                addm_v_int=addm_item['addm_v_int'],
                addm_host=addm_item['addm_host'],
                addm_ip=addm_item['addm_ip'],
                addm_version=single_zip['addm_version'],
                tku_type=single_zip['tku_type'],
                package_type=single_zip['package_type'],
                tku_build=single_zip['tku_build'],
                tku_date=single_zip['tku_date'],
                tku_month=single_zip['tku_month'],
                zip_file_md5_digest=single_zip['zip_file_md5_digest'],
            )
            return composed_results_d
        except Exception as e:
            log.error("<=UploadTestExecutor=> Cannot _compose_test_results: Error: %s", e)
