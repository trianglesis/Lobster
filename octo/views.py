"""
Pages views for main site pages.
Main data, just render pages.

"""
from django.template import loader
from django.http import HttpResponse
from django.views.generic import TemplateView

from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required

from octo_adm.user_operations import UserCheck

from octo_tku_patterns.model_views import AddmDigest
from octo_tku_upload.views import TKUUpdateWorkbenchView
from octo_tku_patterns.views import TestLastDigestListView, TestCasesListView

# Python logger
import logging
log = logging.getLogger("octo.octologger")


class MainPage(TemplateView):
    template_name = 'main/mainpage_widgets.html'
    context_object_name = 'objects'

    def get_context_data(self, **kwargs):
        UserCheck().logator(self.request, 'info', "<=MainPage=> Main page")
        context = super(MainPage, self).get_context_data(**kwargs)
        context.update(
            objects=self.get_queryset(),
        )
        return context

    def get_queryset(self):
        UserCheck().logator(self.request, 'info', "<=MainPage=> Main page queries")

        addm_digest = AddmDigest.objects.all()

        upload_tests = TKUUpdateWorkbenchView.get_queryset(self)
        log.debug("upload_tests: %s", upload_tests)

        selections = dict(
            upload_tests = upload_tests,
            addm_digest = addm_digest,
        )
        return selections


@method_decorator(login_required, name='dispatch')
class UserMainPage(TemplateView):
    template_name = 'user_report_summary.html'
    context_object_name = 'objects'

    def get_context_data(self, **kwargs):
        UserCheck().logator(self.request, 'info', "<=MainPage=> Main page")
        context = super(UserMainPage, self).get_context_data(**kwargs)
        context.update(
            objects=self.get_queryset(),
        )
        return context

    def get_queryset(self):
        UserCheck().logator(self.request, 'info', "<=MainPage=> Main page queries")

        # get User patterns\cases digest shortly
        user_cases_tests_digest = TestLastDigestListView.get_queryset(self)

        # get User cases
        user_cases = TestCasesListView.get_queryset(self)

        selections = dict(
            user_tests = user_cases_tests_digest,
            user_cases = user_cases,
        )
        return selections


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
