
from django.conf.urls import url, include

from rest_framework.routers import DefaultRouter
from octo.api.viewsets import PeriodicTaskViewSet, CeleryTaskmetaViewSet


router = DefaultRouter()
router.register(r'celery_task_meta', CeleryTaskmetaViewSet)
router.register(r'periodic_task', PeriodicTaskViewSet)
urlpatterns = [
    url(r'^', include(router.urls)),
]
