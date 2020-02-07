"""
Pages views for main site pages.
Main data, just render pages.

"""
from django.template import loader
from django.http import HttpResponse
from django.views.generic import TemplateView

from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated

from octo_adm.user_operations import UserCheck

from octo_tku_patterns.models import TestLast
from octo_tku_patterns.model_views import AddmDigest
from octo_tku_upload.views import TKUUpdateWorkbenchView
from octo_tku_patterns.views import TestLastDigestListView, TestCasesListView

from octo.helpers.tasks_oper import TasksOperations

# Python logger
import logging
log = logging.getLogger("octo.octologger")


class MainPage(TemplateView):
    template_name = 'main/mainpage_widgets.html'
    context_object_name = 'objects'

    def get_context_data(self, **kwargs):
        # UserCheck().logator(self.request, 'info', "<=MainPage=> Main page")
        context = super(MainPage, self).get_context_data(**kwargs)
        context.update(
            objects=self.get_queryset(),
        )
        return context

    def get_queryset(self):
        # UserCheck().logator(self.request, 'info', "<=MainPage=> Main page queries")
        addm_digest = AddmDigest.objects.all()
        upload_tests = TKUUpdateWorkbenchView.get_queryset(self)
        # log.debug("upload_tests: %s", upload_tests)
        tests_top_main = TestLast.objects.filter(time_spent_test__isnull=False, tkn_branch__exact='tkn_main').order_by('-time_spent_test')
        tests_top_ship = TestLast.objects.filter(time_spent_test__isnull=False, tkn_branch__exact='tkn_ship').order_by('-time_spent_test')
        selections = dict(
            upload_tests = upload_tests,
            addm_digest = addm_digest,
            tests_top_main = tests_top_main,
            tests_top_ship = tests_top_ship,
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
            # get User patterns\cases digest shortly
            user_cases_tests_digest = TestLastDigestListView.get_queryset(self)
            # get User cases
            user_cases = TestCasesListView.get_queryset(self)
            selections = dict(
                user_tests = user_cases_tests_digest,
                user_cases = user_cases,
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

    widgets = dict(SUBJECT = 'Request submitted. You asked for access to: {}'.format(came_from))
    return HttpResponse(page_widgets.render(widgets, request))


class CeleryWorkersStatusREST(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request=None):
        workers_list = self.request.GET.get('workers_list', [])
        tasks_body = self.request.GET.get('tasks_body', False)
        if not workers_list:
            workers_list = TasksOperations().workers_enabled
            workers_list = workers_list.get('option_value', '').split(',')
        workers_list = [worker+'@tentacle' for worker in workers_list]

        inspected = TasksOperations().check_active_reserved_short(workers_list, tasks_body)
        # inspected = [
        #     {
        #         "alpha@tentacle": {
        #             "all_tasks_len": 0
        #         }
        #     },
        #     {
        #         "beta@tentacle": {
        #             "all_tasks_len": 0
        #         }
        #     },
        #     {
        #         "charlie@tentacle": {
        #             "all_tasks_len": 0
        #         }
        #     },
        #     {
        #         "delta@tentacle": {
        #             "all_tasks_len": 0
        #         }
        #     },
        #     {
        #         "echo@tentacle": {
        #             "all_tasks_len": 0
        #         }
        #     },
        #     {
        #         "foxtrot@tentacle": {
        #             "all_tasks_len": 0
        #         }
        #     },
        #     {
        #         "w_parsing@tentacle": {
        #             "all_tasks_len": 0
        #         }
        #     },
        #     {
        #         "w_routines@tentacle": {
        #             "all_tasks_len": 0
        #         }
        #     }]

        return Response(inspected)
