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
