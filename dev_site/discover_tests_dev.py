
if __name__ == "__main__":
    import logging
    import django

    django.setup()

    from octo.tasks import DiscoverLocalTests
    log = logging.getLogger("octo.octologger")

    test_disco = {
        "test_method": "test002_product_content_update_tkn_ship",
        "test_class": "OctoTestCaseUpload",
        "test_module": "run_core.tests.octotest_upload_tku",
    }

    DiscoverLocalTests().get_all_tests_dev(**test_disco)
