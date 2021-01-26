CREATE ALGORITHM = UNDEFINED DEFINER = `root`@`localhost` SQL SECURITY DEFINER VIEW `test_latest_digest_failed` AS
SELECT `octo_test_last`.`id`                    AS `id`,
       `octo_test_cases`.`test_type`            AS `test_type`,
       `octo_test_last`.`tkn_branch`            AS `tkn_branch`,
       `octo_test_last`.`addm_name`             AS `addm_name`,
       `octo_test_last`.`pattern_library`       AS `pattern_library`,
       `octo_test_last`.`pattern_folder_name`   AS `pattern_folder_name`,
       `octo_test_last`.`time_spent_test`       AS `time_spent_test`,
       `octo_test_last`.`test_date_time`        AS `test_date_time`,
       `octo_test_last`.`addm_v_int`            AS `addm_v_int`,
       `octo_test_cases`.`change`               AS `change`,
       `octo_test_cases`.`change_user`          AS `change_user`,
       `octo_test_cases`.`change_review`        AS `change_review`,
       `octo_test_cases`.`change_ticket`        AS `change_ticket`,
       `octo_test_cases`.`change_desc`          AS `change_desc`,
       `octo_test_cases`.`change_time`          AS `change_time`,
       `octo_test_cases`.`test_case_depot_path` AS `test_case_depot_path`,
       `octo_test_cases`.`test_time_weight`     AS `test_time_weight`,
       `octo_test_cases`.`test_py_path`         AS `test_py_path`,
       `octo_test_last`.`id`                    AS `test_id`,
       `octo_test_cases`.`id`                   AS `case_id`,
       COUNT(DISTINCT `octo_test_last`.`tst_name`,
             `octo_test_last`.`tst_class`)      AS `test_items_prepared`,
       ROUND((SUM(REGEXP_LIKE(`octo_test_last`.`tst_status`,
                              '^(FAIL|fail|unexpected|failure|ERROR)')) /
              COUNT(DISTINCT `octo_test_cases`.`test_case_depot_path`)),
             0)                                 AS `fails`
FROM (`octo_test_last`
         JOIN `octo_test_cases`)
WHERE ((CONVERT(`octo_test_last`.`test_py_path` USING UTF8MB4) = `octo_test_cases`.`test_py_path`)
    AND REGEXP_LIKE(`octo_test_last`.`tst_status`,
                    '^(FAIL|fail|unexpected|failure|ERROR)'))
GROUP BY `octo_test_last`.`test_py_path`, `octo_test_last`.`addm_name`
ORDER BY `octo_test_cases`.`tkn_branch`, `octo_test_last`.`addm_name` DESC, `octo_test_last`.`pattern_library`,
         `octo_test_last`.`pattern_folder_name`