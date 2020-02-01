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


"""
Install order:
tideway-content          tkn_main                       tkn_ship
                         - alpha, beta, echo, golf      - charlie, delta, foxtrot
    -- after tests, after TKU Continuous or GA (ignore TKU prod.cont overlapping)

tideway-devices          tkn_main            tkn_ship
                         - beta              - charlie
    -- any window (not require when TKU Continuous enabled)

continuous               tkn_main            tkn_ship
                         - alpha              - charlie
    -- right after tests (7-8AM)

release GA fresh         - foxtrot         during release rush (24-29 day)
release GA Upgrade       - charlie         during release rush (24-29 day)



"""


class OctoTestCaseUpload(octo_tests.OctoTestCase):

    def setUp(self):
        octo_tests.OctoTestCase.setUp(self)
        # self.user_and_mail('Danylcha', "Dan@bmc.com")

    def test001_product_content_update_tkn_main(self):
        """ Install tideway_content, except ADDM where continuous build installs """
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['alpha', 'beta', 'echo', 'golf'],
            addm_name__in=['custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()

    def test002_product_content_update_tkn_ship(self):
        """ Install tideway_content, except ADDM where continuous build installs """
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['charlie', 'delta', 'foxtrot'],
            addm_name__in=['custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()

    def test003_tideway_devices_update_tkn_main(self):
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_devices'
        self.package_detail = 'tideway-devices'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['beta'],
            addm_name__in=['custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()

    def test004_tideway_devices_update_tkn_ship(self):
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_devices'
        self.package_detail = 'tideway-devices'
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['charlie'],
            addm_name__in=['custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()

    def test005_release_ga_upgrade(self):
        self.tku_wget = True
        self.test_mode = 'update'
        # Update mode will select packages for upgrade test by itself
        # previous = self.select_latest_released()
        # current_ga = self.select_latest_ga()
        # Update mode will select packages for upgrade test by itself
        # package_types=[previous, current_ga],
        self.addm_set = self.addm_set.filter(
            addm_group__in=['foxtrot'],
            addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()

    def test006_release_ga_fresh(self):
        package_type = self.select_latest_ga()
        self.tku_wget = True
        self.test_mode = 'fresh'
        self.addm_set = self.addm_set.filter(
            addm_group__in=['charlie'],
            addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.package_types = [package_type]
        self.run_case()

    def test007_tkn_main_continuous_fresh(self):
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'fresh'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['alpha'],
            addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()

    def test008_tkn_ship_continuous_fresh(self):
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'fresh'
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['charlie'],
            addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()


if __name__ == "__main__":
    unittest.main()
