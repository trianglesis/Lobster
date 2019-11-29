"""
Tests execute here.
WIll use same logic from TPL IDE Automation.

"""

import os
import re
from time import time, sleep

from run_core.addm_operations import ADDMOperations
from octo_tku_patterns.models import TestLast, TestHistory

# Python logger
import logging

log = logging.getLogger("octo.octologger")


class TestExecutor:

    # noinspection PyUnresolvedReferences,SpellCheckingInspection
    def __init__(self):
        """
        May init here some tests lists before?
        /home/user/TH_Octopus/perforce

        For ADDMs example:
        /usr/tideway/SYNC
        /usr/tideway/SYNC/addm/tkn_main/

        """
        # Usual tree paths for TKN:
        # For Otopus
        if os.name == "nt":
            self.p4_workspace = "d:{}perforce".format(os.sep)
        else:
            self.p4_workspace = "/home/user/TH_Octopus/perforce"
        self.octo_workspace = self.p4_workspace

        # For ADDMs:
        self.addm_vm_test_workspace = "/usr/tideway/SYNC"
        self.addm_vm_nfs_workspace = "/usr/tideway/TKU"

    def test_run_threads(self, **kwargs):
        """
        Run each test in pair of connected ADDM instance separately from each other.
        Each this instance is an instance of SSH console of active ADDM + added
        test args to test_exec(). Execute each test.

        """
        # noinspection PyCompatibility
        from queue import Queue
        from threading import Thread

        test_function = kwargs.get('test_function', False)
        addm_items = kwargs.get('addm_items')
        test_item = kwargs.get('test_item')
        test_output_mode = kwargs.get('test_output_mode')

        isinstance(addm_items, dict), "Addm items should be a dict: %s" % type(addm_items)
        isinstance(test_item, dict), "Test item should be a dict: %s " % type(test_item)

        thread_list = []
        test_outputs = []
        ts = time()
        test_q = Queue()
        if isinstance(test_item, dict):
            for addm_item in addm_items:
                # Open SSH connection:
                ssh = ADDMOperations().ssh_c(addm_item=addm_item, where="Executed from test_run_threads in TestExecutor")
                # If opened connection is Up and alive:
                if ssh:
                    args_d = dict(ssh=ssh, test_item=test_item, addm_item=addm_item,
                                  test_function=test_function, test_output_mode=test_output_mode, test_q=test_q)
                    th_name = f"Test thread: addm {addm_item['addm_ip']} test {test_item['test_py_path']}"
                    try:
                        test_thread = Thread(target=self.test_exec, name=th_name, kwargs=args_d)
                        test_thread.start()
                        thread_list.append(test_thread)
                    except Exception as e:
                        msg = "Thread test fail with error: {}".format(e)
                        log.error(msg)
                        # raise Exception(msg)
                        return msg
                # When SSH is not active - skip thread for this ADDM and show log error (later could raise an exception?)
                else:
                    msg = f"<=test_run_threads=> SSH Connection could not be established, thread skipping for ADDM: " \
                          f"{addm_item['addm_ip']} - {addm_item['addm_host']} in {addm_item['addm_group']}"
                    log.error(msg)
                    test_outputs.append(msg)
                    # Raise exception? Stop Execution?
                    # Send mail with this error? BUT not for the multiple tasks!!!

            # Execute threads:
            for test_th in thread_list:
                test_th.join()
                test_outputs.append(test_q.get())
        else:
            msg = "Test item is not a dict! Test Item: {}".format(test_item)
            log.error(msg)
            # raise Exception(msg)
            return msg
        # Do not return much output, or celery and flower can cut it or fail.
        # return 'All tests took {}'.format(time() - ts)
        return 'All tests Took {} Out {}'.format(time() - ts, test_outputs)

    def test_exec(self, **args_d):
        """
        This function execute tests for patterns.
        For test run - test list should be used, even with 1 element.

        Before run it will load tkn_main_bashrc/tkn_ship_bashrc to activate paths to python, tideway, core etc.

        """
        # TODO: Check paramiko to use env from here, not from bashrc
        my_env = os.environ.copy()

        ts = time()
        ssh = args_d.get('ssh')
        test_item = args_d.get('test_item')
        addm_item = args_d.get('addm_item')
        test_output_mode = args_d.get('test_output_mode', False)
        test_function = args_d.get('test_function', '')
        test_q = args_d.get('test_q')

        test_py_t = test_item.get('test_py_path_template', False)
        test_time_weight = test_item.get('test_time_weight', '')

        modern_addms = ['fishfinger']
        test_info = f" {test_py_t} | '{addm_item['addm_name']}' v'{addm_item['addm_v_int']}' " \
                    f"{addm_item['addm_ip']} - {addm_item['addm_host']} {addm_item['addm_group']}"

        bin_python = '/usr/tideway/bin/python'
        if addm_item['addm_name'] in modern_addms:
            bin_python = '/usr/tideway/bin/python3'

        if test_py_t:
            log.debug("<=TEST=> START t:%s %s", test_time_weight, test_info)
            # Change local Octopus path to remote ADDM path:
            test_py_sync = test_py_t.format(self.addm_vm_test_workspace)
            test_wd_sync = test_item.get('test_dir_path_template').format(self.addm_vm_test_workspace)
            tkn_branch = test_item.get('tkn_branch')

            if test_function:
                cmd = f". ~/.{tkn_branch}_bashrc; cd {test_wd_sync}; {bin_python} -u {test_py_sync}" \
                      f" --universal_dml=1 --verbose {test_function.replace('+', '.')}"
            else:
                cmd = f". ~/.{tkn_branch}_bashrc; cd {test_wd_sync}; {bin_python} -u {test_py_sync}" \
                      f" --universal_dml=1 --verbose"

            log.debug("CMD-> '%s'", cmd)
            # Test execution:
            cmd = 'ls'
            log.debug("Making FAKE TEST %s", cmd)
            sleep(10)
            _, stdout, stderr = ssh.exec_command(cmd)
            std_out_err_d = self.std_read(out=stdout, err=stderr, mode=test_output_mode, mgs="<=TEST=>")

            time_spent_test = time() - ts
            log.debug("<=TEST=> FINISH %s", test_info)
            update_save = 'Fake update table!!!!!'
            update_save = self.parse_test_result(stderr_output=std_out_err_d['stderr_output'],
                                                 test_item=test_item,
                                                 addm_item=addm_item,
                                                 time_spent_test=str(time_spent_test))
            # Close previously opened SSH:
            ssh.close()
            # Put test results into a thread queue output:
            test_q.put(update_save)
            # test_q.put('test fake')
        else:
            msg = "<=TEST ERROR=> Test has no test_py_path value! {}".format(test_item)
            log.error(msg)
            test_q.put(msg)
        return True

    @staticmethod
    def std_read(**kwargs):
        """
        Input args as outputs from STDOUT and STDERR
        Compose messages, logs for pipes
        Output raw output for each pipe, if needed.

        :param kwargs:
        :return:
        """
        out = kwargs.get('out')
        err = kwargs.get('err')
        mgs = kwargs.get('mgs')
        mode = kwargs.get('mode')

        if not mode:
            mode = "silent"

        std_output = ""
        stderr_output = ""

        if out:
            output = out.readlines()
            raw_out = "".join(output)
            if raw_out:
                std_output = raw_out
                # sys.stdout.write('\b')
                # noinspection SpellCheckingInspection
                if mode == "verbose":
                    log.debug("%s STDOUT \n%s", mgs, raw_out)
                elif mode == "testlog":
                    log.debug("%s STDOUT \n%s", mgs, raw_out)
                elif mode == "silent":
                    pass
        # This pipe of for unittest output only:
        if err:
            output = err.readlines()
            raw_out = "".join(output)
            if raw_out:
                stderr_output = raw_out
                # sys.stdout.write('\b')
                # noinspection SpellCheckingInspection
                if mode == "verbose":
                    log.debug("%s UNITTEST \n%s", mgs, raw_out)
                elif mode == "testlog":
                    log.debug("%s UNITTEST \n%s", mgs, raw_out)
                elif mode == "silent":
                    pass

        return dict(std_output=std_output, stderr_output=stderr_output)

    def parse_test_result(self, **test_res_args) -> dict:
        # noinspection SpellCheckingInspection,PyPep8
        """
            Parse test result during run and add to database.

            # (?P<test_name>test(?:\S+|)_\S+)\s\((?P<module>\S+)\.(?P<class>\S+)\)(?P<message>(?:(?:\n.*(?<!^)|\s)\.{3}\s))(?P<status>.+$)
            Get STDERR UNITTEST content.

            OLD:
            re.compile(r'(?P<test_name>test(?:\S+|)_\S+)\s'
                                             r'\((?P<module>\S+)\.(?P<class>\S+)\)'
                                             r'(?P<message>(?:(?:\n.*(?<!^)|\s)\.{3}\s))'
                                             r'(?P<status>.+$)', re.MULTILINE)
             NEW:
             re.compile(r'(?P<test_name>test(?:\S+|)_|\S+)\s'
                                             r'\((?P<module>\S+)\.(?P<class>\S+)\)'
                                             r'(?P<message>(?:(?:\n.*(?<!^)|\s)\.{3}\s))'
                                             r'(?P<status>.+$)', re.MULTILINE)

            saved_last_d {'saved_id': 364797, 'item':
                {'addm_name': 'custard_cream', 'addm_v_int': '11.2', 'addm_host': 'vl-aus-rem-qa6h',
                 'time_spent_test': '99.78856325149536',
                 'test_py_path': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/CORE/SunCluster/tests/test.py',
                 'pattern_folder_name': 'SunCluster', 'pattern_library': 'CORE',
                 'addm_group': 'delta', 'tkn_branch': 'tkn_main'},
                'save_insert': <TestLast: TestLast object>}

        Traceback (most recent call last):
          File "/usr/local/lib/python3.6/threading.py", line 916, in _bootstrap_inner
            self.run()
          File "/usr/local/lib/python3.6/threading.py", line 864, in run
            self._target(*self._args, **self._kwargs)
          File "/var/www/octopus/octo_tku_patterns/test_executor.py", line 167, in test_exec
            time_spent_test=str(time_spent_test))
          File "/var/www/octopus/octo_tku_patterns/test_executor.py", line 307, in parse_test_result
            test_fil_details = re.finditer(fail_details_srt, stderr_output, re.MULTILINE)
          File "/var/www/octopus/octo/lib/python3.6/re.py", line 229, in finditer
            return _compile(pattern, flags).finditer(string)
          File "/var/www/octopus/octo/lib/python3.6/re.py", line 301, in _compile
            p = sre_compile.compile(pattern, flags)
          File "/var/www/octopus/octo/lib/python3.6/sre_compile.py", line 562, in compile
            p = sre_parse.parse(p, flags)
          File "/var/www/octopus/octo/lib/python3.6/sre_parse.py", line 855, in parse
            p = _parse_sub(source, pattern, flags & SRE_FLAG_VERBOSE, 0)
          File "/var/www/octopus/octo/lib/python3.6/sre_parse.py", line 416, in _parse_sub
            not nested and not items))
          File "/var/www/octopus/octo/lib/python3.6/sre_parse.py", line 765, in _parse
            p = _parse_sub(source, state, sub_verbose, nested + 1)
          File "/var/www/octopus/octo/lib/python3.6/sre_parse.py", line 416, in _parse_sub
            not nested and not items))
          File "/var/www/octopus/octo/lib/python3.6/sre_parse.py", line 502, in _parse
            code = _escape(source, this, state)
          File "/var/www/octopus/octo/lib/python3.6/sre_parse.py", line 401, in _escape
            raise source.error("bad escape %s" % escape, len(escape))
        sre_constants.error: bad escape \P at position 65


            THIS TUNED ONLY FOR VERBOSE OUTPUTS!
            :param test_res_args:
            :return:
        """
        updated_saved_last = dict(table="last", saved=False)
        updated_saved_hist = dict(table="history", saved=False)
        stderr_output = test_res_args['stderr_output']
        test_item_d = test_res_args['test_item']
        addm_item_d = test_res_args['addm_item']
        time_spent_test = test_res_args['time_spent_test']
        test_name_f_verb_re = re.compile(r'(?P<test_name>test(?:\S+|)_|\S+)\s'
                                         r'\((?P<module>\S+)\.(?P<class>\S+)\)'
                                         r'(?P<message>(?:(?:\n.*(?<!^)|\s)\.{3}\s))'
                                         r'(?P<status>.+$)', re.MULTILINE)
        re_draft_3 = r'(?P<fail>{0}:)\s' \
                     r'(?P<test_name>{1})\s' \
                     r'\((?P<module>{2})\.(?P<class>{3})\)' \
                     r'(?P<message>(?:\n.*(?<!^))+)'

        # test_res = dict(time_spent_test=time_spent_test)
        # log.debug("<=PARSE_TEST_RESULT=>  -> stderr_output %s", stderr_output)
        if stderr_output:
            # Check if test has expected output:
            test_output = re.match(test_name_f_verb_re, stderr_output)
            if test_output:
                # log.info("<=PARSE_TEST_RESULT=> Test output has an expected format!")
                # Search for all test declarations after run. In TOP if content.
                test_cases = re.finditer(test_name_f_verb_re, stderr_output)
                # log.debug("<=PARSE_TEST_RESULT=> Parse test_cases output with: %s", test_name_f_verb_re)
                if test_cases:
                    # log.info("<=PARSE_TEST_RESULT=> if test_cases IS TRUE!!!")
                    # log.info("<=PARSE_TEST_RESULT=> test_cases %s", test_cases)
                    # For each found test item do parse:
                    for item in test_cases:
                        # log.info("<=PARSE_TEST_RESULT=> item in test_cases %s", item)
                        tst_message = item.group('message')
                        tst_name = item.group('test_name')
                        tst_module = item.group('module')
                        tst_class = item.group('class')
                        tst_status = item.group('status')
                        fail_status = ''
                        fail_name = ''
                        fail_module = ''
                        fail_class = ''
                        fail_message = ''

                        # Check the other part of content for fail|error details with composed regex:
                        fail_details_srt = re_draft_3.format(tst_status, tst_name, tst_module, tst_class)
                        # log.debug("<=PARSE_TEST_RESULT=> Parse test output with: %s", fail_details_srt)
                        test_fil_details = re.finditer(fail_details_srt, stderr_output, re.MULTILINE)
                        if test_fil_details:
                            # Parse each detail.
                            for detail in test_fil_details:
                                fail_status = detail.group('fail')
                                fail_name = detail.group('test_name')
                                fail_module = detail.group('module')
                                fail_class = detail.group('class')
                                fail_message = detail.group('message').replace("-" * 70, "").replace("=" * 70, "")
                        test_res = (
                            dict(tst_message=tst_message, tst_name=tst_name, tst_module=tst_module, tst_class=tst_class,
                                 tst_status=tst_status, fail_status=fail_status, fail_name=fail_name,
                                 fail_module=fail_module, fail_class=fail_class, fail_message=fail_message,
                                 time_spent_test=time_spent_test))
                        # Django model way to insert into LAST TESTS table:
                        try:
                            saved_last_d = self.model_save_insert(TestLast, test_res, test_item_d, addm_item_d)
                            updated_saved_last.update(saved=saved_last_d)
                        except Exception as e:
                            m = "<=PARSE_TEST_RESULT=> updated_saved_last had failed with error: {}".format(e)
                            log.error(m)
                        # Django model way to insert into HISTORY TESTS table:
                        try:
                            saved_hist_d = self.model_save_insert(TestHistory, test_res, test_item_d, addm_item_d)
                            updated_saved_hist.update(saved=saved_hist_d)
                        except Exception as e:
                            m = "<=PARSE_TEST_RESULT=> updated_saved_hist had failed with error: {}".format(e)
                            log.error(m)

            else:
                # In case when traceback occurs BEFORE test actually executed:
                log.info("<=PARSE_TEST_RESULT=> Test output has an UNEXPECTED format!")
                test_res = (dict(tst_status='ERROR', fail_message=stderr_output, time_spent_test=time_spent_test))
                log.error("<=PARSE_TEST_RESULT=> test_res %s", test_res)
                # When test has an error in itself - save only to last table, not to the history:
                try:
                    saved_last_d = self.model_save_insert(TestLast, test_res, test_item_d, addm_item_d)
                    updated_saved_last.update(saved=saved_last_d)
                except Exception as e:
                    m = "<=PARSE_TEST_RESULT=> updated_saved_last had failed with error: {}".format(e)
                    log.error(m)

        else:
            log.warning("<=PARSE_TEST_RESULT=> There is no test STDERR output! Kwargs: %s", test_res_args)

        # NOTE: To debug - use 'stderr_output': stderr_output for prod - it could produce too big output!
        # return {'last': updated_saved_last, 'history': updated_saved_hist, 'stderr_output': stderr_output}
        return {'last': updated_saved_last, 'history': updated_saved_hist}

    @staticmethod
    def model_save_insert(db_model, test_res, test_item_d, addm_item_d):
        """
        Here compose dict of test results and addm+test item values to save them
            in database of latest tests and history.
        Warning: do not raise exceptions, this should run in Threads so it will wait an output.
            While raise can produce a deadlock for celery worker!

        :type db_model: class
        :type test_res: dict
        :type test_item_d: dict
        :type addm_item_d: dict
        :return:
        """
        # TODO: If save fail - try to save full stderr instead.

        test_data_res = dict(
            # Part from tku_patterns table
            tkn_branch=test_item_d['tkn_branch'],
            pattern_library=test_item_d['pattern_library'],
            pattern_file_name=test_item_d['pattern_file_name'],
            pattern_folder_name=test_item_d['pattern_folder_name'],
            pattern_file_path=test_item_d['pattern_file_path'],
            test_py_path=test_item_d['test_py_path'],
            pattern_folder_path_depot=test_item_d['pattern_folder_path_depot'],
            pattern_file_path_depot=test_item_d['pattern_file_path_depot'],
            is_key_pattern=test_item_d['is_key_pattern'],
            # Part from test parsed data
            tst_message=test_res.get('tst_message', ''),
            tst_name=test_res.get('tst_name', ''),
            tst_module=test_res.get('tst_module', ''),
            tst_class=test_res.get('tst_class', ''),
            tst_status=test_res.get('tst_status', ''),
            fail_status=test_res.get('fail_status', ''),
            fail_name=test_res.get('fail_name', ''),
            fail_module=test_res.get('fail_module', ''),
            fail_class=test_res.get('fail_class', ''),
            fail_message=test_res.get('fail_message', ''),
            time_spent_test=test_res.get('time_spent_test', ''),
            # Part from addm_dev table
            addm_name=addm_item_d['addm_name'],
            addm_group=addm_item_d['addm_group'],
            addm_v_int=addm_item_d['addm_v_int'],
            addm_host=addm_item_d['addm_host'],
            addm_ip=addm_item_d['addm_ip'])

        # Insert everything:
        # TODO: If not parsed or traceback occurs - save with default pattern name and raw output:
        # TODO: Return True when OK, and False + stderr when Exception occurs
        try:
            save_tst = db_model(**test_data_res)
            save_tst.save(force_insert=True)
            if save_tst.id:
                # NOTE: Return short description of test, not the full output:
                # NOTE: 2 We already have most of these args in task body!
                return dict(saved_id=save_tst.id)
            else:
                msg = "Test result not saved! Result: {}".format(test_data_res)
                log.error(msg)
                return dict(saved_id=False, msg=msg)

        except Exception as e:
            msg = "<=TEST=> _model_save_insert: Error: {}\n-->\t db_model: {}\n-->\t details: {} ".format(
                e, db_model, test_data_res)
            log.error(msg)
            return dict(saved_id=False, error=e)
