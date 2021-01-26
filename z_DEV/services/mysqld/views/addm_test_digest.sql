CREATE ALGORITHM = UNDEFINED DEFINER = `root`@`localhost` SQL SECURITY DEFINER VIEW `addm_test_digest` AS
SELECT `octo_test_last`.`id`                                       AS `id`,
       `octo_test_last`.`tkn_branch`                               AS `tkn_branch`,
       `octo_test_last`.`addm_host`                                AS `addm_host`,
       `octo_test_last`.`addm_name`                                AS `addm_name`,
       `octo_test_last`.`addm_v_int`                               AS `addm_v_int`,
       COUNT(`octo_test_last`.`test_py_path`)                      AS `tests_count`,
       COUNT(DISTINCT `octo_test_last`.`pattern_folder_name`)      AS `patterns_count`,
       SUM(REGEXP_LIKE(`octo_test_last`.`tst_status`,
                       '^(FAIL|fail|unexpected|failure)|Warning')) AS `fails`,
       SUM((`octo_test_last`.`tst_status` = 'ERROR'))              AS `error`,
       SUM((`octo_test_last`.`tst_status` = 'ok'))                 AS `passed`,
       SUM(REGEXP_LIKE(`octo_test_last`.`tst_status`,
                       '(skipped|expected)'))                      AS `skipped`
FROM `octo_test_last`
GROUP BY `octo_test_last`.`addm_name`, `octo_test_last`.`tkn_branch`