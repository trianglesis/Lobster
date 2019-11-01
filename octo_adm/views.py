"""
OCTO ADM - pages and widgets and functions.
"""

import logging
from time import sleep
from datetime import datetime

from django.template import loader
from django.http import HttpResponse
from django.conf import settings

from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required

from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated

from run_core.models import AddmDev
from run_core.addm_operations import ADDMOperations
from run_core.p4_operations import PerforceOperations
from run_core.local_operations import LocalPatternsP4Parse

from octo.models import CeleryTaskmeta

from octo.helpers.tasks_run import Runner
from octo.helpers.tasks_mail_send import Mails
from octo.helpers.tasks_oper import TasksOperations, WorkerOperations, NewTaskOper

from octo_adm.user_operations import UserCheck
from octo_adm.request_service import SelectorRequestsHelpers
from octo_adm.tasks import TaskADDMService, ADDMCases

from octo_tku_patterns.tasks import TPatternParse

log = logging.getLogger("octo.octologger")
curr_hostname = getattr(settings, 'SITE_DOMAIN', None)


class AdminWorkbench(TemplateView):
    pass


def fake_function(*args, **kwargs):
    # Show doc for function executed? This can be helpful for bootstrap toast info on Front side!
    log.debug("Run pseudo task with args=%s kwargs=%s", args, kwargs)
    return dict(
        task_answer = 'Yup, something doing.',
        task_id='8943576894567-4589734589347-i834765783465',
    )


