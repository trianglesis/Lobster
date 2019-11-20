
if __name__ == "__main__":
    import logging
    import django

    django.setup()

    from octotests.tests_discover_run import DiscoverLocalTests, TestRunnerLoc
    log = logging.getLogger("octo.octologger")

    test_disco = {
        "test_method": "test002_product_content_update_tkn_ship",
        "test_class": "OctoTestCaseUpload",
        "test_module": "octotests.tests.octotest_upload_tku",
        "disco_module": "octotests.tests_discover_run"
    }

    DiscoverLocalTests().get_all_tests_dev(**test_disco)

    # Upload routine via test execution call:
    upload_r = {
        "test_method": "test002_product_content_update_tkn_ship",
        "test_class": "OctoTestCaseUpload",
        "test_module": "octotests.tests.octotest_upload_tku"
    }
    # run_routine = TestRunnerLoc().run_subprocess(**upload_r)

