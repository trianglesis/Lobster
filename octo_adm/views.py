"""
OCTO ADM - pages and widgets and functions.
"""

import logging
from datetime import datetime

from celery.result import AsyncResult
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template import loader
from django.views.generic import TemplateView, ListView
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from octo.api.serializers import CeleryTaskmetaSerializer
from octo.api.serializers import StandardResultsSetPagination
from octo.config_cred import p4_cred
from octo.helpers.tasks_oper import TasksOperations, WorkerOperations
from octo.helpers.tasks_run import Runner
from octo.models import CeleryTaskmeta
from octo_adm.serializers import AddmDevSerializer
from octo_adm.tasks import TaskADDMService
from octo_adm.user_operations import UserCheck
from octo_tku_patterns.tasks import TPatternParse
from run_core.addm_operations import ADDMStaticOperations
from run_core.local_operations import LocalPatternsP4Parse
from run_core.models import AddmDev
from run_core.p4_operations import PerforceOperations

log = logging.getLogger("octo.octologger")
curr_hostname = getattr(settings, 'SITE_DOMAIN', None)


class AdminWorkbench(TemplateView):
    __url_path = '/octo_admin/admin/'
    template_name = 'admin_workbench/octo_admin_workbench.html'
    context_object_name = 'objects'


class AddmWorkbench(ListView):
    __url_path = '/octo_admin/addm/'
    template_name = 'addm_workbench/addm_workbench.html'
    context_object_name = 'objects'
    # model = AddmDev
    # Sort in named order
    queryset = AddmDev.objects.all().order_by('addm_name')


class CeleryWorkbench(TemplateView):
    __url_path = '/octo_admin/celery/'
    template_name = 'celery_workbench/celery_workbench.html'
    context_object_name = 'objects'


class CeleryInspect(TemplateView):
    """
    If worker - show tabs for one worker and use data-worker as selectable for JS
    If not worker - show everything in the same tabs, JS check when data-worker is undefined and also query for all.
    """
    __url_path = '/octo_admin/celery_inspect/'
    template_name = 'celery_workbench/celery_inspect.html'
    context_object_name = 'objects'

    def get_context_data(self, **kwargs):
        context = super(CeleryInspect, self).get_context_data(**kwargs)
        workers = self.request.GET.get('workers', 'all-workers')
        context.update(
            workers=workers,
            objects={},
        )
        return context


