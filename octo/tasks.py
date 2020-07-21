"""
Celery tasks.
All celery tasks should be collected here.
- Task should execute only separate case or case_routine.
- Task should not execute any code itself.
- Task should have exception handler which output useful data or send mail.

Note:
    - Be careful with recursive import.
    - Do not import case routines which import tasks from here.
"""
from __future__ import absolute_import, unicode_literals
import logging
from time import sleep
from django.conf import settings

from octo.helpers.tasks_helpers import exception, db_logger
from octo.helpers.tasks_mail_send import Mails
from octo.helpers.tasks_oper import WorkerOperations, TasksOperations
from octo.octo_celery import app

from run_core.db_operations import DBServicing


log = logging.getLogger("octo.octologger")
curr_hostname = getattr(settings, 'CURR_HOSTNAME', None)

"""Initialize only if reset!
app.conf.beat_schedule = {
    # Run MAIN for each working day till 20th:
    'tkn_main_workday_routine': {
        'task': 'cases.tasks_shelf.routine_tasks.tasks.night_test_executor',
        'schedule': crontab(hour=17, minute=0, day_of_week='1,2,3,4,5', day_of_month='1-19,28-31'),
        'options': {'queue': 'routines'},
        'args': ('tkn_main',),
        'kwargs': {'send_mail': True, 'sync_tku': True, 'user_name': 'cron_user'},
    },
}
"""

DAY_LIMIT = 172800
HOURS_2 = 7200
HOURS_1 = 3600
MIN_90 = 5400
MIN_40 = 2400
MIN_20 = 1200
MIN_10 = 600
MIN_1 = 60
SEC_10 = 10
SEC_1 = 1


# noinspection PyUnusedLocal
class TSupport:
    """
    Sending mails for example
    """

    @staticmethod
    @app.task(soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_short_mail(t_tag, **mail_kwargs):
        """Short mail digests task"""
        return Mails().short(**mail_kwargs)

    @staticmethod
    @app.task(soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_long_mail(t_tag, **mail_kwargs):
        """Long mail task for octo test utils"""
        from octo.helpers.tasks_helpers import TMail
        TMail().long_r(**mail_kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='TSupport.t_user_mail',
              soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @db_logger
    @exception
    def t_user_test(t_tag, **mail_opts):
        """User mail task, send mails on user test statuses: init, start, finish and test results."""
        from octo.helpers.tasks_helpers import TMail
        TMail().user_test(**mail_opts)

    @staticmethod
    @app.task(soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_occupy_w(t_tag, sleep_t, **kwargs):
        """
        Just keep worker busy when user change it.
        :return:
        """
        sleep(sleep_t)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='TSupport.fake_task',
              soft_time_limit=HOURS_2, task_time_limit=HOURS_2+900)
    # @db_logger
    @exception
    def fake_task(t_tag, **kwargs):
        """
        Show all passed args and sleep for selected time.
        :param t_tag:
        :param kwargs:
        :return:
        """
        args = kwargs.get('args')
        _kwargs = kwargs.get('kwargs')

        queue = kwargs.get('queue')
        routing_key = kwargs.get('routing_key')
        soft_time_limit = kwargs.get('soft_time_limit')
        task_time_limit = kwargs.get('task_time_limit')

        to_sleep = kwargs.get('to_sleep')
        to_debug = kwargs.get('to_debug')

        msg = ''
        if to_debug:
            msg = f'Args: {args} \n\tKwargs: {_kwargs}'
        log.info(f"<=Fake Task=> Start.\n\tRunning task: \n\t{routing_key}\n\tqueue: {queue}\n\t{msg}")

        sleep(to_sleep)
        return f'<=Fake Task=> Finished work: {routing_key}, queue: {queue}.\t\tEnd.'


class TInternal:

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.test_task_heartbeat_ping_workers',
              soft_time_limit=MIN_1, task_time_limit=MIN_10)
    @exception
    def test_task_heartbeat_ping_workers(t_tag, **kwargs):
        """
        Send heartbeat and ping to all workers in system to keep them up and ready to use.
        This is necessary routine to catch the bug when worker goes down.

        :return:
        """
        log.info("t_tag: %s", t_tag)

        w_up = WorkerOperations().worker_heartbeat()

        # If result dict have a 'down' key:
        if w_up.get('down'):
            msg = '<=test_task_heartbeat_ping_workers=> Worker down: "{}"' \
                  '\nworkers_passed: {}\nworkers_resolved: {}'.format(w_up.get('down'),
                                                                      w_up.get('workers_passed'),
                                                                      w_up.get('workers_resolved'))
            raise Exception(msg)
        else:
            return 'Having workers up and running: {}'.format(w_up)

    # noinspection PyUnusedLocal,PyUnusedLocal
    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.test_task_get_worker_minimal',
              soft_time_limit=MIN_1, task_time_limit=MIN_10)
    @exception
    def test_task_get_worker_minimal(t_tag, **kwargs):
        """
        Testing and catching bug when excluded worker still present in available free workers list.
        Should be ONE free worker.
        We can compare returned worker over list of NOT excluded workers and raise when diff.

        expected_w = 'alpha,beta,charlie'
        worker_min = 'beta'

        :return:
        """
        from octo_adm.request_service import SelectorRequestsHelpers

        expected_w = kwargs.get('expected_w')
        mail_send = kwargs.get('mail_send', False)

        log.info("t_tag: %s", t_tag)
        expected_w_list = expected_w.split(",")

        # Get one minimal loaded worker:
        # worker_min_free = SelectorRequestsHelpers.get_free_included_w()
        worker_min_task = SelectorRequestsHelpers.get_free_included_w_task()
        all_workers_status = TasksOperations().check_active_reserved_short()
        log.debug("<=test_task_get_worker_minimal=> Free min worker: %s", worker_min_task)

        if worker_min_task:
            if worker_min_task not in expected_w_list:
                msg = '<=test_task_get_worker_minimal=> Returned worker "{}" is not in expected list of workers - "{}" on {}'.format(
                    worker_min_task, expected_w_list, curr_hostname)
                # Mails.short(subject='Task fail', body="{} All: {}".format(msg, all_workers_status))
                raise Exception(msg)
            else:
                return "Excluded minimum busy worker expected - OK: {}={}".format(worker_min_task, expected_w_list)
        else:
            msg = "WARNING: Excluded minimum busy worker - EMPTY: {}={}. It may be busy." \
                   "Host {}" \
                  "All workers status: {}".format(worker_min_task, expected_w_list, curr_hostname, all_workers_status)
            # if mail_send:
            #     Mails.short(subject='Expected worker could be busy:', body=msg)
            return msg

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.t_clean_history',
              soft_time_limit=MIN_90, task_time_limit=HOURS_2)
    @exception
    def t_clean_history(t_tag, **kwargs):
        log.info(f"<=t_clean_history=> {t_tag}, {kwargs}")
        DBServicing().history_clean(**kwargs)