class TaskOperationsREST(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.start_time = datetime.now().strftime('%Y-%m-%d_%H-%M')
        self.user_name = ''
        self.admin_users = ''
        self.power_users = ''

    @staticmethod
    def task_operations(operation_key=None):
        """
        Execute task operations or return task operation status.
        If no args passed - return operations dict to show user all possible variants.

        :param operation_key:
        :return:
        """
        goto_ = 'http://'+curr_hostname+'/octo_admin/task_operation/?operation_key='
        operations = dict(
            tasks_get_registered      = dict(func=TasksOperations.tasks_get_registered, args='', kwargs='workers',
                                             doc='Show all registered tasks. For all workers, if worker is not specified.',
                                             goto=f'{goto_}tasks_get_registered',
                                             wiki='https://docs.celeryproject.org/en/latest/userguide/workers.html#dump-of-registered-tasks'),
            tasks_get_active          = dict(func=TasksOperations.tasks_get_active, args='', kwargs='workers',
                                             doc='Show all active(running) tasks. For all workers, if worker is not specified.',
                                             goto=f'{goto_}tasks_get_active',
                                             wiki='https://docs.celeryproject.org/en/latest/userguide/workers.html#dump-of-currently-executing-tasks'),
            tasks_get_reserved        = dict(func=TasksOperations.tasks_get_reserved, args='', kwargs='workers',
                                             doc='Show all reserved(pending\\queued) tasks. For all workers, if worker is not specified.',
                                             goto=f'{goto_}tasks_get_reserved',
                                             wiki='https://docs.celeryproject.org/en/latest/userguide/workers.html#dump-of-reserved-tasks'),
            tasks_get_scheduled       = dict(func=TasksOperations.tasks_get_scheduled, args='', kwargs='workers',
                                             doc='Show all scheduled tasks. For all workers, if worker is not specified.',
                                             goto=f'{goto_}tasks_get_scheduled',
                                             wiki='https://docs.celeryproject.org/en/latest/userguide/workers.html#dump-of-scheduled-eta-tasks'),
            tasks_get_active_reserved = dict(func=TasksOperations.tasks_get_active_reserved, args='', kwargs='workers',
                                             doc='Get all active/reserved tasks. For all workers, if worker is not specified.',
                                             goto=f'{goto_}tasks_get_active_reserved',
                                             wiki='Show Link to official docs'),

            tasks_get_results         = dict(func=TasksOperations.tasks_get_results, args='', kwargs='task_id',
                                             doc='Get all tasks results, or specified results type.',
                                             goto=f'{goto_}tasks_get_results',
                                             wiki='Please use /api/v1/octo/celery_task_meta/'),  # Show all tasks results by type? FAILED, SUCCESS?
            task_get_result           = dict(func=TasksOperations.tasks_get_results, args='', kwargs='task_id',
                                             doc='Get task result, by task ID.',
                                             goto=f'{goto_}task_get_result',
                                             wiki='Please use /api/v1/octo/celery_task_meta/'),  # Show single task result by id?

            task_revoke_by_id           = dict(func=TasksOperations.revoke_task_by_id, args='', kwargs='task_id',
                                               doc='Revoke task by task ID.',
                                               goto=f'{goto_}task_revoke_by_id',
                                               wiki='https://docs.celeryproject.org/en/latest/userguide/workers.html#revoke-revoking-tasks'),
            task_revoke_active          = dict(func=TasksOperations().revoke_tasks_active, args='', kwargs='workers',
                                               doc='Revoke all active tasks.',
                                               goto=f'{goto_}task_revoke_active',
                                               wiki='https://docs.celeryproject.org/en/latest/userguide/workers.html#revoke-revoking-tasks'),
            task_revoke_reserved        = dict(func=TasksOperations().revoke_tasks_reserved, args='', kwargs='workers',
                                               doc='Revoke all reserved tasks',
                                               goto=f'{goto_}task_revoke_reserved',
                                               wiki='https://docs.celeryproject.org/en/latest/userguide/workers.html#revoke-revoking-tasks'),
            task_revoke_active_reserved = dict(func=TasksOperations().revoke_tasks_active_reserved, args='', kwargs='workers',
                                               doc='Revoke all reserved and active tasks',
                                               goto=f'{goto_}task_revoke_active_reserved',
                                               wiki='https://docs.celeryproject.org/en/latest/userguide/workers.html#revoke-revoking-tasks'),
            task_discard_all            = dict(func=TasksOperations.task_discard_all, args='', kwargs='',
                                               doc='This will ignore all tasks waiting for execution, and they will be deleted from the messaging server.',
                                               goto=f'{goto_}task_discard_all',
                                               wiki='https://docs.celeryproject.org/en/latest/reference/celery.app.control.html#celery.app.control.Control.discard_all'),
            task_purge_all              = dict(func=TasksOperations.task_purge_all, args='', kwargs='',
                                               doc='Discard all waiting tasks. This will ignore all tasks waiting for execution, and they will be deleted from the messaging server.',
                                               goto=f'{goto_}task_purge_all',
                                               wiki='https://docs.celeryproject.org/en/latest/reference/celery.app.control.html#celery.app.control.Control.purge'),

            workers_summary  = dict(func=TasksOperations.get_workers_summary, args='', kwargs='workers',
                                    doc='Inspect all available workers and see active and reserved tasks.',
                                    goto=f'{goto_}workers_summary',
                                    wiki='https://docs.celeryproject.org/en/latest/userguide/workers.html#ping'),
            worker_ping      = dict(func=WorkerOperations().worker_ping, args='', kwargs='workers',
                                    doc='Ping worker. If worker is not specified - ping all.',
                                    goto=f'{goto_}worker_ping',
                                    wiki='https://docs.celeryproject.org/en/latest/userguide/workers.html#ping'),
            worker_heartbeat = dict(func=WorkerOperations().worker_heartbeat, args='', kwargs='workers',
                                    doc='HeatBeat worker. If worker is not specified - for all.',
                                    goto=f'{goto_}worker_heartbeat',
                                    wiki='https://docs.celeryproject.org/en/latest/reference/celery.app.control.html#celery.app.control.Control.heartbeat'),
            worker_restart   = dict(func=WorkerOperations.worker_restart, args='', kwargs='workers',
                                    doc='Restart worker. WARNING: This worker could become unavailable for site system!',
                                    goto=f'{goto_}worker_restart',
                                    wiki='https://docs.celeryproject.org/en/latest/reference/celery.app.control.html#celery.app.control.Control.pool_restart'),
        )
        if operation_key:
            actions = operations.get(operation_key, 'No such operation key')
        else:
            actions = operations
        return actions

    def get(self, request=None):
        """
        Show task and doc

        :param request:
        :return:
        """
        operation_key = self.request.GET.get('operation_key', None)
        if not operation_key:
            new_all_possible_operations = dict()
            all_possible_operations = self.task_operations()
            # all_possible_operations = [item for item in all_possible_operations.items()]
            for key, value in all_possible_operations.items():
                # noinspection PyUnresolvedReferences
                value.pop("func")
                new_all_possible_operations.update({key: value})
            return Response(dict(new_all_possible_operations))
        else:
            operation = self.task_operations(operation_key=operation_key)
            # If there is a dict, if no - there is no such operation key:
            if isinstance(operation, dict):
                operation.pop('func')
            return Response(operation)

    def post(self, request=None):
        """
        Run task.
        Response with task id if possible, or with method return \ response?

        :param request:
        :return:
        """
        operation_key = self.request.POST.get('operation_key', None)
        task_id = self.request.POST.get('task_id', None)
        workers = self.request.POST.get('workers', None)
        # TO RUN:
        if operation_key:
            case = self.task_operations(operation_key)
            run = case['func']
            if case.get('kwargs'):
                kwargs = dict()  # Update this set with passed arguments and values from request.
                # Compose arguments:
                if workers:  # Split workers "list" only if argument is present in request, otherwise just pass None.
                    workers = workers.split(',')
                    workers = [worker+'@tentacle' for worker in workers]
                    kwargs.update(workers=workers)
                else:
                    kwargs.update(workers=None)  # Keep arg, but with None.

                if task_id:  # Only add task id if argument passed with request.
                    kwargs.update(task_id=task_id)
                else:
                    kwargs.update(task_id=None)  # Keep arg, but with None.

                # RUN:
                result = run(**kwargs)
            else:
                result = run()

            return Response(result)
        else:
            return Response(dict(error='No operation_key were specified!'))


class AdminOperations(APIView):
    """
        TODO: Add admin/superuser check later.
    """

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
        self.mode = ''
        self.cmd_k = ''
        self.subject = ''
        self.addm_group = ''
        self.fake_run = True

    def task_operations(self, operation_key=None):
        """
        Execute task operations or return task operation status.
        If no args passed - return operations dict to show user all possible variants.

        :param operation_key:
        :return:
        """
        goto_ = 'http://'+curr_hostname+'/octo_admin/admin_operations/?operation_key='
        operations = dict(
            addm_cleanup  = dict(func=self.addm_cleanup, args='', kwargs='mode, addm_group',
                                 doc='Run selected ADDM cleanup therapy. Options: (mode=(weekly, daily, tests), addm_group=(alpha,beta,...))',
                                 goto=f'{goto_}addm_cleanup',
                                 wiki='Example: operation_key=addm_cleanup;addm_group=alpha;mode=weekly'),
            addm_cmd_run  = dict(func=self.addm_cmd_run, args='', kwargs='cmd_k, addm_group',
                                 doc='Run ADDM registered command. Commands should be added to Octopus system. Options: (cmd_k=(TODO: Show all cmd_k?), addm_group=(alpha,beta,...))',
                                 goto=f'{goto_}addm_cmd_run',
                                 wiki='Example: operation_key=addm_cmd_run;addm_group=alpha;cmd_k=show_v'),

            addm_sync_shares = dict(func=self.addm_sync_shares, args='', kwargs='addm_group',
                                    doc='Execute routine for Octopus NFS -> ADDM sync all files for tests. Using rsync. Options: (addm_group=(alpha,beta,...))',
                                    goto=f'{goto_}addm_sync_shares',
                                    wiki='Example: operation_key=addm_sync_shares;addm_group=alpha'),

            p4_info       = dict(func=self.p4_info, args='', kwargs='',
                                 doc='Show current p4 depot status and details for account and workspace.',
                                 goto=f'{goto_}p4_info',
                                 wiki='Example: operation_key=p4_info'),
            p4_sync       = dict(func=self.p4_sync, args='', kwargs='',
                                 doc='Runs "sync" and parse local FS. Get max change (if not - #312830 from 2015), "filelog" the diff, "sync -f" '
                                     'then parse FS -> p4 clean -> p4 sync -> parse local -> insert in DB or shorter run: compare diff and add only update changes.',
                                 goto=f'{goto_}p4_sync',
                                 wiki='Example: operation_key=p4_sync'),
            p4_sync_force = dict(func=self.p4_sync_force, args='', kwargs='',
                                 doc='Execute routine for perforce "sync -f" will forced sync all files from p4 depot to Octopus FS. Options: (depot_path=//depot/branch/...)',
                                 goto=f'{goto_}p4_sync_force',
                                 wiki='Example: operation_key=p4_sync_force'),
            cases_weight  = dict(func=self.cases_weight, args='', kwargs='',
                                 doc='Calculate ETA for test cases based on previous execution logs for last 30 days.',
                                 goto=f'{goto_}cases_weight',
                                 wiki='Example: operation_key=cases_weight'),
        )
        if operation_key:
            # If no such operation key - show this message:
            actions = operations.get(operation_key, 'No such operation key')
        else:
            actions = operations
        return actions

    def metadata_options_set(self):
        self.operation_key = self.request.POST.get('operation_key', None)
        self.fake_run = self.request.POST.get('fake_run', True)  # TODO: Debug, remove default True

        self.is_authenticated = self.request.user.is_authenticated
        self.user_name = self.request.user.get_username()
        self.user_email = self.request.user.email

        self.cmd_k = self.request.POST.get('cmd_k', None)
        self.mode = self.request.POST.get('mode', None)
        self.addm_group = self.request.POST.get('addm_group', None)

        self.admin_users = self.request.user.groups.filter(name='admin_users').exists()
        self.power_users = self.request.user.groups.filter(name='power_users').exists()

        user_status = f'{self.user_name} {self.user_email} admin_users={self.admin_users} power_users={self.power_users}'
        log.info("<=AdminOperations=> Request: %s", user_status)
        request_options = f'operation_key:{self.operation_key} fake_run:{self.fake_run} cmd_k:{self.cmd_k} mode:{self.mode} addm_group:{self.addm_group}'
        log.debug("<=AdminOperations=> request_options: %s", request_options)

    def get(self, request=None):
        """
        Show admin task/function and doc

        :param request:
        :return:
        """
        operation_key = self.request.GET.get('operation_key', None)
        if not operation_key:
            new_all_possible_operations = dict()
            all_possible_operations = self.task_operations()
            for key, value in all_possible_operations.items():
                # noinspection PyUnresolvedReferences
                value.pop("func")
                new_all_possible_operations.update({key: value})
            return Response(dict(new_all_possible_operations))
        else:
            operation = self.task_operations(operation_key=operation_key)
            # If there is a dict, if no - there is no such operation key:
            if isinstance(operation, dict):
                operation.pop('func')
            return Response(operation)

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
            case = self.task_operations(self.operation_key)
            run = case['func']
            result = run()
            return Response(result)
        else:
            return Response(dict(error='No operation_key were specified!'))

    def parse_full(self):
        self.p4_conn = PerforceOperations().p4_initialize(debug=True)
        msg = LocalPatternsP4Parse().parse_and_changes_routine(
            sync_force=False, full=True, p4_conn=self.p4_conn)
        return msg

    def cases_weight(self):
        t_tag = f'tag=t_pattern_weight_index;user_name={self.user_name};fake={self.fake_run};start_time={self.start_time}'
        t_pattern_weight_index = Runner.fire_t(TPatternParse.t_pattern_weight_index, fake_run=self.fake_run, t_args=[t_tag])
        return {'task': t_pattern_weight_index.id}

    def p4_info(self):
        t_tag = f'tag=t_p4_info;user_name={self.user_name};fake={self.fake_run};start_time={self.start_time}'
        t_p4_info = Runner.fire_t(TPatternParse.t_p4_info, fake_run=self.fake_run, t_args=[t_tag])
        return {'task': t_p4_info.id}

    def p4_sync(self):
        # Only sync and parse depot, no ADDM Sync here!
        t_tag = f'tag=t_p4_sync;user_name={self.user_name};fake={self.fake_run};start_time={self.start_time}'
        p4_sync_task = Runner.fire_t(TPatternParse.t_p4_sync, fake_run=self.fake_run, t_args=[t_tag])
        return {'task': p4_sync_task.id}

    def p4_sync_force(self):
        t_tag = f'tag=t_p4_sync_force;user_name={self.user_name};fake={self.fake_run};start_time={self.start_time}'
        t_p4_sync_force = Runner.fire_t(TPatternParse.t_p4_sync_force, fake_run=self.fake_run, t_args=[t_tag])
        return {'task': t_p4_sync_force.id}

    def addm_cleanup(self):
        clean_out = ADDMCases().clean_addm(
            mode=self.mode,
            subject=self.subject,
            user_name=self.user_name,
            user_mail=self.user_email,
            addm_group=self.addm_group,
            fake_run=self.fake_run,
        )
        return {self.mode: clean_out}

    def addm_cmd_run(self):
        cmd_out = ADDMCases().addm_cmd(
            cmd_k=self.cmd_k,
            subject=self.subject,
            user_name=self.user_name,
            user_mail=self.user_email,
            addm_group=self.addm_group,
            fake_run=self.fake_run,
        )
        return {self.cmd_k: cmd_out}

    def addm_sync_shares(self):
        addm_set = ADDMOperations.select_addm_set(addm_group=self.addm_group)
        t_tag = f'tag=t_addm_rsync_threads;addm_group={self.addm_group};user_name={self.user_name};fake={self.fake_run};'
        t_addm_rsync_threads = Runner.fire_t(TPatternParse().t_addm_rsync_threads, fake_run=self.fake_run,
                                             t_args=[t_tag], t_kwargs=dict(addm_items=list(addm_set)),
                                             t_queue=f'{self.addm_group}@tentacle.dq2',
                                             t_routing_key=f'TExecTest.t_addm_rsync_threads.{self.addm_group}')
        return {'task': t_addm_rsync_threads.id}


class ListAllAddmVmREST(APIView):
    pass


class AdminFunctions:
    """
    Functions for admin usage or for powered users.
    """

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def addm_workbench_widgets(request):
        """
        Draw useful widgets for workbench page.

        :param request:
        :return:
        """
        user_name, user_string = UserCheck().user_string_f(request)
        log.debug("<=MAIN Widgets=> workbench_widgets(): %s", user_string)
        page_widgets = loader.get_template('addm_workbench/addm_workbench_widgets.html')
        return HttpResponse(page_widgets.render(dict(SUBJECT = "", ACTIVE=True), request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def addm_buttons_page(request):
        page_widgets = loader.get_template('addm_buttons.html')
        user_name, user_string = UserCheck().user_string_f(request)

        log.debug("<=WEB OCTO AMD=> addm_buttons_page(): %s", user_string)
        all_addms = AddmDev.objects.order_by('addm_group', 'addm_name')

        return HttpResponse(page_widgets.render(dict(SUBJECT='', ALL_ADDMS=all_addms), request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def tasks_inspection_web(request):
        """
        Collect all current tasks statuses and show.

        :param request:
        :return:
        """

        user_name, user_string = UserCheck().user_string_f(request)
        worker_name = request.GET.get('worker_name', False)
        tasks_inspection = TasksOperations()
        log.debug("<=WEB OCTO AMD=>   tasks_inspection_web(): %s", user_string)

        task_statuses_page = loader.get_template('tasks_statuses.html')

        subject = "All tasks statuses in system. On user {0} request.".format(user_name)
        get_all_tasks_statuses = tasks_inspection.get_all_tasks_statuses(worker_name=worker_name)
        inspect_workers = get_all_tasks_statuses['inspect_workers']

        active_workers = []
        task_active = inspect_workers['active']
        for worker_k, worker_v in task_active.items():
            # log.debug("task_active.items(): worker_k %s, worker_v%s", worker_k, worker_v)
            worker_statuses_str = "<li>ACTIVE TASKS - " \
                                  "Worker name: <b>{}</b> " \
                                  "tasks len <b>{}</b> " \
                                  "tasks raw <i>{}</i></li>".format(worker_k, len(worker_v), worker_v)
            active_workers.append(worker_statuses_str)

        reserved_workers = []
        task_reserved = inspect_workers['reserved']
        for worker_k, worker_v in task_reserved.items():
            # log.debug("task_reserved.items(): worker_k %s, worker_v%s", worker_k, worker_v)
            worker_statuses_str = "<li>RESERVED TASKS - " \
                                  "Worker name: <b>{}</b> " \
                                  "tasks len <b>{}</b> " \
                                  "tasks raw <i>{}</i></li>".format(worker_k, len(worker_v), worker_v)
            reserved_workers.append(worker_statuses_str)

        contxt = dict(
            TASK_RESULT=tasks_inspection,
            INSPECT_WORKERS=inspect_workers,
            REGISTERED=inspect_workers['registered'],
            ACTIVE=task_active,
            ACTIVE_WORKERS=active_workers,
            SCHEDULED=inspect_workers['scheduled'],
            RESERVED=task_reserved,
            RESERVED_WORKERS=reserved_workers,
            SUBJECT=subject)
        return HttpResponse(task_statuses_page.render(contxt, request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def workers_raw(request):
        """
        Show all available empty workers
        OR Random empty worker
        :param request:
        :return:
        """
        workers_list = request.GET.get('workers_list', None)
        page_widgets = loader.get_template('worker_active_reserved.html')

        workers_d = SelectorRequestsHelpers().get_raw_w(workers_list=workers_list)
        subject = "RAW Active and reserved tasks on selected workers by default. Random chosen is below."

        return HttpResponse(page_widgets.render(dict(WORKERS=workers_d.get('w_dict'),
                                                     WORKER_MIN=workers_d.get('worker_min'),
                                                     WORKER_MAX=workers_d.get('worker_max'),
                                                     INSPECTED=workers_d.get('inspected'),
                                                     EXCLUDED_LIST=workers_d.get('excluded_list'),
                                                     INCLUDED_LIST=workers_d.get('included_list'),
                                                     SUBJECT=subject
                                                     ), request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def workers_active_reserved(request):
        """
        Show all available empty workers
        OR Random empty worker
        :param request:
        :return:
        """
        workers_list = request.GET.get('workers_list', None)
        page_widgets = loader.get_template('worker_active_reserved.html')

        workers_d = SelectorRequestsHelpers().get_free_included_w(workers_list=workers_list)
        subject = "Active and reserved tasks on included workers by default. Random chosen is below."

        return HttpResponse(page_widgets.render(dict(WORKERS=workers_d.get('w_dict'),
                                                     WORKERS_EXCLUDED=workers_d.get('w_ex_dict'),
                                                     WORKER_MIN=workers_d.get('worker_min'),
                                                     WORKER_MAX=workers_d.get('worker_max'),
                                                     INSPECTED=workers_d.get('inspected'),
                                                     INSPECTED_EXCLUDED=workers_d.get('inspected_excluded'),
                                                     EXCLUDED_LIST=workers_d.get('excluded_list'),
                                                     INCLUDED_LIST=workers_d.get('included_list'),
                                                     SUBJECT=subject
                                                     ), request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def workers_active_reserved_short(request):
        """
        Show all available empty workers shorter
        OR Random empty worker
        :param request:
        :return:
        """
        workers_list = request.GET.get('workers_list', None)
        page_widgets = loader.get_template('service/task-action-request-added-started.html')
        workers_d_short = SelectorRequestsHelpers().get_free_included_w_task(workers_list=workers_list)
        if not workers_d_short:
            subject = "There are no available workers to start test, please check later."
        else:
            subject = "Current min queue worker is: '{}' *note '@{}' is removed from w. name".format(workers_d_short,
                                                                                                     'tentacle')
        return HttpResponse(page_widgets.render(dict(SUBJECT=subject), request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.service_run', login_url='/unauthorized_banner/')
    def addm_cleanup(request):
        """
        Run selected ADDM cleanup therapy.

        :param request:
        :return:
        """
        page_widgets = loader.get_template('service/task-action-request-added-started.html')
        user_name, user_string = UserCheck().user_string_f(request)
        mode = request.GET.get('mode', None)
        addm_group = request.GET.get('addm_group')
        subject = "User request '{} {}' queued! {} on {}".format("addm_cleanup", mode, user_string, addm_group)
        log.debug("<=WEB OCTO AMD=>   addm_cleanup(): mode=%s, %s", mode, user_string)

        ADDMCases().clean_addm(mode=mode, subject=subject, addm_group=addm_group, user_name=user_name)
        Mails.short(subject=subject, body=subject, send_to=[request.user.email])
        return HttpResponse(page_widgets.render(dict(SUBJECT=subject), request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.service_run', login_url='/unauthorized_banner/')
    def addm_custom_cmd(request):
        page_widgets = loader.get_template('service/task-action-request-added-started.html')
        user_name, user_string = UserCheck().user_string_f(request)

        log.debug("<=WEB OCTO AMD=>   addm_custom_cmd(): %s", user_string)
        addm_group = request.GET.get('addm_group', None)  # addm_group=alpha
        cmd_k = request.GET.get('cmd_k', None)  # ;cmd_k=tw_model_wipe
        fake_run = request.GET.get('fake_run', False)

        subject = "User request '{}'. queued! {} on {}".format(cmd_k, user_string, addm_group)

        t_tag = 'addm_custom_cmd|cmd_k={};addm_group={};user_name={user_name}'
        Runner.fire_t(TaskADDMService.t_routine_addm_cmd, fake_run=fake_run,
                      t_args=[t_tag],
                      t_kwargs=dict(cmd_k=cmd_k, subject=subject, addm_group=addm_group, user_name=user_name))
        Mails.short(subject=subject, body=subject, send_to=[request.user.email])
        return HttpResponse(page_widgets.render(dict(SUBJECT=subject), request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.service_run', login_url='/unauthorized_banner/')
    def addm_sync_shares(request):
        page_widgets = loader.get_template('service/task-action-request-added-started.html')
        user_name, user_string = UserCheck().user_string_f(request)
        addm_group = request.GET.get('addm_group', None)  # addm_group=alpha
        fake_run = request.GET.get('fake_run', False)
        subject = "User request 'ADDM SYNC shares'. queued! {} on {}".format(user_string, addm_group)

        addm_set = ADDMOperations.select_addm_set(addm_group=addm_group)

        log.debug("<=TaskPrepare=> Adding task to sync addm group: '%s'", addm_group)
        t_tag = f'tag=t_addm_rsync_threads;addm_group={addm_group};user_name={user_name};' \
                f'fake={fake_run};'
        Runner.fire_t(TPatternParse().t_addm_rsync_threads, fake_run=fake_run,
                      t_args=[t_tag], t_kwargs=dict(addm_items=list(addm_set)),
                      t_queue=addm_group + '@tentacle.dq2',
                      t_routing_key='TExecTest.t_addm_rsync_threads.{0}'.format(addm_group))

        Mails.short(subject=subject, body=subject, send_to=[request.user.email])
        return HttpResponse(page_widgets.render(dict(SUBJECT=subject), request))

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
    def celery_tasks_result(request):
        """
        Get table of celery tasks and statuses.

        Draw tables of failed tasks at first,
        then - maybe add all other?

        :param request:
        :return:
        """
        user_name, user_string = UserCheck().user_string_f(request)
        workers_status_t = loader.get_template('celery_tasks_result.html')
        task_status = request.GET.get('task_status', 'FAILURE')
        log.debug("<=SEL OUT=> celery_tasks_result(): %s", user_string)

        # all_tasks = DjangoTableOper().select_django_celery_tasks_result(mode=task_status)
        all_tasks = CeleryTaskmeta.objects.filter(status__exact=task_status).order_by('-date_done').values('id',
                                                                                                           'task_id',
                                                                                                           'status',
                                                                                                           'date_done',
                                                                                                           'traceback')

        contxt = dict(
            ALL_TASKS=all_tasks,
            ALL_TASKS_LEN=len(all_tasks),
            TASK_STATUS=task_status,
            SUBJECT='')

        return HttpResponse(workers_status_t.render(contxt, request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.test_run', login_url='/unauthorized_banner/')
    def p4_sync_force(request):
        """

        :return:
        """
        page_widgets = loader.get_template('service/task-action-request-added-started.html')
        user_name, user_string = UserCheck().user_string_f(request)

        subject = "Please set depot_path!"
        branch = request.GET.get('branch', False)
        depot_path = request.GET.get('depot_path', False)
        fake_run = request.GET.get('fake_run', False)

        if not depot_path:
            if branch == 'tkn_main':
                depot_path = '//addm/tkn_main/...'
            elif branch == 'tkn_ship':
                depot_path = '//addm/tkn_ship/...'
            else:
                return HttpResponse(page_widgets.render(dict(SUBJECT=subject), request))

        log.debug("<=WEB OCTO AMD=> p4_sync_force(): %s", user_string)
        if depot_path:
            info_string = dict(depot_path=depot_path, user_name=user_name, )
            Runner.fire_t(TPatternParse.t_p4_sync_force, fake_run=fake_run,
                          t_args=['tag=p4_sync_force;type=request;branch={};user={};'.format(
                              branch, user_name), depot_path]
                          )
            subject = "User request: '{}' {}.".format("p4_sync_force", info_string)
        Mails.short(subject=subject, body=subject, send_to=[request.user.email])
        return HttpResponse(page_widgets.render(dict(SUBJECT=subject), request))

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


class CeleryInteract:
    """
    Actions with celery and its tasks and workers. Should not return anything else than celery reports.
    """

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def workers_status(request):
        """
        Get all tasks from al workers and show each for each.

        :param request:
        :return:
        """
        user_name, user_string = UserCheck().user_string_f(request)
        workers_status_t = loader.get_template('service/workers_status.html')
        log.debug("<=SEL OUT=>   workers_status(): %s", user_string)

        workers_task = SelectorRequestsHelpers().workers_all()
        contxt = dict(WORKERS_ACTIVE_TASKS=workers_task['workers_active_tasks'],
                      WORKERS_RESERVED_TASKS=workers_task['workers_reserved_tasks'], )
        return HttpResponse(workers_status_t.render(contxt, request))

    # Workers data for ADDM:
    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def workers_status_single(request):
        """

        :param request:
        :return:
        """
        user_name, user_str = UserCheck().user_string_f(request)
        workers_status_t = loader.get_template('service/workers_status.html')

        worker_name = request.GET.get('worker_name', 'alpha')
        log.debug("<=SEL OUT=>   workers_status(): %s", user_str)
        subject = "Tasks for {} . On user {} request.".format(worker_name, user_name)

        workers_dict = SelectorRequestsHelpers().worker_inspect_single(worker_name)

        contxt = dict(
            WORKERS_ACTIVE_TASKS=workers_dict['workers_active_tasks'],
            WORKERS_RESERVED_TASKS=workers_dict['workers_reserved_tasks'],
            RAW_TASK_ACTIVE=workers_dict['task_active'],
            RAW_TASK_RESERVED=workers_dict['task_reserved'],
            WORKER_NAME=worker_name,
            SUBJECT=subject)

        return HttpResponse(workers_status_t.render(contxt, request))

    @staticmethod
    @permission_required('run_core.task_revoke', 'run_core.task_manage')
    def revoke_task_by_id(request):
        """
        Request with task_id in it - to terminate selected task.

        :param request:
        :return:
        """
        workers_status_t = loader.get_template('service/workers_status.html')
        user_name, user_str = UserCheck().user_string_f(request)

        task_id = request.GET.get('task_id', None)
        terminate = request.GET.get('terminate', False)
        worker_name = request.GET.get('worker_name', False)

        log.debug("<=SEL OUT=>   revoke_task_by_id(): %s", user_str)

        if terminate:
            subject = "Killing task_id: {} - terminating proc. On user {} request. Task list refreshed...".format(
                task_id, user_name)
        else:
            subject = "Killing task_id: {}. On user {} request. Task list refreshed...".format(task_id, user_name)

        log.debug("<=SEL OUT=> revoke_task_by_id() task_id: %s terminate: %s", task_id, terminate)
        TasksOperations().revoke_task_by_id(task_id, terminate)

        # get new items after current task was killed. # When revoked from ADDM worker page:
        if worker_name:
            if "@" not in worker_name:
                worker_name = '{}@tentacle'.format(worker_name)
            workers_dict = SelectorRequestsHelpers().worker_inspect_single(worker_name)
            contxt = dict(
                WORKERS_ACTIVE_TASKS=workers_dict['workers_active_tasks'],
                WORKERS_RESERVED_TASKS=workers_dict['workers_reserved_tasks'],
                WORKER_NAME=worker_name,
                SUBJECT=subject)

            return HttpResponse(workers_status_t.render(contxt, request))
        # When revoked from all workers page:
        else:
            workers_dict = SelectorRequestsHelpers().workers_all()
            contxt = dict(
                WORKERS_ACTIVE_TASKS=workers_dict['workers_active_tasks'],
                WORKERS_RESERVED_TASKS=workers_dict['workers_reserved_tasks'],
                SUBJECT=subject)

            return HttpResponse(workers_status_t.render(contxt, request))

    @staticmethod
    @permission_required('run_core.task_manage')
    def revoke_tasks_active(request):
        """
        Request with task_id in it - to terminate selected task.

        :param request:
        :return:
        """
        workers_status_t = loader.get_template('service/workers_status.html')
        user_name, user_str = UserCheck().user_string_f(request)
        worker_name = request.GET.get('worker_name', False)
        log.debug("<=SEL OUT=>   revoke_tasks_active(): %s", user_str)

        tasks_revoked, revoked_names = TasksOperations().revoke_tasks_active(worker_name=worker_name)

        subject = "Revoke all active tasks, done. {} revoked. On user {} request.".format(
            tasks_revoked, user_name)

        # get new items after current task was killed.
        workers_dict = SelectorRequestsHelpers().workers_all()

        contxt = dict(
            WORKERS_ACTIVE_TASKS=workers_dict['workers_active_tasks'],
            WORKERS_RESERVED_TASKS=workers_dict['workers_reserved_tasks'],
            TASKS_REVOKED=tasks_revoked,
            REVOKED_NAMES=revoked_names,
            # RAW_TASK_ACTIVE      = workers_dict['task_active'],
            # RAW_TASK_RESERVED    = workers_dict['task_reserved'],
            SUBJECT=subject)

        return HttpResponse(workers_status_t.render(contxt, request))

    @staticmethod
    @permission_required('run_core.task_manage')
    def worker_revoke_tasks(request):
        """
        Request with task_id in it - to terminate selected task.

        :param request:
        :return:
        """
        workers_status_t = loader.get_template('service/workers_status.html')
        user_name, user_str = UserCheck().user_string_f(request)
        worker_name = request.GET.get('worker_name', False)
        log.debug("<=SEL OUT=>   revoke_tasks_active(): %s", user_str)

        NewTaskOper().revoke_all_tasks()

        subject = "Revoke all reserved tasks! On user {} request.".format(worker_name if worker_name else "All", user_name)
        # get new items after current task was killed.
        workers_dict = SelectorRequestsHelpers().workers_all()

        contxt = dict(
            WORKERS_ACTIVE_TASKS=workers_dict['workers_active_tasks'],
            WORKERS_RESERVED_TASKS=workers_dict['workers_reserved_tasks'],
            SUBJECT=subject)

        return HttpResponse(workers_status_t.render(contxt, request))

    @staticmethod
    @permission_required('run_core.task_manage')
    def discard_all_tasks(request):
        """
        Discard all tasks:

        Discard all waiting tasks. This will ignore all tasks waiting for execution,
        and they will be deleted from the messaging server.
        Returns:	the number of tasks discarded.

        :param request:
        :return:
        """
        workers_status_t = loader.get_template('service/workers_status.html')
        user_name, user_str = UserCheck().user_string_f(request)
        # worker_name = request.GET.get('worker_name', False)
        log.debug("<=SEL OUT=>   discard_all_tasks_waiting(): %s", user_str)

        discarded_tasks = TasksOperations().task_discard_all()
        subject = "Discard all tasks. ({}) - discarded. On {} request. List refreshed...".format(
            discarded_tasks, user_name)
        # get new items after current task was killed.
        workers_dict = SelectorRequestsHelpers().workers_all()

        contxt = dict(
            WORKERS_ACTIVE_TASKS=workers_dict['workers_active_tasks'],
            WORKERS_RESERVED_TASKS=workers_dict['workers_reserved_tasks'],
            # RAW_TASK_ACTIVE        = workers_dict['task_active'],
            # RAW_TASK_RESERVED      = workers_dict['task_reserved'],
            SUBJECT=subject)

        return HttpResponse(workers_status_t.render(contxt, request))

    @staticmethod
    @permission_required('run_core.task_manage')
    def purge_all_tasks(request):
        """
        Purge all tasks

        Discard all waiting tasks. This will ignore all tasks waiting for execution,
        and they will be deleted from the messaging server.
        Returns:	the number of tasks discarded.
        :param request:
        :return:
        """
        user_name, user_str = UserCheck().user_string_f(request)
        workers_status_t = loader.get_template('service/workers_status.html')
        log.debug("<=SEL OUT=>   purge_all_tasks_waiting(): %s", user_str)
        # worker_name = request.GET.get('worker_name', False)
        purged_tasks = TasksOperations().task_purge_all()
        subject = "Purge all tasks. ({}) - purged. On {} request. List refreshed...".format(purged_tasks, user_name)

        # get new items after current task was killed.
        workers_dict = SelectorRequestsHelpers().workers_all()

        contxt = dict(
            WORKERS_ACTIVE_TASKS=workers_dict['workers_active_tasks'],
            WORKERS_RESERVED_TASKS=workers_dict['workers_reserved_tasks'],
            # RAW_TASK_ACTIVE        = workers_dict['task_active'],
            # RAW_TASK_RESERVED      = workers_dict['task_reserved'],
            SUBJECT=subject)

        return HttpResponse(workers_status_t.render(contxt, request))

    @staticmethod
    @permission_required('run_core.task_manage')
    def workers_restart(request):
        """

        :param request:
        :return:
        """
        user_name, user_str = UserCheck().user_string_f(request)
        workers_status_t = loader.get_template('service/workers_status.html')
        worker_name = request.GET.get('worker_name', None)

        log.debug("<=SEL OUT=>   workers_restart(): %s", user_str)
        if worker_name:

            worker_full_name = worker_name
            if "@" not in worker_name:
                worker_full_name = '{}@tentacle'.format(worker_name)

            w_restart = WorkerOperations().worker_restart(worker_list=[worker_full_name])
        else:
            w_restart = WorkerOperations().worker_restart()

        subject = "Workers restart run. On {} request. List refreshed... {}".format(user_name, w_restart)
        # get new items after current task was killed.
        workers_dict = SelectorRequestsHelpers().workers_all()

        contxt = dict(
            WORKERS_ACTIVE_TASKS=workers_dict['workers_active_tasks'],
            WORKERS_RESERVED_TASKS=workers_dict['workers_reserved_tasks'],
            SUBJECT=subject)

        return HttpResponse(workers_status_t.render(contxt, request))

    @staticmethod
    @permission_required('run_core.task_manage')
    def celery_worker_heartbeat(request):
        """
        http://docs.celeryproject.org/en/latest/reference/celery.app.control.html#celery.app.control.Control.heartbeat        :param request:
        :return:
        """
        user_name, user_str = UserCheck().user_string_f(request)
        workers_status_t = loader.get_template('service/workers_status.html')
        log.debug("<=SEL OUT=>   celery_worker_heartbeat(): %s", user_str)
        worker_name = request.GET.get('worker_name', None)
        # Split if ',' in worker name.
        # Check each for @hostname
        # Format list

        if worker_name:

            worker_full_name = worker_name
            if "@" not in worker_name:
                worker_full_name = '{}@tentacle'.format(worker_name)

            worker_up = WorkerOperations().worker_heartbeat(worker_list=[worker_full_name])
            if worker_up:
                subject = "Workers ping run. Worker '{}' is UP. On {} request. List refreshed... {}".format(
                    worker_name, user_name, worker_up)
            else:
                subject = "Workers ping run. Worker '{}' is DOWN. On {} request. List refreshed... {}".format(
                    worker_name, user_name, worker_up)
        else:
            worker_up = WorkerOperations().worker_heartbeat()
            subject = "Workers heartbeat run. Workers STATUS. On {} request. List refreshed... {}".format(user_name,
                                                                                                          worker_up)
        # get new items after current task was killed.
        workers_dict = SelectorRequestsHelpers().workers_all()
        contxt = dict(
            WORKERS_ACTIVE_TASKS=workers_dict['workers_active_tasks'],
            WORKERS_RESERVED_TASKS=workers_dict['workers_reserved_tasks'],
            SUBJECT=subject)

        return HttpResponse(workers_status_t.render(contxt, request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def celery_worker_ping(request):
        workers_status_t = loader.get_template('service/workers_status.html')
        user_name, user_str = UserCheck().user_string_f(request)
        worker_name = request.GET.get('worker_name', None)
        # Split if ',' in worker name.
        # Check each for @hostname
        # Format list

        log.debug("<=SEL OUT=>   celery_worker_ping(): %s", user_str)
        if worker_name:

            worker_full_name = worker_name
            if "@" not in worker_name:
                worker_full_name = '{}@tentacle'.format(worker_name)

            worker_up = WorkerOperations().worker_ping(worker_list=[worker_full_name])

            if worker_up:
                subject = "Workers ping run. Worker '{}' is UP. On {} request. List refreshed... {}".format(
                    worker_name, user_name, worker_up)
            else:
                subject = "Workers ping run. Worker '{}' is DOWN. On {} request. List refreshed... {}".format(
                    worker_name, user_name, worker_up)
        else:
            worker_up = WorkerOperations().worker_ping()
            subject = "Workers ping run. Workers STATUS. On {} request. List refreshed... {}".format(user_name,
                                                                                                     worker_up)

        workers_dict = SelectorRequestsHelpers().workers_all()
        contxt = dict(WORKERS_ACTIVE_TASKS=workers_dict['workers_active_tasks'],
                      WORKERS_RESERVED_TASKS=workers_dict['workers_reserved_tasks'],
                      SUBJECT=subject)
        return HttpResponse(workers_status_t.render(contxt, request))

    # END
    # noinspection PyUnresolvedReferences,PyUnusedLocal
    @staticmethod
    @permission_required('run_core.task_manage')
    def celery_service_restart(request):
        """
        systemctl restart celery.service && systemctl restart celerybeat.service
        :param request:
        :return:
        """
        from threading import Thread
        import subprocess
        from time import sleep
        user_name, user_str = UserCheck().user_string_f(request)
        w_bench_t = loader.get_template('service/task-action-request-added-started.html')

        log.warning("<=SEL OUT=> WARNING   celery_service_restart(): %s", user_str)
        subject = "WARNING: WIll restart Apache + Celery workers and Beat + Flower! In 5 sec!"

        # Execute cmd:
        # noinspection PyUnusedLocal
        def restart_service():
            sleep(1)

        # cmd = '/var/www/octopus/restart_services.sh'
        cmd = 'sudo /var/www/octopus/octopus_reload.sh'
        # ("(cd ~/catkin_ws/src && catkin_make)", shell=True)
        run_cmd = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   shell=True,
                                   cwd='/var/www/octopus/'
                                   )
        stdout, stderr = run_cmd.communicate()
        stdout, stderr = stdout.decode('utf-8'), stderr.decode('utf-8')
        run_cmd.wait()  # wait until command finished
        log.debug("stdout %s stderr %s", stdout, stderr)

        # t = Thread(target=restart_service, name='restart th', args=['test_args'])
        # t.start()
        # t.join()
        subject = 'stdout {}, stderr {}'.format(stdout, stderr)

        return HttpResponse(w_bench_t.render(dict(SUBJECT=subject), request))
