"""octopus URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

from django.conf.urls import include, url
from django.urls import path

from django.contrib import admin
from octo.views import *

from django.conf import settings


urlpatterns = [
    # Home
    url(r'^$', MainPage.as_view(), name='home'),
    url(r'^inspect_rabbitmq_queues/', RabbitMQQueuesREST.as_view(), name='inspect_rabbitmq_queues'),
    url(r'^inspect_celery_workers/', CeleryWorkersStatusREST.as_view(), name='inspect_celery_workers'),

    url(r'^admin/', admin.site.urls),

    # REST
    url('rest-auth/', include('rest_auth.urls')),
    # url(r'^api-auth/', include('rest_framework.urls')),
    # url(r'^ajax/', include('octo.api.urls')),
    url(r'^api/v1/octo/', include('octo.api.urls')),
    url(r'^api/v1/cases/', include('octo_tku_patterns.api.urls')),
    url(r'^api/v1/upload', include('octo_tku_upload.api.urls')),

    # Other:
    url(r'^user_space/', UserMainPage.as_view(), name='user_space'),

    # Include: App actions and tasks:
    url(r'^octo_admin/', include('octo_adm.urls')),

    # Include: TKU PATTERNS, Pattern TESTS AND RELATED:
    url(r'^octo_tku_patterns/', include('octo_tku_patterns.urls')),
    # Include: TKU UPLOAD AND RELATED:
    url(r'^octo_tku_upload/', include('octo_tku_upload.urls')),

    # Django Auth:
    url(r'^unauthorized_banner/', unauthorized_banner, name='unauthorized_banner'),
    url(r'^request_access/', request_access, name='request_access'),

    # https://django-registration.readthedocs.io/en/3.0/activation-workflow.html#activation-workflow
    # https://django-registration.readthedocs.io/en/3.0/upgrade.html?highlight=hmac
    # url(r'^accounts/login/', include('django_registration.backends.activation.urls')),
    url(r'^accounts/', include('django_registration.backends.activation.urls')),
    url(r'^accounts/', include('django.contrib.auth.urls')),

    url(r'^Discovery-Content/', TestLastDigestListViewBoxes.as_view(), name='patterns_digest_boxes'),

    # DEV SITE
    url(r'^octo_dev_admin/', include('dev_site.urls')),

]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns