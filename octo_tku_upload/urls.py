"""
Keep here TKU UPLOAD part of Octopus site
"""

from django.conf.urls import url
from django.urls import path
from octo_tku_upload.views import *

urlpatterns = [
    # Classical views requests, keep them here for some time.
    url(r'^tku_packages/', UploadTKU.tku_packages, name='tku_packages'),

    #  New
    url(r'^tku_operations/', TKUOperationsREST.as_view(), name='tku_operations'),

    # GENERIC VIEWS:
    # TKU Workbench
    path('tku_workbench/', TKUUpdateWorkbenchView.as_view(), name="tku_workbench"),
    path('tku_workbench_short/', TKUUpdateWorkbenchViewShort.as_view(), name="tku_workbench_short"),
    # Packages
    path('tku_packages_index/', TKUPackagesListView.as_view(), name="tku_packages_index"),
    # Latest by date
    path('upload_index/', UploadTestArchiveIndexView.as_view(), name="upload_test_index"),
    # Example: /octo_tku_upload/upload_day/2019/may/27/
    path('upload_day/<int:year>/<str:month>/<int:day>/', UploadTestDayArchiveView.as_view(), name="upload_test_day"),
    # Test History Today view:
    path('upload_today/', UploadTestTodayArchiveView.as_view(), name="upload_test_today"),

]
