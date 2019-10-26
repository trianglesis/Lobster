"""
Keep here TKU UPLOAD part of Octopus site
"""

from django.conf.urls import url
from django.urls import path

from octo_tku_patterns.views import *


urlpatterns = [

    # Patterns services
    url(r'^sync_patterns/', PatternsService.sync_patterns,
        name='sync_patterns'),
    url(r'^parse_patterns_user/', PatternsService.parse_patterns_user,
        name='parse_patterns_user'),
    url(r'^patterns_weight_compute/', PatternsService.patterns_weight_compute,
        name='patterns_weight_compute'),

    # TESTS RUN:
    # OLD:
    # url(r'^test_execute_web/', TestCaseRunTest.as_view(), name='test_execute_web'),
    # New, also support old:
    url(r'^test_execute_web/', TestCaseRunTestREST.as_view(), name='test_execute_web'),
    url(r'^user_test_add/', TestCaseRunTestREST.as_view(), name='user_test_add'),

    url(r'^test_execute_web/', TestRuns.test_execute_web, name='test_execute_web_old'),

    url(r'^manual_exec_night_run_task/', TestRuns.manual_exec_night_run_task, name='manual_run_night'),

    # Reports
    url(r'^patterns_top_long/', Reports.patterns_top_long, name='patterns_top_long'),

    # TKU Workbench
    # Search
    path('search/', SearchCasesAndLogs.as_view(), name="cases_search"),
    path('found/', SearchCasesAndLogs.as_view(), name="cases_found"),

    path('cases_workbench/', TKNCasesWorkbenchView.as_view(), name="cases_workbench"),
    # GENERIC VIEWS
    # Test cases:
    url(r'^test_cases/', TestCasesListView.as_view(), name='test_cases'),
    path('test_case/<int:pk>/', TestCaseDetailView.as_view(), name='test_case'),
    path('test_case/change/<int:pk>/', TestCasesUpdateView.as_view(), name='test_case_update'),
    # Test cases groups:
    url(r'^test_cases_groups/', TestCasesDetailsListView.as_view(), name='test_cases_groups'),
    path('test_cases_group/<int:pk>/', TestCasesDetailsDetailView.as_view(), name='test_cases_group'),
    path('test_cases_group/change/<int:pk>/', TestCasesDetailsUpdateView.as_view(), name='test_cases_group_update'),
    path('test_cases_group/create/', TestCasesDetailsCreateView.as_view(), name='test_cases_group_create'),

    # Test reports:
    # Tests ADDM digest:
    # 1st level
    url(r'^addm_digest/', AddmDigestListView.as_view(), name='addm_digest'),
    # Tests last:
    # 2nd level
    url(r'^tests_last/', TestLastDigestListView.as_view(), name='tests_last'),
    url(r'^patterns_digest/', TestLastDigestListView.as_view(), name='patterns_digest'),
    # 3rd level
    url(r'^test_details/', TestLastSingleDetailedListView.as_view(), name='test_details'),
    url(r'^pattern_logs/', TestLastSingleDetailedListView.as_view(), name='pattern_logs'),
    # Tests history:
    url(r'^test_item_history/', TestItemSingleHistoryListView.as_view(), name='test_item_history'),
    url(r'^last_success/', TestItemSingleHistoryListView.as_view(), name='last_success'),

    # JUST FOR DEV
    # Test History day view:
    # Latest by date
    path('test_history_index/', TestHistoryArchiveIndexView.as_view(), name="test_history_index_archive"),
    # Example: /2018/nov/10/
    path('test_history_day/<int:year>/<str:month>/<int:day>/', TestHistoryDayArchiveView.as_view(), name="test_history_archive_day"),
    # Test History Today view:
    path('test_history_today/', TestHistoryTodayArchiveView.as_view(), name="test_history_archive_today"),
    # DEV
    path('mail_test_added_dev/', MailTestAddedDev.as_view(), name="mail_test_added_dev"),


]
