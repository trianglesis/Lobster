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
        fake_run = mail_args.get('fake_run', False)
        mail_html = mail_args.get('mail_html', '')  # When nothing to render - send just plain text
        body = mail_args.get('body', False)  # When nothing to render - send just plain text
        subject = mail_args.get('subject', False)  # When nothing to render - send just plain text

        send_to = mail_args.get('send_to', [mails['admin']])  # Send to me, if None.
        send_cc = mail_args.get('send_cc', [mails['admin']])
        bcc = mail_args.get('bcc', [mails['admin']])

        attach_file = mail_args.get('attach_file', '')
        attach_content = mail_args.get('attach_content', '')
        attach_content_name = mail_args.get('attach_content_name', 'octopus.html')

        log.debug(f' send_to: {send_to} send_cc: {send_cc} bcc: {bcc}')
        assert isinstance(send_to, list), 'send_to should be a list!'
        assert isinstance(send_cc, list), 'send_cc should be a list!'
        assert isinstance(bcc, list), 'bcc should be a list!'

        txt = '{} {} host: {}'
        if not body and not mail_html:
            body = txt.format('No txt body added.', '\n', curr_hostname)
        else:
            body = "{} \n\t\tOn host: {}".format(body, curr_hostname)

        if not subject:
            subject = txt.format('No Subject added', ' - ', curr_hostname)

        # msg = f"subject: {subject} \n\tsend_to: {send_to} \n\tsend_cc: {send_cc} \n\tbcc: {bcc}"
        # if fake_run:
        #     # Fake run, but send email:
        #     log.debug(f'NOT Sending short email - FAKE RUN : \n\tsubject: {subject} \n\tsend_to: {send_to} \n\tsend_cc: {send_cc} \n\tbcc: {bcc}')
        #     mail_html_f = open(f'{subject}.html', 'w')
        #     mail_html_f.write(mail_html)
        #     mail_html_f.close()
        #     return f'Short mail sent! {msg}'
        # elif settings.DEV:
        #     # Probably a fake run, but on local dev - so do not send emails? Somehow this could be switchable, so I can test email locally!
        #     log.debug(f'NOT Sending short email settings.DEV: \n\tsubject: {subject} \n\tsend_to: {send_to} \n\tsend_cc: {send_cc} \n\tbcc: {bcc}')
        #     # mail_html_f = open(f'{subject}.html', 'w')
        #     # mail_html_f.write(mail_html)
        #     # mail_html_f.close()
        #     # return f'Short mail sent! {msg}'

        connection = mail.get_connection()
        connection.open()
        email_args = dict(
            subject=subject,
            body=body,
            from_email=getattr(settings, 'EMAIL_ADDR', None),
            to=send_to,
            cc=send_cc,
            bcc=bcc,
            connection=connection,
        )
        # log.debug("<=MailSender=> short email_args - %s", email_args)
        if mail_html:
            # log.debug("<=MAIL SIMPLE=> Mail html send")
            email = EmailMultiAlternatives(**email_args)
            # log.debug("<=MailSender=> short email_args - %s", email_args)
            email.attach_alternative(mail_args.get('mail_html', ''), "text/html")
            if attach_file:
                email.attach_file(attach_file)
            if attach_content:
                email.attach(attach_content_name, attach_content, "text/html")
            email.send()
        else:
            email = EmailMessage(**email_args)
            # log.debug("<=MailSender=> short email_args - %s", email_args)
            if attach_file:
                email.attach_file(attach_file)
            if attach_content:
                email.attach(attach_content_name, attach_content, "text/html")
            email.send()
            # log.debug("<=MAIL SIMPLE=> Mail txt send")
