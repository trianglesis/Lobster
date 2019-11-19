"""
Example for octo test
"""
import unittest
import logging
try:
    from run_core import octo_tests
except ModuleNotFoundError:
    import octo_tests


log = logging.getLogger("octo.octologger")


class OctoTestCaseUpload(octo_tests.OctoTestCase):

    def setUp(self):
        octo_tests.OctoTestCase.setUp(self)
        self.fake_run_on(True)
        self.silent_on(True)
        self.wget_on(False)
        self.debug_on(True)
        self.user_and_mail('Danylcha', "Dan@bmc.com")

    @unittest.skip("Skip, but this should not be executed!")
    def test000_tku_upload_release(self):
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.request.update(addm_group='golf', package_detail='TKU-Product-Content', package_types=[package_type])
        self.run_case()

    def test001_product_content_update_tkn_main(self):
        # self.fake_run_on(False)
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.request.update(addm_group='golf', package_detail='TKU-Product-Content', package_types=[package_type])
        self.run_case()

    def test002_product_content_update_tkn_ship(self):
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.request.update(addm_group='charlie', package_detail='TKU-Product-Content', package_types=[package_type])
        self.run_case()

    def test003_release_ga_upgrade(self):
        # Update mode will select packages for upgrade test by itself
        # previous = self.select_latest_released()
        # current_ga = self.select_latest_ga()
        self.request.update(addm_group='golf', test_mode='update',
                            # Update mode will select packages for upgrade test by itself
                            # package_types=[previous, current_ga],
                            )
        self.run_case()

    def test004_release_ga_fresh(self):
        package_type = self.select_latest_ga()
        self.request.update(addm_group='golf', test_mode='fresh', package_types=[package_type])
        self.run_case()


# if __name__ == "__main__":
#     # Run tests
#     octo_tests.main(__name__)

if __name__ == "__main__":
    unittest.main()
