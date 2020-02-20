"""
Task executor
"""
import octo.config_cred as conf_cred
from octo import settings
from octo.helpers.tasks_helpers import exception
from octo.tasks import TSupport
from octo.helpers.tasks_oper import TasksOperations

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
            log.debug(f"<=Runner Fire Task=> REAL DEBUG: About to fire a task {task.name}")

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
            log.info(f"<=Runner Fire Task=> FAKE: About to fire a task Name {task.name}")
            msg = f"<=Runner Fire Task=> FAKE: Task passed arguments: \n\t\t t_queue={t_queue} \n\t\t t_args={t_args} \n\t\t t_kwargs={t_kwargs} \n\t\t t_routing_key={t_routing_key}"
            log.info(msg)
            task_options.update(args=['fire_t', to_sleep])
            task_options.update(kwargs=dict(t_args=t_args, t_kwargs=t_kwargs))
            log.warning('<=Runner Fire Task=> DEVELOPMENT MODE WILL NOT EXECUTE TASKS, BUT EMULATE WORK BY USING FAKE TASK')
            return TSupport.fake_task.apply_async(**task_options)
