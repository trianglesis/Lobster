
if __name__ == "__main__":

    import django
    import logging

    log = logging.getLogger("octo.octologger")
    django.setup()
    from run_core.models import AddmDev
    from octo_tku_patterns.models import TestHistory
    from django.db.models import Q

    def history_clean():
        query_tests = clean_history_table()
        if query_tests:
            query_tests.delete()
        else:
            log.info("No old records found for test error\skipped\other statuses.")
        query_addms = delete_old_addm_tests()
        if query_addms:
            query_addms.delete()
        else:
            log.info("No old records found for old addm_names")

    def clean_history_table():
        unwanted_query = TestHistory.objects.filter(
            Q(tst_status__iregex='ERROR:') |
            Q(tst_status__iregex='ERROR') |
            Q(tst_status__iregex='WARNING') |
            Q(tst_status__iregex='unexpected success') |
            Q(tst_status__iregex='expected failure') |
            Q(tst_status__iregex=r"skipped\s+") |
            Q(tst_status__iregex=r"testutils\.MY_dml_test_utils")
        ).defer()
        if unwanted_query.count() > 0:
            log.info(f"Unwanted results: {unwanted_query.count()}")
            log.info(f"Unwanted results query: {unwanted_query.query}")
        return unwanted_query

    def delete_old_addm_tests(addm_names=None):
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

    history_clean()