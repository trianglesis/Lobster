"""
Make database operations:
- create tables;
- update tables;
- purge tables;
- run queries;

"""

# Python logger
import logging
log = logging.getLogger("octo.octologger")


class DBServicing:
    """
    Keep some service queries here.
    """

    @staticmethod
    def optimize_table(table):
        # noinspection PyPep8
        """
        Execute simple OPTIMIZE TABLE foo;
        on selected tables/all.

        https://dev.mysql.com/doc/refman/5.7/en/optimize-table.html

        OPTIMIZE TABLE octopus_dev_copy.TESTS_HISTORY;
        OPTIMIZE TABLE octopus_dev_copy.TKU_PATTERNS;

        :param table:
        :return:
        """
        sql = """OPTIMIZE TABLE octopus_dev_copy.octo_test_history;"""

    @staticmethod
    def del_old_records():
        """
        Delete old test records.

        :return:
        """
        sql = """DELETE FROM octopus_dev_copy.octo_test_history WHERE test_date_time < DATE_SUB(NOW(),INTERVAL 365 DAY);"""
