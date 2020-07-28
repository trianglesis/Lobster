
if __name__ == "__main__":
    import re

    import logging
    import django

    django.setup()
    from run_core.models import TestOutputs, AddmDev
    from octo_tku_patterns.models import TestHistory, TestCases
    from octo_tku_patterns.test_executor import TestExecutor
    from octo_tku_patterns.api.serializers import TestCasesSerializer
    from octo_adm.serializers import AddmDevSerializer

    log = logging.getLogger("octo.octologger")
    parsed = []
    log.info("Testing Octopus TH out parsing:")
    # Fake add item, liwe we test it
    addm_item = AddmDev.objects.get(addm_group__exact='alpha', addm_name__exact='fish_finger')
    addm_item = AddmDevSerializer(addm_item).data

    # Fake test item just like we test it
    test_item = TestCases.objects.get(
        test_py_path__exact='/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/CORE/VMwareVirtualCenter/tests/test.py')
    test_item = TestCasesSerializer(test_item).data

    test_outputs = TestOutputs.objects.filter(
        option_key__iregex='TestExecutor_std_out_err_d_tkn_main-VMwareVirtualCenter')
    # test_outputs = TestOutputs.objects.filter(option_key__iregex='TestExecutor_std_out_err_d_tkn_main-OracleRDBMS-OracleRDBMS')
    # test_outputs = TestOutputs.objects.filter(option_key__iregex='TestExecutor_std_out_err_d_tkn_main-WebsphereMQ-WebsphereMQ')
    for test_out in test_outputs:
        # print("Test out: %s", test_out.option_value)
        stderr_output = test_out.option_value
        parsed = TestExecutor().parse_test_result(
            debug=True,
            stderr_output=stderr_output,
            test_item=test_item,
            addm_item=addm_item, time_spent_test=9.9999)
        # print(f"parsed {parsed}")

    # for value in parsed:
    #     # print(value)
    #     print(f"Parsed tst_name: "
    #              f"\n  tst_name {value['tst_name']} "
    #              f"\n\t  tst_status {value['tst_status']}"
    #              f"\n\t tst_message '{value['tst_message']}'"
    #              f"\n\t fail_message '{value.get('fail_message', 'no fail')}'")


REGEXES = [
    re.compile(r"[A-Z]+:\s(test1_Unix_DRDC1_8270)\s\((__main__)\.(DefectCases)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test2_Unix_DRDC1_9174)\s\((__main__)\.(DefectCases)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test3_Unix_DRDC1_10283)\s\((__main__)\.(DefectCases)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test4_Unix_DRDC1_10283)\s\((__main__)\.(DefectCases)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test10_Unix_scan_name)\s\((__main__)\.(TestCluster)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test13_Windows_Oracle11_Rac)\s\((__main__)\.(TestCluster)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test18_Windows_RAC)\s\((__main__)\.(TestCluster)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test9_Unix_Orcl11_RAC)\s\((__main__)\.(TestCluster)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test_AIX12_Clusterware12c_DRDC1_11693)\s\((__main__)\.(TestCluster)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test_Unix_Oracle11_on_Clusterware)\s\((__main__)\.(TestCluster)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),

    re.compile(r"[A-Z]+:\s(test_Unix_Oracle11_on_HACMP)\s\((__main__)\.(TestCluster)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test_Unix_Oracle11_on_HACMP)\s\((__main__)\.(TestCluster)\)\n-+(?:\n.*(?<![=\-]))+"),
    re.compile(r"[A-Z]+\:\s(test_Unix_Oracle11_on_HACMP)\s\((__main__)\.(TestCluster)\)\n\-+(?P<fail_message>(?:\n.*(?<!=|-))+)"),

    re.compile(r"[A-Z]+:\s(test_Solaris_zones)\s\((__main__)\.(TestClusteredOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test10_Unix_Orcl9)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test11_Unix_QM001861749)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test12_Windows_Oracle10_patches)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test14_Windows_OraclePE)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test15_Windows_Orcl10)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test16_Windows_Orcl11_file)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test17_Windows_Orcl11_proc_command)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test18_Oracl11_linked_databases)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test19_Oracle11_hostname_resolution)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test1_configipedia_check)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test20_DRDC1_10673)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test21_DRDC1_10989)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test22_DRDC1_12032)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test23_DRDC1_11102)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test24_standalone_to_RAC_12)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test25_DRDC1_12994)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test26_DRDC1_13517)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test27_DRDC1_13246)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test28_Oracle_PSU)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test29_Oracle_lecture)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test2_Unix_Oracle8)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test30_all_service_names)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test31_Oracle_Version_update)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test32_Oracle_SE_12_1)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test33_Oracle_RU_update)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test34_Oracle_unique_name_update)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test35_Oracle_SID_update)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test3_Unix_Oracle9)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test4_Unix_Orcl10_in_eBusiness_env)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test5_Unix_Oracle10_SE_and_PathVsSubdirQM00182199)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test6_Unix_Orcl10_listener_path)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test7_Unix_Orcl11_command)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test8_Unix_Orcl11_file)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test_Oracle12)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test_Oracle12_sql_pdb_dip)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test_Oracle9_resolved_sockets)\s\((__main__)\.(TestOracleRDBMS)\)\n-+(?P<fail_message>(?:\n.*(?<![=\-]))+)"),

]

EXPERIMENTAL = [
    re.compile(r"[A-Z]+:\s(test_Unix_Oracle11_on_HACMP)\s\((__main__)\.(TestCluster)\)(?:(\n.+)+(?=-{69}).*)(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test_Unix_Oracle11_on_HACMP)\s\((__main__)\.(TestCluster)\)(?:(?:\n.+)+(?=-{69}).*)(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
    re.compile(r"[A-Z]+:\s(test18_Oracl11_linked_databases)\s\((__main__)\.(TestOracleRDBMS)\)(?:(?:\n.+)+(?=-69).*)(?P<fail_message>(?:\n.*(?<![=\-]))+)"),
]


# (.*\n)+(?=(?:={78}))