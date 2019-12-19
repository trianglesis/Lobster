if __name__ == "__main__":
    import logging
    import django

    django.setup()
    from run_core.models import TestOutputs
    from octo_tku_patterns.test_executor import TestExecutor

    log = logging.getLogger("octo.octologger")
    test_outputs = TestOutputs.objects.filter(option_key__iregex='tkn_main-')
    for test_out in test_outputs:
        log.info("Parsing: %s", test_out.option_key)
        # log.info("Test out: %s", test_out.option_value)
        stderr_output = test_out.option_value
        parsed = TestExecutor().parse_test_result(stderr_output=stderr_output, test_item=None, addm_item=None, time_spent_test=None)
        log.info("Parsed values: %s", parsed)

