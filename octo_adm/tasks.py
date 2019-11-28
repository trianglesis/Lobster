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
from time import time

from octo.octo_celery import app
from octo.config_cred import mails
from run_core.addm_operations import ADDMOperations, ADDMStaticOperations

from octo.helpers.tasks_mail_send import Mails
from octo.helpers.tasks_helpers import exception

from octo.helpers.tasks_run import Runner


log = logging.getLogger("octo.octologger")

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
class TaskADDMService:

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TaskADDMService.t_routine_clean_addm',
              soft_time_limit=MIN_40, task_time_limit=MIN_90)
    @exception
    def t_routine_clean_addm(t_tag, **kwargs):
        """
        kwargs:
            - mode: weekly, daily, tests
            - addm_group_arg: addm group string, later split on list
            optional:
            - subject: short description
            - user_name: who run this
            - user_mail: who run this or cron

        :type t_tag: str
        :type kwargs: dict
        :return:
        """
        return ADDMCases().clean_addm(**kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TaskADDMService.t_routine_addm_cmd',
              soft_time_limit=MIN_40, task_time_limit=MIN_90)
    @exception
    def t_routine_addm_cmd(t_tag, **kwargs):
        """
        kwargs:
            - cmd_k: key of the command to run. ref: ADDMOperations.cmd_d
            - addm_group_arg: addm group string, later split on list
            optional:
            - subject: short description
            - user_name: who run this
            - user_mail: who run this or cron

        :type t_tag: str
        :type kwargs: dict
        :return:
        """
        # log.debug("<=t_routine_addm_cmd> Running task t_routine_addm_cmd")
        return ADDMCases().addm_cmd(**kwargs)

    @staticmethod
    @app.task(soft_time_limit=MIN_40, task_time_limit=HOURS_1)
    @exception
    def t_addm_clean(t_tag, **kwargs):
        """
        Check passed addm group or groups
        Add occupy worker task for each
        Get addm groups list and next add clean task for each

        kwargs:
            - mode: weekly, daily, tests
            - subject: short description
            - user_name: who run this
            - user_mail: who run this or cron
            - addm_group_arg: addm group string, later split on list

        :type t_tag: str
        :param kwargs: KV pairs of args
        :return:
        """
        return AddmClean().threading_exec(AddmClean().cleanup_case, **kwargs)

    @staticmethod
    @app.task(soft_time_limit=MIN_40, task_time_limit=HOURS_1)
    @exception
    def t_addm_cmd_k(t_tag, **kwargs):
        """
        Check passed addm group or groups
        Add occupy worker task for each
        Get addm groups list and next add clean task for each

        kwargs:
            - cmd_k: key of the command to run. ref: ADDMOperations.cmd_d
            - addm_group_arg: addm group string, later split on list

        :type t_tag: str
        :param kwargs: KV pairs of args
        :return:
        """
        return AddmClean().threading_exec(AddmClean().key_cmd, **kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2',
              routing_key='routines.TaskADDMService.t_addm_cmd_routine',
              soft_time_limit=MIN_40, task_time_limit=HOURS_1)
    @exception
    def t_addm_cmd_routine(t_tag, **kwargs):
        default = {"command_key": "show_addm_version", "addm_group": ["alpha"]}
        log.info("TaskADDMService.t_addm_cmd_routine: %s", t_tag)
        return ADDMStaticOperations().run_operation_cmd(**kwargs)

    @staticmethod
    @app.task(soft_time_limit=MIN_40, task_time_limit=HOURS_1)
    @exception
    def t_addm_cmd_thread(t_tag, **kwargs):
        return ADDMStaticOperations().threaded_exec_cmd(**kwargs)


