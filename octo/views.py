"""
Pages views for main site pages.
Main data, just render pages.

"""

# Python logger
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template import loader
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from django.views.decorators.vary import vary_on_headers
from django.views.generic import TemplateView, ListView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from octo.cache import OctoCache
from octo.helpers.tasks_oper import TasksOperations
from octo_adm.user_operations import UserCheck
from octo_tku_patterns.model_views import AddmDigest, TestLatestDigestLibShort
from octo_tku_patterns.models import TestLast
from octo_tku_patterns.views import TestLastDigestListView, TestCasesListView
from octo_tku_upload.views import TKUUpdateWorkbenchView
from run_core.rabbitmq_operations import RabbitCheck

log = logging.getLogger("octo.octologger")


@method_decorator(cache_control(max_age=60 * 5), name='dispatch')
class MainPage(TemplateView):
    template_name = 'main/mainpage_widgets.html'
    context_object_name = 'objects'

    def get_context_data(self, **kwargs):
        context = super(MainPage, self).get_context_data(**kwargs)
        context.update(
            objects=self.get_queryset(),
        )
        return context

    def get_queryset(self):
        addm_digest = AddmDigest.objects.all()
        # Test lasts more than 40 minutes.
        test_last_q = TestLast.objects.filter(time_spent_test__isnull=False, time_spent_test__gte=60 * 40)
        tests_top_main = test_last_q.filter(tkn_branch__exact='tkn_main').order_by('-time_spent_test')
        tests_top_ship = test_last_q.filter(tkn_branch__exact='tkn_ship').order_by('-time_spent_test')

        selections = dict(
            upload_tests=TKUUpdateWorkbenchView.get_queryset(self),
            addm_digest=addm_digest,
            tests_top_main=tests_top_main,
            tests_top_ship=tests_top_ship,
        )
        return selections


@method_decorator(login_required, name='dispatch')
class UserMainPage(TemplateView):
    template_name = 'user_report_summary.html'
    context_object_name = 'objects'

    def get_context_data(self, **kwargs):
        context = super(UserMainPage, self).get_context_data(**kwargs)
        context.update(
            objects=self.get_queryset(),
        )
        return context

    def get_queryset(self):
        change_user = self.request.GET.get('change_user', None)
        if change_user:
            selections = dict(
                user_tests=TestLastDigestListView.get_queryset(self),
                user_cases=TestCasesListView.get_queryset(self),
            )
            return selections
        return []


def unauthorized_banner(request):
    page_widgets = loader.get_template('includes/unauthorized_banner.html')
    came_from = request.GET.get('next', None)
    user_name, user_string = UserCheck().user_string_f(request)
    log.debug("<=MAIN Widgets=> unauthorized_banner(): %s", user_string)

    widgets = dict(SUBJECT='', CAME_FROM=came_from)
    log.debug("widgets: %s", widgets)

    return HttpResponse(page_widgets.render(widgets, request))


def request_access(request):
    from octo.helpers.tasks_mail_send import Mails
    came_from = request.GET.get('came_from', None)
    user_name, user_string = UserCheck().user_string_f(request)
    page_widgets = loader.get_template('main/mainpage_widgets.html')

    Mails.short(subject='User {} has requested access to {}'.format(user_name, came_from),
                body='User {} has requested access to {}\n{}'.format(user_name, came_from, user_string))

    widgets = dict(SUBJECT='Request submitted. You asked for access to: {}'.format(came_from))
    return HttpResponse(page_widgets.render(widgets, request))


class RabbitMQQueuesREST(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request=None):
        workers_list = self.request.GET.get('workers_list', [])
        if not workers_list:
            workers_list = TasksOperations().workers_enabled
            workers_list = workers_list.get('option_value', '').split(',')
        workers_list = [worker + '@tentacle.dq2' for worker in workers_list]
        inspected = RabbitCheck().queue_count_list(queues_list=workers_list)
        log.debug(f"inspected RabbitMQ queues: {inspected}")
        return Response(inspected)


class CeleryWorkersStatusREST(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request=None):
        workers_list = self.request.GET.get('workers_list', [])
        tasks_body = self.request.GET.get('tasks_body', False)
        if not workers_list:
            workers_list = TasksOperations().workers_enabled
            workers_list = workers_list.get('option_value', '').split(',')
        workers_list = [worker + '@tentacle' for worker in workers_list]
        log.debug(f'Inspect workers: {workers_list}')

        inspected = []
        inspected = TasksOperations().check_active_reserved_short(workers_list, tasks_body)
        log.debug(f"inspected Celery queues: {inspected}")
        return Response(inspected)


class TestLastDigestListViewBoxes(ListView):
    """
    Grouped by library - view for general reposting for external purposes.

    """
    __url_path = '/octo_tku_patterns/patterns_digest_boxes/'
    template_name = 'tests_last_boxes.html'
    context_object_name = 'tests_digest'

    def get_queryset(self):
        queryset = TestLatestDigestLibShort.objects.all()
        queryset = queryset.filter(pattern_library__isnull=False, tkn_branch__exact='tkn_ship').order_by('pattern_library')
        return queryset