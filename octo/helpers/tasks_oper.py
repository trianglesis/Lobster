"""
Here execute service functions for tasks to collect them, get IDs, statuses, queues, etc.
"""

import logging
from time import sleep

from celery.result import AsyncResult

from octo.api.serializers import CeleryTaskmetaSerializer
from octo.models import CeleryTaskmeta
from octo.octo_celery import app
from run_core.models import Options

log = logging.getLogger("octo.octologger")


class TasksOperations:

    def __init__(self):
        self.service_workers_list = [
            'w_routines@tentacle',
            'w_parsing@tentacle',
        ]
        self.workers_enabled = Options.objects.filter(option_key__exact='workers_enabled').values('option_value')[0]
        __workers_list = Options.objects.get(option_key__exact='workers_list').option_value
        __workers_list = __workers_list.split(',')
        self.workers_list = [f"{worker}@tentacle" for worker in __workers_list]

    @staticmethod
    def task_success(task_itself):
        if task_itself.status == "SUCCESS":
            return True
        return False

    def task_wait_success(self, task_itself, task_name=None):
        """
        "While" for wait if task is finished with SUCCESS
        :return: True
        """
        # TODO: Rethink this, not a best idea to wait task, when celery can answer PENDING on any unknown state!
        if not task_name:
            msg = f"task_wait_success '{task_itself}' status: '{task_itself.status}'"
        else:
            msg = f"task_wait_success '{task_itself}' '{task_name}' status: '{task_itself.status}'"
        while not task_itself.ready():
            sleep(20)  # raised from 10
            log.info(msg)
        return self.task_success(task_itself)

    @staticmethod
    def get_workers_summary(**kwargs):
        if kwargs.get('worker_name'):
            inspect = app.control.inspect(kwargs.get('worker_name'))
            t_active = inspect.active()
            t_reserved  = inspect.reserved()
        else:
            inspect = app.control.inspect()
            t_active = inspect.active()
            t_reserved  = inspect.reserved()

        return {'active': t_active, 'reserved': t_reserved}

    def check_active_reserved_short(self, workers_list=None, tasks_body=False):
        """
        Using list ow workers - get active/reserved tasks items and len of queue.
        tasks_body - if we want to see what tasks are run.

        :param tasks_body:
        :type workers_list: list
        """
        inspected = []

        if not workers_list:
            workers_list = self.workers_list

        # log.debug(f'Inspecting workers {workers_list}')
        # Inspect each worker, instead of list (can be much slower?):
        inspect = app.control.inspect(destination=workers_list)  # :type worker list

        stats = inspect.stats()
        # log.debug(f"Inspect stats {stats}")
        registered_tasks = inspect.registered()
        # log.debug(f"Inspect registered_tasks {registered_tasks}")

        reserved = inspect.reserved()
        active = inspect.active()

        for worker in workers_list:
            try:
                active_tasks = reserved.get(worker, [])  # If None - it's empty.
                # log.debug(f'{worker} active_tasks: {active_tasks}')
                reserved_tasks = active.get(worker, [])  # If None - it's empty.
                # log.debug(f'{worker} reserved_tasks: {reserved_tasks}')
                if tasks_body:
                    inspected.append({worker: dict(all_tasks_len=len(active_tasks + reserved_tasks), all_tasks=active_tasks + reserved_tasks,)})
                else:
                    inspected.append({worker: dict(all_tasks_len=len(active_tasks + reserved_tasks))})
            except AttributeError as e:
                msg = "Some worker could be down '{}'! {}".format(worker, e)
                log.error(msg)
                inspected.append(dict(no_worker=dict(all_tasks=[dict(args='none', name='none')], all_tasks_len=0, error=msg)))
        return inspected

    # VIA REST:
    # Inspect workers:
    @staticmethod
    def tasks_get_active(**kwargs):
        workers = kwargs.get("workers", ())
        if workers:
            tasks = dict()
            inspect = app.control.inspect(workers)
            for worker in workers:
                w_tasks = inspect.active().get(worker)
                tasks.update({worker: w_tasks})
        else:
            tasks_list = []
            inspect = app.control.inspect()
            active = inspect.active()
            for worker_v in active.values():
                for task in worker_v:
                    tasks_list.append(task)
            tasks = dict(active=tasks_list)
        return tasks

    @staticmethod
    def tasks_get_reserved(**kwargs):
        workers = kwargs.get("workers", ())
        # log.debug("workers %s", workers)
        if workers:
            tasks = dict()
            inspect = app.control.inspect(workers)
            # log.debug("inspect %s %s", workers, inspect)
            for worker in workers:
                w_tasks = inspect.reserved().get(worker)
                tasks.update({worker: w_tasks})
        else:
            tasks_list = []
            inspect = app.control.inspect()
            reserved = inspect.reserved()
            for worker_v in reserved.values():
                for task in worker_v:
                    tasks_list.append(task)
            tasks = dict(reserved=tasks_list)
        return tasks

    @staticmethod
    def tasks_get_scheduled(**kwargs):
        workers = kwargs.get("workers", ())
        if workers:
            tasks = dict()
            inspect = app.control.inspect(workers)
            for worker in workers:
                w_tasks = inspect.scheduled().get(worker)
                tasks.update({worker: w_tasks})
        else:
            inspect = app.control.inspect()
            tasks = {'scheduled': inspect.scheduled()}
        return tasks

    @staticmethod
    def tasks_get_active_reserved(**kwargs):
        """
        If workers arguments is passed = inspect only workers selected.
        Then make dict with active, reserved tasks for each worker.

        If no worker passed - inspect all.
        :param kwargs:
        :return:
        """
        workers = kwargs.get("workers", ())
        if workers:
            tasks = dict()
            active = dict()
            reserved = dict()
            inspect = app.control.inspect(workers)
            for worker in workers:
                w_active = inspect.active().get(worker)
                w_reserved = inspect.reserved().get(worker)
                active.update({worker: w_active})
                reserved.update({worker: w_reserved})
            tasks.update(active=active, reserved=reserved)
        else:
            inspect = app.control.inspect()
            active = inspect.active()
            reserved = inspect.reserved()
            tasks = {'active': active, 'reserved': reserved}
        return tasks

    @staticmethod
    def tasks_get_registered(**kwargs):
        """
        operation_key=tasks_get_registered;workers=alpha,charlie
        :param kwargs:
        :return:
        """
        workers = kwargs.get("workers", ())
        if workers:
            tasks = dict()
            registered = dict()
            inspect = app.control.inspect(workers)
            for worker in workers:
                w_tasks = inspect.registered().get(worker)
                registered.update({worker: w_tasks})
            tasks.update(registered=registered)
        else:
            inspect = app.control.inspect()
            tasks = {'registered': inspect.registered()}
        return tasks

    # Cancel tasks:
    @staticmethod
    def revoke_task_by_id(task_id, terminate=False, local=False):
        """
        Push the button to cancel current task.
        Tell all (or specific) workers to revoke a task by id.
        If a task is revoked, the workers will ignore the task and not execute it after all.
        terminate (bool) – Also terminate the process currently working on the task (if any)

        :param task_id:
        :param terminate:
        :param local:
        :return:
        """
        if terminate:
            app.control.revoke(task_id, terminate=terminate, signal='SIGTERM')
        else:
            app.control.revoke(task_id)
        res = AsyncResult(task_id)
        task_res = dict(
            task_id=task_id,
            id=res.id,
            status=res.status,
            traceback=res.traceback,
            worker=res.worker,
            state=res.state,
            queue=res.queue,
            retries=res.retries,
            parent=res.parent,
            name=res.name,
            args=res.args,
            kwargs=res.kwargs,
            children=res.children,
            date_done=res.date_done,
        )
        if task_id == res.id:
            resp = 'Task marked to be revoked!'
        else:
            resp = 'Result task and task to revoke has different ids! Possibly revoke wrong task.'
        if local:
            return task_res
        return {'resp': resp, 'async_result': task_res}

    def revoke_tasks_active(self, **kwargs):
        """
        Revoke all active tasks one by one by theirs id.

        :return:
        """
        workers = kwargs.get("workers", None)
        revoked_count = 0
        revoked_tasks = []
        active_tasks = self.tasks_get_active(workers=workers)
        if active_tasks:
            for worker_v in active_tasks.values():
                for task in worker_v:
                    task_res = self.revoke_task_by_id(task['id'], False, True)
                    revoked_count += 1
                    revoked_tasks.append(task_res)
        return {'revoked_tasks': revoked_tasks, 'revoked_count': revoked_count}

    def revoke_tasks_reserved(self, **kwargs):
        """
        Revoke all active tasks one by one by theirs id.

        :return:
        """
        workers = kwargs.get("workers", None)
        revoked_count = 0
        revoked_tasks = []
        reserved = self.tasks_get_reserved(workers=workers)
        if reserved:
            for worker_v in reserved.values():
                for task in worker_v:
                    task_res = self.revoke_task_by_id(task['id'], False, True)
                    revoked_count += 1
                    revoked_tasks.append(task_res)
        return {'revoked_tasks': revoked_tasks, 'revoked_count': revoked_count}

    def revoke_tasks_active_reserved(self, **kwargs):
        workers = kwargs.get("workers", None)
        revoked_active = self.revoke_tasks_active(workers=workers)
        revoked_reserved = self.revoke_tasks_reserved(workers=workers)
        return {'revoked_active': revoked_active, 'revoked_reserved': revoked_reserved}

    @staticmethod
    def task_discard_all():
        """
        Discard all waiting tasks. This will ignore all tasks waiting for execution,
        and they will be deleted from the messaging server.
        Returns:	the number of tasks discarded.
        :return:
        """
        return app.control.discard_all()

    @staticmethod
    def task_purge_all():
        """
        Discard all waiting tasks. This will ignore all tasks waiting for
        execution, and they will be deleted from the messaging server.
        Returns:	the number of tasks discarded.
        :return:
        """
        return app.control.purge()

    def tasks_get_results(self, **kwargs):
        log.debug("args: %s kwargs %s", 'args', kwargs)
        task_id = kwargs.get('task_id', None)

        if task_id:
            tasks = CeleryTaskmeta.objects.filter(task_id__exact=task_id).order_by('-date_done')
        else:
            tasks = CeleryTaskmeta.objects.all().order_by('-date_done')

        if tasks:
            serializer = CeleryTaskmetaSerializer(tasks, many=True)
            return serializer.data

        else:
            res = AsyncResult(task_id)
            task_res = dict(
                task_id=task_id,
                status=res.status,
                result=res.result,
                state=res.state,
                args=res.args,
            )
            # log.debug("Task result: %s", task_res)
            return [task_res]


