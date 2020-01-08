"""
Example for octo test
"""
import unittest

try:
    from octotests import octo_tests
except ModuleNotFoundError:
    import octotests.octo_tests


class OctoTestCaseUpload(octo_tests.OctoTestCase):

    def setUp(self):
        octo_tests.OctoTestCase.setUp(self)
        # self.user_and_mail('Danylcha', "Dan@bmc.com")

    def test001_product_content_update_tkn_main(self):
        # self.fake_run_on(False)
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.data.update(
            debug=True,
            silent=True,
            fake_run=True,
            addm_group='golf',
            package_detail='TKU-Product-Content',
            package_types=[package_type]
        )
        self.run_case()

    def test002_product_content_update_tkn_ship(self):
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.data.update(
            debug=True,
            silent=True,
            fake_run=True,
            addm_group='golf',
            package_detail='TKU-Product-Content',
            package_types=[package_type])
        self.run_case()

    def test003_release_ga_upgrade(self):
        # Update mode will select packages for upgrade test by itself
        # previous = self.select_latest_released()
        # current_ga = self.select_latest_ga()
        self.data.update(
            debug=True,
            silent=True,
            fake_run=True,
            addm_group='golf',
            test_mode='update',
            # Update mode will select packages for upgrade test by itself
            # package_types=[previous, current_ga],
        )
        self.run_case()

    def test004_release_ga_fresh(self):
        package_type = self.select_latest_ga()
        self.debug = True
        self.silent = True
        self.fake_run = True
        self.addm_group = 'golf'
        self.test_mode = 'fresh'
        self.package_types = [package_type]
        self.run_case()

    # def test005_release_ga_fresh(self):
    #     package_type = self.select_latest_ga()
    #     self.request.update(addm_group='golf', test_mode='fresh', package_types=[package_type])
    #     self.run_case()


if __name__ == "__main__":
    unittest.main()
