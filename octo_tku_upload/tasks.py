from __future__ import absolute_import, unicode_literals
import datetime
import logging
# noinspection PyUnresolvedReferences
from typing import Dict, List, Any

# Celery
from octo.octo_celery import app

from octo_tku_upload.test_executor import UploadTestExec
from run_core.local_operations import LocalDownloads

from octo.helpers.tasks_oper import TasksOperations
from octo.helpers.tasks_helpers import TMail
from octo.helpers.tasks_helpers import exception

from octo.helpers.tasks_run import Runner

log = logging.getLogger("octo.octologger")

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


# noinspection PyUnusedLocal,PyUnusedLocal
class TUploadRoutine:

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TRoutine.t_routine_tku_upload_test_new',
              soft_time_limit=MIN_90, task_time_limit=HOURS_2)
    @exception
    def t_routine_tku_upload(t_tag, **kwargs):
        return UploadCases.tku_upload(**kwargs)


# noinspection PyUnusedLocal,PyUnusedLocal
class TUploadExec:

    @staticmethod
    @app.task(routing_key='worker_tentacle.TExecTest.t_tku_sync.addm_group',
              queue='w_parsing@tentacle.dq2', soft_time_limit=MIN_20, task_time_limit=MIN_40)
    @exception
    def t_tku_sync(t_tag, **kwargs):
        return LocalDownloads().wget_tku_build_hub_option(**kwargs)

    @staticmethod
    @app.task(routing_key='worker_tentacle.TExecTest.t_upload_exec_threads.addm_group',
              soft_time_limit=MIN_90, task_time_limit=HOURS_2)
    @exception
    def t_upload_exec_threads(t_tag, **kwargs):
        return UploadTestExec().upload_run_threads(**kwargs)

    @staticmethod
    @app.task(queue='w_parsing@tentacle.dq2', routing_key='parsing.TUploadExec.t_parse_tku',
              soft_time_limit=MIN_40, task_time_limit=MIN_90)
    @exception
    def t_parse_tku(t_tag, **kwargs):
        log.debug("Tag: %s, kwargs %s", t_tag, kwargs)
        return LocalDownloads().only_parse_tku(**kwargs)


class UploadCases:

    @staticmethod
    def tku_upload(**kwargs):
        """
        Routine case for following operations:
        1. Download/Renew CONTINUOUS TKU zips on Octopus FS from buildhub FTP.
        2. Parse and collect all CONTINUOUS stored zips and args for them. Insert in DB.
        3. Run simple TKU install and parse results. No extra steps required!

        :return:
        """
        # user_name  = kwargs['user_name']
        user_email = kwargs.get('user_email')
        addm_group = kwargs.get('addm_group')
        mode = kwargs.get('mode', None)
        tku_type = kwargs.get('tku_type', None)
        tku_wget = kwargs.get('tku_wget', False)
        fake_run = kwargs.get('fake_run', False)
        tku_downloaded = False
        # Send on init:
        TMail().upload_t(stage='started', mode=mode, tku_type=tku_type, tku_wget=tku_wget, addm_group=addm_group,
                       user_email=user_email, start_time=datetime.datetime.now())

        if tku_wget:
            """ WGET zips and parse locally: """
            tku_download_task = Runner.fire_t(TUploadExec().t_tku_sync, fake_run=fake_run,
                                              t_kwargs=dict(tku_type=tku_type),
                                              t_args=['tag=t_tku_sync;mode={};addm_group={}'.format(mode, addm_group)])
            # Wait until wget task finished successfully:
            if TasksOperations().task_wait_success(tku_download_task, 't_tku_sync_option'):
                tku_downloaded = True
        else:
            # Do not run WGET, just install local zip
            tku_downloaded = True

        if tku_downloaded:
            t_tag = 'tag=upload_t;lock=True;type=routine;tku_type={tku_type};addm_group={addm_group};'.format(
                tku_type=tku_type, addm_group=addm_group)
            Runner.fire_t(TUploadExec().t_upload_exec_threads, fake_run=fake_run,
                          t_queue=addm_group + '@tentacle.dq2',
                          t_args=[t_tag],
                          t_routing_key='routines.TExecTest.t_upload_exec_threads.{}'.format(addm_group),
                          t_kwargs=dict(addm_group=addm_group, tku_type=tku_type, mode=mode, user_email=user_email))
            # Send on start
            TMail().upload_t(stage='tku_install', mode='continuous', tku_type=tku_type, tku_wget=tku_wget,
                           addm_group=addm_group, t_tag=t_tag, start_time=datetime.datetime.now(), )
        else:
            msg = "<=RoutineCases=> t_tku_sync failed to finish. Kwargs: {}".find(**kwargs)
            log.error(msg)
            raise Exception(msg)
