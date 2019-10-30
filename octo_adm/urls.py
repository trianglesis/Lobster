"""
Keep here admin part of Octopus site
"""

from django.conf.urls import url
from octo_adm.views import AdminFunctions, CeleryInteract, TaskOperationsREST, AdminOperations


urlpatterns = [

    # Admin
    url(r'^addm_workbench/', AdminFunctions.addm_workbench_widgets, name='addm_workbench'),

    # P4 and local
    url(r'^p4_sync_force/', AdminFunctions.p4_sync_force,
        name='p4_sync_force'),

    # Tasks for tests:
    url(r'^tasks_statuses/', AdminFunctions.tasks_inspection_web,
        name='tasks_statuses'),
    url(r'^workers_active_reserved/', AdminFunctions.workers_active_reserved,
        name='workers_active_reserved'),
    url(r'^workers_active_reserved_short/', AdminFunctions.workers_active_reserved_short,
        name='workers_active_reserved_short'),
    url(r'^workers_raw/', AdminFunctions.workers_raw,
        name='workers_raw'),


    # ADDM service
    url(r'^addm_buttons_page/', AdminFunctions.addm_buttons_page,
        name='addm_buttons_page'),
    url(r'^addm_cleanup/', AdminFunctions.addm_cleanup,
        name='addm_cleanup'),
    url(r'^addm_custom_cmd/', AdminFunctions.addm_custom_cmd,
        name='addm_custom_cmd'),
    url(r'^addm_sync_shares/', AdminFunctions.addm_sync_shares,
        name='addm_sync_shares'),

    # Celery shed

    url(r'^celery_beat_crontabschedules/', AdminFunctions.celery_beat_crontabschedules,
        name='celery_beat_crontabschedules'),
    url(r'^reset_cron_last_run/', AdminFunctions.reset_cron_last_run,
        name='reset_cron_last_run'),
    url(r'^celery_tasks_result/', AdminFunctions.celery_tasks_result,
        name='celery_tasks_result'),


    # Celery operations
    # New
    url(r'^workers_status/', CeleryInteract.workers_status,
        name='workers_status'),

    url(r'^workers_status_single/', CeleryInteract.workers_status_single,
        name='workers_status_single'),

    url(r'^revoke_task_by_id/', CeleryInteract.revoke_task_by_id,
        name='revoke_task_by_id'),
    url(r'^revoke_tasks_active/', CeleryInteract.revoke_tasks_active,
        name='revoke_tasks_active'),

    url(r'^worker_revoke_tasks/', CeleryInteract.worker_revoke_tasks,
        name='worker_revoke_tasks'),

    url(r'^discard_all_tasks/', CeleryInteract.discard_all_tasks,
        name='discard_all_tasks'),
    url(r'^purge_all_tasks/', CeleryInteract.purge_all_tasks,
        name='purge_all_tasks'),
    url(r'^workers_restart/', CeleryInteract.workers_restart,
        name='workers_restart'),
    url(r'^celery_worker_heartbeat/', CeleryInteract.celery_worker_heartbeat,
        name='celery_worker_heartbeat'),
    url(r'^celery_worker_ping/', CeleryInteract.celery_worker_ping,
        name='celery_worker_ping'),

    # System command to restart celery workers:
    url(r'^celery_service_restart/', CeleryInteract.celery_service_restart,
        name='celery_service_restart'),

    # NEW:
    # REST Support for ADMIN functions and tasks:
    url(r'^task_operation/', TaskOperationsREST.as_view(), name='task_operations'),
    url(r'^admin_operations/', AdminOperations.as_view(), name='admin_operations'),
]
