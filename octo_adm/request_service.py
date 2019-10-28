"""
Making jobs for requests. Composing contexts and etc.
"""
from typing import Dict, List, Any, Union
import pytz
from datetime import datetime

from octo_tku_patterns.table_oper import PatternsDjangoModelRaw
from octo.helpers.tasks_oper import TasksOperations, WorkerOperations

# Python logger
import logging
log = logging.getLogger("octo.octologger")
lon_tz = pytz.timezone('Europe/London')


class SelectorRequestsHelpers:
    """
    Regular functions for selector out mod.

    """

    @staticmethod
    def worker_inspect_single(worker_name):
        """
        Get tasks active and reserved for selected ADDM.

        :return:
        """
        # from time import time
        # import kombu.five

        tasks_inspection = TasksOperations()
        # noinspection PyPep8
        tasks_inspection_result = tasks_inspection.get_addm_tasks_statuses(worker_name)

        workers_active_tasks = []
        workers_reserved_tasks = []

        workers_dict = dict(
            workers_active_tasks   = workers_active_tasks,
            workers_reserved_tasks = workers_reserved_tasks,
            task_active            = 'N/A',
            task_reserved          = 'N/A')

        if tasks_inspection_result:
            task_active = tasks_inspection_result['active']
            # log.debug("task_active: %s", task_active)
            if task_active:
                workers_dict['task_active'] = task_active
                for worker_k, worker_v in task_active.items():
                    active_tasks_d = dict(WORKER = worker_k, TASKS_COUNT = len(worker_v), TASKS_ITEMS = dict())
                    for task in worker_v:
                        if task['time_start'] is not None:
                            # OLD - from celery 4.1.0 - to be removed.
                            # https://stackoverflow.com/questions/20091505/celery-task-with-a-time-start-attribute-in-1970
                            # noinspection PyPep8,PyUnresolvedReferences
                            # task_time_start = datetime.fromtimestamp(time() - (kombu.five.monotonic() - float(task['time_start'])))
                            task_time_start = datetime.fromtimestamp(float(task['time_start']))
                            task_time_progress = datetime.now() - task_time_start
                        else:
                            task_time_start = "Pending..."
                            task_time_progress = "Pending..."

                        tasks_d = dict(TASK_NAME                = task['name'],
                                       TASK_TIME_START          = task_time_start,
                                       TASK_TIME_PROGRESS       = task_time_progress,
                                       TASK_ID                  = task['id'],
                                       TASK_HOSTNAME            = task['hostname'],
                                       TASK_ARGS                = task['args'],
                                       )
                        active_tasks_d['TASKS_ITEMS'] = tasks_d
                        workers_active_tasks.append(active_tasks_d)

            task_reserved = tasks_inspection_result['reserved']
            # log.debug("task_reserved: %s", task_reserved)
            if task_reserved:
                workers_dict['task_reserved'] = task_reserved
                for worker_k, worker_v in task_reserved.items():
                    task_items = []
                    reserved_tasks_d = dict(WORKER      = worker_k,
                                            TASKS_COUNT = len(worker_v),
                                            TASKS_ITEMS = list())
                    for task in worker_v:
                        task_time_start = "Pending..."
                        task_time_progress = "Pending..."

                        tasks_d = dict(TASK_NAME                = task['name'],
                                       TASK_TIME_START          = task_time_start,
                                       TASK_TIME_PROGRESS       = task_time_progress,
                                       TASK_ID                  = task['id'],
                                       TASK_HOSTNAME            = task['hostname'],
                                       TASK_ARGS                = task['args'],
                                       )
                        # One task from one worker
                        task_items.append(tasks_d)
                    # List of tasks for one worker
                    reserved_tasks_d['TASKS_ITEMS'] = task_items
                    # List of workers with list of tasks
                    workers_reserved_tasks.append(reserved_tasks_d)

        # log.debug("<=REQ SERVICE=> Return workers status for addm: %s", addm_group)
        return workers_dict

    @staticmethod
    def workers_all(worker_name=None):
        """
        Get all tasks from all workers
        :return:
        """
        # from time import time
        # import kombu.five
        tasks_inspection = TasksOperations()

        get_all_tasks_statuses = tasks_inspection.get_all_tasks_statuses(worker_name=worker_name)
        inspect_workers = get_all_tasks_statuses['inspect_workers']
        task_active = inspect_workers['active']
        task_reserved = inspect_workers['reserved']
        # active_tasks_d = dict()
        workers_active_tasks = []
        workers_reserved_tasks = []

        if task_active is not None and task_reserved is not None:
            for worker_k, worker_v in task_active.items():
                # log.debug("task_active.items(): worker_k %s, worker_v%s", worker_k, worker_v)
                active_tasks_d = dict(WORKER = worker_k, TASKS_COUNT = len(worker_v), TASKS_ITEMS = dict())
                for task in worker_v:
                    if task['time_start'] is not None:
                        # OLD - from celery 4.1.0 - to be removed.
                        # https://stackoverflow.com/questions/20091505/celery-task-with-a-time-start-attribute-in-1970
                        # noinspection PyPep8,PyUnresolvedReferences
                        # task_time_start = datetime.fromtimestamp(time() - (kombu.five.monotonic() - float(task['time_start'])))
                        task_time_start = datetime.fromtimestamp(float(task['time_start']))
                        task_time_progress = datetime.now() - task_time_start
                    else:
                        task_time_start = "Pending..."
                        task_time_progress = "Pending..."

                    tasks_d = dict(TASK_NAME          = task['name'],
                                   TASK_ARGS          = task['args'],
                                   # TASK_KWARGS          = task['kwargs'],
                                   TASK_TIME_START    = task_time_start,
                                   TASK_TIME_PROGRESS = task_time_progress,
                                   TASK_ID            = task['id'],
                                   TASK_HOSTNAME      = task['hostname'],)
                    active_tasks_d['TASKS_ITEMS'] = tasks_d
                    workers_active_tasks.append(active_tasks_d)

            # reserved_tasks_d = dict()
            for worker_k, worker_v in task_reserved.items():
                # log.debug("task_reserved.items(): worker_k %s, worker_v%s", worker_k, worker_v)
                task_items = []
                reserved_tasks_d = dict(WORKER = worker_k, TASKS_COUNT = len(worker_v), TASKS_ITEMS = list())
                for task in worker_v:
                    if task['time_start'] is not None:
                        # OLD - from celery 4.1.0 - to be removed.
                        # https://stackoverflow.com/questions/20091505/celery-task-with-a-time-start-attribute-in-1970
                        # noinspection PyPep8,PyUnresolvedReferences
                        # task_time_start = datetime.fromtimestamp(time() - (kombu.five.monotonic() - float(task['time_start'])))
                        task_time_start = datetime.fromtimestamp(float(task['time_start']))
                        task_time_progress = datetime.now() - task_time_start
                    else:
                        task_time_start = "Pending..."
                        task_time_progress = "Pending..."

                    # TODO: Parse args to get test details and query DB for last test execution time:
                    tasks_d = dict(TASK_NAME          = task['name'],
                                   TASK_ARGS          = task['args'],
                                   # TASK_KWARGS          = task['kwargs'],
                                   TASK_TIME_START    = task_time_start,
                                   TASK_TIME_PROGRESS = task_time_progress,
                                   TASK_ID            = task['id'],
                                   TASK_HOSTNAME      = task['hostname'],)
                    # One task from one worker
                    task_items.append(tasks_d)
                # List of tasks for one worker
                reserved_tasks_d['TASKS_ITEMS'] = task_items
                # List of workers with list of tasks
                workers_reserved_tasks.append(reserved_tasks_d)

        workers_dict = dict(workers_active_tasks      = workers_active_tasks,
                            workers_reserved_tasks    = workers_reserved_tasks,
                            # REGISTERED_WORKERS        = registered_workers,
                            # REGISTERED_TASKS_CONTXT   = registered_tasks_contxt,
                            # SCHEDULED_WORKERS         = scheduled_workers,
                            # SCHEDULED_TASKS_CONTXT    = scheduled_tasks_contxt,
                            )
        # log.debug("<=REQ SERVICE=> Return ALL workers statuses")
        return workers_dict

    @staticmethod
    def get_raw_w(**kwargs):
        workers_list = kwargs.get('workers_list', None)
        inspected = TasksOperations().check_active_reserved(workers_list=workers_list)  # type: List[Dict[str, Dict[Any, Union[int, Any]]]]
        excluded_list, included_list = TasksOperations().get_free_worker(workers_list=workers_list)  # type: # List[Dict[str, Dict[Any, Union[int, Any]]]]

        w_dict = dict()
        for worker in inspected:
            for w_key, w_val in worker.items():
                # task_sum = w_val.get('reserved_len') + w_val.get('active_len')
                # w_dict.update({w_key: task_sum})
                w_dict.update({w_key: w_val.get('all_tasks_len')})

        worker_min = min(w_dict, key=w_dict.get)
        worker_max = max(w_dict, key=w_dict.get)

        return dict(
            w_dict=w_dict,
            worker_min=worker_min,
            worker_max=worker_max,
            inspected=inspected,
            excluded_list=excluded_list,
            included_list=included_list,
                    )

    @staticmethod
    def get_free_included_w(**kwargs):
        """
        <=get_free_worker=> excluded_list: ['alpha@tentacle', 'beta@tentacle', 'charlie@tentacle', 'delta@tentacle', 'echo@tentacle', 'w_development@tentacle']
        inspected_included: [
                {'foxtrot@tentacle': {'reserved_len': 0,
                                      'active_tasks': [],
                                      'all_tasks': [],
                                      'active_len': 0,
                                      'reserved_tasks': [],
                                      'all_tasks_len': 0}}
            ]
        inspected_excluded: [
                {'alpha@tentacle': {'reserved_len': 0,
                                    'active_tasks': [],
                                    'all_tasks': [],
                                    'active_len': 0,
                                    'reserved_tasks': [],
                                    'all_tasks_len': 0}},
                {'beta@tentacle': {}},
                {'charlie@tentacle': {}},
                {'delta@tentacle': {}},
                {'echo@tentacle': {}},
                {'w_development@tentacle': {}}]

        worker_min: foxtrot@tentacle
        worker_max: alpha@tentacle

        :param kwargs:
        :return:
        """

        workers_list = kwargs.get('workers_list', None)
        excluded_list, included_list = TasksOperations().get_free_worker(workers_list=workers_list)  # type: # List[Dict[str, Dict[Any, Union[int, Any]]]]

        # log.debug("excluded_list: %s", excluded_list)

        inspected_included = TasksOperations().check_active_reserved(workers_list=included_list)  # type: List[Dict[str, Dict[Any, Union[int, Any]]]]
        inspected_excluded = TasksOperations().check_active_reserved(workers_list=excluded_list)  # type: List[Dict[str, Dict[Any, Union[int, Any]]]]

        # log.debug("inspected_included: %s", inspected_included)
        # log.debug("inspected_excluded: %s", inspected_excluded)

        w_dict = dict()
        for worker in inspected_included:
            for w_key, w_val in worker.items():
                w_dict.update({w_key: w_val.get('all_tasks_len')})

        w_ex_dict = dict()
        for worker in inspected_excluded:
            for w_key, w_val in worker.items():
                w_ex_dict.update({w_key: w_val.get('all_tasks_len')})

        worker_min = min(w_dict, key=w_dict.get)
        worker_max = max(w_ex_dict, key=w_ex_dict.get)

        log.debug("<=get_free_included_w=> worker_min: %s", worker_min)

        # log.debug("worker_min: %s", worker_min)
        # log.debug("worker_max: %s", worker_max)

        return dict(w_dict=w_dict,
                    w_ex_dict=w_ex_dict,
                    worker_min=worker_min,
                    worker_max=worker_max,
                    inspected=inspected_included,
                    inspected_excluded=inspected_excluded,
                    excluded_list=excluded_list,
                    included_list=included_list,
                    )

    @staticmethod
    def get_free_included_w_task(**kwargs):
        """
        Return beta as min worker
        :param kwargs:
        :return:
        """
        workers_list = kwargs.get('workers_list', None)
        # Ping all workers to wake them up, then - pick up one free for test.
        WorkerOperations().worker_ping()
        # log.debug("<=get_free_included_w_task=> worker_up: %s", worker_up)

        excluded_list, included_list = TasksOperations().get_free_worker(workers_list=workers_list)  # type: # List[Dict[str, Dict[Any, Union[int, Any]]]]
        inspected_included = TasksOperations().check_active_reserved_short(workers_list=included_list)  # type: List[Dict[str, Dict[Any, Union[int, Any]]]]

        log.debug("<=get_free_included_w_task=> excluded_list %s", excluded_list)
        log.debug("<=get_free_included_w_task=> included_list %s", included_list)
        log.debug("<=get_free_included_w_task=> inspected_included %s", inspected_included)

        w_dict = dict()
        for worker in inspected_included:
            for w_key, w_val in worker.items():
                w_dict.update({w_key: w_val.get('all_tasks_len')})
                log.debug("<=get_free_included_w_task=> All available workers: %s", w_dict)
        worker_min = min(w_dict, key=w_dict.get)

        log.debug("<=get_free_included_w_task=> worker_min: %s", worker_min)
        if worker_min != 'no_worker':
            worker_min = worker_min.replace('@tentacle', '')
        else:
            worker_min = []

        log.info("<=get_free_included_w_task=> Minimal worker selected: %s", worker_min)
        return worker_min

    @staticmethod
    def check_nightly_routine_run():
        tasks_oper  = TasksOperations()
        routine_tasks_list = tasks_oper.get_active_tasks_list('w_routines@tentacle')
        is_night_routine = False

        if routine_tasks_list:
            routine        = routine_tasks_list[0]
            routine_name   = routine.get('name', 'None')
            routine_kwargs = routine.get('kwargs', 'None')
            # Check for running tasks from class TRoutine
            if 't_routine_night_tests' in routine_name:
                log.info("<=REQ Service=> Cannot add new routine until current is not finished yet: %s, %s",
                         routine_name, routine_kwargs)
                subject = "Cannot add new routine! Until current is not finished yet: {} {}".format(
                    routine_name,
                    routine_kwargs)
                is_night_routine = subject

        return is_night_routine

    @staticmethod
    def check_nightly_test_addm_run():
        tasks_oper  = TasksOperations()
        routine_tasks_list = tasks_oper.get_active_tasks_list('w_routines@tentacle')
        is_night_routine = False

        if routine_tasks_list:
            routine        = routine_tasks_list[0]
            routine_name   = routine.get('name', 'None')
            routine_kwargs = routine.get('kwargs', 'None')
            # Check for running tasks from class TRoutine
            if 't_routine_night_tests' in routine_name:
                subject = "Cannot add new routine! Until current is not finished yet: {} {}".format(
                    routine_name,
                    routine_kwargs)
                is_night_routine = subject

        return is_night_routine

    @staticmethod
    def check_user_routine_run(user_name):
        tasks_oper  = TasksOperations()
        routine_tasks_list = tasks_oper.get_reserved_tasks_list('w_routines@tentacle')
        user_routine = False

        if routine_tasks_list:
            routine        = routine_tasks_list[0]
            routine_name   = routine.get('name', 'None')
            routine_args   = routine.get('args', 'None')
            if user_name in routine_args:
                log.info("<=REQ Service=> Cannot add new routine until current is not finished yet: %s, %s",
                         routine_name, routine_args)
                subject = "Cannot add new test task! Until current user {} task is not finished yet: {} {}".format(
                    user_name,
                    routine_name,
                    routine_args)
                user_routine = subject

        return user_routine
