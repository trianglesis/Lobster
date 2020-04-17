"""
Example for octo test
"""
import unittest
import datetime
import pytz

try:
    from octotests import octo_tests
    import octo.config_cred as conf_cred
    from octo import settings
    from run_core.models import Options
except ModuleNotFoundError:
    import octotests.octo_tests

now = datetime.datetime.now(tz=pytz.utc)
tomorrow = now + datetime.timedelta(days=1)


class NightTestCase(octo_tests.OctoPatternsTestCase):

    def setUp(self):
        octo_tests.PatternTestUtils.setUp(self)
        self.debug_on(True)
        # self.fake_run_on(True)
        # self.silent_on(True)
        # self.user_and_mail('Danylcha', "Dan@bmc.com")
        self.exclude_changes = [
            '791013',
            '784570',
            '784672',
            '784741',
            '790845',
            '716460',  # TKN SHIP STARTED HERE
            '716461',
            '790846',
            '787058',
            '787059',
        ]
        # Wide set:
        # self.tkn_main_addm_group_l = ['beta', 'charlie', 'delta', 'hotel', 'india', 'juliett']
        # self.tkn_ship_addm_group_l = ['echo', 'foxtrot', 'golf', 'kilo']
        # Short set:
        self.tkn_main_addm_group_l = ['beta', 'charlie', 'delta']
        self.tkn_ship_addm_group_l = ['echo', 'foxtrot', 'golf']

    def test_001_night_routine_main(self):
        """
        Simple select for cases with change date for last 3 years, for selected branch, excluding mass-changes.
        :return:
        """
        self.branch = 'tkn_main'
        date_from = now - datetime.timedelta(days=int(730))
        self.queryset = self.queryset.filter(change_time__range=[date_from, tomorrow])
        self.excluded_group()
        self.queryset = self.queryset.exclude(change__in=self.exclude_changes)  # Always last!
        self.addm_group_l = self.tkn_main_addm_group_l
        self.wipe_logs_on(True)
        self.run_case()

    def test_002_night_routine_ship(self):
        """
        Simple select for cases with change date for last 3 years, for selected branch, excluding mass-changes.
        :return:
        """
        self.branch = 'tkn_ship'
        date_from = now - datetime.timedelta(days=int(730))
        self.queryset = self.queryset.filter(change_time__range=[date_from, tomorrow])
        self.excluded_group()
        self.queryset = self.queryset.exclude(change__in=self.exclude_changes)  # Always last!
        self.addm_group_l = self.tkn_ship_addm_group_l
        self.wipe_logs_on(True)
        self.run_case()

    def test_003_night_routine_main(self):
        """
        Run only latest 2 month for TKN_MAIN on single group
        :return:
        """
        self.branch = 'tkn_main'
        date_from = now - datetime.timedelta(days=int(60))
        self.queryset = self.queryset.filter(change_time__range=[date_from, tomorrow])
        self.excluded_group()
        self.queryset = self.queryset.exclude(change__in=self.exclude_changes)  # Always last!
        self.wipe_logs_on(True)
        self.addm_group_l = ['hotel']
        self.run_case()

    def test_004_night_routine_wide_tkn_main(self):
        """
        Run during the working week (Mon, Tue, Wed, Thu), each evening at about 17:30 UK time.
        Select all for the last 2 years, excluding mass depot changes, add key patterns,
            exclude using cases group "excluded" and sort the only tkn_ship.
        Use only locked ADDMs for the current branch!
        :return:
        """
        self.branch = 'tkn_main'
        date_from = now - datetime.timedelta(days=int(730))
        self.queryset = self.queryset.filter(change_time__range=[date_from, tomorrow])  # 1
        self.key_group()                                                                # 2
        self.queryset = self.queryset.filter(tkn_branch__exact=self.branch)             # 3
        self.excluded_group()                                                           # 4
        self.queryset = self.queryset.exclude(change__in=self.exclude_changes)          # 5
        self.addm_group_l = self.tkn_main_addm_group_l
        self.wipe_logs_on(True)
        self.run_case()

    def test_005_night_routine_wide_tkn_ship(self):
        """
        Run during the working week (Mon, Tue, Wed, Thu), each evening at about 17:30 UK time.
        Select all for the last 2 years, excluding mass depot changes, add key patterns,
            exclude using cases group "excluded" and sort the only tkn_ship.
        Use only locked ADDMs for the current branch!
        :return:
        """
        self.branch = 'tkn_ship'
        date_from = now - datetime.timedelta(days=int(730))
        self.queryset = self.queryset.filter(change_time__range=[date_from, tomorrow])  # 1
        self.key_group()                                                                # 2
        self.queryset = self.queryset.filter(tkn_branch__exact=self.branch)             # 3
        self.excluded_group()                                                           # 4
        self.queryset = self.queryset.exclude(change__in=self.exclude_changes)          # 5
        self.addm_group_l = self.tkn_ship_addm_group_l
        self.wipe_logs_on(True)
        self.run_case()

    def test009_between_dates_main(self):
        """For dev: choose any cases where change date is in the between of dates provided."""
        self.branch = 'tkn_main'
        self.select_test_cases(tkn_branch='tkn_main', date_from='2019-10-31', date_to='2019-11-20')
        self.excluded_group()
        # HERE: queryset will be set, so we can make django model manager exclude some?
        self.queryset = self.queryset.exclude(change_time__range=['2019-10-30', '2019-11-07'])
        self.queryset = self.queryset.exclude(change_time__range=['2019-11-25', '2019-11-27'])
        self.wipe_logs_on(True)
        self.run_case()

    def test_010_night_routine_all_tkn_main_weekend(self):
        """
        Run the whole repository tests for the selected branch. Execute this only on weekends or from Friday.
        :return:
        """
        self.branch = 'tkn_main'
        self.excluded_group()
        self.queryset = self.queryset.filter(tkn_branch__exact=self.branch)
        self.addm_group_l = Options.objects.get(option_key__exact='branch_workers.tkn_main').option_value.replace(' ', '').split(',')
        self.wipe_logs_on(True)
        self.run_case()

    def test_011_night_routine_all_tkn_ship_weekend(self):
        """
        Run the whole repository tests for the selected branch. Execute this only on weekends or from Friday.
        :return:
        """
        self.branch = 'tkn_ship'
        self.excluded_group()
        self.queryset = self.queryset.filter(tkn_branch__exact=self.branch)
        self.addm_group_l = Options.objects.get(option_key__exact='branch_workers.tkn_ship').option_value.replace(' ', '').split(',')
        self.wipe_logs_on(True)
        self.run_case()

    def test_012_night_routine_wide_tkn_main_beta(self):
        """
        Run during the working week (Mon, Tue, Wed, Thu), each evening at about 17:30 UK time.
        Select all for the last 2 years, excluding mass depot changes, add key patterns,
            exclude using cases group "excluded" and sort the only tkn_ship.
        Use only locked ADDMs for the current branch!
        :return:
        """
        self.branch = 'tkn_main'
        date_from = now - datetime.timedelta(days=int(730))
        self.queryset = self.queryset.filter(change_time__range=[date_from, tomorrow])  # 1
        self.key_group()                                                                # 2
        self.queryset = self.queryset.filter(tkn_branch__exact=self.branch)             # 3
        self.excluded_group()                                                           # 4
        self.queryset = self.queryset.exclude(change__in=self.exclude_changes)          # 5
        self.addm_group_l = ['beta']
        self.wipe_logs_on(True)
        self.run_case()

    def test_013_night_routine_wide_tkn_ship_echo(self):
        """
        Run during the working week (Mon, Tue, Wed, Thu), each evening at about 17:30 UK time.
        Select all for the last 2 years, excluding mass depot changes, add key patterns,
            exclude using cases group "excluded" and sort the only tkn_ship.
        Use only locked ADDMs for the current branch!
        :return:
        """
        self.branch = 'tkn_ship'
        date_from = now - datetime.timedelta(days=int(730))
        self.queryset = self.queryset.filter(change_time__range=[date_from, tomorrow])  # 1
        self.key_group()                                                                # 2
        self.queryset = self.queryset.filter(tkn_branch__exact=self.branch)             # 3
        self.excluded_group()                                                           # 4
        self.queryset = self.queryset.exclude(change__in=self.exclude_changes)          # 5
        self.addm_group_l = ['echo']
        self.wipe_logs_on(True)
        self.run_case()

    def test_014_night_routine_main_options_addm(self):
        """
        Run during the working week (Mon, Tue, Wed, Thu), each evening at about 17:30 UK time.
        Select all for the last 2 years, excluding mass depot changes, add key patterns,
            exclude using cases group "excluded" and sort the only tkn_ship.
        Use only locked ADDMs for the current branch!
        :return:
        """
        self.addm_group_l = Options.objects.get(option_key__exact='branch_workers.tkn_main').option_value.replace(' ', '').split(',')
        self.branch = 'tkn_main'
        date_from = now - datetime.timedelta(days=int(730))
        self.queryset = self.queryset.filter(change_time__range=[date_from, tomorrow])  # 1
        self.key_group()                                                                # 2
        self.queryset = self.queryset.filter(tkn_branch__exact=self.branch)             # 3
        self.excluded_group()                                                           # 4
        self.queryset = self.queryset.exclude(change__in=self.exclude_changes)          # 5
        self.wipe_logs_on(True)
        self.run_case()

    def test_015_night_routine_ship_options_addm(self):
        """
        Run during the working week (Mon, Tue, Wed, Thu), each evening at about 17:30 UK time.
        Select all for the last 2 years, excluding mass depot changes, add key patterns,
            exclude using cases group "excluded" and sort the only tkn_ship.
        Use only locked ADDMs for the current branch!
        :return:
        """
        self.addm_group_l = Options.objects.get(option_key__exact='branch_workers.tkn_ship').option_value.replace(' ', '').split(',')
        self.branch = 'tkn_ship'
        date_from = now - datetime.timedelta(days=int(730))
        self.queryset = self.queryset.filter(change_time__range=[date_from, tomorrow])  # 1
        self.key_group()                                                                # 2
        self.queryset = self.queryset.filter(tkn_branch__exact=self.branch)             # 3
        self.excluded_group()                                                           # 4
        self.queryset = self.queryset.exclude(change__in=self.exclude_changes)          # 5
        self.wipe_logs_on(True)
        self.run_case()

    def test_016_execute_failed_main(self):
        # self.silent_on(True)
        self.branch = 'tkn_main'
        # Select failed log entries
        test_py_list = self.select_latest_failed()
        print(f"Sorted list of tests: {len(test_py_list)} - {test_py_list}")
        # Select actual test cases from failed log details
        cases_q = self.select_failed_cases(test_py_list)
        print(f"Selected cases for rerun: {cases_q.count()}")
        # For each of selected assign worker and add test task:
        for test_item in cases_q:
            self.select_addm_group()
            if self.addm_set:
                # Sync test data to ADDM
                self.sync_test_data_addm_set(addm_item=self.addm_set)
                # Now wipe old results
                print(f"Wipe last logs for {test_item['test_py_path']}")
                self.wipe_case_logs(test_item['test_py_path'])
                # Put each case on selected group
                self.put_test_cases_short([test_item])

    def test_017_execute_failed_ship(self):
        # self.silent_on(True)
        self.branch = 'tkn_ship'
        # Select failed log entries
        test_py_list = self.select_latest_failed()
        print(f"Sorted list of tests: {len(test_py_list)} - {test_py_list}")
        # Select actual test cases from failed log details
        cases_q = self.select_failed_cases(test_py_list)
        print(f"Selected cases for rerun: {cases_q.count()}")
        # For each of selected assign worker and add test task:
        for test_item in cases_q:
            self.select_addm_group()
            if self.addm_set:
                # Sync test data to ADDM
                self.sync_test_data_addm_set(addm_item=self.addm_set)
                # Now wipe old results
                print(f"Wipe last logs for {test_item['test_py_path']}")
                self.wipe_case_logs(test_item['test_py_path'])
                # Put each case on selected group
                self.put_test_cases_short([test_item])

    def test_999_local_debug(self):
        date_from = now - datetime.timedelta(days=int(730))
        self.silent_on(True)
        self.fake_run_on(True)
        # self.wipe_logs_on(False)
        self.branch = 'tkn_main'
        # self.queryset = self.queryset.filter(test_py_path__exact='/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/CORE/MicroStrategy/tests/test.py')
        self.queryset = self.queryset.filter(change_time__range=[date_from, tomorrow])  # 1
        self.key_group()                                                                # 2
        self.queryset = self.queryset.filter(tkn_branch__exact=self.branch)             # 3
        self.excluded_group()                                                           # 4
        self.queryset = self.queryset.exclude(change__in=self.exclude_changes)          # 5

        print(self.queryset.count())
        print(self.queryset.explain())
        print(self.queryset.query)
        self.addm_group_l = ['alpha']
        # OR:
        # self.addm_set = self.addm_set.filter(
        #     addm_group__in=['alpha'],
        #     addm_name__in=['custard_cream', 'double_decker'],  # Skip FF till tpl 12
        #     disables__isnull=True).values().order_by('addm_group')
        self.run_case()

        if conf_cred.DEV_HOST not in settings.CURR_HOSTNAME:
            print("PROD MACHINE")
        else:
            print(f"DEV MACHINE {conf_cred.DEV_HOST} curr host {settings.CURR_HOSTNAME}")


if __name__ == "__main__":
    unittest.main()
