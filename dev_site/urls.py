from django.conf.urls import url
from dev_site.views import DevAdminViews as DevViews
from dev_site.views import Old


urlpatterns = [
    url(r'^$', DevViews.index,
        name='octo_dev_admin'),
    # TEST DEV:
    # Parse and local oper:
    url(r'^dev_p4_info_web/', DevViews.dev_p4_info_web,
        name='dev_p4_info_web'),


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
    url(r'^dev_cron_items/', DevViews.dev_cron_items,
        name='dev_cron_items'),

    url(r'^select_all_routine_logs/', Old.select_all_routine_logs,
        name='select_all_routine_logs'),


    ]
