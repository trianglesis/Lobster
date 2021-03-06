
from django.conf.urls import url, include

from rest_framework.routers import DefaultRouter
from octo_tku_patterns.api.viewsets import *

router = DefaultRouter()

router.register(r'octo_test_cases', TestCasesSerializerViewSet)
router.register(r'octo_test_cases_details', TestCasesDetailsSerializerViewSet)
router.register(r'tests_last', TestLastViewSet)
router.register(r'tests_history', TestHistoryViewSet)
router.register(r'tests_digest_all', TestDigestAllViewSet)
router.register(r'addm_digest', AddmDigestViewSet)


urlpatterns = [
    url(r'^', include(router.urls)),
]