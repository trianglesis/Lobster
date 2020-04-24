
import unittest
import logging
import django
from django.db.models import Max

django.setup()

from octotests.octo_test_utils import UploadTaskUtils, PatternTestUtils
from octo_tku_upload.models import TkuPackagesNew as TkuPackages

log = logging.getLogger("octo.octologger")
module_name = "OctoTest"


class OctoPatternsTestCase(PatternTestUtils):

    @classmethod
    def setUpClass(cls):
        log.debug("Setup Class OctoPatternsTestCase")
        # Early before run tests execute preparation to get most latest p4 changes?
        # Parse local FS
        # Cancel any outgoing tasks and lock workers to be ready?

    def before_tests(self):
        pass

    def after_tests(self):
        pass


class OctoTestCase(UploadTaskUtils):

    @classmethod
    def setUpClass(cls):
        log.debug("Setup Class UploadOctoCaseLoad")

    def select_latest_continuous(self, tkn_branch):
        package_type = TkuPackages.objects.filter(tku_type__exact=tkn_branch + '_continuous').aggregate(
            Max('package_type'))
        return package_type['package_type__max']

    def select_latest_ga(self):
        package_type = TkuPackages.objects.filter(tku_type__exact='ga_candidate').aggregate(Max('package_type'))
        return package_type['package_type__max']

    def select_latest_released(self):
        package_type = TkuPackages.objects.filter(tku_type__exact='released_tkn').aggregate(Max('package_type'))
        return package_type['package_type__max']

    def select_any_amount_of_packages(self):
        package_type = TkuPackages.objects.filter(tku_type__exact='addm_released',
                                                  addm_version__exact='11.3').aggregate(Max('package_type'))
        return package_type['package_type__max']

    def select_tku_type(self, tku_type):
        package_type = TkuPackages.objects.filter(tku_type__exact=tku_type).aggregate(
            Max('package_type'))
        return package_type['package_type__max']


def main(module_name):
    log.info("Running tests: %s", module_name)
    unittest.main()
