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
tideway-content          tkn_main                       tkn_ship (1-24 days)
                         - alpha, beta, echo, golf      - charlie, delta, foxtrot
    -- after tests, after TKU Continuous or GA (ignore TKU prod.cont overlapping)

tideway-devices          tkn_main            tkn_ship
                         - beta              - charlie
    -- any window (not require when TKU Continuous enabled)

continuous               tkn_main            tkn_ship (1-24 days)
                         - alpha              - charlie
    -- right after tests (7-8AM)

release GA fresh         - foxtrot         during release rush (24-30 day)
release GA Upgrade       - charlie         during release rush (24-30 day)



"""


class OctoTestCaseUpload(octo_tests.OctoTestCase):

    def setUp(self):
        octo_tests.OctoTestCase.setUp(self)
        # self.user_and_mail('Danylcha', "Dan@bmc.com")

    def test001_product_content_update_tkn_main(self):
        """
        Product Content Update tkn_main
        Install tideway_content, except ADDM where continuous build installs
        """
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['beta', 'charlie', 'delta', 'hotel', 'india', 'juliett'],
            addm_name__in=['custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()

    def test002_product_content_update_tkn_ship(self):
        """
        Product Content Update tkn_ship
        Install tideway_content, except ADDM where continuous build installs
        """
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['echo', 'foxtrot', 'golf', 'kilo'],
            addm_name__in=['custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()

    def test003_tideway_devices_update_tkn_main(self):
        """
        Tideway Devices Update tkn_main
        Update tideway devices rpm for branch main, for all listed ADDMs: ['beta']
        :return:
        """
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_devices'
        self.package_detail = 'tideway-devices'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['beta', 'charlie', 'delta', 'hotel', 'india', 'juliett'],
            addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()

    def test004_tideway_devices_update_tkn_ship(self):
        """
        Tideway Devices Update tkn_ship
        Update tideway devices RPMs for branch ship, for all listed ADDMs: ['echo']
        :return:
        """
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_devices'
        self.package_detail = 'tideway-devices'
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['echo', 'foxtrot', 'golf', 'kilo'],
            addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()

    def test005_release_ga_upgrade(self):
        """
        RELEASE GA Upgrade mode
        Install TKU release GA in UPGRADE mode. Run BEFORE fresh routine! ADDM: ['alpha'].
        This group is locked only for upload tests! Cron 24-30 days.
        :return:
        """
        # self.silent = True
        self.tku_wget = True
        self.test_mode = 'update'
        # Update mode will select packages for upgrade test by itself
        # previous = self.select_latest_released()
        # current_ga = self.select_latest_ga()
        # Update mode will select packages for upgrade test by itself
        # package_types=[previous, current_ga],
        self.addm_set = self.addm_set.filter(
            addm_group__in=['alpha'],
            addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()

    def test006_release_ga_fresh(self):
        """
        RELEASE GA Fresh mode
        Install TKU release GA in FRESH mode. Run BEFORE fresh routine! ADDM: ['alpha'].
        This group is locked only for upload tests! Cron 24-30 days.
        :return:
        """
        package_type = self.select_latest_ga()
        self.tku_wget = True
        self.test_mode = 'fresh'
        self.addm_set = self.addm_set.filter(
            addm_group__in=['alpha'],
            addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.package_types = [package_type]
        self.run_case()

    def test007_tkn_main_continuous_fresh(self):
        """
        Continuous fresh tkn_main
        Install TKU from the continuous build for the main branch, on assigned ADDM ['beta'].
        Can be any ADDM group, but not the reserved for upload test.
        :return:
        """
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'fresh'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['beta'],
            addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()

    def test008_tkn_ship_continuous_fresh(self):
        """
        Continuous fresh tkn_ship
        Install TKU from the continuous build for the main branch, on assigned ADDM ['echo'].
        Can be any ADDM group, but not the reserved for upload test.
        Run 1-24 days - do not run during release rush, as there is no builds for this.
        :return:
        """
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'fresh'
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['echo'],
            addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()

    def test005_release_ga_upgrade_and_fresh(self):
        self.test005_release_ga_upgrade()
        self.test006_release_ga_fresh()

    def test999_tkn_main_continuous_fresh(self):
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'fresh'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['beta'],
            addm_name__in=['bobblehat'],
            disables__isnull=True).values().order_by('addm_group')
        self.run_case()


if __name__ == "__main__":
    unittest.main()
