"""
Tests execute here.
WIll use same logic from TPL IDE Automation.

"""

# Python logger
import logging
import re

from datetime import datetime
from queue import Queue
from threading import Thread
from time import time

from octo.helpers.tasks_mail_send import Mails
from octo.helpers.tasks_helpers import exception

from octo_tku_upload.models import UploadTestsNew as UploadTests
from run_core.addm_operations import ADDMOperations, ADDMStaticOperations

log = logging.getLogger("octo.octologger")


class UploadTestExec:

    def __init__(self):
        self.preparation_steps = dict(
            fresh=[
                'show.addm.version'
                'test.kill',
                'tku.install.kill',
                'tw_scan_control.clear',
                'tw_pattern_management.remove_all',
                'rpm.delete.tideway_content',
                'rpm.delete.tideway_devices',
            ],
            update=['show.addm.version', 'tw_scan_control.clear'],
            step=['show.addm.version', 'tw_scan_control.clear'],
            tideway_content=[
                'show.addm.version',
                'tku.install.kill',
                'tw_scan_control.clear',
                'tw_pattern_management.remove_all',
                'rpm.delete.tideway_content',
            ],
            tideway_devices=[
                'show.addm.version',
                'tku.install.kill',
                'tw_scan_control.clear',
                'tw_pattern_management.remove_all',
                'rpm.delete.tideway_devices',
            ],
            upload_unzip=['wipe.tideway.TEMP', 'mkdir.tideway.TEMP']
        )

        self.out_clear_re = re.compile(r';#.*;\n')
        self.upload_packages_status_re = re.compile(
            r'Uploaded\s(?P<zip_file>\S+)\s(?:as|adding\sto)\s(?P<tku_package>\S+)\"\s')
        self.upload_packages_skipped_re = re.compile(
            r"Skipping\s(?P<tku_name>.+(?=\s-))\s-\s(?P<reason>.+)")
        self.product_content_re = re.compile(
            r"(?P<cause>(?<!Product\sContent)\w+|(?:\s))\s+Product\sContent\s+(?P<reason>.+)")
        self.warnings_re = re.compile(
            r"Pattern\smodule\s(?P<module>\S+)\s+Warnings:\s+(?P<error>.+)")
        self.errors_re = re.compile(
            r"Pattern\smodule\s(?P<module>\S+)\s+Errors:\s+(?P<error>.+)")

    @exception
    def upload_preparations_threads(self, **kwargs):
        """
        Run sequence of commands on each ADDM to prepare it for TKU Install.
        Usually just delete older TKU (to install released one later), restart services and so on.
        """
        user_email = kwargs.get('user_email', None)
        addm_items = kwargs.get('addm_items', None)
        test_mode = kwargs.get('test_mode', None)
        step_k = kwargs.get('step_k', None)
        addm_group = kwargs.get('addm_group', None)

        ts = time()
        start_time = datetime.now()
        thread_outputs = []

        preps = self.preparation_steps[test_mode]
        commands = ADDMStaticOperations.select_operation(preps)
        for operation_cmd in commands:
            out = ADDMStaticOperations().threaded_exec_cmd(addm_set=addm_items, operation_cmd=operation_cmd)
            thread_outputs.append(out)
        log.info(f"ADDM Preparations output: {thread_outputs}")

        subject = f"TKU_Upload_routines | upload_preparations_threads | {step_k} |  {addm_group} | Finished!"
        log.info(subject)
        body = f"ADDM group: {addm_group}, \n\ttest_mode: {test_mode}, \n\tstep_k: {step_k}, " \
               f"\n\tstart_time: {start_time}, \n\ttime spent: {time() - ts}, \n\tout: {thread_outputs}"
        Mails.short(subject=subject, body=body, send_to=[user_email])
        return f'upload_preparations_threads Took {time() - ts} {body}'

    @exception
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
        addm_group = kwargs.get('addm_group', None)
        pack = packages.first()

        thread_list = []
        thread_outputs = []
        ts = time()
        test_q = Queue()
        start_time = datetime.now()

        for addm_item in addm_items:
            ssh = ADDMOperations().ssh_c(addm_item=addm_item, where="Executed from upload_run_threads in UploadTestExec")
            if ssh and ssh.get_transport().is_active():
                m = f"<=upload_unzip_threads=> OK: SSH Is active - continue... ADDM: {addm_item['addm_name']} {addm_item['addm_host']} {addm_item['addm_group']}"
                log.info(m)
                kwargs = dict(ssh=ssh, addm_item=addm_item, packages=packages, test_q=test_q)
                th_name = f"Upload unzip TKU: addm {addm_item['addm_name']}"
                try:
                    unzip_th = Thread(target=ADDMOperations().upload_unzip, name=th_name, kwargs=kwargs)
                    unzip_th.start()
                    thread_list.append(unzip_th)
                except Exception as e:
                    msg = f"Thread test fail with error: {e}"
                    log.error(msg)
                    return msg
            else:
                msg = f"<=upload_unzip_threads=> SSH Connection could not be established thread skipping for ADDM: " \
                      f"{addm_item['addm_ip']} - {addm_item['addm_host']} in {addm_item['addm_group']}"
                log.error(msg)
                thread_outputs.append(msg)
        for test_th in thread_list:
            test_th.join()
            th_out = test_q.get()
            thread_outputs.append(th_out)
        log.info(f"ADDM Unzip TKUs output: {thread_outputs}")
        # Email confirmation when execution was finished:
        subject = f"TKU_Upload_routines | upload_unzip_threads | {step_k} |  {addm_group} | Finished!"
        log.info(subject)
        body = f"ADDM group: {addm_group}, \n\ttest_mode: {test_mode}, \n\tstep_k: {step_k}, " \
               f"\n\ttku_type: {pack.tku_type}, \n\tpackage_type: {pack.package_type}, \n\tstart_time: {start_time}, " \
               f"\n\ttime spent: {time() - ts}, \n\tout: {thread_outputs}"
        Mails.short(subject=subject, body=body, send_to=[user_email])
        return f'upload_unzip_threads Took {time() - ts} {body}'

    @exception
    def install_tku_threads(self, **kwargs):
        """ Simple TKU Install process, runs for each ADDM om set, with tw_pattern_management utility.
            Return Outputs which need to be saved into DB!
            NOTE: Better not to simplify this as threaded_exec_cmd, because we require more detailed run and output.
        """
        user_email = kwargs.get('user_email', None)
        addm_items = kwargs.get('addm_items', None)
        packages = kwargs.get('packages', None)
        test_mode = kwargs.get('test_mode')
        step_k = kwargs.get('step_k')
        addm_group = kwargs.get('addm_group', None)

        package_detail = kwargs.get('package_detail', None)
        pack = packages.first()

        thread_list = []
        thread_outputs = []
        ts = time()
        test_q = Queue()
        start_time = datetime.now()

        if package_detail:
            mode_key = f'{pack.tku_type}.{test_mode}.{step_k}.{package_detail}'
        else:
            mode_key = f'{pack.tku_type}.{test_mode}.{step_k}'

        for addm_item in addm_items:
            addm_group = addm_item['addm_group']
            msg = f"<=Upload TKU Install Thread=> {addm_item['addm_name']}:{addm_item['addm_v_int']} mode_key={mode_key}"
            log.debug(msg)

            # Open SSH connection:
            ssh = ADDMOperations().ssh_c(addm_item=addm_item, where="Executed from upload_run_threads in UploadTestExec")
            if ssh and ssh.get_transport().is_active():
                m = f"<=install_tku_threads=> OK: SSH Is active - continue... ADDM: {addm_item['addm_name']} {addm_item['addm_host']} {addm_item['addm_group']}"
                log.info(m)
                kwargs = dict(ssh=ssh, addm_item=addm_item, package_detail=package_detail, test_q=test_q)
                th_name = f"Upload unzip TKU: addm {addm_item['addm_name']}"
                try:
                    install_th = Thread(target=self.install_activate, name=th_name, kwargs=kwargs)
                    install_th.start()
                    thread_list.append(install_th)
                except Exception as e:
                    msg = f"Thread test fail with error: {e}"
                    log.error(msg)
                    thread_outputs.append(msg)
            else:
                msg = f"<=install_tku_threads=> SSH Connection could not be established thread skipping for ADDM: " \
                      f"{addm_item['addm_ip']} - {addm_item['addm_host']} in {addm_item['addm_group']}"
                log.error(msg)
                thread_outputs.append(msg)

        for test_th in thread_list:
            test_th.join()
            th_out = test_q.get()
            thread_outputs.append(th_out)  # {addm_item:addm_item, output:upload_outputs_d}
            msg = f'tku_type={packages[0].tku_type};package_type={packages[0].package_type};' \
                  f'test_mode={test_mode}:step_k={step_k};package_detail={package_detail}'
            self.model_save_insert(th_out=th_out, test_mode=test_mode, mode_key=mode_key, packages=packages, ts=ts)

        # Email confirmation when execution was finished:
        subject = f"TKU_Upload_routines | install_tku_threads | {test_mode} | {step_k} | {addm_group} | Finished!"
        log.info(subject)
        body = f"ADDM group: {addm_group}, test_mode: {test_mode}, step_k: {step_k}, tku_type: {pack.tku_type}, " \
               f"package_type: {pack.package_type}, package_detail: {package_detail}, " \
               f"start_time: {start_time}, time spent: {time() - ts} mode_key={mode_key} "
        Mails.short(subject=subject, body=body, send_to=[user_email])
        return f'install_tku_threads Took {time() - ts} {body}'

    @exception
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
        cmd_outputs = []

        if ssh and ssh.get_transport().is_active():
            log.info("<=upload_preparations=> PASSED: SSH Is active")

        preps = self.preparation_steps[mode]
        for operation_cmd in preps:
            res = "ADDMStaticOperations().solo_exec_cmd(ssh=ssh, addm_item=addm_item, operation_cmd=operation_cmd)"
            cmd_outputs.append(f"{operation_cmd} {mode} {addm_item['addm_name']} output: {res}")

        test_q.put(cmd_outputs)
        return True

    @exception
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
        package_detail = kwargs.get('package_detail')

        if ssh and ssh.get_transport().is_active():
            log.info("<=install_activate=> PASSED: SSH Is active")

        cmd_ = "/usr/tideway/bin/tw_pattern_management -p system  --install-activate {} " \
               "--show-progress --loglevel=debug /usr/tideway/TEMP/"

        if float(addm_item['addm_v_int']) > 11.1:
            cmd = cmd_.format('--allow-restart')
        else:
            cmd = cmd_.format('')

        if package_detail:
            cmd += f"{package_detail}*"
        else:
            if float(addm_item['addm_v_int']) > 11.1:
                cmd += "*"
            else:
                cmd += "*.zip"

        # noinspection PyBroadException
        try:
            log.debug("Try CMD: (%s) | on %s - %s ", cmd, addm_item['addm_host'], addm_item['addm_name'])
            _, stdout, stderr = ssh.exec_command(cmd)
            upload_outputs_d = self.std_read(out=stdout, err=stderr)
            test_q.put({"output": upload_outputs_d, "addm_item": addm_item})

        except Exception as e:
            msg = "<=UploadTestExecutor=> Error during 'install_activate' for: {} {}".format(cmd, e)
            log.error(msg)
            raise Exception(msg)

    @exception
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

    @exception
    def model_save_insert(self, **kwargs):
        ts = kwargs.get('ts')
        th_out = kwargs.get('th_out')
        test_mode = kwargs.get('test_mode')
        mode_key = kwargs.get('mode_key')
        packages = kwargs.get('packages')

        package_type = packages[0].package_type
        tku_type = packages[0].tku_type

        addm_item = th_out.get('addm_item')

        upload_outputs_d = th_out.get('output')
        upload_results_d = self.parse_upload_result(upload_outputs_d)

        upload_test = dict(
            # Used mode and mode key:
            test_mode=test_mode,  # What package to install;
            mode_key=mode_key,  # In which order or case to install package;
            # TKU zip details:
            tku_type=tku_type,  # ga_candidate, ..
            package_type=package_type,  # TKN_release_2019-01-1-131, ..
            # # Clean outputs for debug:
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
            # Addm item details:
            addm_name=addm_item['addm_name'],
            addm_v_int=addm_item['addm_v_int'],
            addm_host=addm_item['addm_host'],
            addm_ip=addm_item['addm_ip'],
            addm_version=addm_item['addm_full_version'],
            # Test lasts
            time_spent_test=str(time() - ts),
        )

        upload_tst = UploadTests(**upload_test)
        upload_tst.save(force_insert=True)
        if upload_tst.id:
            # NOTE: Return short description of test, not the full output:
            # NOTE: 2 We already have most of these args in task body!
            return dict(saved_id=upload_tst.id)
        else:
            msg = f"Test result not saved! Result: {upload_test}"
            log.error(msg)
            return dict(saved_id=False, msg=msg)

    @exception
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
