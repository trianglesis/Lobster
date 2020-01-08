"""
Decorator and helpers for tasks, like:
- send emails on start/finish
- fix errors
- parse outputs, etc

"""
import os
import datetime
from django.utils import timezone
import functools
from time import sleep
from collections import OrderedDict

from django.template import loader
from django.conf import settings
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from billiard.exceptions import WorkerLostError
from octo.helpers.tasks_mail_send import Mails
from run_core.models import Options

import json
from pprint import pformat, pprint

from octo.win_settings import SITE_DOMAIN, SITE_SHORT_NAME

# Python logger
import logging
log = logging.getLogger("octo.octologger")
curr_hostname = getattr(settings, 'CURR_HOSTNAME', None)


def exception(function):
    """
    A decorator that wraps the passed in function and logs
    exceptions should one occur
    """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        # Messages for fails
        MSG_T = '<=Time Limit=> {} Task cancelled! Time limit exceeded. {}.{}'
        MSG_T_SOFT = '<=Soft Time Limit=> {} Task soft time limit exceeded. {}.{}'
        MSG_FAIL = '<=TestExecTasks=> Task fail "{}.{}" ! Error output: {}'

        try:
            return function(*args, **kwargs)
        except SoftTimeLimitExceeded:
            log.error("Task SoftTimeLimitExceeded: %s", (function, args, kwargs))
            msg = MSG_T_SOFT.format(curr_hostname, function.__module__, function.__name__)
            TMail().t_lim(msg, function, *args, **kwargs)
            # Do not rise when soft time limit, just inform:
            # raise SoftTimeLimitExceeded(msg)
        except TimeLimitExceeded:
            log.error("Task TimeLimitExceeded: %s", (function, args, kwargs))
            msg = MSG_T.format(curr_hostname, function.__module__, function.__name__)
            TMail().t_lim(msg, function, *args, **kwargs)
            # Raise when task goes out of a latest time limit:
            raise SoftTimeLimitExceeded(msg)
        except WorkerLostError as e:
            log.error("Task WorkerLostError: %s", (function, e, args, kwargs))
            TMail().t_fail(function, e, *args, **kwargs)
            raise Exception(MSG_FAIL.format(function.__module__, function.__name__, e))
        except Exception as e:
            error_d = dict(
                function=function,
                error=e,
                args=args,
                kwargs=kwargs,
            )
            item_sort = json.dumps(error_d, indent=2, ensure_ascii=False, default=pformat)
            log.error("Task Exception: %s", item_sort)
            if not os.name == 'nt':
                TMail().t_fail(function, e, *args, **kwargs)
            raise Exception(MSG_FAIL.format(function.__module__, function.__name__, e))
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

    def upload_t(self, send=True, **mail_kwargs):
        stage = mail_kwargs.get('stage')
        start_time = mail_kwargs.get('start_time')
        mode = mail_kwargs.get('mode', None)
        tku_type = mail_kwargs.get('tku_type', None)
        addm_group = mail_kwargs.get('addm_group', None)

        upload_test_addm = loader.get_template('service/emails/upload_test.html')
        msg_str = "mode: {mode} tku: {tku_type} group: {addm_group}".format(
            mode=mode, tku_type=tku_type, addm_group=addm_group)

        mail_details = dict(SUBJECT='Upload test were lost in nowhere!',
                            START_TIME='This is the time when upload test were started.',
                            TIME_SPENT='Should be a time when test were finished',
                            CURR_HOSTNAME=curr_hostname,
                            MAIL_DETAILS=dict(USER_EMAIL=mail_kwargs.get('user_email'),
                                              STAGE=stage,
                                              MODE=mode,
                                              TKU_TYPE=tku_type,
                                              START_TIME=start_time))

        if stage == 'added':
            mail_details.update(SUBJECT    = "1. Upload test initiated - {msg}".format(msg = msg_str),
                                TKU_WGET   = mail_kwargs.get('tku_wget'),
                                ADDM_GROUP = mail_kwargs.get('addm_group'),
                                USER_NAME  = mail_kwargs.get('user_name'),
                                t_tag   = mail_kwargs.get('t_tag', 'no tag'),
                                START_TIME = start_time)
        elif stage == 'started':
            mail_details.update(SUBJECT    = "2.1 Upload test started - {msg}".format(msg = msg_str),
                                TKU_WGET   = mail_kwargs.get('tku_wget'),
                                START_TIME = start_time)
        elif stage == 'tku_install':
            mail_details.update(SUBJECT    = "2.2 Upload test TKU install - {msg}".format(msg = msg_str),
                                TKU_WGET   = mail_kwargs.get('tku_wget'),
                                t_tag   = mail_kwargs.get('t_tag', 'no tag'),
                                START_TIME = start_time)
        elif stage == 'running':
            # TODO: Add link to test results and link to ADDM UI TKU Page from mail body
            addm_item = mail_kwargs.get('addm_item')
            addm_name = addm_item.get('addm_name')
            finish_time_format = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            time_stamp = datetime.datetime.now() - start_time
            detail_kwargs = mail_kwargs.get('kwargs')
            outputs = mail_kwargs.get('outputs')

            mail_details.update(
                SUBJECT="3.1 Upload test running, got output - {addm_name} - {msg}".format(addm_name=addm_name,
                                                                                           msg=msg_str),
                RUN_OUT=mail_kwargs.get('outputs', 'outputs empty'),
                ADDM_NAME=addm_item.get('addm_name', 'no addm_name'),
                ADDM_HOST=addm_item.get('addm_host', 'no addm_host'),
                ADDM_GROUP=addm_item.get('addm_group', 'no addm_group'),
                START_TIME=start_time,
                FINISH_TIME=finish_time_format,
                TIME_SPENT=time_stamp,
                # TODO: Save the outputs example:
                DETAIL_KWARGS=detail_kwargs,
                # TODO: Save the outputs example:
                MORE_OUTPUTS=outputs,
                )
        elif stage == 'finished':
            # TODO: Add link to test results and link to ADDM UI TKU Page from mail body
            finish_time_format = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            time_stamp = datetime.datetime.now() - start_time
            mail_details.update(SUBJECT    = "3.2 Upload test finished - {msg}".format(msg = msg_str),
                                FIN_OUT    = mail_kwargs.get('outputs'),
                                ADDM_GROUP = addm_group,
                                START_TIME = start_time,
                                FINISH_TIME = finish_time_format,
                                TIME_SPENT = time_stamp)
        else:
            mail_details.update(SUBJECT="0. Upload test has unusual status - {msg}".format(msg=msg_str), START_TIME=start_time)

        mail_html = upload_test_addm.render(mail_details)
        # log.debug("<=MailTRoutines=> mail_args: %s", mail_args)
        if send:
            sleep(5)
            Mails.short(subject=mail_details.get('SUBJECT'),
                        send_to=mail_kwargs.get('user_email', self.m_upload),
                        send_cc=mail_kwargs.get('send_cc', self.m_upload),
                        mail_html=mail_html)
        else:
            return mail_html

    def t_lim(self, msg, function, *args, **kwargs):
        log.error("<=Task Time Limit=> %s", msg)
        task_limit = loader.get_template('service/emails/statuses/task_details.html')
        # Try to get user email if present:
        user_email = kwargs.get('user_email', self.m_service)

        task_details = dict(task_args=args,
                            task_kwargs=kwargs,
                            task=function.__name__,
                            module=function.__module__)

        mail_details = dict(SUBJECT = msg, TASK_DETAILS=task_details)
        mail_html = task_limit.render(mail_details)
        Mails.short(mail_html=mail_html, subject=msg, send_to=user_email, send_cc=self.m_service)

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

        # Cases can be selected by attribute names, last days, date from or by id
        # Depending on those options - compose different subjects for 'init' mail
        if request.get('cases_ids', False):
            init_subject = f'selected cases id: {request.get("cases_ids", None)}'
        else:
            init_subject = f'run custom.'

        # Compose mail mode context:
        mode_context = dict(
            # This stage is when routine only starts
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
            )
        )
        Mails.short(subject=mode_context[mode].get('subject'),
                    send_to=[user_email],
                    send_cc=mail_opts.get('send_cc', self.m_user_test),
                    mail_html=mail_html)
        return mail_html