class ADDMCases:
    """
    Usual routines based on cases:

    """

    @staticmethod
    def addm_groups_validate(**kwargs):
        """
        Complete initial checks of workers health and availability and exec busy tasks.
        :param kwargs:
        :return:
        """
        import os
        from octo.tasks import TSupport
        from octo.helpers.tasks_oper import WorkerOperations

        addm_group_l = kwargs.get('addm_group', [])
        user_name = kwargs.get('user_name', 'cron')
        fake_run = kwargs.get('fake_run', False)
        occupy_sec = kwargs.get('occupy_sec', 40)

        t_tag = f'tag=addm_groups_validate;type=routine;user_name={user_name}'
        if not isinstance(addm_group_l, list):
            addm_group_l = addm_group_l.split(',')

        if isinstance(addm_group_l, list):
            ping_list = WorkerOperations().service_workers_list[:]
            for _worker in addm_group_l:
                if "@tentacle" not in _worker:
                    _worker = f"{_worker}@tentacle"
                ping_list.append(_worker)
            worker_up = WorkerOperations().worker_heartbeat(worker_list=ping_list)
            if worker_up.get('down'):
                log.error("Some workers may be down: %s - sending email!", worker_up)
                subject = f'Worker is down, cannot run all other tasks. W: {worker_up}'
                body = f'Found some workers are DOWN while run (addm_groups_validate) List: {worker_up}'
                admin = mails['admin']
                Mails.short(subject=subject, body=body, send_to=[admin])
                # Nothing else to do here.
                raise Exception(subject)
            else:
                for addm_group in addm_group_l:
                    occupy_sec += 1
                    t_tag_busy = f"{t_tag} | sleep {occupy_sec} Check addm group."
                    addm_val_kw = dict(occupy_sec=occupy_sec, addm_group=addm_group,
                                       ping_list=ping_list, user_name=user_name)
                    Runner.fire_t(TSupport.t_occupy_w, fake_run=fake_run,
                                  t_args=[t_tag_busy, occupy_sec],
                                  t_kwargs=addm_val_kw,
                                  t_queue=f'{addm_group}@tentacle.dq2',
                                  t_routing_key = f'{addm_group}.t_occupy_w')
                return addm_group_l

    def clean_addm(self, **kwargs):
        """
        Check passed addm group or groups
        Add occupy worker task for each
        Get addm groups list and next add clean task for each

        kwargs:
            - mode: weekly, daily, tests
            - subject: short description
            - user_name: who run this
            - user_mail: who run this or cron
            - addm_group_arg: addm group string, later split on list

        :param kwargs: KV pairs of args
        :return:
        """
        mode = kwargs.get('mode')  # type: str
        subject = kwargs.get('subject', 'Running: t_routine_clean_addm')  # type: str
        user_name = kwargs.get('user_name', 'cron')  # type: str
        user_mail = kwargs.get('user_mail', [])  # type: str
        addm_group = kwargs.get('addm_group', [])  # type: list
        fake_run = kwargs.get('fake_run', False)

        Mails.short(subject=subject, body=subject, send_to=[user_mail])

        _addm_groups = []
        addm_set = ADDMOperations.select_addm_set(addm_group=addm_group)
        for addm_ in addm_set.values('addm_group').distinct():
            _addm_groups.append(addm_.get('addm_group'))

        tasks_ids = dict()
        addm_group_l = self.addm_groups_validate(addm_group=_addm_groups)  # type: list
        log.debug("addm_group_l: %s", addm_group_l)
        for addm_group in addm_group_l:
            t_tag = f'tag=addm_cleanup;user_name={user_name};mode={mode};addm={addm_group}'
            task = Runner.fire_t(TaskADDMService.t_addm_clean, fake_run=fake_run,
                                 t_args=[t_tag],
                                 t_kwargs=dict(info_string=subject, addm_group=addm_group, mode=mode),
                                 t_queue=f'{addm_group}@tentacle.dq2',
                                 t_routing_key=f'{addm_group}.t_addm_clean.{mode}'
                                 )
            tasks_ids.update({addm_group: task.id})
        return tasks_ids

    def addm_cmd(self, **kwargs):
        """
        Check passed addm group or groups
        Add occupy worker task for each
        Get addm groups list and next add clean task for each

        kwargs:
            - cmd_k: key of the command to run. ref: ADDMOperations.cmd_d
            - subject: short description
            - user_name: who run this
            - user_mail: who run this or cron
            - addm_group_arg: addm group string, later split on list

        :param kwargs: KV pairs of args
        :return:
        """
        cmd_k = kwargs.get('cmd_k')  # type: str
        subject = kwargs.get('subject', 'Running: t_routine_addm_cmd')  # type: str
        user_name = kwargs.get('user_name', 'cron')  # type: str
        user_mail = kwargs.get('user_mail', [])  # type: str
        addm_group = kwargs.get('addm_group', [])  # type: list
        fake_run = kwargs.get('fake_run', False)
        log.debug("<=addm_cmd=> kwargs %s", kwargs)

        if not user_name == 'cron':
            Mails.short(subject=subject, body=subject, send_to=[user_mail])

        _addm_groups = []
        addm_set = ADDMOperations.select_addm_set(addm_group=addm_group)
        for addm_ in addm_set.values('addm_group').distinct():
            _addm_groups.append(addm_.get('addm_group'))

        tasks_ids = dict()
        addm_group_l = self.addm_groups_validate(addm_group=_addm_groups)  # type: list
        for addm_group in addm_group_l:
            t_tag = f'tag=t_addm_cmd_k;type=task;user_name={user_name};' \
                    f'addm_group={addm_group};cmd_k={cmd_k}| on: "{addm_group}" by: {user_name}'
            t_kwargs = dict(info_string=subject, addm_group=addm_group, cmd_k=cmd_k)
            task = Runner.fire_t(TaskADDMService.t_addm_cmd_k, fake_run=fake_run,
                                 t_queue=f'{addm_group}@tentacle.dq2',
                                 t_args=[t_tag],
                                 t_kwargs=t_kwargs,
                                 t_routing_key=f'{addm_group}.addm_custom_cmd'
                                 )
            log.debug("<=addm_cmd=> Added task: %s", task)
            tasks_ids.update({addm_group: task.id})
        return tasks_ids

    def addm_sync_shares(self, **kwargs):
        from octo_tku_patterns.tasks import TPatternParse
        subject = kwargs.get('subject', 'Running: addm_sync_shares')  # type: str
        user_name = kwargs.get('user_name', 'cron')  # type: str
        user_mail = kwargs.get('user_mail', [])  # type: str
        addm_group = kwargs.get('addm_group', [])  # type: list
        fake_run = kwargs.get('fake_run', False)
        log.debug("<=addm_cmd=> kwargs %s", kwargs)

        if not user_name == 'cron':
            Mails.short(subject=subject, body=subject, send_to=[user_mail])

        _addm_groups = []
        addm_prep_groups = ADDMOperations.select_addm_set(addm_group=addm_group)
        for addm_ in addm_prep_groups.values('addm_group').distinct():
            _addm_groups.append(addm_.get('addm_group'))

        tasks_ids = dict()
        addm_group_l = self.addm_groups_validate(addm_group=_addm_groups)  # type: list
        for addm_group in addm_group_l:
            addm_set = ADDMOperations.select_addm_set(addm_group=addm_group)
            t_tag = f'tag=t_addm_rsync_threads;addm_group={addm_group};user_name={user_name};fake={fake_run};'
            # TODO: Check on live env
            t_addm_rsync_threads = Runner.fire_t(TPatternParse().t_addm_rsync_threads, fake_run=fake_run,
                                                 t_args=[t_tag], t_kwargs=dict(addm_items=addm_set),
                                                 t_queue=f'{addm_group}@tentacle.dq2',
                                                 t_routing_key=f'TExecTest.t_addm_rsync_threads.{addm_group}')
            tasks_ids.update({addm_group: t_addm_rsync_threads.id})
        return tasks_ids


