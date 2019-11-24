"""
balance tasks between ADDM group pools for each separate branch
"""
from typing import List, Any, Dict
import logging

import copy
import collections
from operator import itemgetter

from run_core.models import Options
from octo_tku_patterns.models import TestLast
from octo_tku_patterns.table_oper import PatternsDjangoTableOper

log = logging.getLogger("octo.octologger")


class BalanceNightTests:

    @staticmethod
    def test_items_sorting(test_items, exclude=None):
        """
        Use selected items from django model query and sort out any duplicates for test.py path
            and create the list with all unique tests and only required fields.
            Exclude tests from queryset by pattern folder name if needed.
            Also set default test time weight up to 300 sec if None.

        :param test_items: queryset of all selected tests
        :param exclude: list of pattern folder names to exclude from set
        :return: list if dicts
        """
        log.info("<=test_items_sorting=> All amount of tests to sort: %s", len(test_items))
        if exclude:
            log.info("<=test_items_sorting=> Excluding: %s", exclude)
            test_items = test_items.exclude(pattern_folder_name__in=exclude)
            log.info("<=test_items_sorting=> All amount of tests after exclude: %s", len(test_items))
        # Primitive RawQuerySet to Dict conversion:
        test_items_list = []
        for test_item in test_items:
            try:
                if any(test_item.test_py_path in d for d in test_items_list):
                    # log.debug("This test is already in list: %s", test_item.test_py_path)
                    pass
                else:
                    if not test_item.test_time_weight:
                        test_time_weight = 300
                    else:
                        test_time_weight = round(float(test_item.test_time_weight))

                    test_item_d = {test_item.test_py_path: dict(
                        tkn_branch=test_item.tkn_branch,
                        pattern_library=test_item.pattern_library,
                        pattern_file_name=test_item.pattern_file_name,
                        pattern_folder_name=test_item.pattern_folder_name,
                        pattern_file_path=test_item.pattern_file_path,
                        test_py_path=test_item.test_py_path,
                        test_py_path_template=test_item.test_py_path_template,
                        test_folder_path_template=test_item.test_folder_path_template,
                        pattern_folder_path_depot=test_item.pattern_folder_path_depot,
                        pattern_file_path_depot=test_item.pattern_file_path_depot,
                        is_key_pattern=test_item.is_key_pattern,
                        test_time_weight=test_time_weight,
                    ), 'test_time_weight': test_time_weight}
                    test_items_list.append(test_item_d)
            except AttributeError as e:
                # Ignore items where attr is not set:
                log.error("<=test_items_sorting=> This test item has no attribute: %s", e)
        log.info("<=test_items_sorting=> All amount of tests after sort: %s", len(test_items_list))
        return test_items_list

    @staticmethod
    def select_date_for_branch():
        """
        Select only workers are related to branch
        """
        tkn_main_date = Options.objects.get(option_key__exact='night_tests.tkn_main.date_from')
        tkn_ship_date = Options.objects.get(option_key__exact='night_tests.tkn_ship.date_from')

        dates: Dict[Any, List[str]] = dict(
            tkn_main = tkn_main_date.option_value,
            tkn_ship = tkn_ship_date.option_value)
        return dates

    def select_patterns_to_test(self, branch=None, excluded_seq=None, fake_run=False):
        """ 1. Select tests for run. This should be made after previously run of p4 sync and parse"""

        branches_dates = self.select_date_for_branch()
        log.info("Default branches dates are: %s", branches_dates)
        sel_opts = dict(exclude=excluded_seq, branch=branch)
        if not branch:
            sel_opts.update(date_from=branches_dates.get('tkn_main'), branch='tkn_main')                 # 1.1 Select all for TKN_MAIN:
            tkn_main_tests = PatternsDjangoTableOper.sel_tests_dynamical(sel_opts=sel_opts)
            sel_opts.update(date_from=branches_dates.get('tkn_ship'), branch='tkn_ship')                 # 1.2 Select all for TKN_SHIP:
            tkn_ship_tests = PatternsDjangoTableOper.sel_tests_dynamical(sel_opts=sel_opts)
            # sel_key_patt_tests = PatternsDjangoTableOper()._sel_test_key()                                # 1.3 Select key patterns tests:
            # sum_tests = tkn_main_tests | tkn_ship_tests | sel_key_patt_tests                             # 2. Summarize all tests and sort:
            sum_tests = tkn_main_tests | tkn_ship_tests                             # 2. Summarize all tests and sort:
            sorted_tests_l = self.test_items_sorting(sum_tests, exclude=excluded_seq)
            if not fake_run:
                TestLast.objects.filter().delete()                                                       # 3. DELETE previous
            else:
                log.info("FAKE RUN: Would not delete last run patterns tests log.")
        else:
            sel_opts.update(date_from=branches_dates.get(branch), branch=branch)                         # 1.2 Select all for TKN_SHIP:
            selected_tests = PatternsDjangoTableOper.sel_tests_dynamical(sel_opts=sel_opts)              # 2. Summarize all tests and sort:
            # sel_key_patt_tests = PatternsDjangoTableOper()._sel_test_key(branch=branch)                   # 1.3 Select key patterns tests:
            # sum_tests = selected_tests | sel_key_patt_tests                                              # 2. Summarize all tests and sort:
            sum_tests = selected_tests                                              # 2. Summarize all tests and sort:
            sorted_tests_l = self.test_items_sorting(sum_tests, exclude=excluded_seq)
            if not fake_run:
                TestLast.objects.filter(tkn_branch__exact=branch).delete()                               # 3. DELETE previous
            else:
                log.info("FAKE RUN: Would not delete last run patterns tests log.")
        return sorted_tests_l

    @staticmethod
    def select_addm_list_for_branch(branch):
        """
        Select only workers are related to branch
        :type branch: str
        """
        tkn_main_w = Options.objects.get(option_key__exact='branch_workers.tkn_main')
        tkn_ship_w = Options.objects.get(option_key__exact='branch_workers.tkn_ship')

        tkn_main_w = tkn_main_w.option_value.replace(' ', '').split(',')
        tkn_ship_w = tkn_ship_w.option_value.replace(' ', '').split(',')

        workers: Dict[Any, List[str]] = dict(
            tkn_main = list(tkn_main_w),
            tkn_ship = list(tkn_ship_w))
        return workers.get(branch, [])

    @staticmethod
    def workers_validate_and_occupy(addm_group_l, user_name):
        from octo_adm.tasks import ADDMCases
        addm_group_l = ADDMCases.addm_groups_validate(addm_group=addm_group_l, user_name=user_name)
        return addm_group_l

    def get_available_addm_groups(self, branch, user_name):
        addm_group_l = self.select_addm_list_for_branch(branch=branch)
        available_addm_w = self.workers_validate_and_occupy(addm_group_l=addm_group_l, user_name=user_name)
        return available_addm_w

    @staticmethod
    def test_weight_balancer(addm_group, test_items):
        """
        Use list of available addms workers and list of tests sets to balance tests
        on all available addms by time weight

        :param addm_group:
        :param test_items:
        :return:
        """

        # TODO: ReUse this for queryset from TestCases, not the list of dicts like older version.

        # test_items_prepared = copy.deepcopy(test_items)
        # test_items_prepared = sorted(test_items_prepared, key=itemgetter('test_time_weight'), reverse=True)
        # test_items_prepared = collections.deque(test_items_prepared)
        # New for TestCases
        test_items_prepared = collections.deque(test_items)

        addm_test_balanced = dict()     # It's better to have a dict like {'aplha': dict(tests)}
        # SUM all tests time
        all_tests_time = 0
        for test_item in test_items_prepared:
            # TODO: Need to finish NEW test weight calculation first!
            log.info("Test item: %s", test_item.test_time_weight)
            all_tests_time += test_item.test_time_weight                  # Count overall tests time weight

        tent_avg = round(all_tests_time / len(addm_group) + 900)             # Use average time amount, add +900 sec to narrow float rounds
        log.debug("All tests len %s t:%s avg:%s", len(test_items_prepared), all_tests_time, tent_avg)
        for addm_tentacle in addm_group:                                     # Iter cycle over ADDMs in list
            tent_curr = 0                                                    # Set the counter for one ADDM
            tentacle_set = dict(tests=[], all_tests_weight='', tent_avg='')  # Empty case for tests per ADDM
            # log.debug("START FOR ADDM %s\n", addm_tentacle)
            # log.debug("Start ADDM sort: %s - %s avg: %s", addm_tentacle, tent_curr, tent_avg)
            while tent_avg > tent_curr:                                      # Loop till total added tests weight is lower then average
                try:
                    chosen_tst = test_items_prepared.popleft()
                    test_time_w = chosen_tst.pop('test_time_weight')    # Remove test item (not value) key of test weight
                    for test_v in chosen_tst.values():                  # Add test value cleaned from service keys
                        tentacle_set['tests'].append(test_v)            # Append current test case in list of ADDM
                    tent_curr += test_time_w                            # Increment added tests weight summary
                    # log.debug("In loop %s (agv:%s > %s:curr) + t:%s left: %s", addm_tentacle, tent_avg, tent_curr, test_time_w, len(test_items_prepared))
                except IndexError as e:                                 # This happens when there is no items left
                    log.info("All tests are sorted! %s", e)
                    break                                               # Exit from cycle for current ADDM iter item
            # Finishing tentacle:
            tentacle_set['tent_avg'] = tent_avg                         # Save average tentacle time weight
            tentacle_set['all_tests_weight'] = tent_curr                # Save actual tentacle time weight of tests
            log.debug("FINISH FOR ADDM %s avg:(%s < %s):current tests in: %s", addm_tentacle, tent_avg, tent_curr, len(tentacle_set['tests']))
            addm_test_balanced.update({addm_tentacle: tentacle_set})    # Append one filled ADDM group
        else:
            log.debug("Tests to sort left in addm loop: %s", len(test_items_prepared))

        return addm_test_balanced