class TaskOperationsREST(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.operation_key = ''
        self.start_time = datetime.now().strftime('%Y-%m-%d_%H-%M')
        self.is_authenticated = ''
        # metadata:
        self.user_name = ''
        self.user_email = ''
        self.admin_users = ''
        self.power_users = ''
        # options:
        self.task_id = ''
        self.workers = ''

        self.fake_run = False
        self.goto_ = 'http://'+curr_hostname+'/octo_admin/task_operation/?operation_key='

    def task_operations(self):
        """
        Execute task operations or return task operation status.
        If no args passed - return operations dict to show user all possible variants.

        :return:
        """
        operations = dict(
            get_task_status_by_id=self.get_task_status_by_id,
            tasks_get_registered=self.tasks_get_registered,
            tasks_get_active=self.tasks_get_active,
            tasks_get_reserved=self.tasks_get_reserved,
            tasks_get_scheduled=self.tasks_get_scheduled,
            tasks_get_active_reserved=self.tasks_get_active_reserved,
            tasks_get_results=self.tasks_get_results,
            task_get_result=self.task_get_result,
            task_revoke_by_id=self.revoke_task_by_id,
            task_revoke_active=self.revoke_tasks_active,
            task_revoke_reserved=self.revoke_tasks_reserved,
            task_revoke_active_reserved=self.revoke_tasks_active_reserved,
            task_discard_all=self.task_discard_all,
            task_purge_all=self.task_purge_all,
            workers_summary=self.get_workers_summary,
            worker_ping=self.worker_ping,
            worker_heartbeat=self.worker_heartbeat,
            worker_restart=self.worker_restart,
        )
        if self.operation_key:
            actions = operations.get(self.operation_key, 'No such operation key')
        else:
            actions = operations
        return actions

    def metadata_options_set(self):
        if self.request.POST:
            self.operation_key = self.request.POST.get('operation_key', None)
            self.fake_run = self.request.POST.get('fake_run', False)  # TODO: Debug, remove default True
            self.task_id = self.request.POST.get('task_id', 'ThisIsNotTheTaskJustSayingYouKnow?')
            workers = self.request.POST.get('workers', '')
            if workers:
                workers = workers.split(',')
                self.workers = [f'{worker}@tentacle' for worker in workers]
        elif self.request.GET:
            self.operation_key = self.request.GET.get('operation_key', None)
            self.fake_run = self.request.GET.get('fake_run', False)  # TODO: Debug, remove default True
            self.task_id = self.request.GET.get('task_id', '')
            self.workers = self.request.GET.get('workers', [])

        self.is_authenticated = self.request.user.is_authenticated
        self.user_name = self.request.user.get_username()
        self.user_email = self.request.user.email

        self.admin_users = self.request.user.groups.filter(name='admin_users').exists()
        self.power_users = self.request.user.groups.filter(name='power_users').exists()

        user_status = f'{self.user_name} {self.user_email} admin_users={self.admin_users} power_users={self.power_users}'
        log.info("<=TaskOperationsREST=> Request: %s", user_status)
        request_options = f'operation_key:{self.operation_key} fake_run:{self.fake_run} task_id:{self.task_id} workers:{self.workers}'
        log.debug("<=TaskOperationsREST=> request_options: %s", request_options)

    def get(self, request=None):
        """
        Show task and doc

        :param request:
        :return:
        """
        self.metadata_options_set()
        if not self.operation_key:
            new_all_possible_operations = dict()
            all_possible_operations = self.task_operations()
            # all_possible_operations = [item for item in all_possible_operations.items()]
            for key, value in all_possible_operations.items():
                new_all_possible_operations.update({key: {'doc': value.__doc__.replace('\n', '').replace(' '*4, ' '), 'goto': self.goto_+key}})
            return Response(dict(new_all_possible_operations))
        else:
            operation = self.task_operations()
            if callable(operation):
                response = {self.operation_key: {'doc': operation.__doc__.replace('\n', '').replace(' '*4, ' '), 'goto': self.goto_+self.operation_key}}
            else:
                response = operation
            return Response(response)

    def post(self, request=None):
        """
        Run task.
        Response with task id if possible, or with method return \ response?
        :param request:
        :return:
        """
        self.metadata_options_set()
        if self.operation_key:
            run = self.task_operations()
            result = run()
            return Response(result)
        else:
            return Response(dict(error='No operation_key were specified!'))

    def get_task_status_by_id(self):
        """
        Get current status of task by it's id. If tack is running, show AsyncResult, if task is in the DB
        show DB result.
        Example: task_id=637b710f-4501-4414-b0fb-d4bc3d64bcc8;operation_key=get_task_status_by_id
        :return: task status
        """
        tasks = CeleryTaskmeta.objects.filter(task_id__exact=self.task_id)
        if tasks:
            log.debug("tasks from DB: %s", tasks)
            serializer = CeleryTaskmetaSerializer(tasks, many=True)
            return {'response': serializer.data}
        else:
            res = AsyncResult(self.task_id)
            task_res = dict(
                task_id=self.task_id,
                status=res.status,
                result=res.result,
                state=res.state,
                args=res.args,
            )
            log.debug("Task Async result: %s", task_res)
            return {'response': task_res}

    def tasks_get_registered(self):
        """
        Show all registered tasks. For all workers, if worker is not specified.
        https://docs.celeryproject.org/en/latest/userguide/workers.html#dump-of-registered-tasks
        :return
        """
        workers = self.workers
        resp = TasksOperations.tasks_get_registered(workers=workers)
        return {'response': resp}

    def tasks_get_active(self):
        """
        Show all active(running) tasks. For all workers, if worker is not specified.
        https://docs.celeryproject.org/en/latest/userguide/workers.html#dump-of-currently-executing-tasks
        :return
        """
        workers = self.workers
        resp = TasksOperations.tasks_get_active(workers=workers)
        return {'response': resp}

    def tasks_get_reserved(self):
        """
        Show all reserved(pending\\queued) tasks. For all workers, if worker is not specified.
        https://docs.celeryproject.org/en/latest/userguide/workers.html#dump-of-reserved-tasks
        :return
        """
        workers = self.workers
        resp = TasksOperations.tasks_get_reserved(workers=workers)
        return {'response': resp}

    def tasks_get_scheduled(self):
        """
        Show all scheduled tasks. For all workers, if worker is not specified.
        https://docs.celeryproject.org/en/latest/userguide/workers.html#dump-of-scheduled-eta-tasks
        :return
        """
        workers = self.workers
        resp = TasksOperations.tasks_get_scheduled(workers=workers)
        # resp = {
        #     "w_parsing@tentacle": [],
        #     "charlie@tentacle": [],
        #     "w_routines@tentacle": [],
        #     "alpha@tentacle": []
        # }
        return {'response': resp}

    def tasks_get_active_reserved(self):
        """
        Get all active/reserved tasks. For all workers, if worker is not specified.
        Show Link to official docs
        :return
        """
        workers = self.workers
        resp = TasksOperations.tasks_get_active_reserved(workers=workers)
        return {'response': resp}

    def tasks_get_results(self):
        """
        Get all tasks results, or specified results type.
        Please use /api/v1/octo/celery_task_meta/
        :return
        """
        resp = TasksOperations().tasks_get_results(task_id=self.task_id)
        return {'response': resp}

    def task_get_result(self):
        """
        Get task result, by task ID.
        Please use /api/v1/octo/celery_task_meta/
        :return
        """
        task_id = self.task_id
        resp = TasksOperations().tasks_get_results(task_id=task_id)
        return {'response': resp}

    def revoke_task_by_id(self):
        """
        Revoke task by task ID.
        Require: admin_users;
        https://docs.celeryproject.org/en/latest/userguide/workers.html#revoke-revoking-tasks
        :return
        """
        if not UserCheck.is_power(self.request.user):
            return {'error': 'User has no admin rights!'}
        task_id = self.task_id
        resp = TasksOperations.revoke_task_by_id(task_id=task_id)

        return {'response': resp}

    def revoke_tasks_active(self):
        """
        Revoke all active tasks.
        Require: admin_users;
        https://docs.celeryproject.org/en/latest/userguide/workers.html#revoke-revoking-tasks
        :return
        """
        if not UserCheck.is_power(self.request.user):
            return {'error': 'User has no admin rights!'}
        workers = self.workers
        log.debug("workers: %s", workers)
        resp = TasksOperations().revoke_tasks_active(workers=workers)
        return {'response': resp}

    def revoke_tasks_reserved(self):
        """
        Revoke all reserved tasks
        Require: admin_users;
        https://docs.celeryproject.org/en/latest/userguide/workers.html#revoke-revoking-tasks
        :return
        """
        if not UserCheck.is_power(self.request.user):
            return {'error': 'User has no admin rights!'}
        workers = self.workers
        resp = TasksOperations().revoke_tasks_reserved(workers=workers)
        return {'response': resp}

    def revoke_tasks_active_reserved(self):
        """
        Revoke all reserved and active tasks
        Require: admin_users;
        https://docs.celeryproject.org/en/latest/userguide/workers.html#revoke-revoking-tasks
        :return
        """
        if not UserCheck.is_power(self.request.user):
            return {'error': 'User has no admin rights!'}
        workers = self.workers
        resp = TasksOperations().revoke_tasks_active_reserved(workers=workers)
        return {'response': resp}

    def task_discard_all(self):
        """
        This will ignore all tasks waiting for execution, and they will be deleted from the messaging server.
        Require: admin_users;
        https://docs.celeryproject.org/en/latest/reference/celery.app.control.html#celery.app.control.Control.discard_all
        :return
        """
        if not UserCheck.is_power(self.request.user):
            return {'error': 'User has no admin rights!'}
        resp = TasksOperations().task_discard_all()
        return {'response': resp}

    def task_purge_all(self):
        """
        Discard all waiting tasks. This will ignore all tasks waiting for execution, and they will be deleted from the messaging server.
        Require: admin_users;
        https://docs.celeryproject.org/en/latest/reference/celery.app.control.html#celery.app.control.Control.purge
        :return
        """
        if not UserCheck.is_power(self.request.user):
            return {'error': 'User has no admin rights!'}
        resp = TasksOperations().task_purge_all()
        return {'response': resp}

    def get_workers_summary(self):
        """
        Inspect all available workers and see active and reserved tasks.
        https://docs.celeryproject.org/en/latest/userguide/workers.html#ping
        :return
        """
        workers = self.workers
        resp = TasksOperations().get_workers_summary(worker_name=workers)
        return {'response': resp}

    def worker_ping(self):
        """
        Ping worker. If worker is not specified - ping all.
        https://docs.celeryproject.org/en/latest/userguide/workers.html#ping
        :return
        """
        workers = self.workers
        resp = WorkerOperations().worker_ping(workers=workers)
        return {'response': resp}

    def worker_heartbeat(self):
        """
        HeatBeat worker. If worker is not specified - for all.
        https://docs.celeryproject.org/en/latest/reference/celery.app.control.html#celery.app.control.Control.heartbeat
        :return
        """
        workers = self.workers
        resp = WorkerOperations().worker_heartbeat(workers=workers)
        return {'response': resp}

    def worker_restart(self):
        """
        Restart worker. WARNING: This worker could become unavailable for site system!
        Require: admin_users;
        https://docs.celeryproject.org/en/latest/reference/celery.app.control.html#celery.app.control.Control.pool_restart
        :return
        """
        if not UserCheck.is_power(self.request.user):
            return {'error': 'User has no admin rights!'}
        workers = self.workers
        resp = WorkerOperations().worker_restart(workers=workers)
        return {'response': resp}


class AdminOperationsREST(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.operation_key = ''
        self.p4_conn = ''
        self.start_time = datetime.now().strftime('%Y-%m-%d_%H-%M')
        self.is_authenticated = ''
        # metadata:
        self.user_name = ''
        self.user_email = ''
        self.admin_users = ''
        self.power_users = ''
        # options:
        self.command_key = ''
        self.subject = ''
        self.addm_id = None
        self.addm_host = None
        self.addm_group = ''
        self.fake_run = False
        self.depot_path = p4_cred['dep_path']
        self.goto_ = 'http://'+curr_hostname+'/octo_admin/admin_operations/?operation_key='

    def task_operations(self):
        """
        Execute task operations or return task operation status.
        If no args passed - return operations dict to show user all possible variants.

        :param operation_key:
        :return:
        """
        operations = dict(
            addm_cleanup=self.addm_cleanup,
            addm_cmd_run=self.addm_cmd_run,
            addm_sync_shares=self.addm_sync_shares,
            addm_sync_utils=self.addm_sync_utils,
            p4_info=self.p4_info,
            p4_sync=self.p4_sync,
            p4_sync_force=self.p4_sync_force,
            parse_full=self.parse_full,
            cases_weight=self.cases_weight,
        )
        if self.operation_key:
            # If no such operation key - show this message:
            actions = operations.get(self.operation_key, 'No such operation key')
        else:
            actions = operations
        return actions

    def metadata_options_set(self):
        if self.request.POST:
            self.operation_key = self.request.POST.get('operation_key', None)
            self.fake_run = self.request.POST.get('fake_run', False)
            self.command_key = self.request.POST.get('command_key', None)
            self.addm_group = self.request.POST.get('addm_group', None)
            self.addm_id = self.request.POST.get('addm_id', None)
            self.addm_host = self.request.POST.get('addm_host', None)
            self.depot_path = self.request.POST.get('depot_path', p4_cred['dep_path'])
        elif self.request.GET:
            self.operation_key = self.request.GET.get('operation_key', None)
            self.fake_run = self.request.GET.get('fake_run', False)
            self.command_key = self.request.GET.get('command_key', None)
            self.addm_group = self.request.GET.get('addm_group', None)
            self.addm_id = self.request.GET.get('addm_id', None)
            self.addm_host = self.request.GET.get('addm_host', None)
            self.depot_path = self.request.GET.get('depot_path', p4_cred['dep_path'])

        self.is_authenticated = self.request.user.is_authenticated
        self.user_name = self.request.user.get_username()
        self.user_email = self.request.user.email

        self.admin_users = self.request.user.groups.filter(name='admin_users').exists()
        self.power_users = self.request.user.groups.filter(name='power_users').exists()

        user_status = f'{self.user_name} {self.user_email} admin_users={self.admin_users} power_users={self.power_users}'
        log.info("<=AdminOperations=> Request: %s", user_status)
        request_options = f'operation_key:{self.operation_key} fake_run:{self.fake_run} command_key:{self.command_key} addm_group:{self.addm_group}'
        log.debug("<=AdminOperations=> request_options: %s", request_options)

    def get(self, request=None):
        """
        Show admin task/function and doc

        :param request:
        :return:
        """
        self.metadata_options_set()
        if not self.operation_key:
            new_all_possible_operations = dict()
            all_possible_operations = self.task_operations()
            # all_possible_operations = [item for item in all_possible_operations.items()]
            for key, value in all_possible_operations.items():
                new_all_possible_operations.update({key: {'doc': value.__doc__.replace('\n', '').replace(' '*4, ' '), 'goto': self.goto_+key}})
            return Response(dict(new_all_possible_operations))
        else:
            operation = self.task_operations()
            if callable(operation):
                response = {self.operation_key: {'doc': operation.__doc__.replace('\n', '').replace(' '*4, ' '), 'goto': self.goto_+self.operation_key}}
                log.info(response)
            else:
                response = operation
                log.warning(response)
            return Response(response)

    def post(self, request=None):
        """
        Run task.
        Response with task id if possible, or with method return\response?
        operation_key=p4_sync_force;mode=mode;addm_group=addm_group;cmd_k=cmd_k

        :param request:
        :return:
        """
        self.metadata_options_set()
        if self.operation_key:
            run = self.task_operations()
            result = run()
            return Response(result)
        else:
            return Response(dict(error='No operation_key were specified!'))

    def check_user_rights(self):
        if self.request.user.is_authenticated:
            log.info("User auth OK!")

    def parse_full(self):
        """
        Run internal FS parse and P4 changes refresh procedure
        :return: success message
        """
        self.p4_conn = PerforceOperations().p4_initialize(debug=True)
        msg = LocalPatternsP4Parse().parse_and_changes_routine(
            sync_force=False, full=True, p4_conn=self.p4_conn)
        return {'task_id': 'add_here', 'msg': 'Run local parsing routine.'}

    def cases_weight(self):
        """ Calculate ETA for test cases based on previous execution logs for last 30 days.
        Require: admin_users;
        Example: operation_key=cases_weight
        :return {'task': t_pattern_weight_index.id}"""
        if not UserCheck.is_power(self.request.user):
            return {'error': 'User has no admin rights!'}
        t_tag = f'tag=t_pattern_weight_index;user_name={self.user_name};fake={self.fake_run};start_time={self.start_time}'
        t_pattern_weight_index = Runner.fire_t(TPatternParse.t_pattern_weight_index, fake_run=self.fake_run, t_args=[t_tag])
        return {'task_id': t_pattern_weight_index.id}

    def p4_info(self):
        """ Show current p4 depot status and details for account and workspace. Example: operation_key=p4_info
        :return: {'task': t_p4_info.id}
        """
        t_tag = f'tag=t_p4_info;user_name={self.user_name};fake={self.fake_run};start_time={self.start_time}'
        t_p4_info = Runner.fire_t(TPatternParse.t_p4_info, fake_run=self.fake_run, t_args=[t_tag])
        return {'task_id': t_p4_info.id}

    def p4_sync(self):
        """ Runs "sync" and parse local FS. Get max change (if not - #312830 from 2015), "filelog" the diff, "sync -f"
        then parse FS -> p4 clean -> p4 sync -> parse local -> insert in DB or shorter run: compare diff and add only update changes. Example: operation_key=p4_sync
        :return {'task': p4_sync_task.id}"""
        # Only sync and parse depot, no ADDM Sync here!
        t_tag = f'tag=t_p4_sync;user_name={self.user_name};fake={self.fake_run};start_time={self.start_time}'
        p4_sync_task = Runner.fire_t(TPatternParse.t_p4_sync, fake_run=self.fake_run, t_args=[t_tag],
                                     t_queue='w_parsing@tentacle.dq2',
                                     t_routing_key='parsing.perforce.AdminOperationsREST.p4_sync.TPatternParse.t_p4_sync')
        return {'task_id': p4_sync_task.id}

    def p4_sync_force(self):
        """ Execute routine for perforce "sync -f" will forced sync all files from p4 depot to Octopus FS.
        Require: admin_users;
        Example: operation_key=p4_sync_force
        :return{'task': t_p4_sync_force.id}"""
        if not UserCheck.is_power(self.request.user):
            return {'error': 'User has no admin rights!'}

        t_tag = f'tag=t_p4_sync_force;user_name={self.user_name};fake={self.fake_run};start_time={self.start_time}'
        t_p4_sync_force = Runner.fire_t(TPatternParse.t_p4_sync_force, fake_run=self.fake_run, t_args=[t_tag, self.depot_path],
                                        t_queue='w_parsing@tentacle.dq2', t_routing_key='parsing.perforce.AdminOperationsREST.p4_sync_force.TPatternParse.t_p4_sync_force')
        return {'task_id': t_p4_sync_force.id}

    def addm_cleanup(self):
        """ Run selected ADDM cleanup therapy.
        Require: admin_users;
        addm_group=()
        Example: operation_key=addm_cleanup;addm_group=alpha
        :return: mode: task.id
        """
        if not UserCheck.is_power(self.request.user):
            return {'error': 'User has no admin rights!'}

        command_key = [
            "show.addm.version",
            "test.kill",
            "tku.install.kill",
            "tw_scan_control.clear",
            "tw_pattern_management.remove_all",
            "wipe.tideway.data.installed.tpl",
            "tw_model_wipe.force",
            "wipe.addm.logs",
            "wipe.addm.pool",
            "wipe.addm.record",
            "wipe.rsync.logs",
            "wipe.tideway.syslogs",
            "wipe.tideway.TEMP",
            "wipe.tpl.files"
        ]
        commands_set = ADDMStaticOperations.select_operation(command_key)
        t_tag = f'tag=t_addm_cmd_routine.addm_cleanup;user_name={self.user_name};fake={self.fake_run};start_time={self.start_time}'
        t_kwargs = dict(
            command_key=command_key,
            commands_set=commands_set,
            subject=self.subject,
            user_name=self.user_name,
            user_mail=self.user_email,
            addm_group=self.addm_group,
            addm_host=self.addm_host,
            addm_id=self.addm_id,
            fake_run=self.fake_run
        )

        task = Runner.fire_t(TaskADDMService.t_addm_cmd_routine, fake_run=self.fake_run, t_args=[t_tag], t_kwargs=t_kwargs)
        # task = TaskADDMService.t_addm_cmd_routine.apply_async(args=[t_tag], kwargs=t_kwargs)
        return {'task_id': task.id}

    def addm_cmd_run(self):
        """ Run ADDM registered command. Commands should be added to Octopus system. (see /admin/run_core/addmcommands/)
        Require: admin_users;
        Options: (command_key=(), addm_group=()
        Example: operation_key=addm_cmd_run;addm_group=alpha;command_key=show.addm.version
        :return cmd_k: task.id """
        if not UserCheck.is_power(self.request.user):
            return {'error': 'User has no admin rights!'}
        command_key = self.command_key.split(',')
        # TODO: I can fill the variables of CMD string right here, if neded, using user input or extra input (like: upload_unzip)?
        commands_set = ADDMStaticOperations.select_operation(command_key)
        t_tag = f'tag=t_addm_cmd_routine.{self.command_key};user_name={self.user_name};fake={self.fake_run};start_time={self.start_time}'
        t_kwargs = dict(
            command_key=self.command_key.split(','),
            commands_set=commands_set,
            subject=self.subject,
            user_name=self.user_name,
            user_mail=self.user_email,
            addm_group=self.addm_group,
            addm_host=self.addm_host,
            addm_id=self.addm_id,
            fake_run=self.fake_run
        )
        task = Runner.fire_t(TaskADDMService.t_addm_cmd_routine, fake_run=self.fake_run, t_args=[t_tag],
                             t_kwargs=t_kwargs)
        return {'task_id': task.id}

    def addm_sync_shares(self):
        """ Execute routine for Octopus NFS -> ADDM sync all files for tests. Using rsync. Keys used: rsync.tku.data
        Options: addm_group=()
        Example: operation_key=addm_sync_shares;addm_group=alpha
        :return task: task.id"""
        t_tag = f'tag=t_addm_cmd_routine.addm_sync_shares;user_name={self.user_name};fake={self.fake_run};start_time={self.start_time}'
        command_key = [
            "rsync.tku.data",
        ]
        commands_set = ADDMStaticOperations.select_operation(command_key)
        t_kwargs = dict(
            command_key=command_key,
            commands_set=commands_set,
            subject=self.subject,
            user_name=self.user_name,
            user_mail=self.user_email,
            addm_group=self.addm_group,
            addm_host=self.addm_host,
            addm_id=self.addm_id,
            fake_run=self.fake_run
        )
        task = Runner.fire_t(TaskADDMService.t_addm_cmd_routine, fake_run=self.fake_run, t_args=[t_tag],
                             t_kwargs=t_kwargs)
        return {'task_id': task.id}

    def addm_sync_utils(self):
        """ Execute routine for Octopus NFS -> ADDM sync all files for test utils. Using rsync. keys used rsync.python.testutils, rsync.tideway.utils
        Require: admin_users;
        Options: addm_group=()
        Example: operation_key=addm_sync_utils;addm_group=alpha
        :return task: task.id"""
        if not UserCheck.is_power(self.request.user):
            return {'error': 'User has no admin rights!'}
        command_key = [
            "rsync.python.testutils",
            "rsync.tideway.utils",
        ]
        commands_set = ADDMStaticOperations.select_operation(command_key)
        t_tag = f'tag=t_addm_cmd_routine.addm_sync_utils;user_name={self.user_name};fake={self.fake_run};start_time={self.start_time}'
        t_kwargs = dict(
            command_key=command_key,
            commands_set=commands_set,
            subject=self.subject,
            user_name=self.user_name,
            user_mail=self.user_email,
            addm_group=self.addm_group,
            addm_host=self.addm_host,
            addm_id=self.addm_id,
            fake_run=self.fake_run
        )
        task = Runner.fire_t(TaskADDMService.t_addm_cmd_routine, fake_run=self.fake_run, t_args=[t_tag],
                             t_kwargs=t_kwargs)
        return {'task_id': task.id}


class ListAllAddmVmREST(viewsets.ModelViewSet):
    queryset = AddmDev.objects.all().order_by('addm_group')
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = AddmDevSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):

        disables = self.request.GET.get('disables', None)
        addm_name = self.request.GET.get('addm_name', None)
        addm_group = self.request.GET.get('addm_group', None)
        branch_lock = self.request.GET.get('branch_lock', None)

        queryset = AddmDev.objects.all()
        if disables:
            queryset = self.queryset.filter(disables__isnull=False)
        if addm_name:
            queryset = self.queryset.filter(addm_name__exact=addm_name)
        if addm_group:
            queryset = self.queryset.filter(addm_group__exact=addm_group)
        if branch_lock:
            queryset = self.queryset.filter(branch_lock__exact=branch_lock)

        return queryset.order_by('addm_group')


class AdminFunctions:
    """
    Functions for admin usage or for powered users.
    """

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def _old_addm_buttons_page(request):
        page_widgets = loader.get_template('addm_buttons.html')
        user_name, user_string = UserCheck().user_string_f(request)

        log.debug("<=WEB OCTO AMD=> addm_buttons_page(): %s", user_string)
        all_addms = AddmDev.objects.order_by('addm_group', 'addm_name')

        return HttpResponse(page_widgets.render(dict(SUBJECT='', ALL_ADDMS=all_addms), request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def celery_beat_crontabschedules(request):
        """
        Show schedulers
        :param request:
        :return:
        """
        # from octo.models import DjangoCeleryBeatPeriodictask
        from django_celery_beat.models import PeriodicTask
        user_name, user_string = UserCheck().user_string_f(request)
        log.debug("<=SEL OUT=>   celery_beat_crontabschedules(): %s", user_string)

        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=DEV OCTO AMD=> dev_cron_items(): %s", user_str)

        planned_tasks = PeriodicTask.objects.filter(enabled__exact=1)
        simple_output = loader.get_template('dev_debug_workbench/debug/dev_cron_simple.html')

        widgets = dict(
            SUBJECT='Select CRON tasks.',
            planned_tasks=planned_tasks,
        )

        return HttpResponse(simple_output.render(widgets, request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def reset_cron_last_run(request):
        from django_celery_beat.models import PeriodicTask
        user_name, user_string = UserCheck().user_string_f(request)
        page_widgets = loader.get_template('service/task-action-request-added-started.html')
        log.debug("<=WEB OCTO AMD=>   reset_cron_last_run(): %s", user_string)

        info_string = dict(user_name=user_name)
        PeriodicTask.objects.update(last_run_at=None)

        subject = "User request: '{}' {}.".format("reset_cron_last_run", info_string)
        return HttpResponse(page_widgets.render(dict(SUBJECT=subject), request))

