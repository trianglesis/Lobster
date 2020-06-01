
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

    def upload_daily_fails_warnings(self, kwargs):
        status = kwargs.get('status', 'error')

        # mail body
        mail_body = loader.get_template('digests/email_upload_digest.html')
        # digest table
        mail_digest_tb = loader.get_template('digests/tables_details/email_today_table.html')
        # Digest full log
        mail_log_html = loader.get_template('digests/email_upload_full_log.html')

        # Select ANY failed, errored or warning log:strp
        # today     = datetime.date.today()
        today = datetime.datetime.strptime('2020-05-25', '%Y-%m-%d')
        log.debug(f"today: {today}")

        queryset = UploadTestsNew.objects.all()

        queryset = queryset.filter(Q(test_date_time__year=today.year, test_date_time__month=today.month, test_date_time__day=today.day))
        # queryset = queryset.filter(Q(test_date_time__year=today.year, test_date_time__month=today.month, test_date_time__day=today.day))
        log.debug(f"today queryset fail: {queryset.count()} - {queryset}\n{queryset.query}")

        if status == 'error':
            queryset = queryset.filter(~Q(all_errors__exact='0'))
        elif status == 'warning':
            queryset = queryset.filter(~Q(all_errors__exact='0') | ~Q(all_warnings__exact='0'))

        log.debug(f"not 0 issues query: {queryset.count()} - {queryset} \n{queryset.query}")
        queryset = queryset.filter(Q(upload_warnings__isnull=False)| Q(upload_errors__isnull=False) | Q(upload_test_status__exact='failed'))
        log.debug(f"upload errors\warnings query: {queryset.count()} - {queryset} \n{queryset.query}")

        mail_html = mail_body.render(
            dict(
                subject='DEV EMAIL',
                domain=SITE_DOMAIN,
                mail_opts='mail_opts',
                tests_digest=queryset,
            )
        )