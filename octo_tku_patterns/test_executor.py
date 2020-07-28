"""
Tests execute here.
WIll use same logic from TPL IDE Automation.

"""

# Python logger
import logging
import os
import re
import datetime
from time import time

from django.conf import settings

from octo.helpers.tasks_helpers import exception
from octo_tku_patterns.api.serializers import TestCasesSerializer
from octo_tku_patterns.models import TestLast, TestHistory
from run_core.addm_operations import ADDMOperations
from run_core.models import Options

from django.db.models.query import QuerySet
from octo_tku_patterns.models import TestCases

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
        # TODO: Should be initialised with all needed data before run any threads
        # TODO: We may want to save who run this test?
        self.user_email = ''

        if settings.DEV:
            self.p4_workspace = "d:{}perforce".format(os.sep)
        else:
            self.p4_workspace = "/home/user/TH_Octopus/perforce"
        self.octo_workspace = self.p4_workspace

        # For ADDMs:
        self.addm_vm_test_workspace = "/usr/tideway/SYNC"
        self.addm_vm_nfs_workspace = "/usr/tideway/TKU"

    @exception
    def test_run_threads(self, **kwargs):
        """
        Run each test in pair of connected ADDM instance separately from each other.
        Each this instance is an instance of SSH console of active ADDM + added
        test args to test_exec(). Execute each test.

        """
        # noinspection PyCompatibility
        from queue import Queue
        from threading import Thread

        self.user_email = kwargs.get('user_email', None)
        test_function = kwargs.get('test_function', False)
        addm_items = kwargs.get('addm_items')
        test_item = kwargs.get('test_item')
        test_output_mode = kwargs.get('test_output_mode')

        isinstance(addm_items, QuerySet), "Addm items should be a QuerySet: %s" % type(addm_items)
        isinstance(test_item, TestCases), "Test item should be a TestCases: %s " % type(test_item)
        test_item = TestCasesSerializer(test_item).data

        thread_list = []
        test_outputs = []
        ts = time()
        test_q = Queue()
        for addm_item in addm_items:
            # Open SSH connection:
            ssh = ADDMOperations().ssh_c(addm_item=addm_item)
            # If opened connection is Up and alive:
            if ssh:
                args_d = dict(ssh=ssh, test_item=test_item, addm_item=addm_item, user_email=self.user_email,
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
        # Do not return much output, or celery and flower can cut it or fail.
        # return 'All tests took {}'.format(time() - ts)
        return 'All tests Took {} Out {}'.format(time() - ts, test_outputs)

    @exception
    def test_exec(self, **args_d):
        """
        This function execute tests for patterns.
        For test run - test list should be used, even with 1 element.

        Before run it will load tkn_main_bashrc/tkn_ship_bashrc to activate paths to python, tideway, core etc.

        """
        ts = time()
        ssh = args_d.get('ssh')
        user_email = args_d.get('user_email')
        test_item = args_d.get('test_item')
        addm_item = args_d.get('addm_item')
        test_output_mode = args_d.get('test_output_mode', False)
        test_function = args_d.get('test_function', '')
        test_q = args_d.get('test_q')

        test_py_t = test_item.get('test_py_path_template', False)
        test_time_weight = test_item.get('test_time_weight', 300)

        modern_addms = Options.objects.get(option_key__exact='modern_addm').option_value.replace(' ', '').split(',')

        test_info = f" {test_py_t} | '{addm_item['addm_name']}' v'{addm_item['addm_v_int']}' " \
                    f"{addm_item['addm_ip']} - {addm_item['addm_host']} {addm_item['addm_group']}"

        bin_python = '/usr/tideway/bin/python'
        if addm_item['addm_name'] in modern_addms:
            bin_python = '/usr/tideway/bin/python3'

        if test_py_t:
            log.debug(f"<=TEST=> START {test_info} t:{test_time_weight}")
            # Change local Octopus path to remote ADDM path:
            test_py_sync = test_py_t.format(self.addm_vm_test_workspace)
            test_wd_sync = test_item.get('test_dir_path_template').format(self.addm_vm_test_workspace)
            tkn_branch = test_item.get('tkn_branch')

            if test_function:
                cmd = f". ~/.{tkn_branch}_bashrc; cd {test_wd_sync}; {bin_python} -u {test_py_sync}" \
                      f" --verbose {test_function.replace('+', '.')}"
            else:
                cmd = f". ~/.{tkn_branch}_bashrc; cd {test_wd_sync}; {bin_python} -u {test_py_sync}" \
                      f" --verbose"

            log.debug(f"'{cmd}'")
            # Test execution:
            _, stdout, stderr = ssh.exec_command(cmd)
            std_out_err_d = self.std_read(out=stdout, err=stderr, mode=test_output_mode, mgs="<=TEST=>")

            time_spent_test = time() - ts
            log.debug(f"<=TEST=> FINISH {test_info} t:{time_spent_test}")
            update_save = self.parse_test_result(stderr_output=std_out_err_d['stderr_output'],
                                                 user_email=user_email,
                                                 test_item=test_item,
                                                 addm_item=addm_item,
                                                 # TODO: Fix to DurationField
                                                 time_spent_test=str(time_spent_test),
                                                 # time_spent_test=datetime.timedelta(seconds=time_spent_test),
                                                 )
            # TODO: Safe raw output here:
            # std_out_err_d
            # Close previously opened SSH:
            ssh.close()
            # Put test results into a thread queue output:
            test_q.put(update_save)
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

    @exception
    def parse_test_result(self, **test_out):
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
            :param test_out:
            :return:
        """
        debug = test_out.get('debug', False)
        parsed_debug = []
        user_email = test_out.get('user_email')

        last_save = dict(table="last", saved=False)
        hist_save = dict(table="history", saved=False)

        stderr_output = test_out.get('stderr_output', '').replace('\r', '')
        test_item = test_out.get('test_item', {})
        addm_item = test_out.get('addm_item', {})
        time_spent_test = test_out.get('time_spent_test', None)

        test_name_f_verb_re = re.compile(
            r'(?P<test_name>test(?:\S+|)_|\S+)\s'
            r'\((?P<module>\S+)\.(?P<class>\S+)\)'
            r'(?P<message>(?:(?:\n.*(?<!^)|\s)\.\.\.\s))'
            r'(?P<status>.+$)', re.MULTILINE)

        # Do not use tst_status to compose RE group to match the result, test_name.module.class is enough.
        re_draft_5 = r'[A-Z]+\:\s({0})\s\(({1})\.({2})\)\n\-+(?P<fail_message>(?:\n.*(?<!=|-))+)'
        re_draft_6 = r'[A-Z]+:\s({0})\s\(({1})\.({2})\)(?:(?:\n.+)+(?=-{3}).*)(?P<fail_message>(?:\n.*(?<![=\-]))+)'
        test_output = re.match(test_name_f_verb_re, stderr_output)
        if test_output:  # Search for all test declarations after run. In TOP if content.
            test_cases = re.finditer(test_name_f_verb_re, stderr_output)
            for item in test_cases:  # For each found test item do parse:
                test_res = dict(
                    tst_message=item.group('message'), tst_name=item.group('test_name'),
                    tst_module=item.group('module'), tst_class=item.group('class'),
                    tst_status=item.group('status').replace('\r', ''),
                    time_spent_test=time_spent_test
                )
                # Check the other part of content for fail|error details with composed regex:
                fail_details_srt = re_draft_6.format(item.group('test_name'), item.group('module'), item.group('class'), '{69}')
                # log.debug(f"fail_details_srt: {fail_details_srt}")
                test_fil_details = re.finditer(fail_details_srt, stderr_output)
                for detail in test_fil_details:
                    test_res.update(fail_message=detail.group('fail_message').replace("-" * 70, "").replace("=" * 70, ""))
                if not debug:
                    last_save.update(saved=self.model_save_insert(db=TestLast, res=test_res, test_item=test_item, addm_item=addm_item, user_email=user_email))
                    hist_save.update(saved=self.model_save_insert(db=TestHistory, res=test_res, test_item=test_item, addm_item=addm_item, user_email=user_email))
                else:
                    parsed_debug.append(test_res)
        else:
            test_res = dict(tst_status='ERROR', fail_message=stderr_output, time_spent_test=time_spent_test)
            log.error("<=PARSE_TEST_RESULT=> test_res %s", test_res)
            # Save test error if this error happened before actual test run:
            last_save.update(saved=self.model_save_insert(db=TestLast, res=test_res, test_item=test_item, addm_item=addm_item, user_email=user_email))
        if not debug:
            return {'last': last_save, 'history': hist_save}
        else:
            return parsed_debug

    @staticmethod
    @exception
    def model_save_insert(**kwargs):
        """
        Here compose dict of test results and addm+test item values to save them
            in database of latest tests and history.
        Warning: do not raise exceptions, this should run in Threads so it will wait an output.
            While raise can produce a deadlock for celery worker!

        :return:
        """

        db_model = kwargs.get('db', None)
        test_res = kwargs.get('res', None)
        test_item = kwargs.get('test_item', None)
        addm_item = kwargs.get('addm_item', None)

        test_data_res = dict(
            # Part from tku_patterns table
            tkn_branch=test_item.get('tkn_branch', None),
            pattern_library=test_item.get('pattern_library', None),
            pattern_folder_name=test_item.get('pattern_folder_name', None),
            test_case_dir=test_item.get('test_case_dir', None),
            test_py_path=test_item['test_py_path'],
            # Part from test parsed data
            tst_message=test_res.get('tst_message', ''),
            tst_name=test_res.get('tst_name', ''),
            tst_module=test_res.get('tst_module', ''),
            tst_class=test_res.get('tst_class', ''),
            tst_status=test_res.get('tst_status', ''),
            fail_message=test_res.get('fail_message', ''),
            # Part from addm_dev table
            addm_name=addm_item['addm_name'],
            addm_group=addm_item['addm_group'],
            addm_v_int=addm_item['addm_v_int'],
            addm_host=addm_item['addm_host'],
            addm_ip=addm_item['addm_ip'],
            time_spent_test=test_res.get('time_spent_test', ''),
        )
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
