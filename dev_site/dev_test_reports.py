import datetime

from django.db.models import Q
from django.db.models.aggregates import Sum

if __name__ == "__main__":

    import django
    import logging

    log = logging.getLogger("octo.octologger")
    django.setup()

    from octo_tku_patterns.model_views import TestReportsView
    from octo_tku_patterns.models import TestReports


    def get_stats(**kwargs):
        # print(f"Selecting by: {kwargs}")
        report_date_time = kwargs.get('report_date_time')

        if not isinstance(report_date_time, datetime.date):
            print(f"Warning: report_date_time should bw a datetime object, if not - will use today date by default!")
            date_var = datetime.date.today()
        else:
            date_var = report_date_time

        queryset = TestReports.objects.all()
        if kwargs.get("test_type"):
            queryset = queryset.filter(
                test_type__exact=kwargs.get("test_type")
            )
        else:
            queryset = queryset.filter(
                tkn_branch__isnull=False)
        if kwargs.get('addm_name'):
            queryset = queryset.filter(
                addm_name__exact=kwargs.get('addm_name')
            )
        if kwargs.get('tkn_branch'):
            queryset = queryset.filter(
                tkn_branch__exact=kwargs.get('tkn_branch')
            )
        if kwargs.get('pattern_library'):
            queryset = queryset.filter(
                pattern_library__exact=kwargs.get('pattern_library')
            )
        if kwargs.get('report_date_time'):
            queryset = queryset.filter(
            Q(report_date_time__year=date_var.year,
              report_date_time__month=date_var.month,
              report_date_time__day=date_var.day)
            )

        return queryset

    def insert_digest():
        tests = TestReportsView.objects.all().values(
            'test_type',
            'tkn_branch',
            'pattern_library',
            'addm_name',
            'addm_v_int',
            'tests_count',
            'patterns_count',
            'fails',
            'error',
            'passed',
            'skipped',
        )
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
        return queryset

    # insert_digest()
    for day in range(5):
        date_var_ = datetime.datetime.now() - datetime.timedelta(days=day)

        # date_var_ = datetime.date.today()
        queryset_ = select_stats(
            tkn_branch='tkn_ship',
            test_type='tku_patterns',
            # pattern_library='CORE',
            grouping='tkn_branch',
            report_date_time=date_var_,
        )
        for row in queryset_.values():
            print(row)