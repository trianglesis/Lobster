"""
Make database operations:
- create tables;
- update tables;
- purge tables;
- run queries;

"""

# Python logger
import logging

from django.db.models import Q

from octo_tku_patterns.model_views import AddmDigest
from octo_tku_patterns.models import TestHistory
from run_core.models import AddmDev

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

    def history_clean(self, **kwargs):
        addm_names = kwargs.get('addm_names', None)

        query_tests = self.clean_history_table()
        if query_tests:
            query_tests.delete()
        else:
            log.info("No old records found for test error\skipped\other statuses.")
        query_addms = self.delete_old_addm_tests(addm_names)
        if query_addms:
            query_addms.delete()
        else:
            log.info("No old records found for old addm_names")

    def clean_history_table(self):
        unwanted_query = TestHistory.objects.filter(
            Q(tst_status__iregex='ERROR:') |
            Q(tst_status__iregex='ERROR') |
            Q(tst_status__iregex='WARNING') |
            Q(tst_status__iregex='unexpected success') |
            Q(tst_status__iregex='expected failure') |
            Q(tst_status__iregex=r"skipped\s+") |
            Q(tst_status__iregex=r"Traceback\s+") |
            Q(tst_status__iregex=r"CORBA\.") |
            Q(tst_status__iregex=r"testutils\.MY_dml_test_utils")
        ).defer()
        if unwanted_query.count() > 0:
            log.info(f"Unwanted results: {unwanted_query.count()}")
            log.info(f"Unwanted results query: {unwanted_query.query}")
        return unwanted_query

    def delete_old_addm_tests(self, addm_names=None):
        if addm_names is None:
            addm_names = []
        if not addm_names:
            addm_names_ = AddmDev.objects.values('addm_name').order_by('-addm_name').distinct()
            for addm in addm_names_:
                addm_names.append(addm['addm_name'])
            log.info(F"Select all records ARE NOT in addm_names = {addm_names}")

        unwanted_query = TestHistory.objects.exclude(addm_name__in=addm_names)
        if unwanted_query.count() > 0:
            log.info(f"Unwanted results: {unwanted_query.count()}")
            log.info(f"Unwanted results query: {unwanted_query.query}")
        return unwanted_query
