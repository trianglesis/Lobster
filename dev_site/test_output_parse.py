if __name__ == "__main__":
    import logging
    import django

    django.setup()
    from run_core.models import TestOutputs
    from octo_tku_patterns.test_executor import TestExecutor

    log = logging.getLogger("octo.octologger")
    test_outputs = TestOutputs.objects.filter(option_key__iregex='TestExecutor_std_out_err_d_tkn_main-WebsphereMQ-WebsphereMQ')
    for test_out in test_outputs:
        log.info("Parsing: %s", test_out.option_key)
        # log.info("Test out: %s", test_out.option_value)
        stderr_output = test_out.option_value
        parsed = TestExecutor().parse_test_result(stderr_output=stderr_output, test_item=None,
                                                  addm_item={'addm_name': 'local_ff'}, time_spent_test=None)
        log.info("Parsed values: %s", parsed)

