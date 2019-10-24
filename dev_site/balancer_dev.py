

if __name__ == "__main__":
    import datetime
    import logging
    import django
    import copy
    import collections
    from operator import itemgetter
    # PPRINT
    # import json
    # from pprint import pformat

    django.setup()

    # from run_core.local_operations import LocalPatternsParse, LocalDownloads
    # from run_core.test_executor import UploadTestExec
    # from octo_tku_patterns.models import TkuPatterns
    # from octo_tku_upload.models import TkuPackagesNew as TkuPackages

    from octo_tku_patterns.table_oper import PatternsDjangoModelRaw, PatternsDjangoTableOper
    from run_core.addm_operations import ADDMOperations
    # from octo_tku_patterns.tasks import PatternTestExecCases
    from octo_tku_patterns.night_test_balancer import BalanceNightTests

    log = logging.getLogger("octo.octologger")
    log.info("\n\n\n\n\nRun dev_site/run_local_functions.py")
    log.debug("BALANCER")
    log.debug("")
    log.debug("")

    """
    Night routine example like:
    """

    # Experimental some patterns only:
    # sel_opts = dict(
    #     exclude=None,
    #     last_days=None,
    #     date_from=None,
    #     branch='tkn_main',
    #     pattern_folder_name=['SterlingCommerceConnectDirect'],
    #     user=None,
    #     change=None,
    #     library=None)
    #
    # some_patterns = PatternsDjangoTableOper().sel_tests_dynamical(sel_opts=sel_opts)
    # log.debug("sel_routine_tests_main len %s", len(some_patterns))

    sel_opts = dict(
        exclude=None,
        last_days=None,
        date_from='2017-09-25',
        branch='tkn_main',
        user=None,
        change=None,
        library=None)

    sel_routine_tests_main = PatternsDjangoTableOper().sel_tests_dynamical(sel_opts=sel_opts)
    # log.debug("sel_routine_tests_main len %s", len(sel_routine_tests_main))

    sel_opts = dict(
        exclude=None,
        last_days=None,
        date_from='2017-10-12',
        branch='tkn_ship',
        user=None,
        change=None,
        library=None, )

    sel_routine_tests_ship = PatternsDjangoTableOper().sel_tests_dynamical(sel_opts=sel_opts)
    # log.debug("sel_routine_tests_ship len %s", len(sel_routine_tests_ship))

    sel_key_patt_tests = PatternsDjangoTableOper().sel_test_key()
    # log.debug("sel_key_patt_tests len %s", len(sel_key_patt_tests))
    selected_sum_query = sel_routine_tests_main | sel_routine_tests_ship | sel_key_patt_tests

    # selected_sum_query = some_patterns

    # log.debug("selected_sum_query len %s", len(selected_sum_query))

    # Sort
    # test_items_sorting
    sorted_items = BalanceNightTests.test_items_sorting(selected_sum_query,
                                                    exclude=["TKU-ProcessorInfo", "TKU-CDM-Mapping"])
    log.debug("sorted_items len %s", len(sorted_items))

    for test in sorted_items:
        for test_k, test_v in test.items():
            if test_k not in ['test_time_weight']:
                # log.debug("test_k %s | test_v %s", test_k, test_v)
                if test_v['pattern_folder_name'] in ["TKU-ProcessorInfo", "TKU-CDM-Mapping"]:
                    log.debug("This test should be excluded %s", test)

    # addm_test_pairs = TestPrepCases().case_select_sort_addm_test_items(addm_group=['alpha', 'beta', 'charlie', 'delta', 'echo', 'foxtrot'], test_items=sorted_items[:12])
    # log.debug("OLD addm_test_pairs %s", addm_test_pairs)

    # log.debug("sorted_item one %s", sorted_items[0])
    # log.debug('Test: %s', sel_routine_tests_ship[0])

    # slice_arg = False
    # excluded_seq = False
    # included_seq = False
    #
    # sorted_tests_l = DjangoModelRaw.patterns_for_test_both(
    #     slice_arg=slice_arg, excluded_seq=excluded_seq, included_seq=included_seq)
    # log.debug("Selected tests: %s", len(sorted_tests_l))

    """
    Balancer
    """

    addm_group = ['alpha', 'beta', 'charlie', 'delta', 'echo', 'foxtrot']
    # addm_group = ['foxtrot']

    # addm_set = ADDMOperations.select_addm_set(addm_group=addm_group)
    # TExecTest.t_addm_rsync_threads.apply_async(queue=_addm_group+'@tentacle.dq2', args=[mail_task_arg], kwargs=dict(addm_items=addm_set))

    # Splitting and chunk:
    test_items_prepared = copy.deepcopy(sorted_items)
    test_items_prepared = sorted(test_items_prepared, key=itemgetter('test_time_weight'), reverse=True)
    test_items_prepared = collections.deque(test_items_prepared)


    # item_sort = json.dumps(test_items_prepared, indent=2, ensure_ascii=False, default=pformat)
    # log.debug(item_sort)

    # noinspection PyPep8Naming
    @staticmethod
    def chunkIt(seq, num):
        avg = len(seq) / float(num)
        out = collections.deque()
        last = 0.0

        while last < len(seq):
            out.append(seq[int(last):int(last + avg)])
            # log.debug("<=TestPrepCases=> chunk - seq[%s:int(%s)]", int(last), int(last + avg))
            last += avg
        return out

    def case_select_sort_addm_test_items(self, addm_group, test_items):
        """
        Split test items to groups based on len of addm_group list:
        - https://confluence/display/~USER/Sorting+and+splitting+tests+over+ADDM+groups

        :type addm_group: list
        :type test_items: list
        :return:
        """
        addm_test_pairs = dict()

        addm_set = ADDMOperations.select_addm_set(addm_group=addm_group)
        log.debug("<=TestPrepCases> addm_set len: %s = %s", len(addm_set), addm_group)
        log.debug("<=TestPrepCases> test_items_prepared list len: %s", len(test_items))
        splitting = self.chunkIt(test_items, len(addm_set))
        for addm, test in zip(addm_set, splitting):
            addm_test_pairs.update({addm[0]['addm_group']: dict(test=test, addm=addm)})
            log.debug("<=TestPrepCases> ADDM - TEST pairs: %s %s", addm[0]['addm_group'], len(test))

        return addm_test_pairs

    # noinspection PyShadowingNames,PyShadowingNames,PyShadowingNames,PyShadowingNames,PyShadowingNames
    def balancer(addm_group, test_items_prepared):
        addm_test_balanced = dict()
        # SUM all tests time
        all_tests_time = 0
        for test_item in test_items_prepared:
            all_tests_time += test_item['test_time_weight']

        tent_avg = round(
            all_tests_time / len(addm_group) + 900)  # Use average time amount, add +900 sec to narrow float rounds
        log.debug("All tests len %s t:%s(%s) avg:%s(%s)", len(test_items_prepared),
                  all_tests_time, str(datetime.timedelta(seconds=all_tests_time)),
                  tent_avg, str(datetime.timedelta(seconds=tent_avg)))

        for addm_tentacle in addm_group:
            log.debug("START FOR ADDM %s\n", addm_tentacle)
            tent_curr = 0  # Set the counter for one ADDM
            tentacle_set = dict(tests=[], all_tests_weight='', tent_avg='')  # Empty case for tests per ADDM

            log.debug("Start ADDM sort: %s - %s(%s) avg: %s(%s)", addm_tentacle,
                      tent_curr, str(datetime.timedelta(seconds=tent_curr)),
                      tent_avg, str(datetime.timedelta(seconds=tent_avg)))
            """First approach: """
            # for test_case in test_items_prepared:                                           # Iterate over test cases:
            #     test_time_w = test_case.get('test_time_weight')
            #     log.debug("tent_curr %s (agv:%s > %s:curr) + t:%s left: %s", addm_tentacle, tent_avg, tent_curr, test_time_w, len(test_items_prepared))
            #     if tent_avg > tent_curr:                                         # Loop till total added tests weight is lower then average
            #         tentacle_set[addm_tentacle].append(test_items_prepared.popleft())                           # Append current test case in list of ADDM
            #         tentacle_set[addm_tentacle].append(test_case)                           # Append current test case in list of ADDM
            #         test_items_prepared.remove(test_case)                                   # Remove current test case from input list
            #
            #         # DEBUG:
            #         for tst_k, _ in test_case.items():                                     # Debug - show test.py path:
            #             if 'test.py' in tst_k:
            #                 log.debug("\t %s --> %s t:%s", addm_tentacle, tst_k, str(test_time_w))
            #
            #         log.debug("\tBefore sum tst time %s", tent_curr)
            #         tent_curr += test_time_w
            #         log.debug("\tAfter sum tst time %s", tent_curr)
            #     else:
            #         break
            # else:
            #     log.debug("Tests to sort left in test case: %s", len(test_items_prepared))
            """Second approach: """

            while tent_avg > tent_curr:  # Loop till total added tests weight is lower then average
                try:
                    chosen_tst = test_items_prepared.popleft()
                    test_time_w = chosen_tst.pop('test_time_weight')
                    for test_v in chosen_tst.values():
                        tentacle_set['tests'].append(test_v)  # Append current test case in list of ADDM

                    tent_curr += test_time_w
                    # log.debug("In loop %s (agv:%s > %s:curr) + t:%s left: %s", addm_tentacle, tent_avg, tent_curr, test_time_w, len(test_items_prepared))
                except IndexError as e:
                    log.info("All tests are sorted! %s", e)
                    break

            # Finishing tentacle:
            # Current and avg tests time
            tentacle_set['tent_avg'] = tent_avg
            tentacle_set['all_tests_weight'] = tent_curr

            # Append one filled ADDM
            log.debug("FINISH FOR ADDM %s avg:(%s < %s):(%s < %s)current tests in: %s\n", addm_tentacle,
                      tent_avg, tent_curr,
                      str(datetime.timedelta(seconds=tent_curr)), str(datetime.timedelta(seconds=tent_avg)),
                      len(tentacle_set['tests']))
            addm_test_balanced.update({addm_tentacle: tentacle_set})
        else:
            log.debug("Tests to sort left in addm loop: %s", len(test_items_prepared))

        return addm_test_balanced


    addm_tests_balanced = balancer(addm_group, test_items_prepared)
    if test_items_prepared:
        log.debug("This list now should be empty: %s", len(test_items_prepared))

    log.debug("This list now should be empty: %s -  %s", len(test_items_prepared), test_items_prepared)
    log.debug("addm_test_balanced len %s", len(addm_tests_balanced))
    # log.debug("addm_tests_balanced: %s", addm_tests_balanced)

    addm_set = ADDMOperations.select_addm_set(addm_group=addm_group)
    for addm_item in addm_set:
        addm_group = addm_item[0]['addm_group']
        addm_coll = addm_tests_balanced.get(addm_group)

        addm_tests = addm_coll.get('tests', [])
        if addm_tests:
            all_tests_weight = addm_coll.get('all_tests_weight')
            tent_avg = addm_coll.get('tent_avg')
            log.debug("ADDM: %s tests: %s ~t: %s Human(%s) avg: %s Human(%s)", addm_group, len(addm_tests),
                      all_tests_weight, str(datetime.timedelta(seconds=all_tests_weight)),
                      tent_avg, str(datetime.timedelta(seconds=tent_avg)))
            # log.debug("Tests for %s -> %s", addm_group, addm_tests)
            for test_item in addm_tests:
                if test_item['test_time_weight']:
                    test_t_w = test_item['test_time_weight']
                    log.info("Test to run %s", (test_item['tkn_branch'], test_item['pattern_library'],
                                                test_item['pattern_folder_name'],
                                                test_t_w, str(datetime.timedelta(seconds=test_t_w))))
                else:
                    log.error("Wrong test t: %s", test_item)
        else:
            log.info("ADDM %s has no tasks to run now.", addm_group)

    log.info("\n\n\n\nFinish dev_site/run_local_functions.py\n\n\n\n")
