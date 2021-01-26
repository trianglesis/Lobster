CREATE OR REPLACE VIEW test_last_digest_tkn_main_double_decker AS
SELECT octo_test_last.id,
       octo_test_last.pattern_file_name,
       octo_test_last.pattern_library,
       octo_test_last.pattern_folder_name,
       octo_test_last.time_spent_test,
       octo_test_last.test_date_time,
       octo_test_last.addm_name,+
       octo_test_last.addm_v_int,
       octo_tku_patterns.pattern_folder_change,
       octo_tku_patterns.change_user,
       octo_tku_patterns.change_review,
       octo_tku_patterns.change_ticket,
       octo_tku_patterns.pattern_folder_change,
       COUNT(octo_tku_patterns.pattern_file_path)                        AS patterns_count,
       COUNT(DISTINCT octo_test_last.tst_name, octo_test_last.tst_class) AS test_items_prepared,
       ROUND(SUM(octo_test_last.tst_status REGEXP '^(FAIL|fail|unexpected|failure)') / COUNT(DISTINCT octo_tku_patterns.pattern_file_path), 0) AS fails,
       ROUND(SUM(octo_test_last.tst_status REGEXP 'ERROR') / COUNT(DISTINCT octo_tku_patterns.pattern_file_path), 0) AS error,
       ROUND(SUM(octo_test_last.tst_status REGEXP 'ok') / COUNT(DISTINCT octo_tku_patterns.pattern_file_path), 0) AS passed,
       ROUND(SUM(octo_test_last.tst_status REGEXP '(skipped|expected)') / COUNT(DISTINCT octo_tku_patterns.pattern_file_path), 0) AS skipped,
       ROUND((SUM(octo_test_last.tst_status REGEXP 'ok') / COUNT(DISTINCT octo_tku_patterns.pattern_file_path) / COUNT(DISTINCT octo_test_last.tst_name, octo_test_last.tst_class) * 100), 2) AS passed_percent
FROM octopus_dev_copy.octo_test_last,
     octopus_dev_copy.octo_tku_patterns
WHERE octo_test_last.test_py_path = octo_tku_patterns.test_py_path
  AND octo_test_last.tkn_branch = 'tkn_main'
  AND octo_test_last.addm_name = 'double_decker'
  AND octo_test_last.tst_status REGEXP '^(FAIL|fail|unexpected|failure|ERROR)'
GROUP BY octo_test_last.test_py_path, octo_test_last.addm_name