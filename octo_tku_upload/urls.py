"""
Keep here TKU UPLOAD part of Octopus site
"""

from django.conf.urls import url
from django.urls import path
from octo_tku_upload.views import *

urlpatterns = [
    # Upload tests and TKU packages:
    url(r'^tku_sync/', UploadTKU.tku_sync, name='tku_sync'),
    url(r'^run_tku_parse/', UploadTKU.run_tku_parse, name='run_tku_parse'),
    url(r'^tku_packages/', ViewTKU.tku_packages, name='tku_packages'),

    #  New
    url(r'^tku_operations/', TKUOperationsREST.as_view(), name='tku_operations'),

    # GENERIC VIEWS:
    # TKU Workbench
    path('tku_workbench/', TKUUpdateWorkbenchView.as_view(), name="tku_workbench"),
    # Packages
    path('tku_packages_index/', TKUPackagesListView.as_view(), name="tku_packages_index"),
    # Latest by date
    path('upload_index/', UploadTestArchiveIndexView.as_view(), name="upload_test_index"),
    # Example: /octo_tku_upload/upload_day/2019/may/27/
    path('upload_day/<int:year>/<str:month>/<int:day>/', UploadTestDayArchiveView.as_view(), name="upload_test_day"),
    # Test History Today view:
    path('upload_today/', UploadTestTodayArchiveView.as_view(), name="upload_test_today"),

]
