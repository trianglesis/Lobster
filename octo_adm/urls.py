"""
Keep here admin part of Octopus site
"""

from rest_framework.routers import DefaultRouter
from django.conf.urls import url, include
from octo_adm.views import *
from django.urls import path

router = DefaultRouter()
router.register(r'list_addms', ListAllAddmVmREST)

urlpatterns = [
    # REST model views
    url(r'^api/v1/', include(router.urls)),

    url(r'^admin/', AdminWorkbench.as_view(), name='admin_workbench'),
    url(r'^addm/', AddmWorkbench.as_view(), name='addm_workbench'),
    # Celery related:
    url(r'^celery/', CeleryWorkbench.as_view(), name='celery_workbench'),
    url(r'^celery_inspect/', CeleryInspect.as_view(), name='celery_inspect'),


    # Admin
    url(r'^old_addm_workbench/', AdminFunctions.addm_workbench_widgets, name='old_addm_workbench'),

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
    url(r'^addm_workbench/', AddmWorkbench.as_view(), name='addm_workbench'),
    # REST Support for ADMIN functions and tasks:
    url(r'^task_operation/', TaskOperationsREST.as_view(), name='task_operations'),
    url(r'^admin_operations/', AdminOperationsREST.as_view(), name='admin_operations'),

]
