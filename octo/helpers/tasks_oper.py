"""
Here execute service functions for tasks to collect them, get IDs, statuses, queues, etc.
"""

import logging
import sys
from time import sleep

from celery.result import AsyncResult

from octo.octo_celery import app
from run_core.models import Options
from octo.models import CeleryTaskmeta
from octo.api.serializers import CeleryTaskmetaSerializer


log = logging.getLogger("octo.octologger")


class recursionlimit:
    def __init__(self, limit):
        self.limit = limit
        self.old_limit = sys.getrecursionlimit()

    def __enter__(self):
        sys.setrecursionlimit(self.limit)

    def __exit__(self, type, value, tb):
        sys.setrecursionlimit(self.old_limit)


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
        if not task_name:
            msg = "task_wait_success '{}' status: '{}'".format(task_itself, task_itself.status)
        else:
            msg = "task_wait_success '{}' '{}' status: '{}'".format(task_itself, task_name, task_itself.status)
        while not task_itself.ready():
            sleep(20)  # raised from 10
            log.info(msg)
        return self.task_success(task_itself)

    @staticmethod
    def get_all_tasks_statuses(worker_name):
        """
        Collect all tasks and show their statuses.
        Maybe collect only user tasks?

        http://docs.celeryproject.org/en/master/userguide/workers.html#inspecting-workers
        https://stackoverflow.com/questions/5544629/retrieve-list-of-tasks-in-a-queue-in-celery
        :return:
        """

        if worker_name:
            inspect        = app.control.inspect([worker_name])
            inspect_active = app.control.inspect([worker_name]).active_queues()
        else:
            inspect        = app.control.inspect()
            inspect_active = app.control.inspect().active_queues()

        tasks_inspection = dict(
            inspect_workers=dict(
                         registered     = inspect.registered(),
                         active         = inspect.active(),
                         scheduled      = inspect.scheduled(),
                         reserved       = inspect.reserved()
                         ),
            inspect_active_tsk=inspect_active,)
        return tasks_inspection

    @staticmethod
    def get_addm_tasks_statuses(worker):
        """
        Get tasks running on worker with selected name:
        worker@tentacle or tentacle

        :param worker:
        :return:
        """
        worker_k = worker
        if '@tentacle' not in worker:
            worker_k = '{}@tentacle'.format(worker)
        inspect = app.control.inspect([worker_k])
        return dict(active = inspect.active(), reserved = inspect.reserved())

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

    def check_active_reserved(self, workers_list=None):
        """
        Using list ow workers - get active/reserved tasks items and len of queue.

        :type workers_list: list
        """
        inspect = app.control.inspect()
        reserved = inspect.reserved()
        active = inspect.active()
        inspected = []
        if not workers_list:
            workers_list = self.workers_list

        for worker in workers_list:
            if active is not None and reserved is not None:
                active_tasks = reserved.get(worker, [])  # If None - it's empty.
                reserved_tasks = active.get(worker, [])  # If None - it's empty.
                all_tasks = active_tasks + reserved_tasks

                inspected.append({
                    worker: dict(
                        active_tasks=active_tasks,
                        reserved_tasks=reserved_tasks,
                        all_tasks=all_tasks,
                        all_tasks_len=len(all_tasks),
                        reserved_len=len(reserved_tasks) if reserved_tasks else 0,
                        active_len=len(active_tasks) if active_tasks else 0,)
                })
            else:
                inspected.append({
                    worker: dict(
                        active_tasks=[], reserved_tasks=[], all_tasks=[], all_tasks_len=0, reserved_len=0, active_len=0)
                })
        return inspected

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

        # Inspect each worker, instead of list (can be much slower?):
        inspect = app.control.inspect(destination=workers_list)  # :type worker list
        reserved = inspect.reserved()
        active = inspect.active()

        for worker in workers_list:
            try:
                active_tasks = reserved.get(worker, [])  # If None - it's empty.
                reserved_tasks = active.get(worker, [])  # If None - it's empty.
                if tasks_body:
                    inspected.append({worker: dict(all_tasks_len=len(active_tasks + reserved_tasks), all_tasks=active_tasks + reserved_tasks,)})
                else:
                    inspected.append({worker: dict(all_tasks_len=len(active_tasks + reserved_tasks))})
            except AttributeError as e:
                msg = "Some worker could be down '{}'! {}".format(worker, e)
                log.error(msg)
                inspected.append(dict(no_worker=dict(all_tasks=[dict(args='none', name='none')], all_tasks_len=0, error=msg)))
        return inspected

    def get_free_worker(self, workers_list):
        """
        Using list of workers get state of each, sort out busy workers or
            workers with very long tasks like upload tests.

        :return:
        """
        # workers_list = kwargs.get('workers_list', None)
        # excluding_task = kwargs.get('excluding_task', None)
        excl = 'lock=True'
        excluded_option = Options.objects.filter(option_key__exact='workers_excluded_list').values('option_value')[0]
        excluded_list = excluded_option.get('option_value', []).replace(' ', '').split(',')
        included_list = []
        workers_list_actual = []

        if not workers_list:
            workers_list = self.workers_list
        log.debug("Use workers_list: %s", workers_list)

        # Ping all workers before any action to be sure they're up:
        worker_up = WorkerOperations().worker_ping(worker_list=workers_list)  # List of all workers?
        log.debug("Pinged workers: %s", worker_up)

        for w_key, w_val in worker_up.items():
            if 'pong' in w_val:
                # 1st check if this worker excluded in options:
                if w_key not in excluded_list:
                    # Better exclude workers here, before inspecting theirs state?
                    workers_list_actual.append(w_key)

        inspected = self.check_active_reserved_short(workers_list=workers_list_actual, tasks_body=True)
        log.debug("<=get_free_worker=> excluded_list: %s", excluded_list)
        for worker in inspected:
            for w_key, w_val in worker.items():
                all_tasks = w_val.get('all_tasks')

                # Update excluded list with new workers where tasks lock=True
                if any(excl in d.get('args') for d in all_tasks) or any(excl in d.get('name') for d in all_tasks):
                    log.debug("<=get_free_worker=> Exclude worker due task lock: %s", w_key)
                    excluded_list.append(w_key)
                    break
                else:

                    # 2nd check if inspected worker is in dynamical excluded list:
                    if w_key not in excluded_list:
                        if w_key not in included_list:
                            included_list.append(w_key)

        for candidate in included_list:
            # 3rd check after all:
            # To check if we not choosing worker from other branch
            if candidate in excluded_list:
                included_list.remove(candidate)

        return excluded_list, included_list

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
            inspect = app.control.inspect()
            tasks = inspect.active()
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
            inspect = app.control.inspect()
            # log.debug("inspect %s", inspect)
            tasks = inspect.reserved()
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
            tasks = inspect.scheduled()
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
            inspect = app.control.inspect(workers)
            for worker in workers:
                w_active = inspect.active().get(worker)
                w_reserved = inspect.reserved().get(worker)
                tasks.update({worker: {"active": w_active, "reserved": w_reserved}})
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
            inspect = app.control.inspect(workers)
            for worker in workers:
                w_tasks = inspect.registered().get(worker)
                tasks.update({worker: w_tasks})
        else:
            inspect = app.control.inspect()
            tasks = inspect.registered()
        return tasks

    # Cancel tasks:
    @staticmethod
    def revoke_task_by_id(task_id, terminate=False):
        """
        Push the button to cancel current task.
        Tell all (or specific) workers to revoke a task by id.
        If a task is revoked, the workers will ignore the task and not execute it after all.
        terminate (bool) – Also terminate the process currently working on the task (if any)

        :param task_id:
        :param terminate:
        :return:
        """
        if terminate:
            resp = app.control.revoke(task_id, terminate=terminate, signal='SIGTERM')
        else:
            resp = app.control.revoke(task_id)
        return resp

    def revoke_tasks_active(self, **kwargs):
        """
        Revoke all active tasks one by one by theirs id.

        :return:
        """
        workers = kwargs.get("workers", None)

        tasks_revoked = 0
        revoked_names = []

        active_tasks = self.tasks_get_active(workers=workers)
        if active_tasks:
            for worker_k, worker_v in active_tasks.items():
                for task in worker_v:
                    self.revoke_task_by_id(task['id'])
                    tasks_revoked += 1
                    revoked_names.append(dict(
                        task_id=task['id'],
                        task_name=task['name'],
                        task_args=task['args'],
                        task_hostname=task['hostname'],
                    ))

        return {'tasks_revoked': tasks_revoked, 'revoked_names': revoked_names}

    def revoke_tasks_reserved(self, **kwargs):
        """
        Revoke all active tasks one by one by theirs id.

        :return:
        """
        workers = kwargs.get("workers", None)

        tasks_revoked = 0
        revoked_names = []

        active_tasks = self.tasks_get_reserved(workers=workers)
        if active_tasks:
            for worker_k, worker_v in active_tasks.items():
                for task in worker_v:
                    self.revoke_task_by_id(task['id'])
                    tasks_revoked += 1
                    revoked_names.append(dict(
                        task_id=task['id'],
                        task_name=task['name'],
                        task_args=task['args'],
                        task_hostname=task['hostname'],
                    ))

        return {'tasks_revoked': tasks_revoked, 'revoked_names': revoked_names}

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
    def ping_check(w_ping, worker_up):
        for pinged in w_ping:
            for ping_k, ping_v in pinged.items():
                if 'pong' in ping_v.get('ok'):
                    worker_up.update({ping_k: ping_v.get('ok')})
                else:
                    worker_up.update({ping_k: 'down'})
        return worker_up

    @staticmethod
    def worker_restart(**kwargs):
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
        worker_list = kwargs.get("worker_list", None)  # leave old param here, somewhere it still be used!
        workers = kwargs.get("workers", None)
        my_modules = ['octo.tasks', 'octo_adm.tasks', 'octo_tku_patterns.tasks', 'octo_tku_upload.tasks']

        # TODO: Remove when ready.
        if worker_list:
            workers = worker_list

        if workers and isinstance(workers, list):
            w_restart = app.control.pool_restart(modules=my_modules, destination=workers, reload=True)
            log.info("<=WorkerOperations=> Executing worker_restart(%s): w_restart - %s", workers, w_restart)
        else:
            w_restart = app.control.pool_restart(modules=my_modules, reload=True)
            log.info("<=WorkerOperations=> Executing worker_restart() for all: %s", w_restart)
        return w_restart

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
        worker_up = self.ping_check(w_ping, worker_up)

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
        worker_up = self.ping_check(w_ping, worker_up)

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
            worker_up = self.ping_check(w_ping, worker_up)
        else:
            log.error("<=WorkerOperations=> This should be a list of workers!")

        log.debug("<=WorkerOperations=> worker_up %s", worker_up)
        return worker_up


