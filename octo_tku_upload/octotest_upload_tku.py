"""
Example for octo test
"""

from octo_tku_upload.tasks import UploadTaskPrepare


class OctoTestCase(UploadTaskPrepare):

    def __init__(self, obj):
        obj.tku_wget = False
        obj.silent = True
        obj.fake_run = True
        obj.request = dict()
        self.tku_upload_release()
        super().__init__(obj)

    def tku_upload_release(self):

        select_latest_tkn_main_continuous = self.select_latest_continuous('tkn_main')
        select_latest_tkn_ship_continuous = self.select_latest_continuous('tkn_ship')
        select_latest_ga = self.select_latest_ga()
        select_latest_released = self.select_latest_released()

        print(f"select_latest_tkn_main_continuous: {select_latest_tkn_main_continuous}")
        print(f"select_latest_tkn_ship_continuous: {select_latest_tkn_ship_continuous}")
        print(f"select_latest_ga: {select_latest_ga}")
        print(f"select_latest_released: {select_latest_released}")

        self.request.update(
            fake_run=True,
            user_name='octotests',
            user_email='octotests',

            # For update mode just pass a mode:
            # test_mode='update',
            # Of select packages manually:
            test_mode='step',
            package_types=[select_latest_ga, select_latest_released],

            # For step mode pass mode and ordered list of packages by: 'package_type'
            # test_mode='step',
            # package_types=['TKN_release_2018-09-1-114', 'TKN_release_2018-09-1-113'],

            # For fresh package install
            # test_mode='fresh',
            # package_types=['TKN_release_2018-09-1-114', 'TKN_release_2018-09-1-113'],

            # For just package install
            # package_types=['TKN_release_2018-09-1-114', 'TKN_release_2018-09-1-113'],

        )

    def run(self):
        self.run_tku_upload()

    @staticmethod
    def select_latest_continuous(tkn_branch):
        package_type = TkuPackages.objects.filter(tku_type__exact=tkn_branch+'_continuous').aggregate(Max('package_type'))
        return package_type['package_type__max']

    @staticmethod
    def select_latest_ga():
        package_type = TkuPackages.objects.filter(tku_type__exact='ga_candidate').aggregate(Max('package_type'))
        return package_type['package_type__max']

    @staticmethod
    def select_latest_released():
        package_type = TkuPackages.objects.filter(tku_type__exact='released_tkn').aggregate(Max('package_type'))
        return package_type['package_type__max']

    @staticmethod
    def select_any_amount_of_packages():
        package_type = TkuPackages.objects.filter(tku_type__exact='addm_released',
                                                  addm_version__exact='11.3').aggregate(Max('package_type'))
        return package_type['package_type__max']


if __name__ == "__main__":
    import django
    django.setup()
    from django.db.models import Max
    from octo_tku_upload.models import TkuPackagesNew as TkuPackages
    OctoTestCase(UploadTaskPrepare).run()
