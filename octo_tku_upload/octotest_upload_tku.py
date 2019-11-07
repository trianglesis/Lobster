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
        self.request.update(
            fake_run=True,
            user_name='octotests',
            user_email='octotests',
            selector=dict(
                # For update mode just pass a mode:
                # test_mode='update',
                # For step mode pass mode and ordered list of packages by: 'package_type'
                # test_mode='step',
                # package_types=['TKN_release_2018-09-1-114', 'TKN_release_2018-09-1-113'],
                # For fresh package install
                # test_mode='fresh',
                # package_types=['TKN_release_2018-09-1-114', 'TKN_release_2018-09-1-113'],
                # For just package install
                package_types=['TKN_release_2018-09-1-114', 'TKN_release_2018-09-1-113'],
            ),

        )

    def run(self):
        self.run_tku_upload()


if __name__ == "__main__":
    import django
    django.setup()
    OctoTestCase(UploadTaskPrepare).run()
