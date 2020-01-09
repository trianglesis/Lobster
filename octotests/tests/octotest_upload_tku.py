"""
Example for octo test
"""
import unittest
from itertools import groupby
from operator import itemgetter

try:
    from octotests import octo_tests
except ModuleNotFoundError:
    import octotests.octo_tests


class OctoTestCaseUpload(octo_tests.OctoTestCase):

    def setUp(self):
        octo_tests.OctoTestCase.setUp(self)
        # self.user_and_mail('Danylcha', "Dan@bmc.com")

    def test001_product_content_update_tkn_main(self):
        self.debug = True
        self.silent = True
        self.tku_wget = True
        self.fake_run = True
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_detail = 'TKU-Product-Content'
        self.package_types = [package_type]
        # self.addm_group = 'golf'
        self.addm_set = self.addm_set.filter(
            addm_group__in=['alpha', 'golf'],
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()

    def test002_product_content_update_tkn_ship(self):
        self.debug = True
        self.silent = True
        self.tku_wget = False
        self.fake_run = True
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.package_detail = 'TKU-Product-Content'
        self.package_types = [package_type]
        self.addm_group = 'golf'
        self.run_case()

    def test003_release_ga_upgrade(self):
        self.debug = True
        self.silent = True
        self.tku_wget = False
        self.fake_run = True
        self.test_mode = 'update'
        # Update mode will select packages for upgrade test by itself
        # previous = self.select_latest_released()
        # current_ga = self.select_latest_ga()
        # Update mode will select packages for upgrade test by itself
        # package_types=[previous, current_ga],
        self.addm_group = 'golf'
        self.run_case()

    def test004_release_ga_fresh(self):
        package_type = self.select_latest_ga()
        self.debug = True
        self.silent = True
        self.tku_wget = False
        self.fake_run = True
        self.test_mode = 'fresh'
        # self.addm_group = 'golf'
        # self.addm_set = self.addm_set.filter(addm_group__exact='golf', disables__isnull=True).values().order_by('addm_group')
        self.addm_set = self.addm_set.filter(
            addm_group__in=['alpha', 'golf'],
            disables__isnull=True).values().order_by('addm_group')
        self.package_types = [package_type]
        self.run_case()

    # def test005_release_ga_fresh(self):
    #     package_type = self.select_latest_ga()
    #     self.request.update(addm_group='golf', test_mode='fresh', package_types=[package_type])
    #     self.run_case()


if __name__ == "__main__":
    unittest.main()
