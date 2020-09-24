"""
Example for octo test
"""
import unittest
from itertools import groupby
from operator import itemgetter

try:
    from octotests import octo_tests
    from run_core.models import Options
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
        # self.tkn_main_addm_group_l = ['beta', 'charlie', 'delta', 'hotel', 'india', 'juliett']
        self.tkn_main_addm_group_l = ['beta', 'charlie', 'delta']
        self.tkn_ship_addm_group_l = ['echo','foxtrot','golf']

    def test001_product_content_update_tkn_main(self):
        """
        Product Content Update tkn_main
        Install tideway_content, except ADDM where continuous build installs
        """
        self.addm_group_l = Options.objects.get(option_key__exact='night_workers.tkn_main').option_value.replace(' ', '').split(',')
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=self.tkn_main_addm_group_l,
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test002_product_content_update_tkn_ship(self):
        """
        Product Content Update tkn_ship
        Install tideway_content, except ADDM where continuous build installs
        """
        self.addm_group_l = Options.objects.get(option_key__exact='night_workers.tkn_ship').option_value.replace(' ', '').split(',')
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=self.tkn_ship_addm_group_l,
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
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
            addm_group__in=self.tkn_main_addm_group_l,
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
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
            addm_group__in=self.tkn_ship_addm_group_l,
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test005_release_ga_upgrade(self):
        """
        RELEASE GA Upgrade mode
        Install TKU release GA in UPGRADE mode. Run BEFORE fresh routine! ADDM: ['alpha'].
        This group is locked only for upload tests! Cron 24-30 days.
        :return:
        """
        # self.tku_wget = True
        self.test_mode = 'update'
        self.revert_snapshot = True
        # Update mode will select packages for upgrade test by itself
        # previous = self.select_latest_released()
        # current_ga = self.select_latest_ga()
        # Update mode will select packages for upgrade test by itself
        # package_types=[previous, current_ga],
        self.addm_set = self.addm_set.filter(
            addm_group__in=['alpha'],
            # addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test006_release_ga_fresh(self):
        """
        RELEASE GA Fresh mode
        Install TKU release GA in FRESH mode. Run BEFORE fresh routine! ADDM: ['alpha'].
        This group is locked only for upload tests! Cron 24-30 days.
        :return:
        """
        package_type = self.select_latest_ga()
        # self.tku_wget = True
        self.test_mode = 'fresh'
        self.revert_snapshot = True
        self.addm_set = self.addm_set.filter(
            addm_group__in=['alpha'],
            # addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.package_types = [package_type]
        self.run_case()

    def test007_tkn_main_continuous_fresh(self):
        """
        Continuous fresh tkn_main
        Install TKU from the continuous build for the main branch, on assigned ADDM ['beta'].
        Can be any ADDM group, but not the reserved for upload test.
        :return:
        """
        # TODO: Run this when WGET routine detects a new tkn_main_cont package by md5
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'fresh'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['beta'],
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
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
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['bobblehat', 'custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test009_release_ga_upgrade_and_fresh(self):
        # self.tku_wget = True
        self.test005_release_ga_upgrade()
        self.test006_release_ga_fresh()

    def test010_product_content_update_tkn_main_beta(self):
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
            addm_group__in=['beta'],
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test011_product_content_update_tkn_ship_echo(self):
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
            addm_group__in=['echo'],
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['custard_cream', 'double_decker'],  # Skip FF till tpl 12
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test012_product_content_update_main_options_addm(self):
        """
        Product Content Update tkn_main
        Install tideway_content, except ADDM where continuous build installs
        """
        self.addm_group_l = Options.objects.get(option_key__exact='night_workers.tkn_main').option_value.replace(' ', '').split(',')
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=self.addm_group_l,
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test013_product_content_update_ship_options_addm(self):
        """
        Product Content Update tkn_ship
        Install tideway_content, except ADDM where continuous build installs
        """
        self.addm_group_l = Options.objects.get(option_key__exact='night_workers.tkn_ship').option_value.replace(' ', '').split(',')
        self.silent = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_latest_continuous(tkn_branch='tkn_ship')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=self.addm_group_l,
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test014_product_content_update_main_continuous(self):
        """ Usual branch is tkn_main, no ship alowed because there should be only released packages and VMs
        Install dev TKU packages for latest addm. (12.0 for example)"""
        self.addm_group_l = Options.objects.get(option_key__exact='night_workers.tkn_main').option_value.replace(' ', '').split(',')
        self.silent = True
        self.development = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_tku_type(tku_type='main_continuous')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=self.addm_group_l,
            # addm_group__in=['beta'],
            addm_v_int__in=['11.90'],
            disables__isnull=True).order_by('addm_group')
        print(self.addm_set)
        self.run_case()

    def test015_product_content_update_main_latest(self):
        """ Usual branch is tkn_main, no ship alowed because there should be only released packages and VMs
        Install dev TKU packages for latest addm. (12.0 for example)"""
        self.addm_group_l = Options.objects.get(option_key__exact='night_workers.tkn_main').option_value.replace(' ', '').split(',')
        self.silent = True
        self.development = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'tideway_content'
        self.package_detail = 'TKU-Product-Content'
        package_type = self.select_tku_type(tku_type='main_latest')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=self.addm_group_l,
            # addm_group__in=['beta'],
            addm_v_int__in=['11.90'],
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test016_tku_install_main_continuous(self):
        """ Usual branch is tkn_main, no ship alowed because there should be only released packages and VMs
        Install dev TKU packages for latest addm. (12.0 for example)"""
        self.silent = True
        self.development = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'fresh'
        package_type = self.select_tku_type(tku_type='main_continuous')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['beta'],
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['fish_finger'],
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test017_tku_install_main_latest(self):
        """ Usual branch is tkn_main, no ship alowed because there should be only released packages and VMs
        Install dev TKU packages for latest addm. (12.0 for example)"""
        self.silent = True
        self.development = True
        self.tku_wget = False
        self.fake_run = False
        self.test_mode = 'fresh'
        package_type = self.select_tku_type(tku_type='main_latest')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['beta'],
            addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['fish_finger'],
            disables__isnull=True).order_by('addm_group')
        self.run_case()

    def test999_tkn_main_continuous_fresh(self):
        self.revert_snapshot = True
        self.silent = False
        self.tku_wget = True
        self.fake_run = True
        self.test_mode = 'fresh'
        package_type = self.select_latest_continuous(tkn_branch='tkn_main')
        self.package_types = [package_type]
        self.addm_set = self.addm_set.filter(
            addm_group__in=['alpha'],
            # addm_v_int__in=['11.3', '12.0', '12.1'],
            # addm_name__in=['bobblehat'],
            disables__isnull=True).order_by('addm_group')
        self.run_case()


if __name__ == "__main__":
    unittest.main()
