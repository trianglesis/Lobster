CREATE OR REPLACE VIEW test_latest_digest_skipped AS
SELECT 
    octo_test_last.id,
    octo_test_cases.test_type,
    octo_test_last.tkn_branch,
    octo_test_last.addm_name,
    octo_test_last.pattern_library,
    octo_test_last.pattern_folder_name,
    octo_test_last.time_spent_test,
    octo_test_last.test_date_time,
    octo_test_last.addm_v_int,
    octo_test_cases.change,
    octo_test_cases.change_user,
    octo_test_cases.change_review,
    octo_test_cases.change_ticket,
    octo_test_cases.change_desc,
    octo_test_cases.change_time,
    octo_test_cases.test_case_depot_path,
    octo_test_cases.test_time_weight,
    octo_test_cases.test_py_path,
    octo_test_last.id AS test_id,
    octo_test_cases.id AS case_id,
    COUNT(DISTINCT octo_test_last.tst_name,
        octo_test_last.tst_class) AS test_items_prepared,
    ROUND(SUM(octo_test_last.tst_status REGEXP '(skipped|expected)') / COUNT(DISTINCT octo_test_cases.test_case_depot_path),
            0) AS skipped
FROM
    octopus_dev_copy.octo_test_last,
    octopus_dev_copy.octo_test_cases
WHERE
    octo_test_last.test_py_path = octo_test_cases.test_py_path
        AND octo_test_last.tst_status REGEXP '(skipped|expected)'
GROUP BY octo_test_last.test_py_path , octo_test_last.addm_name
ORDER BY octo_test_cases.tkn_branch, 
         octo_test_last.addm_name DESC,
         octo_test_last.pattern_library, 
         octo_test_last.pattern_folder_name
-- 659 row(s) returned | with cases: 0.047 sec / 0.031 sec
