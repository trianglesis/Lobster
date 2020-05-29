
import logging
import datetime
from itertools import groupby
from operator import itemgetter

from django.utils import timezone
from django.template import loader
from django.db.models import Q

from octo.win_settings import SITE_DOMAIN

from octo_tku_upload.models import UploadTestsNew, TkuPackagesNew

from octo.helpers.tasks_run import Runner
from octo.tasks import TSupport

log = logging.getLogger("octo.octologger")


class TKUEmailDigest:

    def upload_daily_fails_warnings(self):

        queryset = UploadTestsNew.objects.filter()