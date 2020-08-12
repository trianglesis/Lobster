"""
Decorator and helpers for tasks, like:
- send emails on start/finish
- fix errors
- parse outputs, etc

"""
import datetime
import functools
import json
# Python logger
import logging
import sys
import traceback
from pprint import pformat
from time import sleep

from billiard.exceptions import WorkerLostError
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.template import loader
from django.utils import timezone
from run_core.models import TaskExceptionLog

from octo.helpers.tasks_mail_send import Mails
from run_core.models import Options, MailsTexts

log = logging.getLogger("octo.octologger")
curr_hostname = getattr(settings, 'CURR_HOSTNAME', None)


def exception(function):
    """
    A decorator that wraps the passed in function and logs exceptions should one occur
    """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):

        try:
            return function(*args, **kwargs)
        except SoftTimeLimitExceeded as e:
            log.warning("Firing SoftTimeLimitExceeded exception. Test should run for additional 500 seconds before die")
            exc_more = f'{e} Task has reached soft time limit. Task will be cancelled in 500 seconds.'
            TMail().mail_log(function, exc_more, _args=args, _kwargs=kwargs)
            # Do not rise when soft time limit, just inform:
            # raise SoftTimeLimitExceeded(msg)
            # TODO: Add addm_cleanup
            addm_items = kwargs.get('addm_items', False)
            if addm_items:
                log.info(f"TODO: WIll run ADDM Clean task 'run_operation_cmd'!")
                # ADDMStaticOperations().run_operation_cmd(**kwargs)
            return wrapper

        except TimeLimitExceeded as e:
            log.warning("Firing TimeLimitExceeded exception. Task will now die!")
            exc_more = f'{e} Task time limit reached! This task was cancelled to release the worker.'
            TMail().mail_log(function, exc_more, _args=args, _kwargs=kwargs)
            # Raise when task goes out of a latest time limit:
            raise TimeLimitExceeded(e)

        except WorkerLostError as e:
            exc_more = f'{e} Task cannot be executed. Celery worker lost or became unreachable.'
            TMail().mail_log(function, exc_more, _args=args, _kwargs=kwargs)
            raise Exception(e)

        except Exception as e:
            log.error(f"Unusual task exception! Check mail or logs for more info. {e}")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            sam = traceback.format_exception(exc_type, exc_value, exc_traceback)
            exc_more = f'{e} Task catches the unusual exception. Please check logs or run debug. \n\t - Traceback: {sam}'
            TMail().mail_log(function, exc_more, _args=args, _kwargs=kwargs)
            error_d = dict(
                function=function,
                error=sam,
                args=args,
                kwargs=kwargs,
            )
            log.error(f"Task Exception: {error_d}")
            try:
                item_sort = json.dumps(error_d, indent=2, ensure_ascii=False, default=pformat)
                log.error(f"Task Exception: {e} {item_sort}")
            except TypeError:
                log.error(f"Task Exception: {error_d}")
            if settings.DEV:
                log.info(
                    f'Exceptions into DEV mode {settings.DEV}: do not send mail log on task fail! {function} {exc_more} {args} {kwargs}')
                TMail().mail_log(function, exc_more, _args=args, _kwargs=kwargs)
            raise Exception(e)

    return wrapper


def f_exception(function):
    """
    A decorator that wraps the passed in function and logs exceptions should one occur
    """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):

        try:
            return function(*args, **kwargs)

        except Exception as e:
            log.error(f"Unusual function exception! Check mail or logs for more info. {e}")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            sam = traceback.format_exception(exc_type, exc_value, exc_traceback)
            exc_more = f'{e} Func catches the unusual exception. Please check logs or run debug. \n\t - Traceback: {sam}'
            TMail().mail_log(function, exc_more, _args=args, _kwargs=kwargs)
            error_d = dict(
                function=function,
                error=sam,
                args=args,
                kwargs=kwargs,
            )
            log.error(f"Func Exception: {error_d}")
            try:
                item_sort = json.dumps(error_d, indent=2, ensure_ascii=False, default=pformat)
                log.error(f"Func Exception: {e} {item_sort}")
            except TypeError:
                log.error(f"Func Exception: {error_d}")
            if settings.DEV:
                log.info(
                    f'Exceptions into DEV mode {settings.DEV}: do not send mail log on task fail! {function} {exc_more} {args} {kwargs}')
                TMail().mail_log(function, exc_more, _args=args, _kwargs=kwargs)
            raise Exception(e)

    return wrapper


class TMail:

    def __init__(self):

        m_night = Options.objects.get(option_key__exact='mail_recipients.night_test_routines')
        self.m_night = m_night.option_value.replace(' ', '').split(',')

        m_service = Options.objects.get(option_key__exact='mail_recipients.service')
        self.m_service = m_service.option_value.replace(' ', '').split(',')

        m_upload = Options.objects.get(option_key__exact='mail_recipients.upload_test')
        self.m_upload = m_upload.option_value.replace(' ', '').split(',')

        m_user_test = Options.objects.get(option_key__exact='mail_recipients.user_test_cc')
        self.m_user_test = m_user_test.option_value.replace(' ', '').split(',')

    def mail_log(self, function, e, _args, _kwargs):
        user_email = _kwargs.get('user_email', False)
        send_to = []
        if user_email:
            send_to.append(user_email)
        send_to.extend(self.m_service)
        # When something bad happened - use selected text object to fill mail subject and body:
        log.error(f'<=TASK Exception mail_log=> Selecting mail txt for: "{function.__module__}.{function.__name__}"')
        try:
            mails_txt = MailsTexts.objects.get(mail_key__contains=f'{function.__module__}.{function.__name__}')
        except ObjectDoesNotExist:
            mails_txt = MailsTexts.objects.get(mail_key__contains='general_exception')

        subject = f'Exception: {mails_txt.subject} | {curr_hostname}'
        log.debug(f"<=TASK Exception mail_log=> Selected mail subject: {subject} send to: {send_to}")
        body = f' - Body: {mails_txt.body} \n - Exception: {e} \n - Explain: {mails_txt.description}' \
               f'\n\n\t - args: {_args} \n\t - kwargs: {_kwargs}' \
               f'\n\t - key: {mails_txt.mail_key}' \
               f'\n\t - occurred in: {function.__module__}.{function.__name__}'
        TaskExceptionLog(subject=subject, details=body, user_email=send_to).save()
        Mails.short(subject=subject, body=body, send_to=send_to)

    def t_fail(self, function, err, *args, **kwargs):
        log.error("<=Task helpers=> %s", '({}) : ({}) Task failed!'.format(curr_hostname, function.__name__))
        task_limit = loader.get_template('service/emails/statuses/task_details.html')
        # Try to get user email if present:
        user_email = kwargs.get('user_email', self.m_service)

        subj_txt = '{} - Task Failed - {}'.format(curr_hostname, function.__name__)

        task_details = dict(task_args=args,
                            task_kwargs=kwargs,
                            task=function.__name__,
                            module=function.__module__,
                            err=err)

        mail_details = dict(SUBJECT=subj_txt, TASK_DETAILS=task_details)
        mail_html = task_limit.render(mail_details)
        Mails.short(mail_html=mail_html, subject=subj_txt, send_to=user_email)
