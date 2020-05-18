from django.conf.urls import url
from dev_site.views import DevAdminViews as DevViews


urlpatterns = [
    url(r'^$', DevViews.index, name='octo_dev_admin'),
    url(r'^dev_user_test_finished', DevViews.dev_user_test_finished, name='dev_user_test_finished'),

    ]
