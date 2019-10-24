if __name__ == "__main__":
    from time import time
    import pytz
    from datetime import datetime, timezone, timedelta

    import logging
    import django

    import os
    import re
    import copy
    import collections
    from operator import itemgetter

    # PPRINT
    import json
    from pprint import pformat

    django.setup()
    from django.db.models.query import QuerySet

    from run_core.models import Options
    from octo_tku_patterns.models import TestLast
    from octo_tku_patterns.models import TestCases
    from octo_tku_patterns.models import TkuPatterns

    from octo_tku_patterns.table_oper import PatternsDjangoTableOper

    log = logging.getLogger("octo.octologger")


    class SelectCasesForTests:

        @staticmethod
        def select_date_for_branch():
            tkn_main_date = Options.objects.get(option_key__exact='night_tests.tkn_main.date_from')
            tkn_ship_date = Options.objects.get(option_key__exact='night_tests.tkn_ship.date_from')
            dates = dict(
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
                tkn_main_tests = TableOperCases.sel_tests_dynamical(sel_opts=sel_opts)
                sel_opts.update(date_from=branches_dates.get('tkn_ship'), branch='tkn_ship')                 # 1.2 Select all for TKN_SHIP:
                tkn_ship_tests = TableOperCases.sel_tests_dynamical(sel_opts=sel_opts)
                sel_key_patt_tests = TableOperCases().sel_test_key()                                # 1.3 Select key patterns tests:
                sum_tests = tkn_main_tests | tkn_ship_tests | sel_key_patt_tests                             # 2. Summarize all tests and sort:
                sorted_tests_l = self.test_items_sorting(sum_tests, exclude=excluded_seq)
                if not fake_run:
                    TestLast.objects.filter().delete()                                                       # 3. DELETE previous
                else:
                    log.info("FAKE RUN: Would not delete last run patterns tests log.")
            else:
                sel_opts.update(date_from=branches_dates.get(branch), branch=branch)                         # 1.2 Select all for TKN_SHIP:
                selected_tests = TableOperCases.sel_tests_dynamical(sel_opts=sel_opts)              # 2. Summarize all tests and sort:
                sel_key_patt_tests = TableOperCases().sel_test_key(branch=branch)                   # 1.3 Select key patterns tests:
                sum_tests = selected_tests | sel_key_patt_tests                                              # 2. Summarize all tests and sort:
                sorted_tests_l = self.test_items_sorting(sum_tests, exclude=excluded_seq)
                if not fake_run:
                    TestLast.objects.filter(tkn_branch__exact=branch).delete()                               # 3. DELETE previous
                else:
                    log.info("FAKE RUN: Would not delete last run patterns tests log.")
            return sorted_tests_l

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

    class TableOperCases:

        @staticmethod
        def sel_tests_dynamical(**kwargs):
            """
            Based on options from kwargs - select patterns for test routine.
            Possible options:

            - include: list of pattern folder names should be selected anyway;
            - exclude: list of pattern folder names should NOT be selected anyway;
            - last_days: datetime window converted from int of last days changes to select patterns;
            - date_from: datetime str from what date to start;
                - date_to: if set - the latest date of changes, if not - use tomorrow date
            - branch: tkn_main or tkn_ship or both if none
            - user: user_adprod name - to choose only those patterns;
            - change: str - number of p4 change
            - library: CORE, CLOUD etc

            :param kwargs:
            :return:
            """
            from django.utils import timezone
            import datetime
            sel_opts = kwargs.get('sel_opts', {})

            now = datetime.datetime.now(tz=timezone.utc)
            tomorrow = now + datetime.timedelta(days=1)

            # switch-case:
            selectables = dict(
                # sel_k = sel_v
                # Experimental options:
                pattern_folder_name='pattern_folder_name__in',
                # Dynamical options:
                last_days='change_time__range',
                date_from='change_time__range',
                # Strict options:
                exclude='pattern_folder_name__in',
                branch='tkn_branch__exact',
                user='change_user__exact',
                change='change__exact',
                library='pattern_library__exact',
            )

            log.debug("<=Django Model intra_select=> Select sel_opts %s", sel_opts)

            # Select everything valid for test:
            all_patterns = TestCases.objects.filter(test_py_path__iendswith='test.py')

            def intra_select(queryset, option_key, option_value):
                sel_k = selectables.get(option_key)
                select_d = {sel_k: option_value}

                # # NOT Work fine, NOT excluding by pattern's folder
                if option_key == 'exclude':
                    # log.debug("<=Django Model intra_select=> Select exclude: %s", select_d)
                    intra_filtered = queryset.exclude(**select_d)

                # Select from last N-days, till today(tomorrow)
                elif option_key == 'last_days':
                    date_from = now - datetime.timedelta(days=int(option_value))
                    # log.debug("<=Django Model intra_select=> Select for the last %s days. %s %s", option_value, date_from, tomorrow)
                    select_d.update(change_time__range=[date_from, tomorrow])
                    # log.debug("<=Django Model intra_select=> Select last_days: %s", select_d)
                    intra_filtered = queryset.filter(**select_d)

                # Select from strict date till today(tomorrow)
                elif option_key == 'date_from':
                    date_from = datetime.datetime.strptime(option_value, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    # log.debug("<=Django Model intra_select=> Select date_from %s %s to %s", option_value, date_from, tomorrow)
                    select_d.update(change_time__range=[date_from, tomorrow])
                    # log.debug("<=Django Model intra_select=> Select date_from: %s", select_d)
                    intra_filtered = queryset.filter(**select_d)

                # All other strict options:
                else:
                    # log.debug("<=Django Model intra_select=> Select %s: %s", sel_k, select_d)
                    intra_filtered = queryset.filter(**select_d)

                return intra_filtered

            for opt_k, opt_v in sel_opts.items():
                # When key value is present and not None
                if opt_v:
                    # log.info("<=Django Model=> Using this option: %s value is %s", opt_k, opt_v)
                    all_patterns = intra_select(all_patterns, opt_k, opt_v)
                else:
                    # log.info("<=Django Model=> Skipping this option: %s value is %s", opt_k, opt_v)
                    pass

            log.debug("<=Django Model intra_select=> sel_tests_dynamical() "
                      "selected len: %s "
                      "history_recs.query: \n%s", len(all_patterns), all_patterns.query)

            return all_patterns

        @staticmethod
        def sel_test_key(exclude=None, branch=None):
            """
            Only select key patterns
            :return:
            """
            log.debug("<=Django Model key_select=> Selecting key patterns only. Branch: %s", branch)
            if branch:
                key_patterns = TkuPatterns.objects.filter(test_py_path__iendswith='test.py',
                                                          tkn_branch__exact=branch,
                                                          is_key_pattern__exact=True)
            else:
                key_patterns = TkuPatterns.objects.filter(test_py_path__iendswith='test.py',
                                                          is_key_pattern__exact=True)
            if exclude:
                key_patterns.exclude(pattern_folder_name__in=exclude)

            log.debug("<=Django Model key_select=> Selected key patterns len %s", len(key_patterns))
            return key_patterns

        """ Select case for user test """
        @staticmethod
        def select_case_user_test(branch, pattern_library, pattern_folder):
            test_item = TestCases.objects.filter(
                tkn_branch__exact=branch,
                pattern_library__exact=pattern_library,
                pattern_folder_name__exact=pattern_folder
            ).values()
            return test_item


    class OptionsAndExamples:

        @staticmethod
        def user_test_selector(branch, pattern_library, pattern_folder):
            user_test_selected_case = TableOperCases.select_case_user_test(branch, pattern_library, pattern_folder)
            print(user_test_selected_case)

        @staticmethod
        def night_routine_selector(branch, excluded_seq, fake_run=True):
            sorted_tests_l = SelectCasesForTests().select_patterns_to_test(branch, excluded_seq, fake_run)
            print(sorted_tests_l)

        @staticmethod
        def optional_tests_selector():
            pass

        @staticmethod
        def dev_select_tkn_main():
            # Should be less than TkuPatterns because there is no duplicates!
            sel_opts = dict(
                exclude=None,
                last_days=None,
                date_from='2017-09-25',
                branch='tkn_main',
                user=None,
                change=None,
                library=None)
            sel_routine_tests_main = TableOperCases().sel_tests_dynamical(sel_opts=sel_opts)
            return sel_routine_tests_main

        @staticmethod
        def dev_select_tkn_ship():
            # Should be less than TkuPatterns because there is no duplicates!
            sel_opts = dict(
                exclude=None,
                last_days=None,
                date_from='2017-10-12',
                branch='tkn_ship',
                user=None,
                change=None,
                library=None, )
            sel_routine_tests_ship = TableOperCases().sel_tests_dynamical(sel_opts=sel_opts)
            return sel_routine_tests_ship

        @staticmethod
        def dev_select_key():
            sel_key_patt_tests = TableOperCases().sel_test_key()
            return sel_key_patt_tests


    """
    Run:
    """
    cases_tkn_main = OptionsAndExamples.dev_select_tkn_main()
    print("cases_tkn_main: {} ALL: {}".format(len(cases_tkn_main), cases_tkn_main))
    cases_tkn_ship = OptionsAndExamples.dev_select_tkn_ship()
    print("cases_tkn_ship: {} ALL: {}".format(len(cases_tkn_ship), cases_tkn_ship))
    cases_key = OptionsAndExamples.dev_select_key()
    print("cases_key: {} ALL: {}".format(len(cases_key), cases_key))
