"""
Example for octo test
"""
import unittest
try:
    from octotests import octo_tests
except ModuleNotFoundError:
    import octotests.octo_tests


class NightTestCase(octo_tests.OctoPatternsTestCase):

    def setUp(self):
        octo_tests.PatternTestUtils.setUp(self)
        # self.fake_run_on(True)
        # self.silent_on(True)
        self.debug_on(True)
        # self.user_and_mail('Danylcha', "Dan@bmc.com")

    def test_001_night_routine_main(self):
        self.branch = 'tkn_main'
        self.select_test_cases(tkn_branch='tkn_main', last_days=60)
        self.excluded_group()
        self.queryset = self.queryset.exclude(change__in=[
                    '791013',
                    '784570',
                    '784672',
                    '784741',
                    '790845',
                    '716460',  # TKN SHIP STARTED HERE
                    '716461',
                    '790846',
                    '787058',
                    '787059'])
        self.wipe_logs_on(True)
        # print(self.addm_set)  # TODO: Way to exclude ADDM from actual addm set if needed
        self.run_case()

    def test_002_night_routine_ship(self):
        self.branch = 'tkn_ship'
        self.select_test_cases(tkn_branch='tkn_ship', last_days=60)
        self.queryset = self.queryset.exclude(change_time__range=['2019-11-25', '2019-11-27'])
        self.excluded_group()
        self.wipe_logs_on(True)
        self.run_case()

    def test003_between_dates_main(self):
        self.branch = 'tkn_main'
        self.select_test_cases(tkn_branch='tkn_main', date_from='2019-10-31', date_to='2019-11-20')
        self.excluded_group()
        # HERE: queryset will be set, so we can make django model manager exclude some?
        self.queryset = self.queryset.exclude(change_time__range=['2019-10-30', '2019-11-07'])
        self.queryset = self.queryset.exclude(change_time__range=['2019-11-25', '2019-11-27'])
        self.wipe_logs_on(True)
        self.run_case()


if __name__ == "__main__":
    unittest.main()
