from __future__ import absolute_import, unicode_literals
from typing import List, Any, Dict

import logging
from run_core.models import Options
from octo.helpers.tasks_mail_send import Mails
from octo.helpers.tasks_oper import TasksOperations, WorkerOperations
from octo.config_cred import mails

from octo_tku_patterns.table_oper import PatternsDjangoTableOper
from octo_tku_patterns.models import TestCases, TestLast


log = logging.getLogger("octo.octologger")


class WorkerGetAvailable:

    @staticmethod
    def branched_w(branch):
        """
        Select only workers are related to branch
        :type branch: str
        """

        tkn_main_w = Options.objects.get(option_key__exact='branch_workers.tkn_main')
        tkn_ship_w = Options.objects.get(option_key__exact='branch_workers.tkn_ship')

        tkn_main_w = tkn_main_w.option_value.replace(' ', '').split(',')
        tkn_ship_w = tkn_ship_w.option_value.replace(' ', '').split(',')

        workers: Dict[Any, List[str]] = dict(
            tkn_main=list(tkn_main_w),
            tkn_ship=list(tkn_ship_w))
        return workers.get(branch, [])

    @staticmethod
    def excluded_w():
        """
        Select from octopus Options table the list of workers exluded from user test execution.
        :return:
        """
        excluded_option = Options.objects.get(option_key__exact='workers_excluded_list')
        return excluded_option.option_value.replace(' ', '').split(',')

    @staticmethod
    def actualize_w(branch_w, excluded_w):
        """
        Sort out excluded workers from the list of available workers.
        - Add @tentacle to worker name for celery operations. Will replace later.
        :type excluded_w: list
        :type branch_w: list
        """
        actualized_w: List[str] = []
        for w in branch_w:
            if w not in excluded_w:
                actualized_w.append('{}@tentacle'.format(w))
        return actualized_w

    @staticmethod
    def ping_actual_w(actual_w):
        """
        Ping only included workers, append only worker which responds.
        :type actual_w: list
        """
        w_down = []
        running_w: List[str] = []
        worker_up = WorkerOperations().worker_ping_alt(worker_list=actual_w)
        for w_key, w_val in worker_up.items():
            if 'pong' in w_val:
                running_w.append(w_key)
            else:
                w_down.append("<=WorkerGetAvailable=> Worker is down {}:{}".format(w_key, w_val))

        if w_down:
            log.error("<=WorkerGetAvailable=> Some workers may be down: %s - sending email!", w_down)
            subject = 'Currently some workers are DOWN!'
            body = '''Found some workers are DOWN while run User test pre-checks. List: {}'''.format(w_down)
            admin = mails['admin']
            Mails.short(subject=subject, body=body, send_to=[admin])

        return running_w

    @staticmethod
    def inspect_w(running_w):
        """
        Get workers tasks: running and reserved.
        :type running_w: List[str]
        """
        inspected = TasksOperations().check_active_reserved_short(workers_list=running_w, tasks_body=True)
        return inspected

    @staticmethod
    def not_locked_w(inspected):
        """
        Exclude workers where task has a lock key in name or args.
        :type inspected: list
        """
        # excl = 'lock=True'
        included_list: List[Dict] = []
        for worker in inspected:
            if worker not in included_list:
                included_list.append(worker)
            # for w_key, w_val in worker.items():
                # # Do not care about lock no more - add task to min worker
                # all_tasks = w_val.get('all_tasks')
                # if any(excl in d.get('args') for d in all_tasks) or any(excl in d.get('name') for d in all_tasks):
                #     log.debug("<=WorkerGetAvailable=> Exclude worker due task lock: %s", w_key)
                #     break
                # else:
        return included_list

    @staticmethod
    def min_w(not_busy_w):
        """
        Get worker with minimal count of active/reserved tasks.
        - Replacing @tentacle from worker name to get addm_group name.
        :type not_busy_w: list
        """
        w_dict: Dict[str, int] = dict()
        for worker in not_busy_w:
            for w_key, w_val in worker.items():
                w_dict.update({w_key: w_val.get('all_tasks_len')})
        log.debug("<=WorkerGetAvailable=> All available workers: %s", w_dict)
        worker_min = min(w_dict, key=w_dict.get)
        if '@tentacle' in worker_min:
            worker_min = worker_min.replace('@tentacle', '')
        return worker_min

    def user_test_available_w(self, branch, user_mail):
        log.info("<=WorkerGetAvailable=> Getting available worker to run test for branch %s", branch)

        branch_w = self.branched_w(branch)
        log.debug("<=WorkerGetAvailable=> Branch w: %s = %s", branch, branch_w)

        excluded_w = self.excluded_w()
        log.debug("<=WorkerGetAvailable=> Workers excluded: %s", excluded_w)

        actual_w = self.actualize_w(branch_w, excluded_w)
        if actual_w:
            log.debug("<=WorkerGetAvailable=> Actualized w: %s", actual_w)
            # TODO: Add here all_queues_len = RabbitCheck().queue_count_list(queues_list)
            running_w = self.ping_actual_w(actual_w)

            if running_w:
                log.debug("<=WorkerGetAvailable=> : Running w: %s", running_w)

                inspected_w = self.inspect_w(running_w)
                # Do not show debug - it will output all reserved tasks!!!
                # log.debug("<=WorkerGetAvailable=> Inspected w: %s", inspected_w)

                not_locked_w = self.not_locked_w(inspected_w)
                # Do not show debug - it will output all reserved tasks!!!
                # log.debug("<=WorkerGetAvailable=> Not locked w: %s", not_locked_w)

                min_w = self.min_w(not_locked_w)
                log.debug("<=WorkerGetAvailable=> Min w: %s", min_w)
                log.info("<=WorkerGetAvailable=> Worker has been selected for run test on branch %s - w: %s", branch,
                         min_w)
                return min_w
            else:
                log.warning("<=WorkerGetAvailable=> There is no running workers, may be DOWN!")
                log.warning("<=WorkerGetAvailable=> Cannot run task, STOP NOW!")
                subject = 'Cannot get worker to run your test, workers may be down.'
                body = '''Arguments: \n branch = {} \n branch_w = {} \n excluded_w = {} \n actual_w = {} \n running_w = {}
                '''.format(branch, branch_w, excluded_w, actual_w, running_w)
                Mails.short(subject=subject, body=body, send_to=[user_mail])
                return []
        else:
            log.warning("<=WorkerGetAvailable=> There is no available workers! All excluded.")
            log.warning("<=WorkerGetAvailable=> Cannot run task, STOP NOW!")
            subject = 'Cannot get worker to run your test, workers may be busy.'
            body = '''Arguments: \n branch = {} \n branch_w = {} \n excluded_w = {} \n actual_w = {}
            '''.format(branch, branch_w, excluded_w, actual_w)
            Mails.short(subject=subject, body=body, send_to=[user_mail])
            return []