class NewTaskOper:

    @staticmethod
    def tasks_inspect(workers_list=None):
        if workers_list:
            inspect = app.control.inspect(workers_list)
        else:
            inspect = app.control.inspect()
        return inspect

    def tasks_active(self, inspected, workers_list=None):
        if not inspected:
            inspected = self.tasks_inspect(workers_list)
        t_active = inspected.active()
        return t_active

    def tasks_reserved(self, inspected, workers_list=None):
        if not inspected:
            inspected = self.tasks_inspect(workers_list)
        t_reserved = inspected.reserved()
        return t_reserved

    def list_tasks_ids(self, active=False, workers_list=None):
        all_tasks_ids = []

        inspect = self.tasks_inspect(workers_list)
        t_reserved = inspect.reserved()

        log.debug("<=Tasks Len => t_reserved: %s", len(t_reserved))

        for _, worker_v in t_reserved.items():
            for task in worker_v:
                if task['id'] not in all_tasks_ids:
                    all_tasks_ids.append(task['id'])

        if active:
            t_active = inspect.active()
            log.debug("<=Tasks Len => t_active: %s", len(t_active))
            for _, worker_v in t_active.items():
                for task in worker_v:
                    if task['id'] not in all_tasks_ids:
                        all_tasks_ids.append(task['id'])

        log.debug("All tasks active and reserved len: %s", len(all_tasks_ids))
        return all_tasks_ids

    @staticmethod
    def revoke_ids_l(tasks_ids_list):
        log.info("About to revoke %s task(s)", len(tasks_ids_list))
        app.control.revoke(tasks_ids_list)

    def revoke_all_tasks(self):
        log.info("Will revoke all active and reserved tasks!")
        all_t = self.list_tasks_ids()
        rec_limit = len(all_t) + 1500
        with recursionlimit(rec_limit):
            self.revoke_ids_l(all_t)
        log.info("Revoking all tasks job has finished it's run!")
