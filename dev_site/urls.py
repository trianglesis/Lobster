from django.conf.urls import url
from dev_site.views import DevAdminViews as DevViews


urlpatterns = [
    url(r'^$', DevViews.index, name='octo_dev_admin'),
    url(r'^dev_user_test_finished', DevViews.dev_user_test_finished, name='dev_user_test_finished'),
    url(r'^failed_pattern_test_user_daily_digest', DevViews.failed_pattern_test_user_daily_digest, name='failed_pattern_test_user_daily_digest'),
    url(r'^overall_pattern_test_library_daily_digest', DevViews.overall_pattern_test_library_daily_digest, name='overall_pattern_test_library_daily_digest'),
    url(r'^upload_daily_fails', DevViews.upload_daily_fails, name='upload_daily_fails'),

    ]
