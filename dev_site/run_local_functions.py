

if __name__ == "__main__":

    import logging
    import django
    import copy
    import collections
    from operator import itemgetter
    # PPRINT
    import json
    from pprint import pformat

    django.setup()

    # from run_core.local_operations import LocalPatternsParse, LocalDownloads
    # from run_core.test_executor import UploadTestExec
    from octo_tku_patterns.models import TkuPatterns
    # from octo_tku_upload.models import TkuPackagesNew as TkuPackages
    from octo_tku_patterns.table_oper import PatternsDjangoModelRaw, PatternsDjangoTableOper
    from octo_tku_patterns.night_test_balancer import BalanceNightTests

    from octo_tku_patterns.tasks import PatternTestExecCases
    from run_core.addm_operations import ADDMOperations

    log = logging.getLogger("octo.octologger")
    log.info("\n\n\n\n\nRun dev_site/run_local_functions.py")
    log.debug("")
    log.debug("")
    log.debug("")

    # Select ADDM
    # addm_group__in=['development']
    # addm_group__in=['alpha', 'beta', 'charlie', 'delta', 'echo', 'foxtrot']
    # addm_dev_group = AddmDev.objects.filter(disables__isnull=True,
    #                                         addm_group__in=['alpha', 'beta', 'charlie', 'delta', 'echo', 'foxtrot']
    #                                         ).order_by('addm_full_version').values('addm_v_int', 'addm_full_version')
    # addm_sort = []
    # for addm_item in addm_dev_group:
    #     if addm_item not in addm_sort:
    #         addm_sort.append(addm_item)
    # log.debug("addm_sort: %s", addm_sort)
        # log.debug("addm group %s dis: %s ver: %s", addm_item.addm_group, addm_item.disables, addm_item.addm_full_version)


    """
    Upload test examples:
    """
    # Exec as function:
    # parse_tku = LocalDownloads().only_parse_tku(path_key='tkn_main_continuous')
    # parse_tku = LocalDownloads().only_parse_tku()
    # log.debug("parse_tku %s", parse_tku)

    # View select TKU:
    # query_args = dict(tku_type='tkn_main_continuous')
    # query_args = dict(tku_type=False)
    # tku_packages, ga_candidate_max, released_tkn_max, tkn_main_continuous_max = PatternsDjangoTableOper().select_tku_packages(query_args)
    # log.debug(tku_packages)

    # wget_cmd_d = LocalDownloads().tku_wget_cmd_compose()
    # log.debug("wget_cmd_d: %s", wget_cmd_d)
    # for cmd_k, cmd_v in wget_cmd_d.items():
    #     log.debug("<=LocalDownloads=> cmd_item: %s %s", cmd_k, cmd_v.replace(';', ' '))


    #  Exec as task:
    # t_tag = 'dev_addm_custom_cmd|cmd_k={};addm_group={};user_name={user_name}'
    # parse_tku_task = TDev.dev_task_parse_local_tku.apply_async(args=[t_tag], kwargs=dict(a='b'))
    # log.debug("parse_tku_task %s", parse_tku_task)

    # addm_item = dict(addm_v_int='11.3')
    # #
    # ga_candidate_MAX_zips = DjangoTableOper.select_packages_narrow(
    #     addm_item, tku_type='ga_candidate', package_type=None).values()
    # RELEASED_PREV_CYCLE = DjangoTableOper.select_packages_narrow(
    #     addm_item, tku_type='released_tkn', package_type=None).values()
    #
    # SELECT_NOTHING = DjangoTableOper.select_packages_narrow(
    #     addm_item, tku_type=None, package_type=None).values()

    # addm_released_MAX_zips = DjangoTableOper.select_packages_narrow(
    #     addm_item, tku_type='addm_released', package_type=None)
    #
    # tkn_main_continuous_MAX_zips = DjangoTableOper.select_packages_narrow(
    #     addm_item, tku_type='tkn_main_continuous', package_type=None)
    #
    # TKN_RELEASE_2019_02_1_137 = DjangoTableOper.select_packages_narrow(
    #     addm_item, tku_type='ga_candidate', package_type='TKN_release_2019-02-1-137')
    #
    # ADDM_RELEASED_2016_03_2_000 = DjangoTableOper.select_packages_narrow(
    #     addm_item, tku_type=None, package_type='addm_released_2018-02-3-000')



    #
    # for item in addm_released_MAX_zips:
    #     log.info("addm_released_MAX_zips %s", item.get('package_type'))
    #
    # for item in tkn_main_continuous_MAX_zips:
    #     log.info("tkn_main_continuous_MAX_zips %s", item.get('package_type'))
    #
    # for item in TKN_RELEASE_2019_02_1_137:
    #     log.info("TKN_RELEASE_2019_02_1_137 %s", item.get('package_type'))
    #
    # for item in ADDM_RELEASED_2016_03_2_000:
    #     log.info("ADDM_RELEASED_2016_03_2_000 %s", item.get('package_type'))


    # for item in ga_candidate_MAX_zips:
    #     log.info("ga_candidate_MAX_zips (should be latest GA) get %s", item.get('package_type'))
    #     log.info("ga_candidate_MAX_zips (should be latest GA) [''] %s", item['package_type'])
    #
    # for item in SELECT_NOTHING:
    #     log.info("SELECT_NOTHING (should be latest GA) %s", item.get('package_type'))
    #
    # for item in RELEASED_PREV_CYCLE:
    #     log.info("RELEASED_PREV_CYCLE (to be upgraded from) %s", item.get('package_type'))
    #
    #
    # log.info("Compare 'package_type' of GA with RELEASED, if equal - select older 'package_type'")
    # max_ga = ga_candidate_MAX_zips[0].get('package_type')
    # max_released = RELEASED_PREV_CYCLE[0].get('package_type')
    # if max_ga == max_released:
    #     log.warning("max_ga == max_released, need to select previous RELEASED TKU! %s == %s", max_ga, max_released)
    #
    #     # TKN_release_2019-01-3-133
    #     RELEASED_PREV_LOWER = DjangoTableOper.select_packages_wide(addm_item, tku_type='released_tkn', package_type=max_released, step='lower')
    #     for item in RELEASED_PREV_LOWER:
    #         # TKN_release_2019-01-3-133
    #         log.info("RELEASED_PREV_CYCLE (to be upgraded from) %s", item.get('package_type'))
    #
    #
    # GREATER_PACK = DjangoTableOper.select_packages_wide(addm_item, tku_type='released_tkn', package_type='TKN_release_2019-01-3-133', step='greater')
    # for item in GREATER_PACK:
    #     log.info("GREATER_PACK (to be upgraded from) %s", item.get('package_type'))
    #
    #
    # # RUN UPLOAD TEST MANUALLY:
    # upload_test_kw = dict(
    #     # tku_type='ga_candidate',
    #     # tku_type='tkn_main_continuous',
    #     addm_group='foxtrot',
    #     user_email='',
    #     # mode='step',
    #     mode='update',
    # )
    # UploadTestExec().upload_run_threads(**upload_test_kw)


    # continuous_install = PatternsDjangoTableOper().select_tku_update_digest(mode_key='continuous_install')
    # for item in continuous_install:
    #     log.info(item)

    # tku_upload_logs = PatternsDjangoTableOper().select_upload_test_logs_new('double_decker', 'ga_candidate_install', 'TKN_release_2019-03-1-145', '2019-03-24_13-39')
    # for item in tku_upload_logs:
    #     log.info(item)
    #
    # options = dict(
    #     branch='tkn_main',
    #     pattern_library=False,
    #     is_key_pattern=False,
    #     date_from=False,
    #     date_to=False,
    #     select_release=True)
    #
    # selected_tku_tests = PatternsDjangoTableOper().select_tku_test_patterns(**options)
    #
    # log.debug("selected_tku_tests len %s", len(selected_tku_tests))
    # for item in selected_tku_tests:
    #     # log.debug(item)
    #     log.debug("Filtering: %s %s", item['pattern_folder_name'], item['test_py_path'])



    """
    User optional test run like:
    """

    # sel_opts = dict(
    #     exclude=None,
    #     last_days='35',
    #     date_from=None,
    #     branch='tkn_main',
    #     user='USER',
    #     change=None,
    #     library=None)
    #
    # user_selected = PatternsDjangoTableOper().sel_tests_dynamical(sel_opts=sel_opts)
    # log.debug("user_selected len %s", len(user_selected))
    #
    # sorted_items = PatternTestExecCases.test_items_sorting(user_selected)
    # log.debug("sorted_items len %s", len(sorted_items))
    #
    # for item in sorted_items:
    #     # for key in item.keys():
    #     #     log.debug("sorted_item one %s", key)
    #     for test_k, test_item in item.items():
    #         log.debug("test_k %s", test_k)
    #         log.debug("test_item %s", test_item)
    #
    # DjangoTableOperDel.delete_optional_test_logs(sorted_items)

    """
    Select and update test time weight
    """

    # Next dict of all patterns weight:
    # patterns_weight = dict()
    # # Select all patterns
    # patterns_selected = TkuPatterns.objects.all()[:10]
    # log.debug("patterns_selected len %s", len(patterns_selected))
    #
    # # Now select history tests for this pattern for the last n days:
    # for pattern_item in patterns_selected:
    #     test_query_args = dict(
    #         last_days=7,
    #         test_py_path=pattern_item.test_py_path)
    #     tests_for_pattern = DjangoModelRaw().sel_history_by_latest(query_args=test_query_args)
    #
    #     # Make dict with test.py path as key and sum of test time / days(selected items)
    #     # If nothing was selected - update pattern row with default value of 10 min or do nothing if value is already exists
    #     if tests_for_pattern:
    #         # This should be only one pattern result:
    #         log.debug("Found tests len %s", len(tests_for_pattern))
    #
    #         time_sum = 0
    #         for test_res in tests_for_pattern:
    #             # log.debug("test_res %s", (test_res.id, test_res.time_spent_test, test_res.test_py_path, test_res.test_date_time))
    #             time_sum = time_sum + float(test_res.time_spent_test)
    #         # log.debug("time_sum %s", time_sum)
    #         # log.debug("average %s", (time_sum / len(tests_for_pattern)))
    #         weight = {tests_for_pattern[0].test_py_path: dict(day_rec=len(tests_for_pattern), time_sum=time_sum, average=time_sum / len(tests_for_pattern))}
    #         patterns_weight.update(weight)
    #         # log.debug("weight: %s", weight)
    #     else:
    #         log.debug("This pattern test not run for last days: %s", pattern_item.test_py_path)
    #         log.debug("Assign DEFAULT weight near 10 min")
    #         weight = {pattern_item.test_py_path: dict(average=600)}
    #         patterns_weight.update(weight)


    """
    SECOND APPROACH:
    Select ALL from history and then update patterns
    """

    patterns_weight = dict()

    test_query_args = dict(last_days=30)
    all_history_weight = PatternsDjangoModelRaw().sel_history_by_latest_all(query_args=test_query_args)

    # Make dict with test.py path as key and sum of test time / days(selected items)
    # If nothing was selected - update pattern row with default value of 10 min or do nothing if value is already exists
    log.debug("Found tests len %s", len(all_history_weight))
    if all_history_weight:
        # This should be only one pattern result:
        count = 0
        for test_res in all_history_weight:

            # log.debug("Test result %s", test_res)
            # log.debug("test_res %s", (test_res.id, test_res.time_spent_test, test_res.test_py_path, test_res.test_date_time))

            # If current test.py IS already in the list of dicts -> update days count, time and time sum abd average:
            if any(test_res.test_py_path in d for d in patterns_weight):
                already_have = patterns_weight[test_res.test_py_path]

                already_have['day_rec'] = already_have['day_rec'] + 1
                already_have['time_sum'] = already_have['time_sum'] + float(test_res.time_spent_test)
                already_have['average'] = already_have['time_sum'] / already_have['day_rec']

            # If current test.py IS NOT in the list of dicts -> only add values
            else:
                weight = {test_res.test_py_path: dict(day_rec=1, time_sum=float(test_res.time_spent_test), average=float(test_res.time_spent_test))}
                patterns_weight.update(weight)
    else:
        log.debug("There are no hist records for selected: %s", test_query_args)

    log.debug("patterns_weight: %s", patterns_weight)

    # go throught dict and update patterns:
    for patt_k, patt_v in patterns_weight.items():
        # 1. Select all patterns with according test.py path:
        patterns_sel = TkuPatterns.objects.filter(
            test_py_path__exact=patt_k,
        )
        # 1. Iter over each found pattern item with corresponding test.py
        if patterns_sel:
            for pattern in patterns_sel:
                pattern.test_time_weight = patt_v['average']
                pattern.save()


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
        library=None,)

    sel_routine_tests_ship = PatternsDjangoTableOper().sel_tests_dynamical(sel_opts=sel_opts)
    # log.debug("sel_routine_tests_ship len %s", len(sel_routine_tests_ship))

    sel_key_patt_tests = PatternsDjangoTableOper().sel_test_key()
    # log.debug("sel_key_patt_tests len %s", len(sel_key_patt_tests))
    selected_sum_query = sel_routine_tests_main | sel_routine_tests_ship | sel_key_patt_tests

    # selected_sum_query = some_patterns

    # log.debug("selected_sum_query len %s", len(selected_sum_query))

    # Sort
    #test_items_sorting
    sorted_items = BalanceNightTests.test_items_sorting(selected_sum_query, exclude=["TKU-ProcessorInfo", "TKU-CDM-Mapping"])
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

    # addm_group = ['alpha', 'beta', 'charlie', 'delta', 'echo', 'foxtrot']
    addm_group = ['foxtrot']

    # addm_set = ADDMOperations.select_addm_set(addm_group=addm_group)
    # TExecTest.t_addm_rsync_threads.apply_async(queue=_addm_group+'@tentacle.dq2', args=[mail_task_arg], kwargs=dict(addm_items=addm_set))


    # Splitting and chunk:
    test_items_prepared = copy.deepcopy(sorted_items)
    test_items_prepared = sorted(test_items_prepared, key=itemgetter('test_time_weight'), reverse=True)
    test_items_prepared = collections.deque(test_items_prepared)

    # item_sort = json.dumps(test_items_prepared, indent=2, ensure_ascii=False, default=pformat)
    # log.debug(item_sort)

    # noinspection PyShadowingNames,PyShadowingNames,PyShadowingNames,PyShadowingNames,PyShadowingNames
    def balancer(addm_group, test_items_prepared):

        # addm_test_balanced = []
        addm_test_balanced = dict()
        # SUM all tests time
        all_tests_time = 0
        for test_item in test_items_prepared:
            all_tests_time += test_item['test_time_weight']

        tent_avg = round(all_tests_time / len(addm_group) + 900)                        # Use average time amount, add +900 sec to narrow float rounds
        log.debug("All tests len %s t:%s avg:%s", len(test_items_prepared), all_tests_time, tent_avg)

        for addm_tentacle in addm_group:
            log.debug("START FOR ADDM %s\n", addm_tentacle)
            tent_curr = 0                                                               # Set the counter for one ADDM
            tentacle_set = dict(tests=[], all_tests_weight='', tent_avg='')  # Empty case for tests per ADDM

            log.debug("Start ADDM sort: %s - %s avg: %s", addm_tentacle, tent_curr, tent_avg)
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
                        tentacle_set['tests'].append(test_v)            # Append current test case in list of ADDM

                    tent_curr += test_time_w
                    log.debug("In loop %s (agv:%s > %s:curr) + t:%s left: %s", addm_tentacle, tent_avg, tent_curr, test_time_w, len(test_items_prepared))
                except IndexError as e:
                    log.info("All tests are sorted! %s", e)
                    break

            # Finishing tentacle:
            # Current and avg tests time
            tentacle_set['tent_avg'] = tent_avg
            tentacle_set['all_tests_weight'] = tent_curr

            # Append one filled ADDM
            log.debug("FINISH FOR ADDM %s avg:(%s < %s):current tests in: %s\n", addm_tentacle, tent_avg, tent_curr, len(tentacle_set['tests']))
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
            log.debug("ADDM: %s tests: %s ~t: %s avg: %s", addm_group, len(addm_tests), all_tests_weight, tent_avg)
            # log.debug("Tests for %s -> %s", addm_group, addm_tests)
            for test_item in addm_tests:
                if test_item['test_time_weight']:
                    test_t_w = round(float(test_item['test_time_weight']))
                    # log.info("Test to run %s", (test_item['tkn_branch'], test_item['pattern_library'], test_item['pattern_folder_name'], test_t_w))
                else:
                    log.error("Wrong test t: %s", test_item)
        else:
            log.info("ADDM %s has no tasks to run now.", addm_group)

    log.info("\n\n\n\nFinish dev_site/run_local_functions.py\n\n\n\n")
