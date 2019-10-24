"""
Example for octo test
"""
from octo_tku_patterns.tasks import TaskPrepare


class OctoTestCase(TaskPrepare):

    def __init__(self, obj):
        obj.silent = True
        obj.fake_run = True
        obj.exclude = True
        obj.request = dict()
        self.pattern_folder_names()
        super().__init__(obj)

    def pattern_folder_names(self):
        self.request.update(
            refresh=True,
            # silent=True,
            fake_run=True,
            exclude=True,
            user_name='octotests',
            user_email='octotests',
            selector=dict(
                cases_ids='1,2',
            ),
            # selector=dict(
            #     tkn_branch='tkn_main',
            #     pattern_library='CORE',
            #     pattern_folder_names=[
            #         '10genMongoDB',
            #         'BlazegraphDatabase',
            #         'BMCBladelogicServerAutomationSuite',
            #         'BMCMiddlewareMngmntPerformanceAvailability',
            #         'EmbarcaderoDSAuditor',
            #     ],
            # ),
        )

    def run(self):
        self.run_tku_patterns()


if __name__ == "__main__":
    import django
    django.setup()
    OctoTestCase(TaskPrepare).run()
