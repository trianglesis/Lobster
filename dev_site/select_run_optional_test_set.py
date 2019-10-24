if __name__ == "__main__":

    import logging
    import django

    django.setup()

    from octo_tku_patterns.table_oper import PatternsDjangoTableOper
    from octo_tku_patterns.models import TkuPatterns, TestLast
    from octo_tku_patterns.night_test_balancer import BalanceNightTests

    log = logging.getLogger("octo.octologger")
    log.info("\n\n\n\n\nRun dev_site/run_local_functions.py")
    log.debug("")

    """
    User optional test run like:
    """

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
            patterns_tests = TkuPatterns.objects.filter(
                test_py_path__in=test_py_list)
            return patterns_tests

        def select_latest_failed_sort(self, branch, addm_name):
            failed_patterns = self.select_patterns_failed_tests(branch, addm_name)

            test_py_l = self.list_test_py(patterns_q=failed_patterns)
            log.debug("<=OptionalTestsSelect=> All failed items: %s", len(test_py_l))

            patterns_to_test = self.select_patterns_by_testpy(test_py_list=test_py_l)
            log.debug("<=OptionalTestsSelect=> Selected tests items: %s", len(patterns_to_test))
            show_patterns_list = []
            for item in patterns_to_test:
                if item.pattern_folder_name not in show_patterns_list:
                    show_patterns_list.append(item.pattern_folder_name)

            sorted_tests_l = self.test_items_sorting(patterns_to_test)
            log.debug("<=OptionalTestsSelect=> Sorted tests items: %s", len(patterns_to_test))
            return sorted_tests_l, show_patterns_list


    branch = 'tkn_main'
    addm_name = 'double_decker'

    test_items_l, show_patterns_list = OptionalTestsSelect().select_latest_failed_sort(branch=branch, addm_name=addm_name)

    log.debug("show_patterns_list: %s", show_patterns_list)

    # Unpack - show:
    for test_composed in test_items_l:
        test_composed.pop('test_time_weight')
        # log.debug("test_item: %s", test_composed)
        for test_item in test_composed.values():
            # log.debug("test_item: %s", test_item)
            pattern_dir = test_item.get('pattern_folder_name')
            test_py_t = test_item.get('test_py_path_template', False)
            test_time_weight = test_item.get('test_time_weight', '')
            log.debug("pattern_dir, test_py_t, test_time_weight: %s ", (pattern_dir, test_py_t, test_time_weight))
















