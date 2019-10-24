from django.conf.urls import url
from dev_site.views import DevAdminViews as DevViews
from dev_site.views import DevAdminTasksCall as DevTasksCall
from dev_site.views import DevRunTasks
from dev_site.views import Old


urlpatterns = [
    url(r'^$', DevViews.index,
        name='octo_dev_admin'),
    # TEST DEV:
    # Parse and local oper:
    url(r'^dev_p4_info_web/', DevViews.dev_p4_info_web,
        name='dev_p4_info_web'),
    # Test t_p4_sync_smart:
    url(r'^dev_p4_sync_smart/', DevTasksCall.dev_p4_sync_smart,
        name='dev_p4_sync_smart'),

    # Testing how it parse local files: compose_tree_paths
    url(r'^dev_parse_local_files/', DevViews.dev_parse_local_files,
        name='dev_parse_local_files'),
    # Testing how it parse local files with threading: t_p4_changes_threads
    url(r'^dev_parse_patterns_thread/', DevTasksCall.dev_parse_patterns_thread,
        name='dev_parse_patterns_thread'),

    # TEST EMAILS
    url(r'^dev_test_email_templates/', DevViews.dev_test_email_templates,
        name='dev_test_email_templates'),
    url(r'^dev_test_email_templates_upload_test/', DevViews.dev_test_email_templates_upload_test,
        name='dev_test_email_templates_upload_test'),
    url(r'^dev_test_email_night_routine/', DevViews.dev_test_email_night_routine,
        name='dev_test_email_night_routine'),

    # Show options
    url(r'^dev_get_options_table_values/', DevViews.dev_get_options_table_values,
        name='dev_get_options_table_values'),

    # Run task:

    url(r'^dev_addm_custom_cmd/', DevTasksCall.dev_addm_custom_cmd,
        name='dev_addm_custom_cmd'),

    url(r'^dev_addm_tw_restart/', DevTasksCall.dev_addm_tw_restart,
        name='dev_addm_tw_restart'),

    url(r'^dev_select_night_test/', DevViews.dev_select_night_test,
        name='dev_select_night_test'),
    url(r'^dev_cron_items/', DevViews.dev_cron_items,
        name='dev_cron_items'),

    # Run Dev versions of prod tasks:
    url(r'^dev_manual_exec_night_run_task/', DevRunTasks.dev_manual_exec_night_run_task,
        name='dev_manual_exec_night_run_task'),


    url(r'^select_all_routine_logs/', Old.select_all_routine_logs,
        name='select_all_routine_logs'),


    ]
