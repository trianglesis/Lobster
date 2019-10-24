
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from octo_tku_upload.api.serializers import *

import logging
log = logging.getLogger("octo.octologger")


class TkuPackagesNewViewSet(viewsets.ModelViewSet):
    queryset = TkuPackagesNew.objects.all().order_by('-updated_at')
    serializer_class = TkuPackagesNewSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )


class UploadTestsNewViewSet(viewsets.ModelViewSet):
    queryset = UploadTestsNew.objects.all().order_by('-test_date_time')
    serializer_class = UploadTestsNewSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )
