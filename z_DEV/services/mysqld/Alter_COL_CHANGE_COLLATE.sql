ALTER TABLE octo_tku_patterns CHANGE COLUMN `change_desc` `change_desc` longtext  CHARACTER SET 'utf8' COLLATE 'utf8_general_ci';
#1	2	11:20:13	ALTER TABLE octo_tku_patterns CHANGE COLUMN `change_desc` `change_desc` longtext  CHARACTER SET 'utf8' COLLATE 'utf8_general_ci'	2765 row(s) affected, 1 warning(s):
# 3719 'utf8' is currently an alias for the character set UTF8MB3, but will be an alias for UTF8MB4 in a future release. Please consider using UTF8MB4 in order to be unambiguous.
# Records: 2765  Duplicates: 0  Warnings: 1	0.672 sec

ALTER TABLE `octopus_dev_copy`.`octo_tku_patterns` 
CHANGE COLUMN `change_desc` `change_desc` LONGTEXT CHARACTER SET 'utf8mb4' NULL DEFAULT NULL ;
