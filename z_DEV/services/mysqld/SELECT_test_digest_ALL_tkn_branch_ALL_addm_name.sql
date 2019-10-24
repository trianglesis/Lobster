CREATE OR REPLACE VIEW test_latest_digest_all AS
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
    ROUND(SUM(octo_test_last.tst_status REGEXP '^(FAIL|fail|unexpected|failure)') / COUNT(DISTINCT octo_test_cases.test_case_depot_path),
            0) AS fails,
    ROUND(SUM(octo_test_last.tst_status REGEXP '^ERROR') / COUNT(DISTINCT octo_test_cases.test_case_depot_path),
            0) AS error,
    ROUND(SUM(octo_test_last.tst_status REGEXP 'ok') / COUNT(DISTINCT octo_test_cases.test_case_depot_path),
            0) AS passed,
    ROUND(SUM(octo_test_last.tst_status REGEXP '(skipped |expected failure)') / COUNT(DISTINCT octo_test_cases.test_case_depot_path),
            0) AS skipped
FROM
    octopus_dev_copy.octo_test_last,
    octopus_dev_copy.octo_test_cases
WHERE
    octo_test_last.test_py_path = octo_test_cases.test_py_path
GROUP BY octo_test_last.test_py_path , octo_test_last.addm_name
ORDER BY octo_test_cases.tkn_branch,
         octo_test_last.addm_name DESC,
         octo_test_last.pattern_library,
         octo_test_last.pattern_folder_name
-- 5168 row(s) returned 14.047 sec / 0.094 sec  - no percent | with percent 14.359 sec / 0.110 sec | with cases: 0.062 sec / 0.391 sec