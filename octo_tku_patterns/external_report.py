import datetime
import openpyxl
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Border, Side, Alignment, Protection, Font, Fill

from django.db.models import Q
from django.db.models.aggregates import Sum, Avg, Max, Min, StdDev, Variance, Count

from octo_tku_patterns.model_views import TestReportsView
from octo_tku_patterns.models import TestReports

import logging

log = logging.getLogger("octo.octologger")


class Report:

    @staticmethod
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

    @staticmethod
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

        fake_date = datetime.datetime.now() - datetime.timedelta(days=5)
        for item in tests:
            save_tst = TestReports(**item, report_date_time=fake_date)
            save_tst.save(force_insert=True)

    def select_stats(self, **kwargs):
        by_value = kwargs.get('grouping')
        queryset = self.get_stats(**kwargs)
        queryset = queryset.values(by_value).order_by(by_value).annotate(
            date=Max('report_date_time'),
            addm_v_int=Max('addm_v_int'),
            tests_sum=Sum('tests_count'),
            patterns_sum=Sum('patterns_count'),
            errors_sum=Sum('error'),
            fails_sum=Sum('fails'),
            passed_sum=Sum('passed'),
            skipped_sum=Sum('skipped'),
        )
        # print(f"{queryset.query}")
        return queryset

    def generate_xlxs(self, **kwargs):
        log.debug(f"Generating XML dummy! {kwargs}")