class AddmClean:

    def __init__(self):
        """
        Better init addm items in routine and then use for each case.
        """
        # TODO: Move it to DB - so we can change keys without app restart
        self.addm_weekly_cleanup_options = ['tw_scan_control',
                                            'test_kill',
                                            'wipe_tpl',
                                            'wipe_log',
                                            'wipe_sync_log',
                                            'wipe_syslog',
                                            'tw_pattern_management',
                                            'wipe_pool',
                                            'wipe_record',
                                            'tw_model_wipe',
                                            # 'tw_tax_import',  # Do not import taxonomy - better install product content
                                            'tideway_restart']

        self.daily_cleanup_options = ['tw_scan_control',
                                      'test_kill',
                                      'wipe_tpl',
                                      'wipe_log',
                                      'wipe_sync_log',
                                      'wipe_syslog',
                                      'tw_pattern_management',
                                      'wipe_pool',
                                      'wipe_record',
                                      # 'tw_tax_import',  # Do not import taxonomy - better install product content
                                      'tideway_restart']

        self.clean_test_options = ['tw_scan_control',
                                   'test_kill',
                                   'wipe_tpl',
                                   'wipe_log',
                                   'wipe_sync_log',
                                   'wipe_syslog',
                                   'tw_pattern_management',
                                   'wipe_pool',
                                   'wipe_record']

    @staticmethod
    def threading_exec(func_target, **kwargs):
        # noinspection PyCompatibility
        from queue import Queue
        from threading import Thread

        mode = kwargs.get('mode', None)
        addm_group = kwargs.get('addm_group')
        cmd_k = kwargs.get('cmd_k', None)

        thread_list = []
        test_outputs = []
        ts = time()
        out_q = Queue()

        addm_set = ADDMOperations.select_addm_set(addm_group=addm_group)
        for addm_item in addm_set:
            ssh = ADDMOperations().ssh_c(addm_item=addm_item, where="Executed from threading_exec")
            if ssh:
                th_name = 'Addm clean thread: {} - {} {}'.format(addm_group, addm_item['addm_host'], addm_item['addm_ip'])
                args_d = dict(ssh=ssh, addm_item=addm_item, out_q=out_q, cmd_k=cmd_k, mode=mode)
                try:
                    test_thread = Thread(target=func_target, name=th_name, kwargs=args_d)
                    test_thread.start()
                    thread_list.append(test_thread)
                except Exception as e:
                    msg = "Thread test fail with error: {}".format(e)
                    log.error(msg)
                    raise Exception(msg)
            else:
                msg = "SSH Connection died! Addm: {}".format(addm_item)
                log.error(msg)
                raise Exception(msg)
        for test_th in thread_list:
            test_th.join()
            test_outputs.append(out_q.get())

        return 'All CMD took {} Out {}'.format(time() - ts, test_outputs)

    @staticmethod
    def key_cmd(**kwargs):
        out_q = kwargs.get('out_q')
        output = ADDMOperations().addm_exec_cmd(ssh=kwargs.get('ssh'),
                                                addm_item=kwargs.get('addm_item'),
                                                cmd_k=kwargs.get('cmd_k'))
        log.debug('key_cmd -> output: %s', output)
        out_q.put(output)

    def cleanup_case(self, **kwargs):
        out_q = kwargs.get('out_q')
        addm_item = kwargs.get('addm_item')
        ssh = kwargs.get('ssh')

        mode = kwargs.get('mode')
        if mode == 'weekly':
            cmd_keys = self.addm_weekly_cleanup_options
        elif mode == 'daily':
            cmd_keys = self.daily_cleanup_options
        elif mode == 'tests':
            cmd_keys = self.clean_test_options
        else:
            cmd_keys = self.clean_test_options

        cmd_outputs = []
        for cmd_k in cmd_keys:
            output = ADDMOperations().addm_exec_cmd(ssh=ssh, addm_item=addm_item, cmd_k=cmd_k)
            cmd_outputs.append(output)
        out_q.put(cmd_outputs)