class WorkerOperations:
    """
    Usually service functions for workers, like restarts, queues, consumers etc.
    """

    def __init__(self):
        self.workers_list = TasksOperations().workers_list
        self.service_workers_list = TasksOperations().service_workers_list

    @staticmethod
    def _ping_check(w_ping, worker_up):
        for pinged in w_ping:
            for ping_k, ping_v in pinged.items():
                if 'pong' in ping_v.get('ok'):
                    worker_up.update({ping_k: ping_v.get('ok')})
                else:
                    worker_up.update({ping_k: 'down'})
        return worker_up

    def worker_restart(self, **kwargs):
        """
        Control.pool_restart(modules=None, reload=False, reloader=None, destination=None, **kwargs)[source]
        Restart the execution pools of all or specific workers.

       Keyword Arguments:
            modules (Sequence[str]): List of modules to reload.
            reload (bool): Flag to enable module reloading.  Default is False.
            reloader (Any): Function to reload a module.
            destination (Sequence[str]): List of worker names to send this
                command to.

        :param kwargs:
        :return:
        """
        workers = kwargs.get("workers", None)
        my_modules = ['run_core', 'octo.tasks', 'octo_adm.tasks', 'octo_tku_patterns.tasks', 'octo_tku_upload.tasks']

        # TODO: Remove when ready.
        if not workers:
            workers = self.workers_list

        for worker in workers:
            w_restart = app.control.pool_restart(modules=my_modules, destination=[worker], reload=True)
            log.info("<=WorkerOperations=> Executing worker_restart() for %s: %s", worker, w_restart)
        return 'Restart...'

    def worker_heartbeat(self, **kwargs):
        """
        Check if worker is listen to.
        Heartbeat return None
        Ping return answer: [{'alpha@tentacle': {'ok': 'pong'}}]

        :param worker_list:
        :return:
        """
        worker_list = kwargs.get("worker_list", None)  # leave old param here, somewhere it still be used!
        workers = kwargs.get("workers", None)
        worker_up = dict()

        # TODO: Remove when ready.
        if worker_list:
            workers = worker_list

        if workers and isinstance(workers, list):
            app.control.heartbeat(destination=workers)
            w_ping = app.control.ping(destination=workers, timeout=10)

            if len(w_ping) != len(workers):
                down = []
                for w_can in workers:
                    if not any([ping.get(w_can) for ping in w_ping]):
                        down.append(w_can)
                worker_up.update(status='down', workers_passed=workers, workers_resolved=w_ping, down=down)
                log.error("<=WorkerOperations=> worker_heartbeat(): -> workers down %s", down)
                return worker_up

        else:
            app.control.heartbeat()
            w_ping = app.control.ping(timeout=10)
        worker_up = self._ping_check(w_ping, worker_up)

        return worker_up

    def worker_ping(self, **kwargs):
        """
        Ping return answer: [{'alpha@tentacle': {'ok': 'pong'}}]
         {'charlie@tentacle': 'pong', 'alpha@tentacle': 'pong',
         'w_parsing@tentacle': 'pong', 'delta@tentacle': 'pong', 'w_routines@tentacle': 'pong',
         'beta@tentacle': 'pong'}

         {'foxtrot@tentacle': 'pong', 'beta@tentacle': 'pong',
          'echo@tentacle': 'pong', 'delta@tentacle': 'pong',
          'charlie@tentacle': 'pong', 'alpha@tentacle': 'pong'}


        :param worker_list:
        :return:
        """
        worker_list = kwargs.get("worker_list", None)  # leave old param here, somewhere it still be used!
        workers = kwargs.get("workers", None)
        worker_up = dict()

        # TODO: Remove when ready.
        if worker_list:
            workers = worker_list

        if workers and isinstance(workers, list):
            w_ping = app.control.ping(destination=workers, timeout=20)
            if len(w_ping) != len(workers):
                down = []
                for w_can in workers:
                    if not any([ping.get(w_can) for ping in w_ping]):
                        down.append(w_can)
                worker_up.update(status='down', workers_passed=workers, workers_resolved=w_ping, down=down)
                log.error("<=worker_ping=> workers down: %s", down)
                return worker_up
        else:
            w_ping = app.control.ping(timeout=5)
        worker_up = self._ping_check(w_ping, worker_up)

        return worker_up

    def worker_ping_alt(self, worker_list):
        """
        Check workers list with ping. Ping will return only list of workers with answer.
        Check the list of workers that answered to be sure they're have 'pong' in answer.
        Update dict with workers with live workers and add also ones which hasn't 'pong' or not answered.
        Show warnings if worker are down.

        Ping return answer: [{'alpha@tentacle': {'ok': 'pong'}}]
            worker_up {'foxtrot@tentacle': 'down', 'charlie@tentacle': 'pong', 'delta@tentacle': 'pong'}


        :param worker_list:
        :return:
        """
        worker_up = dict()

        if worker_list and isinstance(worker_list, list):
            w_ping = app.control.ping(destination=worker_list, timeout=2)
            log.debug("<=WorkerOperations=> w_ping: %s", w_ping)

            if len(w_ping) != len(worker_list):
                for w_can in worker_list:
                    if not any([ping.get(w_can) for ping in w_ping]):
                        worker_up.update({w_can: 'down'})
                        log.error("<=WorkerOperations=> Worker DOWN: %s", w_can)
            worker_up = self._ping_check(w_ping, worker_up)
        else:
            log.error("<=WorkerOperations=> This should be a list of workers!")

        log.debug("<=WorkerOperations=> worker_up %s", worker_up)
        return worker_up