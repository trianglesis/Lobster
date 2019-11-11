"""
Test digest, mails, reports, charts, pages for Confluence
will be compose and send here.

"""
import os
from django.conf import settings
from django.core import mail
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from octo.config_cred import mails

# Python logger
import logging
log = logging.getLogger("octo.octologger")
curr_hostname = getattr(settings, 'CURR_HOSTNAME', None)


class Mails:

    @staticmethod
    def short(**mail_args):
        """
        Simply get the args to fill mail with to, cc, subject and text and send.
        https://docs.djangoproject.com/en/2.0/topics/email/

        :param mail_args: dict
        :return:
        """
        mail_html = mail_args.get('mail_html', '')   # When nothing to render - send just plain text
        body      = mail_args.get('body', False)     # When nothing to render - send just plain text
        subject   = mail_args.get('subject', False)  # When nothing to render - send just plain text

        send_to   = mail_args.get('send_to', [mails['admin'], ])  # Send to me, if None.
        send_cc   = mail_args.get('send_cc', '')

        txt = '{} {} host: {}'
        if not body and not mail_html:
            body = txt.format('No txt body added.', '\n', curr_hostname)
        else:
            body = "{} \nOn host: {}".format(body, curr_hostname)

        if not subject:
            subject = txt.format('No Subject added', ' - ', curr_hostname)

        if os.name == "nt":
            msg = f"mail_html={mail_html} body={body} subject={subject} send_to={send_to} send_cc={send_cc}"
            log.debug('Sending short email confirmation: %s', msg)
        else:
            connection = mail.get_connection()
            connection.open()

            admin = mails['admin']

            email_args = dict(
                from_email = getattr(settings, 'EMAIL_ADDR', None),
                to         = send_to,
                cc         = send_cc,
                bcc        = [admin, ],  # Always send to me.
                subject    = subject,
                body       = body,
                connection = connection
            )

            # log.debug("<=MailSender=> short email_args - %s", email_args)
            if mail_html:
                # log.debug("<=MAIL SIMPLE=> Mail html send")
                email = EmailMultiAlternatives(**email_args)
                # log.debug("<=MailSender=> short email_args - %s", email_args)
                email.attach_alternative(mail_args.get('mail_html', ''), "text/html")
                email.send()
            else:
                email = EmailMessage(**email_args)
                # log.debug("<=MailSender=> short email_args - %s", email_args)
                email.send()
                # log.debug("<=MAIL SIMPLE=> Mail txt send")
