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

from django.views.generic import TemplateView, ListView
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated

from celery.result import AsyncResult
from octo.api.serializers import CeleryTaskmetaSerializer

from run_core.models import AddmDev
from run_core.p4_operations import PerforceOperations
from run_core.local_operations import LocalPatternsP4Parse

from octo.models import CeleryTaskmeta
from octo.api.serializers import StandardResultsSetPagination

from octo.helpers.tasks_run import Runner
from octo.helpers.tasks_oper import TasksOperations, WorkerOperations

from octo_adm.user_operations import UserCheck
from octo_adm.request_service import SelectorRequestsHelpers
from octo_adm.tasks import ADDMCases
from octo_adm.serializers import AddmDevSerializer

from octo_tku_patterns.tasks import TPatternParse

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
    model = AddmDev
    # queryset = AddmDev.objects.all().order_by('addm_group')


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
        worker = self.request.GET.get('worker', 'all-workers')
        context.update(
            worker=worker,
            objects={},
        )
        return context

    # Inspect one worker
    # Inspect all workers


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
        # resp = {
        #     "charlie@tentacle": [
        #         "octo.tasks.fake_task",
        #         "octo.tasks.t_long_mail",
        #         "octo.tasks.t_occupy_w",
        #         "octo.tasks.t_user_mail [routing_key=TSupport.t_user_mail]",
        #         "octo.tasks.t_user_test [routing_key=TSupport.t_user_mail]",
        #         "octo.tasks.test_task_get_worker_minimal [routing_key=routines.test_task_get_worker_minimal]",
        #         "octo.tasks.test_task_heartbeat_ping_workers [routing_key=routines.test_task_heartbeat_ping_workers]",
        #         "octo_adm.tasks.t_addm_clean",
        #         "octo_adm.tasks.t_addm_cmd_k",
        #         "octo_adm.tasks.t_routine_addm_cmd [routing_key=routines.TRoutine.t_routine_addm_cmd]",
        #         "octo_adm.tasks.t_routine_clean_addm [routing_key=routines.TRoutine.t_routine_clean_addm]",
        #         "octo_tku_patterns.tasks.t_addm_rsync_threads [routing_key=parsing.TExecTest.make_addm_sync_threads.addm_group]",
        #         "octo_tku_patterns.tasks.t_p4_info [routing_key=parsing.perforce.TExecTest.t_p4_info]",
        #         "octo_tku_patterns.tasks.t_p4_sync [routing_key=parsing.perforce.TExecTest.t_p4_sync_NEW]",
        #         "octo_tku_patterns.tasks.t_p4_sync_force [routing_key=parsing.perforce.TExecTest.t_p4_sync_force]",
        #         "octo_tku_patterns.tasks.t_pattern_weight_index [routing_key=routines.t_pattern_weight_index]",
        #         "octo_tku_patterns.tasks.t_routine_night_tests [routing_key=routines.TRoutine.t_routine_night_tests]",
        #         "octo_tku_patterns.tasks.t_test_exec_threads [routing_key=addm_group.TExecTest.t_test_exec_threads.pattern_folder]",
        #         "octo_tku_patterns.tasks.t_test_prep [routing_key=routines.TRoutine.t_test_prep]",
        #         "octo_tku_upload.tasks.t_parse_tku [routing_key=parsing.TUploadExec.t_parse_tku]",
        #         "octo_tku_upload.tasks.t_routine_tku_upload [routing_key=routines.TRoutine.t_routine_tku_upload_test_new]",
        #         "octo_tku_upload.tasks.t_tku_sync [routing_key=worker_tentacle.TExecTest.t_tku_sync.addm_group]",
        #         "octo_tku_upload.tasks.t_upload_exec_threads [routing_key=worker_tentacle.TExecTest.t_upload_exec_threads.addm_group]"
        #     ],
        #     "w_parsing@tentacle": [
        #         "octo.tasks.fake_task",
        #         "octo.tasks.t_long_mail",
        #         "octo.tasks.t_occupy_w",
        #         "octo.tasks.t_user_mail [routing_key=TSupport.t_user_mail]",
        #         "octo.tasks.t_user_test [routing_key=TSupport.t_user_mail]",
        #         "octo.tasks.test_task_get_worker_minimal [routing_key=routines.test_task_get_worker_minimal]",
        #         "octo.tasks.test_task_heartbeat_ping_workers [routing_key=routines.test_task_heartbeat_ping_workers]",
        #         "octo_adm.tasks.t_addm_clean",
        #         "octo_adm.tasks.t_addm_cmd_k",
        #         "octo_adm.tasks.t_routine_addm_cmd [routing_key=routines.TRoutine.t_routine_addm_cmd]",
        #         "octo_adm.tasks.t_routine_clean_addm [routing_key=routines.TRoutine.t_routine_clean_addm]",
        #         "octo_tku_patterns.tasks.t_addm_rsync_threads [routing_key=parsing.TExecTest.make_addm_sync_threads.addm_group]",
        #         "octo_tku_patterns.tasks.t_p4_info [routing_key=parsing.perforce.TExecTest.t_p4_info]",
        #         "octo_tku_patterns.tasks.t_p4_sync [routing_key=parsing.perforce.TExecTest.t_p4_sync_NEW]",
        #         "octo_tku_patterns.tasks.t_p4_sync_force [routing_key=parsing.perforce.TExecTest.t_p4_sync_force]",
        #         "octo_tku_patterns.tasks.t_pattern_weight_index [routing_key=routines.t_pattern_weight_index]",
        #         "octo_tku_patterns.tasks.t_routine_night_tests [routing_key=routines.TRoutine.t_routine_night_tests]",
        #         "octo_tku_patterns.tasks.t_test_exec_threads [routing_key=addm_group.TExecTest.t_test_exec_threads.pattern_folder]",
        #         "octo_tku_patterns.tasks.t_test_prep [routing_key=routines.TRoutine.t_test_prep]",
        #         "octo_tku_upload.tasks.t_parse_tku [routing_key=parsing.TUploadExec.t_parse_tku]",
        #         "octo_tku_upload.tasks.t_routine_tku_upload [routing_key=routines.TRoutine.t_routine_tku_upload_test_new]",
        #         "octo_tku_upload.tasks.t_tku_sync [routing_key=worker_tentacle.TExecTest.t_tku_sync.addm_group]",
        #         "octo_tku_upload.tasks.t_upload_exec_threads [routing_key=worker_tentacle.TExecTest.t_upload_exec_threads.addm_group]"
        #     ],
        #     "w_routines@tentacle": [
        #         "octo.tasks.fake_task",
        #         "octo.tasks.t_long_mail",
        #         "octo.tasks.t_occupy_w",
        #         "octo.tasks.t_user_mail [routing_key=TSupport.t_user_mail]",
        #         "octo.tasks.t_user_test [routing_key=TSupport.t_user_mail]",
        #         "octo.tasks.test_task_get_worker_minimal [routing_key=routines.test_task_get_worker_minimal]",
        #         "octo.tasks.test_task_heartbeat_ping_workers [routing_key=routines.test_task_heartbeat_ping_workers]",
        #         "octo_adm.tasks.t_addm_clean",
        #         "octo_adm.tasks.t_addm_cmd_k",
        #         "octo_adm.tasks.t_routine_addm_cmd [routing_key=routines.TRoutine.t_routine_addm_cmd]",
        #         "octo_adm.tasks.t_routine_clean_addm [routing_key=routines.TRoutine.t_routine_clean_addm]",
        #         "octo_tku_patterns.tasks.t_addm_rsync_threads [routing_key=parsing.TExecTest.make_addm_sync_threads.addm_group]",
        #         "octo_tku_patterns.tasks.t_p4_info [routing_key=parsing.perforce.TExecTest.t_p4_info]",
        #         "octo_tku_patterns.tasks.t_p4_sync [routing_key=parsing.perforce.TExecTest.t_p4_sync_NEW]",
        #         "octo_tku_patterns.tasks.t_p4_sync_force [routing_key=parsing.perforce.TExecTest.t_p4_sync_force]",
        #         "octo_tku_patterns.tasks.t_pattern_weight_index [routing_key=routines.t_pattern_weight_index]",
        #         "octo_tku_patterns.tasks.t_routine_night_tests [routing_key=routines.TRoutine.t_routine_night_tests]",
        #         "octo_tku_patterns.tasks.t_test_exec_threads [routing_key=addm_group.TExecTest.t_test_exec_threads.pattern_folder]",
        #         "octo_tku_patterns.tasks.t_test_prep [routing_key=routines.TRoutine.t_test_prep]",
        #         "octo_tku_upload.tasks.t_parse_tku [routing_key=parsing.TUploadExec.t_parse_tku]",
        #         "octo_tku_upload.tasks.t_routine_tku_upload [routing_key=routines.TRoutine.t_routine_tku_upload_test_new]",
        #         "octo_tku_upload.tasks.t_tku_sync [routing_key=worker_tentacle.TExecTest.t_tku_sync.addm_group]",
        #         "octo_tku_upload.tasks.t_upload_exec_threads [routing_key=worker_tentacle.TExecTest.t_upload_exec_threads.addm_group]"
        #     ],
        #     "alpha@tentacle": [
        #         "octo.tasks.fake_task",
        #         "octo.tasks.t_long_mail",
        #         "octo.tasks.t_occupy_w",
        #         "octo.tasks.t_user_mail [routing_key=TSupport.t_user_mail]",
        #         "octo.tasks.t_user_test [routing_key=TSupport.t_user_mail]",
        #         "octo.tasks.test_task_get_worker_minimal [routing_key=routines.test_task_get_worker_minimal]",
        #         "octo.tasks.test_task_heartbeat_ping_workers [routing_key=routines.test_task_heartbeat_ping_workers]",
        #         "octo_adm.tasks.t_addm_clean",
        #         "octo_adm.tasks.t_addm_cmd_k",
        #         "octo_adm.tasks.t_routine_addm_cmd [routing_key=routines.TRoutine.t_routine_addm_cmd]",
        #         "octo_adm.tasks.t_routine_clean_addm [routing_key=routines.TRoutine.t_routine_clean_addm]",
        #         "octo_tku_patterns.tasks.t_addm_rsync_threads [routing_key=parsing.TExecTest.make_addm_sync_threads.addm_group]",
        #         "octo_tku_patterns.tasks.t_p4_info [routing_key=parsing.perforce.TExecTest.t_p4_info]",
        #         "octo_tku_patterns.tasks.t_p4_sync [routing_key=parsing.perforce.TExecTest.t_p4_sync_NEW]",
        #         "octo_tku_patterns.tasks.t_p4_sync_force [routing_key=parsing.perforce.TExecTest.t_p4_sync_force]",
        #         "octo_tku_patterns.tasks.t_pattern_weight_index [routing_key=routines.t_pattern_weight_index]",
        #         "octo_tku_patterns.tasks.t_routine_night_tests [routing_key=routines.TRoutine.t_routine_night_tests]",
        #         "octo_tku_patterns.tasks.t_test_exec_threads [routing_key=addm_group.TExecTest.t_test_exec_threads.pattern_folder]",
        #         "octo_tku_patterns.tasks.t_test_prep [routing_key=routines.TRoutine.t_test_prep]",
        #         "octo_tku_upload.tasks.t_parse_tku [routing_key=parsing.TUploadExec.t_parse_tku]",
        #         "octo_tku_upload.tasks.t_routine_tku_upload [routing_key=routines.TRoutine.t_routine_tku_upload_test_new]",
        #         "octo_tku_upload.tasks.t_tku_sync [routing_key=worker_tentacle.TExecTest.t_tku_sync.addm_group]",
        #         "octo_tku_upload.tasks.t_upload_exec_threads [routing_key=worker_tentacle.TExecTest.t_upload_exec_threads.addm_group]"
        #     ]
        # }
        return {'response': resp}

    def tasks_get_active(self):
        """
        Show all active(running) tasks. For all workers, if worker is not specified.
        https://docs.celeryproject.org/en/latest/userguide/workers.html#dump-of-currently-executing-tasks
        :return
        """
        workers = self.workers
        resp = TasksOperations.tasks_get_active(workers=workers)
        # resp = {
        #     "w_parsing@tentacle": [],
        #     "alpha@tentacle": [
        #         {
        #             "id": "477ea6dd-1725-4b1f-96ed-85c679bbc4c0",
        #             "name": "octo.tasks.fake_task",
        #             "args": "['fire_t', 10]",
        #             "kwargs": "{'t_args': ['tag=t_test_exec_threads;type=user_routine;branch=tkn_main;addm_group=alpha;user_name=octopus_super;refresh=False;test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE/NetApp_REST/tests/test.py'], 't_kwargs': {'addm_items': [{...}, {...}, {...}, {...}], 'test_item': {'id': 3, 'test_type': 'tku_patterns', 'tkn_branch': 'tkn_main', 'pattern_library': 'STORAGE', 'pattern_folder_name': 'NetApp_REST', 'pattern_folder_path': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE/NetApp_REST', 'pattern_library_path': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE', 'test_case_dir': '', 'change': '781310', 'change_desc': '@ - RFE | DRDC1-13510 | CARGILL (Esc 135354): Enhancement request for NetApp storage to add CIFS System name\n', 'change_user': 'pthiyaga', 'change_review': '', 'change_ticket': 'DRDC1-13510', 'change_time': datetime.datetime(2019, 9, 30, 13, 27, 24, tzinfo=<UTC>), 'test_case_depot_path': '//addm/tkn_main/tku_patterns/STORAGE/NetApp_...', ...}}}",
        #             "type": "octo.tasks.fake_task",
        #             "hostname": "alpha@tentacle",
        #             "time_start": 1572727361.2668045,
        #             "acknowledged": True,
        #             "delivery_info": {
        #                 "exchange": "",
        #                 "routing_key": "alpha@tentacle.dq2",
        #                 "priority": None,
        #                 "redelivered": False
        #             },
        #             "worker_pid": 2626027249888
        #         },
        #         {
        #             "id": "477ea6dd-1725-4b1f-96ed-85c679bbc4c0",
        #             "name": "octo.tasks.fake_task",
        #             "args": "['fire_t', 10]",
        #             "kwargs": "{'t_args': ['tag=t_test_exec_threads;type=user_routine;branch=tkn_main;addm_group=alpha;user_name=octopus_super;refresh=False;test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE/NetApp_REST/tests/test.py'], 't_kwargs': {'addm_items': [{...}, {...}, {...}, {...}], 'test_item': {'id': 3, 'test_type': 'tku_patterns', 'tkn_branch': 'tkn_main', 'pattern_library': 'STORAGE', 'pattern_folder_name': 'NetApp_REST', 'pattern_folder_path': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE/NetApp_REST', 'pattern_library_path': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE', 'test_case_dir': '', 'change': '781310', 'change_desc': '@ - RFE | DRDC1-13510 | CARGILL (Esc 135354): Enhancement request for NetApp storage to add CIFS System name\n', 'change_user': 'pthiyaga', 'change_review': '', 'change_ticket': 'DRDC1-13510', 'change_time': datetime.datetime(2019, 9, 30, 13, 27, 24, tzinfo=<UTC>), 'test_case_depot_path': '//addm/tkn_main/tku_patterns/STORAGE/NetApp_...', ...}}}",
        #             "type": "octo.tasks.fake_task",
        #             "hostname": "alpha@tentacle",
        #             "time_start": 1572727361.2668045,
        #             "acknowledged": True,
        #             "delivery_info": {
        #                 "exchange": "",
        #                 "routing_key": "alpha@tentacle.dq2",
        #                 "priority": None,
        #                 "redelivered": False
        #             },
        #             "worker_pid": 2626027249888
        #         }
        #     ],
        #     "w_routines@tentacle": [],
        #     "charlie@tentacle": [
        #         {
        #             "id": "2af39cc0-7cd7-4a93-8ce6-b239b6efa156",
        #             "name": "octo.tasks.fake_task",
        #             "args": "['fire_t', 10]",
        #             "kwargs": "{'t_args': ['tag=t_test_exec_threads;type=user_routine;branch=tkn_ship;addm_group=charlie;user_name=octopus_super;refresh=False;test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE/BrocadeNetworkAdvisor/tests/test.py'], 't_kwargs': {'addm_items': [{...}, {...}, {...}, {...}], 'test_item': {'id': 1148, 'test_type': 'tku_patterns', 'tkn_branch': 'tkn_ship', 'pattern_library': 'CORE', 'pattern_folder_name': 'BrocadeNetworkAdvisor', 'pattern_folder_path': '/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE/BrocadeNetworkAdvisor', 'pattern_library_path': '/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE', 'test_case_dir': '', 'change': '780999', 'change_desc': 'Merging\n\n//addm/tkn_main/tku_patterns/CORE/BrocadeNetworkAdvisor/tests/test.py\n\nto //addm/tkn_ship/tku_patterns/CORE/BrocadeNetworkAdvisor/tests/test.py\n', 'change_user': 'pthiyaga', 'change_review': '', 'change_ticket': '', 'change_time': datetime.datetime(2019, 9, 26, 15, 54, 51, tzinfo=<UTC>), 'test_case_de...', ...}}}",
        #             "type": "octo.tasks.fake_task",
        #             "hostname": "charlie@tentacle",
        #             "time_start": 1572727361.8308136,
        #             "acknowledged": True,
        #             "delivery_info": {
        #                 "exchange": "",
        #                 "routing_key": "charlie@tentacle.dq2",
        #                 "priority": None,
        #                 "redelivered": False
        #             },
        #             "worker_pid": 2560315772704
        #         },
        #         {
        #             "id": "2af39cc0-7cd7-4a93-8ce6-b239b6efa156",
        #             "name": "octo.tasks.fake_task",
        #             "args": "['fire_t', 10]",
        #             "kwargs": "{'t_args': ['tag=t_test_exec_threads;type=user_routine;branch=tkn_ship;addm_group=charlie;user_name=octopus_super;refresh=False;test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE/BrocadeNetworkAdvisor/tests/test.py'], 't_kwargs': {'addm_items': [{...}, {...}, {...}, {...}], 'test_item': {'id': 1148, 'test_type': 'tku_patterns', 'tkn_branch': 'tkn_ship', 'pattern_library': 'CORE', 'pattern_folder_name': 'BrocadeNetworkAdvisor', 'pattern_folder_path': '/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE/BrocadeNetworkAdvisor', 'pattern_library_path': '/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE', 'test_case_dir': '', 'change': '780999', 'change_desc': 'Merging\n\n//addm/tkn_main/tku_patterns/CORE/BrocadeNetworkAdvisor/tests/test.py\n\nto //addm/tkn_ship/tku_patterns/CORE/BrocadeNetworkAdvisor/tests/test.py\n', 'change_user': 'pthiyaga', 'change_review': '', 'change_ticket': '', 'change_time': datetime.datetime(2019, 9, 26, 15, 54, 51, tzinfo=<UTC>), 'test_case_de...', ...}}}",
        #             "type": "octo.tasks.fake_task",
        #             "hostname": "charlie@tentacle",
        #             "time_start": 1572727361.8308136,
        #             "acknowledged": True,
        #             "delivery_info": {
        #                 "exchange": "",
        #                 "routing_key": "charlie@tentacle.dq2",
        #                 "priority": None,
        #                 "redelivered": False
        #             },
        #             "worker_pid": 2560315772704
        #         }
        #     ]
        # }
        return {'response': resp}

    def tasks_get_reserved(self):
        """
        Show all reserved(pending\\queued) tasks. For all workers, if worker is not specified.
        https://docs.celeryproject.org/en/latest/userguide/workers.html#dump-of-reserved-tasks
        :return
        """
        workers = self.workers
        resp = TasksOperations.tasks_get_reserved(workers=workers)
        # resp = {
        #     "w_routines@tentacle": [],
        #     "w_parsing@tentacle": [],
        #     "charlie@tentacle": [
        #         {
        #             "id": "ec200d27-5f3b-47e3-a473-1c8a5831d5b8",
        #             "name": "octo.tasks.fake_task",
        #             "args": "['fire_t', 10]",
        #             "kwargs": "{'t_args': ['tag=t_user_mail;mode=start;addm_group=charlie;user_name=octopus_super;test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE/CitrixXen/tests/test.py'], 't_kwargs': {'mail_opts': {'mode': 'start', 'view_obj': {...}, 'test_item': {...}, 'addm_set': <QuerySet [{'id': 12, 'addm_host': 'vl-aus-rem-qa6n', 'addm_name': 'custard_cream', 'tideway_user': 'tideway', 'tideway_pdw': 'S0m3w@y', 'root_user': 'root', 'root_pwd': 'tidewayroot', 'addm_ip': '172.25.148.106', 'addm_v_code': 'ADDM_11_2', 'addm_v_int': '11.2', 'addm_full_version': '11.2.0.6', 'addm_branch': 'r11_2_0_x', 'addm_owner': 'Alex D', 'addm_group': 'charlie', 'disables': None, 'branch_lock': 'tkn_ship', 'description': None, 'vm_cluster': None, 'vm_id': None}, {'id': 13, 'addm_host': 'vl-aus-rem-qa6p', 'addm_name': 'bobblehat', 'tideway_user': 'tideway', 'tideway_pdw': 'S0m3w@y', 'root_user': 'root', 'root_pwd': 'tidewayroot', 'addm_ip': '172.25.148.107', 'addm_v_code': 'ADDM_11_1', 'addm_v_int': '11.1',...}}}",
        #             "type": "octo.tasks.fake_task",
        #             "hostname": "charlie@tentacle",
        #             "time_start": None,
        #             "acknowledged": False,
        #             "delivery_info": {
        #                 "exchange": "",
        #                 "routing_key": "charlie@tentacle.dq2",
        #                 "priority": None,
        #                 "redelivered": False
        #             },
        #             "worker_pid": None
        #         }
        #     ],
        #     "alpha@tentacle": [
        #         {
        #             "id": "82aa9fb0-2190-4661-b052-1d8d2677ceef",
        #             "name": "octo.tasks.fake_task",
        #             "args": "['fire_t', 10]",
        #             "kwargs": "{'t_args': ['tag=t_user_mail;mode=start;addm_group=alpha;user_name=octopus_super;test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE/BrocadeSANSwitches/tests/test.py'], 't_kwargs': {'mail_opts': {'mode': 'start', 'view_obj': {...}, 'test_item': {...}, 'addm_set': <QuerySet [{'id': 6, 'addm_host': 'vl-aus-tkudev-38', 'addm_name': 'custard_cream', 'tideway_user': 'tideway', 'tideway_pdw': 'S0m3w@y', 'root_user': 'root', 'root_pwd': 'tidewayroot', 'addm_ip': '172.25.144.118', 'addm_v_code': 'ADDM_11_2', 'addm_v_int': '11.2', 'addm_full_version': '11.2.0.6', 'addm_branch': 'r11_2_0_x', 'addm_owner': 'Alex D', 'addm_group': 'alpha', 'disables': None, 'branch_lock': 'tkn_main', 'description': None, 'vm_cluster': 'tku_cluster', 'vm_id': 'vim.VirtualMachine:vm-69'}, {'id': 7, 'addm_host': 'vl-aus-tkudev-39', 'addm_name': 'bobblehat', 'tideway_user': 'tideway', 'tideway_pdw': 'S0m3w@y', 'root_user': 'root', 'root_pwd': 'tidewayroot', 'addm_ip': '172.25.144.119', 'addm_v_code': 'ADDM_11_1',..., ...}}",
        #             "type": "octo.tasks.fake_task",
        #             "hostname": "alpha@tentacle",
        #             "time_start": None,
        #             "acknowledged": False,
        #             "delivery_info": {
        #                 "exchange": "",
        #                 "routing_key": "alpha@tentacle.dq2",
        #                 "priority": None,
        #                 "redelivered": False
        #             },
        #             "worker_pid": None
        #         }
        #     ]
        # }
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
        # resp = {
        #     "active": {
        #         "alpha@tentacle": [
        #             {
        #                 "id": "82aa9fb0-2190-4661-b052-1d8d2677ceef",
        #                 "name": "octo.tasks.fake_task",
        #                 "args": "['fire_t', 10]",
        #                 "kwargs": "{'t_args': ['tag=t_user_mail;mode=start;addm_group=alpha;user_name=octopus_super;test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE/BrocadeSANSwitches/tests/test.py'], 't_kwargs': {'mail_opts': {'mode': 'start', 'view_obj': {...}, 'test_item': {...}, 'addm_set': <QuerySet [{'id': 6, 'addm_host': 'vl-aus-tkudev-38', 'addm_name': 'custard_cream', 'tideway_user': 'tideway', 'tideway_pdw': 'S0m3w@y', 'root_user': 'root', 'root_pwd': 'tidewayroot', 'addm_ip': '172.25.144.118', 'addm_v_code': 'ADDM_11_2', 'addm_v_int': '11.2', 'addm_full_version': '11.2.0.6', 'addm_branch': 'r11_2_0_x', 'addm_owner': 'Alex D', 'addm_group': 'alpha', 'disables': None, 'branch_lock': 'tkn_main', 'description': None, 'vm_cluster': 'tku_cluster', 'vm_id': 'vim.VirtualMachine:vm-69'}, {'id': 7, 'addm_host': 'vl-aus-tkudev-39', 'addm_name': 'bobblehat', 'tideway_user': 'tideway', 'tideway_pdw': 'S0m3w@y', 'root_user': 'root', 'root_pwd': 'tidewayroot', 'addm_ip': '172.25.144.119', 'addm_v_code': 'ADDM_11_1',..., ...}}",
        #                 "type": "octo.tasks.fake_task",
        #                 "hostname": "alpha@tentacle",
        #                 "time_start": 1572727381.3611205,
        #                 "acknowledged": True,
        #                 "delivery_info": {
        #                     "exchange": "",
        #                     "routing_key": "alpha@tentacle.dq2",
        #                     "priority": None,
        #                     "redelivered": False
        #                 },
        #                 "worker_pid": 2626027249888
        #             }
        #         ],
        #         "w_parsing@tentacle": [],
        #         "charlie@tentacle": [
        #             {
        #                 "id": "ec200d27-5f3b-47e3-a473-1c8a5831d5b8",
        #                 "name": "octo.tasks.fake_task",
        #                 "args": "['fire_t', 10]",
        #                 "kwargs": "{'t_args': ['tag=t_user_mail;mode=start;addm_group=charlie;user_name=octopus_super;test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE/CitrixXen/tests/test.py'], 't_kwargs': {'mail_opts': {'mode': 'start', 'view_obj': {...}, 'test_item': {...}, 'addm_set': <QuerySet [{'id': 12, 'addm_host': 'vl-aus-rem-qa6n', 'addm_name': 'custard_cream', 'tideway_user': 'tideway', 'tideway_pdw': 'S0m3w@y', 'root_user': 'root', 'root_pwd': 'tidewayroot', 'addm_ip': '172.25.148.106', 'addm_v_code': 'ADDM_11_2', 'addm_v_int': '11.2', 'addm_full_version': '11.2.0.6', 'addm_branch': 'r11_2_0_x', 'addm_owner': 'Alex D', 'addm_group': 'charlie', 'disables': None, 'branch_lock': 'tkn_ship', 'description': None, 'vm_cluster': None, 'vm_id': None}, {'id': 13, 'addm_host': 'vl-aus-rem-qa6p', 'addm_name': 'bobblehat', 'tideway_user': 'tideway', 'tideway_pdw': 'S0m3w@y', 'root_user': 'root', 'root_pwd': 'tidewayroot', 'addm_ip': '172.25.148.107', 'addm_v_code': 'ADDM_11_1', 'addm_v_int': '11.1',...}}}",
        #                 "type": "octo.tasks.fake_task",
        #                 "hostname": "charlie@tentacle",
        #                 "time_start": 1572727381.8880484,
        #                 "acknowledged": True,
        #                 "delivery_info": {
        #                     "exchange": "",
        #                     "routing_key": "charlie@tentacle.dq2",
        #                     "priority": None,
        #                     "redelivered": False
        #                 },
        #                 "worker_pid": 2560316563680
        #             }
        #         ],
        #         "w_routines@tentacle": []
        #     },
        #     "reserved": {
        #         "w_parsing@tentacle": [],
        #         "charlie@tentacle": [
        #             {
        #                 "id": "50096f4f-40c0-4170-a75f-39fe23b6eae8",
        #                 "name": "octo.tasks.fake_task",
        #                 "args": "['fire_t', 10]",
        #                 "kwargs": "{'t_args': ['tag=t_test_exec_threads;type=user_routine;branch=tkn_ship;addm_group=charlie;user_name=octopus_super;refresh=False;test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE/CitrixXen/tests/test.py'], 't_kwargs': {'addm_items': [{...}, {...}, {...}, {...}], 'test_item': {'id': 1184, 'test_type': 'tku_patterns', 'tkn_branch': 'tkn_ship', 'pattern_library': 'CORE', 'pattern_folder_name': 'CitrixXen', 'pattern_folder_path': '/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE/CitrixXen', 'pattern_library_path': '/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE', 'test_case_dir': '', 'change': '780768', 'change_desc': 'INTERNAL | Fix test\n', 'change_user': 'vturchin', 'change_review': '', 'change_ticket': '', 'change_time': datetime.datetime(2019, 9, 25, 5, 59, 53, tzinfo=<UTC>), 'test_case_depot_path': '//addm/tkn_ship/tku_patterns/CORE/CitrixXen', 'test_py_path': '/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE/CitrixXen/tests/test.py', 'test_...', ...}}}",
        #                 "type": "octo.tasks.fake_task",
        #                 "hostname": "charlie@tentacle",
        #                 "time_start": None,
        #                 "acknowledged": False,
        #                 "delivery_info": {
        #                     "exchange": "",
        #                     "routing_key": "charlie@tentacle.dq2",
        #                     "priority": None,
        #                     "redelivered": False
        #                 },
        #                 "worker_pid": None
        #             }
        #         ],
        #         "w_routines@tentacle": [],
        #         "alpha@tentacle": [
        #             {
        #                 "id": "1759096e-8597-4d8e-89c3-c01d8adfa200",
        #                 "name": "octo.tasks.fake_task",
        #                 "args": "['fire_t', 10]",
        #                 "kwargs": "{'t_args': ['tag=t_test_exec_threads;type=user_routine;branch=tkn_main;addm_group=alpha;user_name=octopus_super;refresh=False;test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE/BrocadeSANSwitches/tests/test.py'], 't_kwargs': {'addm_items': [{...}, {...}, {...}, {...}], 'test_item': {'id': 4, 'test_type': 'tku_patterns', 'tkn_branch': 'tkn_main', 'pattern_library': 'STORAGE', 'pattern_folder_name': 'BrocadeSANSwitches', 'pattern_folder_path': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE/BrocadeSANSwitches', 'pattern_library_path': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE', 'test_case_dir': '', 'change': '780988', 'change_desc': 'Merging\n\n//addm/tkn_main/tku_patterns/CORE/BrocadeNetworkAdvisor/BrocadeNetworkAdvisor.tplpre\n\nto //addm/tkn_ship/tku_patterns/CORE/BrocadeNetworkAdvisor/BrocadeNetworkAdvisor.tplpre\n\n\n@776308 - RFE | DRDC1-13065 | TRINITY_HEALTH (Esc 129636) Discover Brocade Storage with the re-branded Connectrix software,...', ...}}}",
        #                 "type": "octo.tasks.fake_task",
        #                 "hostname": "alpha@tentacle",
        #                 "time_start": None,
        #                 "acknowledged": False,
        #                 "delivery_info": {
        #                     "exchange": "",
        #                     "routing_key": "alpha@tentacle.dq2",
        #                     "priority": None,
        #                     "redelivered": False
        #                 },
        #                 "worker_pid": None
        #             }
        #         ]
        #     }
        # }
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
        https://docs.celeryproject.org/en/latest/userguide/workers.html#revoke-revoking-tasks
        :return
        """
        task_id = self.task_id
        resp = TasksOperations.revoke_task_by_id(task_id=task_id)
        return {'response': resp}

    def revoke_tasks_active(self):
        """
        Revoke all active tasks.
        https://docs.celeryproject.org/en/latest/userguide/workers.html#revoke-revoking-tasks
        :return
        """
        workers = self.workers
        resp = TasksOperations().revoke_tasks_active(workers=workers)
        return {'response': resp}

    def revoke_tasks_reserved(self):
        """
        Revoke all reserved tasks
        https://docs.celeryproject.org/en/latest/userguide/workers.html#revoke-revoking-tasks
        :return
        """
        workers = self.workers
        resp = TasksOperations().revoke_tasks_reserved(workers=workers)
        return {'response': resp}

    def revoke_tasks_active_reserved(self):
        """
        Revoke all reserved and active tasks
        https://docs.celeryproject.org/en/latest/userguide/workers.html#revoke-revoking-tasks
        :return
        """
        workers = self.workers
        resp = TasksOperations().revoke_tasks_active_reserved(workers=workers)
        return {'response': resp}

    def task_discard_all(self):
        """
        This will ignore all tasks waiting for execution, and they will be deleted from the messaging server.
        https://docs.celeryproject.org/en/latest/reference/celery.app.control.html#celery.app.control.Control.discard_all
        :return
        """
        resp = TasksOperations().task_discard_all()
        return {'response': resp}

    def task_purge_all(self):
        """
        Discard all waiting tasks. This will ignore all tasks waiting for execution, and they will be deleted from the messaging server.
        https://docs.celeryproject.org/en/latest/reference/celery.app.control.html#celery.app.control.Control.purge
        :return
        """
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
        https://docs.celeryproject.org/en/latest/reference/celery.app.control.html#celery.app.control.Control.pool_restart
        :return
        """
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
        self.mode = ''
        self.cmd_k = ''
        self.subject = ''
        self.addm_group = ''
        self.fake_run = True
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
            self.fake_run = self.request.POST.get('fake_run', True)  # TODO: Debug, remove default True
            self.cmd_k = self.request.POST.get('cmd_k', None)
            self.mode = self.request.POST.get('mode', None)
            self.addm_group = self.request.POST.get('addm_group', None)
        elif self.request.GET:
            self.operation_key = self.request.GET.get('operation_key', None)
            self.fake_run = self.request.GET.get('fake_run', True)  # TODO: Debug, remove default True
            self.cmd_k = self.request.GET.get('cmd_k', None)
            self.mode = self.request.GET.get('mode', None)
            self.addm_group = self.request.GET.get('addm_group', None)

        self.is_authenticated = self.request.user.is_authenticated
        self.user_name = self.request.user.get_username()
        self.user_email = self.request.user.email

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

    def parse_full(self):
        """
        Run internal FS parse and P4 changes refresh procedure
        :return: success message
        """
        self.p4_conn = PerforceOperations().p4_initialize(debug=True)
        msg = LocalPatternsP4Parse().parse_and_changes_routine(
            sync_force=False, full=True, p4_conn=self.p4_conn)
        return msg

    def cases_weight(self):
        """ Calculate ETA for test cases based on previous execution logs for last 30 days. Example: operation_key=cases_weight
        :return {'task': t_pattern_weight_index.id}"""
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
        p4_sync_task = Runner.fire_t(TPatternParse.t_p4_sync, fake_run=self.fake_run, t_args=[t_tag])
        return {'task_id': p4_sync_task.id}

    def p4_sync_force(self):
        """ Execute routine for perforce "sync -f" will forced sync all files from p4 depot to Octopus FS. Example: operation_key=p4_sync_force
        :return{'task': t_p4_sync_force.id}"""
        t_tag = f'tag=t_p4_sync_force;user_name={self.user_name};fake={self.fake_run};start_time={self.start_time}'
        t_p4_sync_force = Runner.fire_t(TPatternParse.t_p4_sync_force, fake_run=self.fake_run, t_args=[t_tag])
        return {'task_id': t_p4_sync_force.id}

    def addm_cleanup(self):
        """ Run selected ADDM cleanup therapy.
        mode=[weekly, daily, tests], addm_group=()
        Example: operation_key=addm_cleanup;addm_group=alpha;mode=weekly
        :return: mode: task.id
        """
        # TODO: Retest with addm_group=all
        clean_out = ADDMCases().clean_addm(
            mode=self.mode,
            subject=self.subject,
            user_name=self.user_name,
            user_mail=self.user_email,
            addm_group=self.addm_group,
            fake_run=self.fake_run,
        )
        return {'task_id': clean_out}

    def addm_cmd_run(self):
        """ Run ADDM registered command. Commands should be added to Octopus system.
        Options: (cmd_k=(), addm_group=()
        Example: operation_key=addm_cmd_run;addm_group=alpha;cmd_k=show_v
        :return cmd_k: task.id """
        # TODO: Retest with addm_group=all
        cmd_out = ADDMCases().addm_cmd(
            cmd_k=self.cmd_k,
            subject=self.subject,
            user_name=self.user_name,
            user_mail=self.user_email,
            addm_group=self.addm_group,
            fake_run=self.fake_run,
        )
        return {'task_id': cmd_out}

    def addm_sync_shares(self):
        """ Execute routine for Octopus NFS -> ADDM sync all files for tests. Using rsync.
        Options: addm_group=()
        Example: operation_key=addm_sync_shares;addm_group=alpha
        :return task: task.id"""
        # TODO: Retest with addm_group=all
        sync_out = ADDMCases().addm_sync_shares(
            subject=self.subject,
            user_name=self.user_name,
            user_mail=self.user_email,
            addm_group=self.addm_group,
            fake_run=self.fake_run,
        )
        return {'task_id': sync_out}


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
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def _old_addm_workbench_widgets(request):
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
