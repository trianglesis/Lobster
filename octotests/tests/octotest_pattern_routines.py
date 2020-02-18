"""
Example for octo test
"""
import unittest
import datetime
import pytz
try:
    from octotests import octo_tests
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
        self.tkn_main_changes_exclude = ['791013', '784570', '784672', '784741', '790845']
        self.tkn_ship_changes_exclude = ['716460', '716461', '790846', '787058', '787059']

    def test_001_night_routine_main(self):
        """
        Simple select for cases with change date for last 3 years, for selected branch, excluding mass-changes.
        :return:
        """
        self.branch = 'tkn_main'
        date_from = now - datetime.timedelta(days=int(730))
        self.queryset = self.queryset.filter(change_time__range=[date_from, tomorrow])
        self.queryset = self.queryset.exclude(change__in=self.tkn_main_changes_exclude)
        self.excluded_group()
        self.addm_group_l = ['beta', 'charlie', 'delta', 'hotel', 'india', 'juliett']
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
        self.queryset = self.queryset.exclude(change__in=self.tkn_ship_changes_exclude)
        self.queryset = self.queryset.exclude(change__in=[
                    '716460',  # TKN SHIP STARTED HERE
                    '716461',
                    '790846',
                    '787058',
                    '787059',
                    '716460',  # TKN SHIP STARTED HERE
                    '716461',
                    '790846',
                    '787058',
                    '787059',
        ])
        self.excluded_group()
        self.addm_group_l = ['echo', 'foxtrot', 'golf', 'kilo']
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
        self.queryset = self.queryset.exclude(change__in=self.tkn_main_changes_exclude)
        self.excluded_group()
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
        self.queryset = self.queryset.filter(change_time__range=[date_from, tomorrow])
        self.queryset = self.queryset.exclude(change__in=self.tkn_main_changes_exclude)
        self.key_group()
        self.excluded_group()
        self.queryset = self.queryset.filter(tkn_branch__exact='tkn_main')
        self.addm_group_l = ['beta', 'charlie', 'delta', 'hotel', 'india', 'juliett']
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
        self.queryset = self.queryset.filter(change_time__range=[date_from, tomorrow])
        self.queryset = self.queryset.exclude(change__in=self.tkn_ship_changes_exclude)
        self.key_group()
        self.excluded_group()
        self.queryset = self.queryset.filter(tkn_branch__exact='tkn_ship')
        self.addm_group_l = ['echo', 'foxtrot', 'golf', 'kilo']
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
        self.queryset = self.queryset.filter(tkn_branch__exact='tkn_main')
        self.addm_group_l = ['beta', 'charlie', 'delta', 'hotel', 'india', 'juliett']
        self.wipe_logs_on(True)
        self.run_case()

    def test_011_night_routine_all_tkn_ship_weekend(self):
        """
        Run the whole repository tests for the selected branch. Execute this only on weekends or from Friday.
        :return:
        """
        self.branch = 'tkn_ship'
        self.excluded_group()
        self.queryset = self.queryset.filter(tkn_branch__exact='tkn_ship')
        self.addm_group_l = ['echo', 'foxtrot', 'golf', 'kilo']
        self.wipe_logs_on(True)
        self.run_case()

    def test_999_local_debug(self):
        date_from = now - datetime.timedelta(days=int(730))
        self.silent_on(True)
        self.fake_run_on(True)
        # self.wipe_logs_on(False)
        self.branch = 'tkn_main'
        self.queryset = self.queryset.filter(change_time__range=[date_from, tomorrow])
        # self.excluded_group()
        # self.queryset = self.queryset.exclude(change__in=[
        #             '791013',
        #             '784570',
        #             '784672',
        #             '784741',
        #             '790845',
        # ])
        # self.queryset = self.queryset.filter(test_py_path__exact='/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/CORE/MicroStrategy/tests/test.py')
        # self.addm_group_l = ['alpha', 'beta', 'echo']
        self.queryset = self.queryset.exclude(change__in=[
                    '716460',  # TKN SHIP STARTED HERE
                    '716461',
                    '790846',
                    '787058',
                    '787059',
                    '716460',  # TKN SHIP STARTED HERE
                    '716461',
                    '790846',
                    '787058',
                    '787059',
        ])
        self.key_group()
        self.excluded_group()
        self.queryset = self.queryset.filter(tkn_branch__exact='tkn_main')
        print(self.queryset.count())
        print(self.queryset.explain())
        print(self.queryset.query)
        self.addm_group_l = ['golf']
        # OR:
        self.addm_set = self.addm_set.filter(
            addm_group__in=['golf'],
            addm_name__in=['custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()


if __name__ == "__main__":
    unittest.main()
