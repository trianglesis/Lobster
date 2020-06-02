import logging
import datetime

from run_core.models import Options
from django.template import loader
from django.db.models import Q

from octo.win_settings import SITE_DOMAIN

from octo_tku_upload.models import UploadTestsNew

from octo.helpers.tasks_run import Runner
from octo.tasks import TSupport

log = logging.getLogger("octo.octologger")


class TKUEmailDigest:

    @staticmethod
    def upload_daily_fails_warnings(kwargs):
        status = kwargs.get('status', 'error')  # error, warning, everything
        tku_type = kwargs.get('tku_type', None)  # tku_type, everything
        fake_run = kwargs.get('fake_run', False)
        send_to = kwargs.get('send_to', None)
        send_cc = kwargs.get('send_cc', ['oleksandr_danylchenko_cw@bmc.com'])

        if not send_to:
            m_upload = Options.objects.get(option_key__exact='mail_recipients.upload_test')
            send_to = m_upload.option_value.replace(' ', '').split(',')

        # mail body
        mail_body = loader.get_template('digests/email_upload_digest.html')
        # Digest full log
        mail_log_html = loader.get_template('digests/email_upload_full_log.html')

        # Select ANY failed, errored or warning log:strp
        today = datetime.date.today()

        queryset = UploadTestsNew.objects.all()
        queryset = queryset.filter(
            Q(test_date_time__year=today.year, test_date_time__month=today.month, test_date_time__day=today.day))

        if status == 'error':
            queryset = queryset.filter(~Q(all_errors__exact='0'))
            queryset = queryset.filter(Q(upload_warnings__isnull=False) | Q(upload_errors__isnull=False) | Q(
                upload_test_status__exact='failed'))
        elif status == 'warning':
            queryset = queryset.filter(~Q(all_errors__exact='0') | ~Q(all_warnings__exact='0'))
            queryset = queryset.filter(Q(upload_warnings__isnull=False) | Q(upload_errors__isnull=False) | Q(
                upload_test_status__exact='failed'))
        elif status == 'everything':
            log.info("Show all statuses")

        if tku_type:
            queryset = queryset.filter(tku_type__exact=tku_type)

        if queryset:
            log.debug("Sending email with TKU fail upload statuses.")
            subject = f'Upload status mail: "{status}" type: {tku_type if tku_type else "all"}'

            mail_html = mail_body.render(
                dict(
                    subject=subject,
                    domain=SITE_DOMAIN,
                    status=status,
                    tests_digest=queryset,
                )
            )
            mail_log = mail_log_html.render(
                dict(
                    subject=subject,
                    domain=SITE_DOMAIN,
                    status=status,
                    tests_digest=queryset,
                )
            )

            t_kwargs = dict(subject=subject,
                            send_to=send_to,
                            send_cc=send_cc,
                            mail_html=mail_html,
                            attach_content=mail_log,
                            attach_content_name=f'TKU_Upload_log_{status}_{tku_type if tku_type else "everything"}_{today.strftime("%Y-%m-%d")}.html',
                            )
            t_args = f'TKU_Upload_digest.{status}.mail'
            t_routing_key = 'UserTestsDigest.TSupport.t_short_mail'
            t_queue = 'w_routines@tentacle.dq2'
            Runner.fire_t(TSupport.t_short_mail, fake_run=fake_run, to_sleep=2, to_debug=True,
                          t_queue=t_queue, t_args=[t_args], t_kwargs=t_kwargs, t_routing_key=t_routing_key)
        else:
            log.info('Do not send any!')
