from typing import List, Any, Dict

if __name__ == "__main__":
    import logging
    import django
    import copy
    import collections
    from operator import itemgetter

    django.setup()

    from run_core.addm_operations import ADDMOperations
    from octo_tku_patterns.table_oper import PatternsDjangoTableOper, PatternsDjangoTableOperDel
    from octo_tku_patterns.tasks import PatternTestExecCases
    from run_core.models import Options
    from run_core.models import AddmDev

    log = logging.getLogger("octo.octologger")
    log.info("\n\n\n\n\nRun dev_site/night_routine_select_and_balance_branches.py")

    class BalanceNightTests:

        @staticmethod
        def select_addm(addm_group):
            addm_set = AddmDev.objects.filter(
                addm_group__exact=addm_group,
                disables__isnull=True
            ).values(
                'addm_group',
                'addm_ip',
                'addm_host',
                'addm_name',
                'addm_v_int',
                'tideway_user',
                'tideway_pdw',
            )
            return addm_set

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
        def test_weight_balancer(addm_group, test_items):
            """
            Use list of available addms workers and list of tests sets to balance tests
            on all available addms by time weight

            :param addm_group:
            :param test_items:
            :return:
            """
            test_items_prepared = copy.deepcopy(test_items)
            test_items_prepared = sorted(test_items_prepared, key=itemgetter('test_time_weight'), reverse=True)
            test_items_prepared = collections.deque(test_items_prepared)

            addm_test_balanced = dict()     # It's better to have a dict like {'aplha': dict(tests)}
            # SUM all tests time
            all_tests_time = 0
            for test_item in test_items_prepared:
                all_tests_time += test_item['test_time_weight']                  # Count overall tests time weight

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

        @staticmethod
        def select_date_for_branch():
            """
            Select only workers are related to branch
            :type branch: str
            """
            tkn_main_date = Options.objects.get(option_key__exact='night_tests.tkn_main.date_from')
            tkn_ship_date = Options.objects.get(option_key__exact='night_tests.tkn_ship.date_from')

            dates: Dict[Any, List[str]] = dict(
                tkn_main = tkn_main_date.option_value,
                tkn_ship = tkn_ship_date.option_value)
            return dates

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

        def select_patterns_to_test(self, branch=None, excluded_seq=None):
            """ 1. Select tests for run. This should be made after previously run of p4 sync and parse"""

            branches_dates = self.select_date_for_branch()
            log.info("Default branches dates are: %s", branches_dates)
            sel_opts = dict(exclude=excluded_seq, branch=branch)
            if not branch:
                sel_opts.update(date_from=branches_dates.get('tkn_main'), branch='tkn_main')                            # 1.1 Select all for TKN_MAIN:
                tkn_main_tests = PatternsDjangoTableOper.sel_tests_dynamical(sel_opts=sel_opts)

                sel_opts.update(date_from=branches_dates.get('tkn_ship'), branch='tkn_ship')                            # 1.2 Select all for TKN_SHIP:
                tkn_ship_tests = PatternsDjangoTableOper.sel_tests_dynamical(sel_opts=sel_opts)

                sel_key_patt_tests = PatternsDjangoTableOper().sel_test_key()                                           # 1.3 Select key patterns tests:
                sum_tests = tkn_main_tests | tkn_ship_tests | sel_key_patt_tests                                        # 2. Summarize all tests and sort:
                sorted_tests_l = self.test_items_sorting(sum_tests, exclude=excluded_seq)
                # TestLast.objects.filter().delete()                                                                    # 3. DELETE previous
            else:
                sel_opts.update(date_from=branches_dates.get(branch), branch=branch)                                    # 1.2 Select all for TKN_SHIP:
                selected_tests = PatternsDjangoTableOper.sel_tests_dynamical(sel_opts=sel_opts)                         # 2. Summarize all tests and sort:

                sel_key_patt_tests = PatternsDjangoTableOper().sel_test_key(branch=branch)                              # 1.3 Select key patterns tests:
                sum_tests = selected_tests | sel_key_patt_tests                                                         # 2. Summarize all tests and sort:

                sorted_tests_l = self.test_items_sorting(sum_tests, exclude=excluded_seq)
                # TestLast.objects.filter(tkn_branch__exact=branch).delete()                                            # 3. DELETE previous

            return sorted_tests_l

        @staticmethod
        def workers_validate_and_occupy(addm_group_l, user_name):
            from octo_adm.tasks import ADDMCases
            addm_group_l = ADDMCases.addm_groups_validate(addm_group=addm_group_l, user_name=user_name)
            return addm_group_l

        @staticmethod
        def balance_tasks_on_workers(addm_group_l, sorted_tests_l):
            addm_tests_balanced = BalanceNightTests().test_weight_balancer(addm_group=addm_group_l, test_items=sorted_tests_l)
            return addm_tests_balanced

        @staticmethod
        def select_addm_set(addm_group_l):
            addm_set = ADDMOperations.select_addm_set(addm_group=addm_group_l)
            return addm_set

        @staticmethod
        def fill_workers_with_tasks(addm_set, addm_tests_balanced, user_name):
            for addm_item in addm_set:
                _addm_group = addm_item[0]['addm_group']
                addm_coll = addm_tests_balanced.get(_addm_group)
                addm_tests = addm_coll.get('tests', [])
                if addm_tests:
                    addm_tests_weight = addm_coll.get('all_tests_weight')
                    tent_avg = addm_coll.get('tent_avg')
                    log.debug("ADDM: %s tests: %s ~t: %s avg: %s", _addm_group, len(addm_tests), addm_tests_weight, tent_avg)
                    """ TEST EXECUTION: Init loop for test execution. Each test for each ADDM item. """
                    for test_item in addm_tests:
                        test_t_w = round(float(test_item['test_time_weight']))
                        tsk_msg = 'tag=night_routine;lock=True;type=routine {}/{}/{} t:{} on: "{}" by: {}'
                        r_key = '{}.TExecTest.nightly_routine_case.{}'.format(_addm_group, test_item['pattern_folder_name'])
                        t_tag = tsk_msg.format(test_item['tkn_branch'], test_item['pattern_library'],
                                               test_item['pattern_folder_name'], test_t_w, _addm_group, user_name)

                        # log.debug("Task execution here: %s %s", r_key, t_tag)
            else:
                log.debug("Finished tasks filling.")

        def get_available_addm_groups(self, branch):
            user_name = 'dev_script'
            addm_group_l = self.select_addm_list_for_branch(branch=branch)
            log.debug("Selected set of ADDMs addm_group_l: %s", addm_group_l)
            available_addm_w = self.workers_validate_and_occupy(addm_group_l=addm_group_l, user_name=user_name)
            return available_addm_w

        def load_tasks(self, user_name, branch, excluded_seq):
            sorted_tests_l = self.select_patterns_to_test(branch=branch, excluded_seq=excluded_seq)

            addm_group_l = self.select_addm_list_for_branch(branch=branch)
            log.debug("Selected set of ADDMs addm_group_l: %s", addm_group_l)

            available_addm_w = self.workers_validate_and_occupy(addm_group_l=addm_group_l, user_name=user_name)
            log.debug("Available set of ADDMs and occupied with wait task available_addm_w: %s", available_addm_w)

            addm_tests_balanced = self.balance_tasks_on_workers(addm_group_l=available_addm_w, sorted_tests_l=sorted_tests_l)
            log.debug("Set of tests balanced over each ADDM group len: %s", len(addm_tests_balanced))

            addm_set = self.select_addm_set(addm_group_l=available_addm_w)
            log.debug("Database query set of ADDMs by group - will be used to SSH: %s", addm_set)

            self.fill_workers_with_tasks(addm_set=addm_set, addm_tests_balanced=addm_tests_balanced, user_name=user_name)


    user_name = 'dev_script'
    excluded_seq = ["TKU-ProcessorInfo", "TKU-CDM-Mapping"]
    # BalanceNightTests().load_tasks(user_name, 'tkn_main', excluded_seq)
    # BalanceNightTests().load_tasks(user_name, 'tkn_ship', excluded_seq)

    # w_for_night_tkn_main = BalanceNightTests().get_available_addm_groups('tkn_main')
    # log.debug("w_for_night_tkn_main: %s", w_for_night_tkn_main)
    # w_for_night_tkn_ship = BalanceNightTests().get_available_addm_groups('tkn_ship')
    # log.debug("w_for_night_tkn_ship: %s", w_for_night_tkn_ship)

    addm_group = 'alpha'
    branch, pattern_library, pattern_folder, pattern_filename = ('tkn_main', 'CORE', '10genMongoDB', '10genMongoDB')

    addm_set = BalanceNightTests().select_addm(addm_group)
    log.debug("addm_set: %s", addm_set)
    pattern_item = BalanceNightTests().select_pattern_test(branch, pattern_library, pattern_folder, pattern_filename)
    log.debug("pattern_item: %s", pattern_item)
