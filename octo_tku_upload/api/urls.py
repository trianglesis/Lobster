
from django.conf.urls import url, include

from rest_framework.routers import DefaultRouter
from octo_tku_upload.api.viewsets import *


router = DefaultRouter()
router.register(r'tku_packages', TkuPackagesNewViewSet)
router.register(r'upload_tests', UploadTestsNewViewSet)
urlpatterns = [
    url(r'^', include(router.urls)),
]
