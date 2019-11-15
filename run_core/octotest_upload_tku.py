"""
Example for octo test
"""
import unittest
from run_core import octo_test_cases


class OctoTestCase(octo_test_cases.OctoTestCase):

    def setUp(self):
        octo_test_cases.OctoTestCase.setUp(self)
        # self.fake_run_on(True)
        self.silent_on(True)
        self.wget_on(False)

    def test000_tku_upload_release(self):
        self.debug_on(True)
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.request.update(addm_group='golf', package_detail='TKU-Product-Content', package_types=[package_type])
        self.run_case()

    def test001_product_content_update_tkn_main(self):
        self.fake_run_on(False)
        # self.user_and_mail('Danylcha', "Dan@bmc.com")
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
        self.request.update(addm_group='golf', test_mode='fresh', package_types=[self.select_latest_ga])


if __name__ == "__main__":
    # Run tests
    octo_test_cases.main(__name__)
