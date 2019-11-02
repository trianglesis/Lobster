"""
Keep here admin part of Octopus site
"""

from rest_framework.routers import DefaultRouter
from django.conf.urls import url, include
from octo_adm.views import AdminFunctions, CeleryInteract, TaskOperationsREST, AdminOperationsREST, ListAllAddmVmREST

router = DefaultRouter()
router.register(r'addm_sets', ListAllAddmVmREST)

urlpatterns = [
    # REST model views
    url(r'^', include(router.urls)),
    # Admin
    url(r'^addm_workbench/', AdminFunctions.addm_workbench_widgets, name='addm_workbench'),

    # ADDM service
    url(r'^addm_buttons_page/', AdminFunctions.addm_buttons_page, name='addm_buttons_page'),
    # Celery shed
    url(r'^celery_beat_crontabschedules/', AdminFunctions.celery_beat_crontabschedules, name='celery_beat_crontabschedules'),
    url(r'^reset_cron_last_run/', AdminFunctions.reset_cron_last_run, name='reset_cron_last_run'),

    # Celery operations
    # New
    url(r'^workers_status/', CeleryInteract.workers_status, name='workers_status'),
    # System command to restart celery workers:
    url(r'^celery_service_restart/', CeleryInteract.celery_service_restart, name='celery_service_restart'),

    # NEW:
    # REST Support for ADMIN functions and tasks:
    url(r'^task_operation/', TaskOperationsREST.as_view(), name='task_operations'),
    url(r'^admin_operations/', AdminOperationsREST.as_view(), name='admin_operations'),
]
