"""
Task executor
"""
import os
from octo.helpers.tasks_helpers import exception
from octo.tasks import TSupport

# Python logger
import logging
log = logging.getLogger("octo.octologger")



class Runner:

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
        # from octo.tasks import TSupport
        # Debug and test options:
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

        # Show debug messages:
        if to_debug:
            log.debug("<=Runner Fire Task=> REAL DEBUG: About to fire a task %s", task.name)

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

        # Do not really send a task if fake=True
        if not fake_run:
            return task.apply_async(**task_options)
        else:
            to_sleep = kwargs.get('to_sleep', 10)
            log.debug("<=Runner Fire Task=> FAKE: About to fire a task Name %s", task.name)
            log.debug("<=Runner Fire Task=> FAKE: Task passed arguments: \n\t\t t_queue=%s \n\t\t t_args=%s \n\t\t t_kwargs=%s "
                      "\n\t\t t_routing_key=%s", t_queue, t_args, t_kwargs, t_routing_key)
            if not os.name == 'nt':
                return TSupport.fake_task.apply_async(
                    args=['fire_t', to_sleep], kwargs=dict(t_args=t_args, t_kwargs=t_kwargs), queue=t_queue, routing_key=t_routing_key)
            else:
                log.warning('fake_task on WIn')
                return TSupport.fake_task.apply_async(
                    args=['fire_t', to_sleep], kwargs=dict(t_args=t_args, t_kwargs=t_kwargs), queue=t_queue, routing_key=t_routing_key)

    @staticmethod
    @exception
    def fire_case(case, **kwargs):
        """
        Execute routine case passed as argument.
        Use for fake, debug or usual executions.
        :param case:
        :param kwargs:
        :return:
        """
        # Debug and test options:
        fake_run = kwargs.get('fake_run', False)
        to_debug = kwargs.get('to_debug', False)
        # Real case kwargs:
        c_kwargs = kwargs.get('c_kwargs', {})

        # Show debug messages:
        if to_debug:
            log.debug("<=Runner=> REAL DEBUG: About to fire a case %s", case.__name__)

        if not fake_run:
            return case(**c_kwargs)
        else:
            log.debug("<=PatternRoutineCases=> FAKE: About to fire a function (CASE) %s", case.__name__)
            return True
