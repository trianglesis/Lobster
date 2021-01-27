import datetime
import openpyxl
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Border, Side, Alignment, Protection, Font

from django.db.models import Q
from django.db.models.aggregates import Sum, Avg, Max, Min, StdDev, Variance, Count

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

        fake_date = datetime.datetime.now() - datetime.timedelta(days=5)
        for item in tests:
            save_tst = TestReports(**item, report_date_time=fake_date)
            save_tst.save(force_insert=True)


    def select_stats(**kwargs):
        by_value = kwargs.get('grouping')
        queryset = get_stats(**kwargs)
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


    def make_queries(day_range=30):
        for day in range(day_range):
            date_var_ = datetime.datetime.now() - datetime.timedelta(days=day)
            # date_var_ = datetime.date.today()
            queryset_ = select_stats(
                tkn_branch='tkn_ship',
                test_type='tku_patterns',
                grouping='tkn_branch',
                report_date_time=date_var_,
                # addm_name='gargoyle',
                # pattern_library='CORE',
            )
            for row in queryset_:
                print(f"Result for day {date_var_.strftime('%Y-%m-%d')}: {row}")

    def make_query(day):
        # date_var_ = datetime.datetime.now() - datetime.timedelta(days=30)
        # date_var_ = date_var_ + datetime.timedelta(days=day)
        date_var_ = datetime.datetime.now()
        date_var_ = date_var_ - datetime.timedelta(days=day)
        print(f"Query stats for: {date_var_.strftime('%m/%d')}")
        queryset_ = select_stats(
                tkn_branch='tkn_ship',
                test_type='tku_patterns',
                grouping='tkn_branch',
                report_date_time=date_var_,
                # addm_name='gargoyle',
                # pattern_library='CORE',
        )
        if queryset_:
            return queryset_[0]
        else:
            return dict(
                date=date_var_,
                tests_sum=0,
            )


    def print_col_letter(cell, p=None):
        if hasattr(cell, 'column_letter'):
            if p:
                print(f'{cell.column_letter}{cell.row}')
            return True
        else:
            return False


    def workbook_create(filename=None):
        if not filename:
            filename = 'test.xlsx'
        else:
            filename = f'{filename}.xlsx'

        wb = Workbook()
        ws1 = wb.active
        ws1.title = "Last_30_days"
        ws1.page_setup.fitToWidth = 1

        font_B = Font(name='Calibri', size=9, bold=True)
        font_N = Font(name='Calibri', size=9, bold=False)
        border_t = Border(
            left=Side(border_style='thin', color='FF000000'),
            right=Side(border_style='thin', color='FF000000'),
            top=Side(border_style='thin', color='FF000000'),
            bottom=Side(border_style='thin', color='FF000000'),
        )
        border_s = Border(
            left=Side(border_style='thin', color='FF000000'),
            right=Side(border_style='thin', color='FF000000'),
            # top=Side(border_style='thin', color='FF000000'),
            # bottom=Side(border_style='thin', color='FF000000'),
        )

        # Merge Cells:
        # ws1.merge_cells('B1:AI1')
        ws1.column_dimensions['A'].width = 2
        ws1.column_dimensions['AG'].width = 2
        ws1.column_dimensions['AJ'].width = 2
        ws1.column_dimensions['B'].width = 20
        ws1.column_dimensions['AH'].width = 20
        # HEAD
        ws1.merge_cells(start_row=1, start_column=2, end_row=2, end_column=36)
        # HEADER
        ws1["B1"] = 'Automation Status for ADE Optimize'
        ws1["B1"].font = font_B
        # MONTH VIEW
        ws1["B5"] = 'Pass %'
        ws1["B6"] = '# of Failures'
        ws1["B7"] = '# of Tests Executed'
        ws1["B8"] = '# of Tests Not  Executed'
        # MONTH STATS
        ws1["AH3"] = 'Last 30 days stats:'
        ws1["AH3"].font = font_B
        ws1["AH5"] = '# of Days at 100%:'
        ws1["AH6"] = 'Avg Pass Rate:'
        ws1["AH7"] = 'Avg # of Failures:'

        """
        C4:AF4 - Date %m-%d
        C5:AF4 - Pass %
        C6:AF6 - Fails #
        C7:AF7 - Run test #
        C8:AF8 - Not run test #
        
        AI5 - Days 100% Success
        AI6 - Avg Pass Rate
        AI7 - Avg # of Failures
        """

        # Get ROWs 4:8
        for _r in range(4, 9):
            # Get COLs A:AI
            for _c in range(1, 36):
                # Get COLs: B:AF
                cell = ws1.cell(column=_c, row=_r)
                # print(f"COL: {cell.column_letter}:{_r}")
                # Make borders B:AF
                if _c in range(2, 33):
                    # Get COLs C:AF and not on rows 4:8
                    if _c in range(3, 33) and not _r in [4, 8]:
                        cell.border = border_s
                    # Get COLs C:AF on rows 4:8
                    else:
                        cell.border = border_t
                    # Make COL thinner C:AF
                    if _c in range(3, 33) and _r == 4:
                        ws1.column_dimensions[cell.column_letter].width = 6
                # Make font
                # Get COLs A:AJ
                if _c in range(1, 36):
                    cell.font = font_N
                # Make summary table borders
                # Get ROWs 4:7
                if _r in range(4, 8):
                    # Get COLs AH:AI
                    if _c in range(34, 36):
                        cell.border = border_t

        """
        Possible way to get all cells previously filled with style
         and iter COLs from each 4th to the last 8th with borders.
         While iteration over each COL - we also get its child CELLs from above C1,C2,...C8
         We only need to fill CELLs with data starting from 4th cell from above staying in current COL.
         Next COL D and all following CELLs will be filled accordingly.
         
         Iterate all COLS from ROW 4th - which is the ROW where is no merged cells!
         
         Firstly the list of COLs to iterate is reversed, so we start from the end - "AJ" col, 
          which is latest one with the style applied.
         Then we step back for 4 cols, to get as first actual COL "AF" as starting point to fill with Data.
         During iteration - increment the i variable which is used as day timedelta from today, to minus 31 day at past.
         Each incrementation calls a query for that day and fill table with a test stat data.
         
          
        """
        i = 0
        # Iter each COL in row 4
        reversed_col_l = list(ws1[4])[::-1]
        print(f"Col 4 list reversed {reversed_col_l[4:]}\n")
        for cell_r in reversed_col_l[4:]:
            i += 1
            if i in range(1,31):
                # get queryset for last 30 days, DESC?
                test_stats = make_query(day=i)

                # Get COL literal name
                col_lit = cell_r.column_letter
                # Get CELL list from column with specific literal name:
                cell_list = list(ws1[col_lit])
                # print(f"COL: {col_lit} CELL list: {cell_list}")

                if test_stats:
                    print(test_stats)

                    # Here assign required cell with some data:
                    cell_list[3].value = test_stats['date'].strftime('%m/%d') # 'date'
                    if test_stats['tests_sum']:
                        cell_list[4].value = f"{round(100 * (int(test_stats['passed_sum']) + int(test_stats['skipped_sum'])) / float(test_stats['tests_sum']), 1)}%" # 'pass %'
                        cell_list[5].value = test_stats['fails_sum'] # '# fails'
                        cell_list[6].value = test_stats['tests_sum'] # '# executed'
                        cell_list[7].value = 0 # '# not executed'


                # Get each 3rd cell, iter over last active: A4:A8
                # for cell in cell_list:
                for cell in cell_list[3:]:
                    print(f'each 3rd cell: {cell} {cell.value}')

        ws2 = wb.create_sheet(title="Historical")
        wb.save(filename=filename)


    # insert_digest()
    # make_queries()
    # make_query(day=1)
    workbook_create()
