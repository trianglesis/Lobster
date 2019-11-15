import os
import unittest
import logging
import django
from django.db.models import Max

django.setup()

from run_core.octo_case_caller import UploadTaskUtils
from octo_tku_upload.models import TkuPackagesNew as TkuPackages

log = logging.getLogger("octo.octologger")
module_name = "OctoTest"


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


def main(module_name):
    unittest.main()
