CREATE OR REPLACE VIEW addm_test_digest AS
SELECT octo_test_last.id,
       octo_test_last.tkn_branch,
       octo_test_last.addm_host,
       octo_test_last.addm_name,
       octo_test_last.addm_v_int,
       COUNT(octo_test_last.test_py_path)                                      AS tests_count,
       COUNT(DISTINCT octo_test_last.pattern_folder_name)                        AS patterns_count,
       SUM(octo_test_last.tst_status REGEXP '^(FAIL|fail|unexpected|failure)') AS fails,
       SUM(octo_test_last.tst_status = 'ERROR')                                AS error,
       SUM(octo_test_last.tst_status = 'ok')                                   AS passed,
       SUM(octo_test_last.tst_status REGEXP '(skipped|expected)')              AS skipped
FROM octopus_dev_copy.octo_test_last
GROUP BY octo_test_last.addm_name, octo_test_last.tkn_branch
;