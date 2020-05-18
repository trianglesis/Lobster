"""
Decorator and helpers for tasks, like:
- send emails on start/finish
- fix errors
- parse outputs, etc

"""
import os
import sys
import datetime
import traceback

from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
import functools
from time import sleep
from collections import OrderedDict

from django.template import loader
from django.conf import settings
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from billiard.exceptions import WorkerLostError

import octo.config_cred as conf_cred
from octo import settings

from octo.helpers.tasks_mail_send import Mails
from run_core.models import Options, MailsTexts, TestOutputs
from octo_tku_patterns.models import TestLast
from octo_tku_patterns.model_views import TestLatestDigestAll

import json
from pprint import pformat, pprint

from octo.win_settings import SITE_DOMAIN, SITE_SHORT_NAME

# Python logger
import logging
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
            log.error("Unusual task exception! Check mail or logs for more info.")
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
            try:
                item_sort = json.dumps(error_d, indent=2, ensure_ascii=False, default=pformat)
                log.error("Task Exception: %s", item_sort)
            except TypeError:
                log.error("Task Exception: %s", error_d)
            if conf_cred.DEV_HOST not in settings.CURR_HOSTNAME:
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
        log.debug(f"Selected mail subject: {subject}")
        body = f' - Body: {mails_txt.body} \n - Exception: {e} \n - Explain: {mails_txt.description}' \
               f'\n\n\t - args: {_args} \n\t - kwargs: {_kwargs}' \
               f'\n\t - key: {mails_txt.mail_key}' \
               f'\n\t - occurred in: {function.__module__}.{function.__name__}'

        Mails.short(subject=subject, body=body, send_to=[user_email], send_cc=[self.m_service])
        kwargs_d = dict(
            option_key=f'{function.__module__}.{function.__name__}',
            option_value=e,
            description=f'{mails_txt.subject} \n\t args: {_args} \n\t kwargs: {_kwargs}',
        )
        log.error(kwargs_d)
        test_out = TestOutputs(**kwargs_d)
        test_out.save()

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
                        send_cc=mail_kwargs.get('send_cc', self.m_night),
                        mail_html=mail_html)
        else:
            return mail_html

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

        mail_details = dict(SUBJECT = subj_txt, TASK_DETAILS=task_details)
        mail_html = task_limit.render(mail_details)
        Mails.short(mail_html=mail_html, subject=subj_txt, send_to=user_email, send_cc=self.m_service)

    def user_test(self, mail_opts):
        test_added = loader.get_template('service/emails/statuses/test_added.html')
        mode = mail_opts.get('mode')  # Mode decision
        request = mail_opts.get('request')  # Initial stage
        test_item = mail_opts.get('test_item')  # When test are sorted and prepared
        user_email = mail_opts.get('user_email')

        # When run-finish a single test case: show it'a attributes.
        # Pattern related case has one set of attrs, py case - another:
        subject_str = 'Placeholder'
        if mode == 'start' or mode == 'finish':
            if test_item['tkn_branch']:
                subject_str = f'{test_item["tkn_branch"]} | ' \
                              f'{test_item["pattern_library"]} | ' \
                              f'{test_item["pattern_folder_name"]} '
            else:
                subject_str = f'{test_item["test_py_path_template"]} '

        tests_digest = []
        if mode == 'finish':
            # TODO: Select addm digest for test case and last test results
            tests_digest = TestLatestDigestAll.objects.filter(test_py_path__exact=test_item['test_py_path']).order_by('-addm_name').distinct()
            log.info(f"Test results selected by: {test_item['test_py_path']} are {tests_digest}")

        # Cases can be selected by attribute names, last days, date from or by id
        # Depending on those options - compose different subjects for 'init' mail
        if request.get('cases_ids', False):
            init_subject = f'selected cases id: {request.get("cases_ids", None)}'
        else:
            init_subject = f'run custom.'

        # Compose mail mode context:
        mode_context = dict(
            # This stage is when routine only starts
            # TODO: Add more information, select some pattern so show details of it.
            init=dict(
                subject=f'[{SITE_SHORT_NAME}] User test init: {init_subject}',
            ),
            # This stage is when routine prepare task to run
            start=dict(
                subject=f'[{SITE_SHORT_NAME}] User test started: {subject_str}'
            ),
            # This stage is when routine added task and finish loop step
            finish=dict(
                subject=f'[{SITE_SHORT_NAME}] User test finished: {subject_str}'
            ),
            # This stage is when routine had any issues
            fail=dict(
                subject=f'[{SITE_SHORT_NAME}] User test failed: : {init_subject}',
            ),
        )
        # send_cc = [mails['admin', ]
        mail_html = test_added.render(
            dict(
                subject=mode_context[mode].get('subject'),
                domain=SITE_DOMAIN,
                mail_opts=mail_opts,
                tests_digest=tests_digest,
            )
        )
        Mails.short(subject=mode_context[mode].get('subject'),
                    send_to=[user_email],
                    send_cc=mail_opts.get('send_cc', self.m_user_test),
                    mail_html=mail_html)
        return mail_html
