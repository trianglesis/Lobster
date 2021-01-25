from django.db.models.aggregates import Sum

if __name__ == "__main__":

    import django
    import logging

    log = logging.getLogger("octo.octologger")
    django.setup()

    from octo_tku_patterns.model_views import TestLatestDigestAll, TestReportsView
    from octo_tku_patterns.models import TestReports

    def get_stats(**kwargs):
        queryset = TestReports.objects.all()
        print(f"Selecting by: {kwargs}")
        if kwargs.get("test_type"):
            queryset = queryset.filter(test_type__exact=kwargs.get("test_type"))
        else:
            queryset = queryset.filter(tkn_branch__isnull=False)
        if kwargs.get('addm_name'):
            queryset = queryset.filter(addm_name__exact=kwargs.get('addm_name'))
        if kwargs.get('tkn_branch'):
            queryset = queryset.filter(tkn_branch__exact=kwargs.get('tkn_branch'))
        if kwargs.get('pattern_library'):
            queryset = queryset.filter(pattern_library__exact=kwargs.get('pattern_library'))
        return queryset

    def insert_digest():
        tests = TestReportsView.objects.all().values()
        for item in tests:
            save_tst = TestReports(**item)
            save_tst.save(force_insert=True)

    def select_stats(**kwargs):
        by_value = kwargs.get('grouping')
        queryset = get_stats(**kwargs)
        queryset = queryset.values(by_value).order_by(by_value).annotate(
            total_tests_count=Sum('tests_count'),
            total_patterns_count=Sum('patterns_count'),
            total_errors=Sum('error'),
            total_fails=Sum('fails'),
            total_passed=Sum('passed'),
            total_skipped=Sum('skipped'),
        )
        for row in queryset:
            print(row)

    # insert_digest()
    select_stats(
        tkn_branch='tkn_ship',
        test_type='tku_patterns',
        # pattern_library='CORE',
        grouping='tkn_branch',
    )