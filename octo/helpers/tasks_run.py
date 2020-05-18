"""
Task executor
"""
from octo.helpers.tasks_helpers import exception
from octo.tasks import TSupport
from octo.helpers.tasks_oper import TasksOperations

import octo.config_cred as conf_cred
from octo import settings

# Python logger
import logging
log = logging.getLogger("octo.octologger")


class Runner:

    @staticmethod
    def check_task_added():
        all_tasks = []
        active_reserved = TasksOperations.tasks_get_active_reserved()
        active = active_reserved.get('active')
        reserved = active_reserved.get('reserved')
        if active:
            for _, val in active.items():
                if val:
                    all_tasks.append(val)
        if reserved:
            for _, val in reserved.items():
                if val:
                    all_tasks.append(val)
        log.debug("All active and reserved tasks to check: %s", all_tasks)
        return all_tasks

    @staticmethod
    @exception
    def fire_t(task, **kwargs):
        """
        This method will execute task object.
        Based on kwargs
        - will execute task in usual manner.
        - will show debug info or simulate task execution with fake task with sleep timer.
        :param task:
        :param kwargs:
        :return:
        """
        fake_run = kwargs.get('fake_run', False)
        to_debug = kwargs.get('to_debug', False)

        this_t = 'FireTasks.fire_t.{}'.format(task.__name__)
        # Task related options:
        t_args = kwargs.get('t_args', [this_t])
        t_kwargs = kwargs.get('t_kwargs', {})
        t_queue = kwargs.get('t_queue', None)
        t_routing_key = kwargs.get('t_routing_key', this_t)
        t_soft_time_limit = kwargs.get('t_soft_time_limit', None)
        t_task_time_limit = kwargs.get('t_task_time_limit', None)

        task_options = dict()
        if t_args:
            task_options.update(args=t_args)
        if t_kwargs:
            task_options.update(kwargs=t_kwargs)
        if t_queue:
            task_options.update(queue=t_queue)
        if t_routing_key:
            task_options.update(routing_key=t_routing_key)
        if t_soft_time_limit:
            task_options.update(soft_time_limit=t_soft_time_limit)
        if t_task_time_limit:
            task_options.update(task_time_limit=t_task_time_limit)

        # TODO: Overriding on local
        # if conf_cred.DEV_HOST in settings.CURR_HOSTNAME:
        #     fake_run = True

        # Do not really send a task if fake=True
        if not fake_run:
            return task.apply_async(**task_options)
        else:
            to_sleep = kwargs.get('to_sleep', 10)
            task_options.update(to_sleep=to_sleep, to_debug=to_debug)
            return TSupport.fake_task.apply_async(
                args=[f'Fake task run: t_args: {t_args}; sleep {to_sleep}; debug {to_debug}'],
                kwargs=task_options,
                queue=t_queue,
                routing_key=t_routing_key,
                soft_time_limit=t_soft_time_limit,
                task_time_limit=t_task_time_limit,
            )
