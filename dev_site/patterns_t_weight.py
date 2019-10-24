

if __name__ == "__main__":

    import time
    import datetime
    import logging
    import django
    import copy
    import collections
    from operator import itemgetter
    # PPRINT
    import json
    from pprint import pformat


    django.setup()

    from octo_tku_patterns.models import TkuPatterns
    from run_core.local_operations import LocalDB



    log = logging.getLogger("octo.octologger")
    log.info("\n\n\n\n\nRun dev_site/run_local_functions.py")
    log.debug("Patterns time weight dev")
    log.debug("")
    log.debug("")

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
    #
    # patterns_weight = collections.OrderedDict()
    # test_query_args = dict(last_days=30)
    # all_history_weight = DjangoModelRaw().sel_history_by_latest_all(query_args=test_query_args)
    #
    # # Make dict with test.py path as key and sum of test time / days(selected items)
    # # If nothing was selected - update pattern row with default value of 10 min or do nothing if value is already exists
    # log.debug("Found tests len %s", len(all_history_weight))
    # if all_history_weight:
    #     # This should be only one pattern result:
    #     count = 0
    #     for test_res in all_history_weight:
    #
    #         # log.debug("Test result %s", test_res)
    #         # log.debug("test_res %s", (test_res.id, test_res.time_spent_test, test_res.test_py_path, test_res.test_date_time))
    #
    #         # If current test.py IS already in the list of dicts -> update days count, time and time sum abd average:
    #         if any(test_res.test_py_path in d for d in patterns_weight):
    #             already_have = patterns_weight[test_res.test_py_path]
    #
    #             already_have['day_rec'] = already_have['day_rec'] + 1
    #             already_have['time_sum'] = already_have['time_sum'] + round(float(test_res.time_spent_test))
    #             already_have['average'] = round(already_have['time_sum'] / already_have['day_rec'])
    #
    #         # If current test.py IS NOT in the list of dicts -> only add values
    #         else:
    #             weight = {test_res.test_py_path: dict(day_rec=1, time_sum=round(float(test_res.time_spent_test)), average=round(float(test_res.time_spent_test)))}
    #             patterns_weight.update(weight)
    # else:
    #     log.debug("There are no hist records for selected: %s", test_query_args)
    #
    # log.info("Grouped and sum of tests: %s", len(patterns_weight.items()))
    # # patterns_weight_prepared = sorted(patterns_weight, key=itemgetter('day_rec'), reverse=True)
    # # patterns_weight_prepared = collections.OrderedDict(patterns_weight)
    # # patterns_weight_prepared = collections.OrderedDict(sorted(patterns_weight.items(), key=lambda t: t[0]))
    # item_sort = json.dumps(patterns_weight, indent=2, ensure_ascii=False, default=pformat)
    # log.debug(item_sort)
    #
    # all_tests_time = 0
    # for k, v in patterns_weight.items():
    #     all_tests_time += v['average']
    # log.info("All patterns with %s sum all t: %s human: %s", len(patterns_weight.items()), all_tests_time, str(datetime.timedelta(seconds=all_tests_time)))


    # go throught dict and update patterns:
    # for patt_k, patt_v in patterns_weight.items():
    #     # 1. Select all patterns with according test.py path:
    #     patterns_sel = TkuPatterns.objects.filter(
    #         test_py_path__exact=patt_k,
    #     )
    #     # 1. Iter over each found pattern item with corresponding test.py
    #     if patterns_sel:
    #         for pattern in patterns_sel:
    #             pattern.test_time_weight = patt_v['average']
    #             pattern.save()


    """
    As in live:
    """

    # Select and group history records:
    # patterns_weight = LocalDB.history_weight(last_days=30)
    # Insert sorted in TKU Patterns table:
    # LocalDB.insert_patt_weight(patterns_weight)