class OptionalTestsSelect:

    @staticmethod
    def test_items_sorting(test_items, exclude=None):
        from octo_tku_patterns.night_test_balancer import BalanceNightTests
        test_items_list = BalanceNightTests().test_items_sorting(test_items, exclude)
        return test_items_list

    @staticmethod
    def optional_patterns_select(**kwargs):
        """

        :return:
        """

        sel_opts = dict(
            exclude=kwargs.get('exclude', None),
            last_days=kwargs.get('last_days', '1'),
            date_from=kwargs.get('date_from', None),
            branch=kwargs.get('branch', None),
            user=kwargs.get('user', None),
            change=kwargs.get('change', None),
            library=kwargs.get('library', None),
        )

        selected = PatternsDjangoTableOper().sel_tests_dynamical(sel_opts=sel_opts)
        log.debug("selected len %s", len(selected))

        return selected

    def select_by_patterns(self, pattern_dir_list: list):

        # Experimental some patterns only:
        sel_opts = dict(
            exclude=None,
            last_days=None,
            date_from=None,
            branch='tkn_main',
            pattern_folder_name=pattern_dir_list,
            user=None,
            change=None,
            library=None)

        some_patterns = self.optional_patterns_select(sel_opts=sel_opts)
        log.debug("sel_routine_tests_main len %s", len(some_patterns))

    @staticmethod
    def select_patterns_failed_tests(branch, addm_name):

        raw_sql = """SELECT octo_test_last.id,
                            octo_test_last.tkn_branch,
                            octo_test_last.pattern_library,
                            octo_test_last.pattern_file_name,
                            octo_test_last.pattern_folder_name,
                            octo_test_last.pattern_file_path,
                            octo_test_last.test_py_path
                        FROM octopus_dev_copy.octo_test_last
                        WHERE octo_test_last.tst_status REGEXP '^(FAIL|fail|unexpected|failure|ERROR)'
                        AND octo_test_last.tkn_branch = '{0}'
                        AND octo_test_last.addm_name = '{1}'
                        GROUP BY octo_test_last.test_py_path
                        ;""".format(branch, addm_name)

        failed_patterns_q = TestLast.objects.raw(raw_sql)
        return failed_patterns_q

    @staticmethod
    def list_test_py(patterns_q):
        test_py_list = []
        for failed_item in patterns_q:
            if failed_item.test_py_path not in test_py_list:
                test_py_list.append(failed_item.test_py_path)
        return test_py_list

    @staticmethod
    def select_patterns_by_testpy(test_py_list):
        patterns_tests = TestCases.objects.filter(
            test_py_path__in=test_py_list).distinct()
        return patterns_tests

    def select_latest_failed_sort(self, branch, addm_name, wipe=False, info=False):
        """
            Select only failed/error tests from last tests table.
            Sort by tkn_branch and addm_name, no need to rerun for all possible addm, branches at once.

            failed_patterns - use only to show pattern p4 data

        """
        failed_patterns = self.select_patterns_failed_tests(branch, addm_name)

        test_py_l = self.list_test_py(patterns_q=failed_patterns)
        log.debug("<=OptionalTestsSelect=> All failed items: %s", len(test_py_l))

        patterns_to_test = self.select_patterns_by_testpy(test_py_list=test_py_l)
        log.debug("<=OptionalTestsSelect=> Selected tests items: %s", len(patterns_to_test))

        show_patterns_list = []
        for item in patterns_to_test:
            if item.pattern_folder_name not in show_patterns_list:
                show_patterns_list.append(item.pattern_folder_name)

        all_tests_w = 0
        for item in patterns_to_test:
            if item.test_time_weight:
                all_tests_w += int(item.test_time_weight)
            else:
                all_tests_w += 300

        sorted_tests_l = self.test_items_sorting(patterns_to_test)
        log.debug("<=OptionalTestsSelect=> patterns_to_test items: %s", len(patterns_to_test))
        log.debug("<=OptionalTestsSelect=> sorted_tests_l items: %s", len(sorted_tests_l))

        if info:
            return sorted_tests_l, show_patterns_list, failed_patterns, patterns_to_test, all_tests_w
        else:
            if wipe:
                log.debug("<=OptionalTestsSelect=> Wiping last records for patterns: %s", show_patterns_list)
                self.wipe_last_selected_logs(branch, addm_name, show_patterns_list)
            return sorted_tests_l, show_patterns_list

    @staticmethod
    def wipe_last_selected_logs(branch, addm_name, selected_l):
        TestLast.objects.filter(
            tkn_branch__exact=branch,
            addm_name__exact=addm_name,
            pattern_folder_name__in=selected_l
        ).delete()
