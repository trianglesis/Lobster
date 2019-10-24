# MODEL

from run_core.models import RoutineExecutionLog
from octo.helpers.tasks_oper import WorkerOperations

# Python logger
import logging
log = logging.getLogger("octo.octologger")


class RoutineHelpers:

    @staticmethod
    def addm_workers_checker(addm_group_arg):
        """
        Get addm group arg, make it list and then ping all service workers and selected ADDM workers.
        Return list of addm groups when all workers are UP.

        :return:
        """

        if addm_group_arg:
            addm_l = addm_group_arg.split(',')
            # ping_list = ['w_routines@tentacle', 'w_perforce@tentacle', 'w_parsing@tentacle']  # To be sure we have those w up!
            ping_list = WorkerOperations().service_workers_list[:]
            if isinstance(addm_group_arg, list):
                for _worker in addm_group_arg:
                    ping_list.append("{}@tentacle".format(_worker))
                worker_up = WorkerOperations().worker_heartbeat(worker_list=ping_list)
                if worker_up.get('down'):
                    msg = '<=workers_checker=> Worker is down, cannot run all other tasks. W: {} '.format(worker_up)
                    return [], msg
            else:
                msg = '<=workers_checker=> addm_group_arg is not a list, while it should! {}'.format(addm_group_arg)
                return [], msg
            # When everything is OK and workers are UP:
            return addm_l, 'Workers are up!'
        else:
            msg = '<=workers_checker=> addm_group_arg is not set! {}'.format(addm_group_arg)
            return [], msg

    @staticmethod
    def night_routine_log(**kwargs):
        log.info("4. ====> Last task - save log")

        branch = kwargs.get('branch', None)
        user_name = kwargs.get('user_name', None)
        start_time = kwargs.get('start_time', None)
        send_mail = kwargs.get('send_mail', None)
        sync_tku = kwargs.get('sync_tku', None)
        release_window = kwargs.get('release_window', None)
        tests_set_list_len = kwargs.get('tests_set_list_len', [])
        routine_time_spent = kwargs.get('routine_time_spent', '')
        finish_time = kwargs.get('finish_time', '')
        time_stamp = kwargs.get('time_stamp', '')
        finish_time_format = kwargs.get('finish_time_format', '')

        try:
            routine_log = RoutineExecutionLog(
                routine_key='nightly_test_routine_case_{}_{}_{}'.format(branch, user_name, start_time),
                routine_name='RoutineCases.nightly_test',
                routine_time_spent=routine_time_spent,
                routine_args=(branch, send_mail, sync_tku, user_name),
                routine_kwargs='',
                routine_desc_details=dict(
                    release_window=release_window,
                    all_tests_len=tests_set_list_len,
                    branch=branch,
                    start_time=start_time,
                    finish_time=finish_time,
                    time_stamp=time_stamp,
                    finish_time_format=finish_time_format,
                    user_name=user_name,
                )
            )
            routine_log.save()
        except Exception as e:
            log.error("Cannot save routine log to DB with error: %s", e)
