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

from octo.helpers.tasks_run import Runner
from octo.helpers.tasks_helpers import exception

from octo.octo_celery import app
from run_core.addm_operations import ADDMStaticOperations
from run_core.models import AddmDev
from run_core.vcenter_operations import VCenterOperations

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
    @app.task(queue='w_routines@tentacle.dq2',
              routing_key='routines.TaskADDMService.t_addm_cmd_routine',
              soft_time_limit=MIN_40, task_time_limit=MIN_90)
    @exception
    def t_addm_cmd_routine(t_tag, **kwargs):
        return ADDMStaticOperations().run_operation_cmd(**kwargs)

    @staticmethod
    @app.task(soft_time_limit=HOURS_1, task_time_limit=MIN_90)
    @exception
    def t_addm_cmd_thread(t_tag, **kwargs):
        return ADDMStaticOperations().threaded_exec_cmd(**kwargs)


class TaskVMService:

    @staticmethod
    @app.task(soft_time_limit=MIN_40, task_time_limit=HOURS_1)
    @exception
    def t_vm_operation_thread(t_tag, **kwargs):
        log.info(f'Running {t_tag}')
        return VCenterOperations().threaded_operations(**kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2',
              routing_key='routines.TaskVMService.t_vm_operation_addm_groups',
              soft_time_limit=MIN_40, task_time_limit=HOURS_1)
    @exception
    def t_vm_operation_addm_groups(t_tag, **kwargs):
        fake_run = kwargs.get('fake_run', False)
        addm_groups = kwargs.get('addm_groups', '')
        operation_k = kwargs.get('operation_k', 'vm_power_off')
        log.info(f'Running {t_tag}')

        if isinstance(addm_groups, str):
            addm_groups = addm_groups.split(',')
        elif isinstance(addm_groups, list):
            pass
        else:
            log.error("Addm group should be a list or str!")
            return False

        for addm_group in addm_groups:
            addm_set = AddmDev.objects.filter(addm_group__exact=addm_group)
            Runner.fire_t(TaskVMService.t_vm_operation_thread,
                          fake_run=fake_run,
                          t_queue=f"{addm_group}@tentacle.dq2",
                          t_args=[f"TaskVMService;task=t_vm_power_off_addm_groups;operation_k={operation_k}"],
                          t_kwargs=dict(addm_set=addm_set, operation_k=operation_k),
                          t_routing_key=f"{addm_group}.TaskVMService.t_vm_operation_thread.{operation_k}")
