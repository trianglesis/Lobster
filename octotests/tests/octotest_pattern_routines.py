"""
Example for octo test
"""
import unittest
try:
    from octotests import octo_tests
except ModuleNotFoundError:
    import octotests.octo_tests

# from octo_tku_patterns.tasks import TaskPrepare

# class OctoTestCase(TaskPrepare):
#
#     def __init__(self, obj):
#         obj.silent = True
#         obj.fake_run = True
#         obj.exclude = True
#         obj.request = dict()
#         self.pattern_folder_names()
#         super().__init__(obj)
#
#     def pattern_folder_names(self):
#         self.request.update(
#             refresh=True,
#             # silent=True,
#             fake_run=True,
#             exclude=True,
#             user_name='octotests',
#             user_email='octotests',
#             selector=dict(
#                 cases_ids='1,2',
#             ),
#             # selector=dict(
#             #     tkn_branch='tkn_main',
#             #     pattern_library='CORE',
#             #     pattern_folder_names=[
#             #         '10genMongoDB',
#             #         'BlazegraphDatabase',
#             #         'BMCBladelogicServerAutomationSuite',
#             #         'BMCMiddlewareMngmntPerformanceAvailability',
#             #         'EmbarcaderoDSAuditor',
#             #     ],
#             # ),
#         )
#
#     def run(self):
#         self.run_tku_patterns()


class NightTestCase(octo_tests.OctoPatternsTestCase):

    def setUp(self) -> None:
        octo_tests.PatternTestUtils.setUp(self)
        self.fake_run_on(True)
        self.silent_on(True)
        self.debug_on(True)
        self.wipe_logs(False)
        self.user_and_mail('Danylcha', "Dan@bmc.com")

    def test_001_night_routine_main(self):
        self.branch = 'tkn_main'
        self.select_test_cases(tkn_branch='tkn_main', days=730)
        self.excluded_group()
        self.run_case()

    def test_002_night_routine_ship(self):
        self.branch = 'tkn_ship'
        self.select_test_cases(tkn_branch='tkn_ship', days=730)
        self.excluded_group()
        self.run_case()

    def test003_between_dates_main(self):
        self.branch = 'tkn_main'
        self.select_test_cases(tkn_branch='tkn_main', date_from='2019-10-31', date_to='2019-11-20')
        self.excluded_group()
        self.run_case()


# if __name__ == "__main__":
#     import django
#     django.setup()
#     OctoTestCase(TaskPrepare).run()

if __name__ == "__main__":
    unittest.main()
