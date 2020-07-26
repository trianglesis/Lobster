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
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.template import loader
from django.utils import timezone

from octo.helpers.tasks_mail_send import Mails
from octo.settings import SITE_DOMAIN, SITE_SHORT_NAME
from octo_tku_patterns.model_views import TestLatestDigestAll
from octo_tku_patterns.models import TestLast, TestCases
from run_core.models import Options, MailsTexts, TestOutputs, RoutinesLog, ServicesLog

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
                log.error(f"Task Exception: {e}")
            except TypeError:
                log.error(f"Task Exception: {error_d}")
            if settings.DEV:
                log.info(
                    f'Exceptions into DEV mode {settings.DEV}: do not send mail log on task fail! {function} {exc_more} {args} {kwargs}')
                TMail().mail_log(function, exc_more, _args=args, _kwargs=kwargs)
            raise Exception(e)

    return wrapper


def db_logger(function):
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        if settings.DEV:
            log.debug(f'DB Logger task {function.__name__} opts: {args}, {kwargs}')
        start = datetime.datetime.now(tz=timezone.utc)
        opt_kwargs = {
            'task_name': f'{function.__name__}',
            'user': 'task_wrapper',
            't_args': args,
            't_kwargs': kwargs,
            't_start_time': start,
            'description': f'{function.__doc__}',
        }
        run = function(*args, **kwargs)
        finish = datetime.datetime.now(tz=timezone.utc)
        est = finish - start
        opt_kwargs.update(
            t_finish_time=finish,
            t_est_time=est
        )
        routine_log = RoutinesLog(**opt_kwargs)
        routine_log.save()
        return run
    return wrapper


def db_log_f(option=None):
    def decorator(function):
        if settings.DEV:
            log.debug(f"<=db_log_f=> {function}")
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            if settings.DEV:
                log.debug(f'DB Logger function {function.__name__} opts: {args}, {kwargs}')
            start = datetime.datetime.now(tz=timezone.utc)
            opt_kwargs = {
                'task_name': f'{function.__name__}',
                'user': 'function_wrapper',
                't_args': args,
                't_kwargs': kwargs,
                't_start_time': start,
                'description': f'{function.__doc__}',
            }
            run = function(*args, **kwargs)
            finish = datetime.datetime.now(tz=timezone.utc)
            est = finish - start
            opt_kwargs.update(
                t_finish_time=finish,
                t_est_time=est
            )
            routine_log = RoutinesLog(**opt_kwargs)
            routine_log.save()
            return run
        return wrapper
    return decorator


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
        user_email = _kwargs.get('user_email', None)
        if not user_email:
            request = _kwargs.get('request', None)
            if request:
                user_email = request.get('user_email', self.m_service)

        # When something bad happened - use selected text object to fill mail subject and body:
        log.error(f'<=TASK Exception=> Selecting mail txt for: "{function.__module__}.{function.__name__}"')

        try:
            mails_txt = MailsTexts.objects.get(mail_key__contains=f'{function.__module__}.{function.__name__}')
        except ObjectDoesNotExist:
            mails_txt = MailsTexts.objects.get(mail_key__contains='general_exception')

        subject = f'Exception: {mails_txt.subject} | {curr_hostname}'
        log.debug(f"Selected mail subject: {subject} send to: {user_email}")
        body = f' - Body: {mails_txt.body} \n - Exception: {e} \n - Explain: {mails_txt.description}' \
               f'\n\n\t - args: {_args} \n\t - kwargs: {_kwargs}' \
               f'\n\t - key: {mails_txt.mail_key}' \
               f'\n\t - occurred in: {function.__module__}.{function.__name__}'

        Mails.short(subject=subject, body=body, send_to=[user_email])

    def long_r(self, **mail_kwargs):
        """
        Send email with task status and details:
        - what task, name, args;
        - when started, added to queue, finished
        - which status have
        - etc.

        :return:
        """
        mode = mail_kwargs.get('mode')
        r_type = mail_kwargs.get('r_type', 'Custom')
        send = mail_kwargs.get('send', True)
        branch = mail_kwargs.get('branch')
        start_time = mail_kwargs.get('start_time')
        addm_group = mail_kwargs.get('addm_group')  # Initially selected from request

        routine_mail = loader.get_template('service/emails/routines_mail.html')
        msg_str = "{addm_group}; branch:{branch}".format(addm_group=addm_group, branch=branch)
        mail_details = dict(SUBJECT='SUBJECT',
                            START_TIME=start_time,
                            TIME_SPENT='Should be a time when test were finished',
                            MAIL_KWARGS=mail_kwargs)
        if mode == "start":
            mail_details.update(
                SUBJECT="0. {type} routine - manual - {msg}".format(type=r_type, msg=msg_str),
                START_TIME=start_time,
                START_ARGS=mail_kwargs.get('start_args'))
        elif mode == "run":
            mail_details.update(
                SUBJECT="1. {type} routine - started - {msg}".format(type=r_type, msg=msg_str),
                START_TIME=start_time,
                EXTRA_ARGS=mail_kwargs.get('extra_args'))
        elif mode == "fin":
            mail_details.update(
                SUBJECT="2. {type} routine - finished - {msg}".format(type=r_type, msg=msg_str),
                START_TIME=start_time,
                FINISH_TIME=datetime.datetime.now(tz=timezone.utc),
                TIME_SPENT=datetime.datetime.now(tz=timezone.utc) - start_time,
                EXTRA_ARGS=mail_kwargs.get('extra_args'))
        # Send mail
        mail_html = routine_mail.render(mail_details)
        if send:
            sleep(5)
            Mails.short(subject=mail_details.get('SUBJECT'),
                        send_to=mail_kwargs.get('user_email', self.m_night),
                        mail_html=mail_html)
        else:
            return 'Long mail sent!'

        log_kwargs = dict(
            task_name='NightRoutine',
            user='OctoTest',
            description='Night test routine finishing email.',
            t_kwargs=mail_kwargs,
            input=mail_details,
            t_finish_time=datetime.datetime.now(tz=timezone.utc),
            t_est_time=datetime.datetime.now(tz=timezone.utc) - start_time,
        )
        service_log = ServicesLog(**log_kwargs)
        service_log.save()

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

