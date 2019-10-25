"""
OCTO ADM - pages and widgets and functions.
"""
import datetime
import logging

from django.db.models import Max
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from django.template import loader

from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.edit import UpdateView, CreateView
from django.views.generic.dates import ArchiveIndexView, DayArchiveView, \
    TodayArchiveView, DayMixin, MonthMixin, YearMixin


from octo.helpers.tasks_helpers import TMail
from octo.helpers.tasks_run import Runner

from octo_adm.user_operations import UserCheck

from octo_tku_upload.table_oper import UploadTKUTableOper
from octo_tku_upload.tasks import TUploadExec, TUploadRoutine
from octo_tku_upload.models import *


log = logging.getLogger("octo.octologger")


class ViewTKU:

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def tku_packages(request):
        """
        Draw table with TKU zips

        :param request:
        :return:
        """
        patterns_summary = loader.get_template('OLD/tku_packages.html')
        user_name, user_str = UserCheck().user_string_f(request)
        # log.debug("<=ViewTKU=> tku_packages(): %s", user_str)

        tku_type = request.GET.get('tku_type', False)

        query_args = dict(tku_type=tku_type)
        tku_packages, ga_candidate_max, released_tkn_max, tkn_main_continuous_max = UploadTKUTableOper().select_tku_packages(
            query_args)
        subject = 'System TKU Packages used for upload\\upgrade tests.'

        patterns_contxt = dict(
            SUBJECT=subject,
            TKU_PACKAGES=tku_packages,
            ga_candidate_max=ga_candidate_max,
            released_tkn_max=released_tkn_max,
            tkn_main_continuous_max=tkn_main_continuous_max,
        )
        return HttpResponse(patterns_summary.render(patterns_contxt, request))


# TASKs Actions
class UploadTKU:

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def tku_update_test(request):
        """
        Execute upload test continuous task + routine:

        tku_type = tkn_main_continuous
        package_type = no type due to no release
        zip_file_name = should be used to check integrity:
            - Technology-Knowledge-Update-2069-03-1-ADDM-11.3+.zip
            - Technology-Knowledge-Update-Storage-2069-03-1-ADDM-11.3+.zip
            - Extended-Data-Pack-2069-03-1-ADDM-11.3+.zip


        :param request:
        :return:
        """
        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=UploadTKU=> tku_update_test(): %s", user_str)

        page_widgets = loader.get_template('small_blocks/user_test_added.html')

        addm_group = request.GET.get('addm_group', 'foxtrot')
        tku_type = request.GET.get('tku_type', None)  # Used to select specific tku to install?
        mode = request.GET.get('mode', None)  # Indicate mode: fresh, update or step
        tku_wget = request.GET.get('tku_wget', False)  # Indicate mode: fresh, update or step
        fake_run = request.GET.get('fake_run', False)

        user_email = [request.user.email]
        widgets = dict(
            SUBJECT='TKU Upload test',
            OPTION_VALUES=dict(
                USER_NAME=user_name,
                USER_EMAIL=user_email,
                addm_group=addm_group,
                tku_type=tku_type,
                mode=mode,
                tku_wget=tku_wget,
                user_str=user_str,
            ),
        )
        mail_to = ''
        if user_email:
            mail_to = "DEV Will send confirmation to: '{}'".format(user_email)

        widgets['OPTION_VALUES']['SUBJECT'] = "DEV User {user_name}/{mail_to} execute upload test. " \
                                              "Options: addm_group={addm_group} tku_type={tku_type} ".format(
            user_name=user_name, mail_to=mail_to, addm_group=addm_group, tku_type=tku_type)

        tsk_msg = 'tag=upload_routine;lock=True;type=routine;user_name={user_name};tku_type={tku_type}' \
                  '| on: "{addm_group}" by: {user_name}'
        t_tag = tsk_msg.format(user_name=user_name, addm_group=addm_group, tku_type=tku_type)

        log.debug("<=OCTO ADM=> User test test_execute_web: \n%s", t_tag)
        Runner.fire_t(TUploadRoutine.t_routine_tku_upload, fake_run=fake_run,
                      t_args=[t_tag],
                      t_kwargs=dict(user_name=user_name, user_email=user_email, tku_type=tku_type,
                                    addm_group=addm_group, mode=mode, tku_wget=tku_wget))

        TMail().upload_t(stage='added', t_tag=t_tag, start_time=datetime.datetime.now(),
                       user_name=user_name, addm_group=addm_group, mode=mode,
                       tku_type=tku_type, tku_wget=tku_wget, user_email=user_email)
        return HttpResponse(page_widgets.render(widgets, request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def tku_sync(request):
        """
        Execute upload TKU routine - wget and parse.
        :param request:
        :return:
        """
        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=UploadTKU=> tku_sync(): %s", user_str)
        fake_run = request.GET.get('fake_run', False)

        simple_output = loader.get_template('dev_debug_workbench/dev_helpers/simple_output.html')

        tku_type = request.GET.get('tku_type', None)
        subject = 'Execute WGET TKU routine only, no uploads'
        task_id = Runner.fire_t(TUploadExec.t_tku_sync, fake_run=fake_run,
                                t_kwargs=dict(tku_type=tku_type),
                                t_args=['tag=t_tku_sync;'])
        widgets = dict(
            SUBJECT=subject,
            KV_OUTPUT=dict(
                subject=subject,
                user_name=user_name,
                user_str=user_str,
                task_id=task_id)
        )
        return HttpResponse(simple_output.render(widgets, request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def run_tku_parse(request):
        """
        Use to run only local TKU packages parse procedure.
        :param request:
        :return:
        """
        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=UploadTKU=> run_tku_parse(): %s", user_str)
        fake_run = request.GET.get('fake_run', False)

        page_widgets = loader.get_template('dev_debug_workbench/dev_main.html')

        tku_type = request.GET.get('tku_type', None)

        subject = '{} Run run_tku_parse -> run_tku_parse'.format(user_name)
        options = dict(user_name=user_name, subject=subject, tku_type=tku_type)
        t_tag = 'run_tku_parse'
        Runner.fire_t(TUploadExec.t_parse_tku, fake_run=fake_run,
                      t_args=[t_tag],
                      t_kwargs=options)
        return HttpResponse(page_widgets.render(dict(SUBJECT=subject), request))


def compose_selector(self):
    selector = dict()
    selector.update(
        # Packages:
        # package_type already in
        # tku_type already in
        addm_version=self.request.GET.get('addm_version', None),
        zip_type=self.request.GET.get('zip_type', None),
        tku_name=self.request.GET.get('tku_name', None),
        # Tests:
        test_mode=self.request.GET.get('test_mode', None),
        tku_type=self.request.GET.get('tku_type', None),
        mode_key=self.request.GET.get('mode_key', None),
        addm_name=self.request.GET.get('addm_name', None),
        package_type=self.request.GET.get('package_type', None),
        upload_test_status=self.request.GET.get('upload_test_status', None),
    )
    return selector


def upload_case_query_selector(queryset, sel_opts):
    # Packages:
    # package_type already in
    # tku_type already in
    if sel_opts.get('addm_version'):
        # log.debug("queryset sort: addm_version %s", sel_opts.get('addm_version'))
        queryset = queryset.filter(addm_version__exact=sel_opts.get('addm_version'))
    if sel_opts.get('zip_type'):
        # log.debug("queryset sort: zip_type %s", sel_opts.get('zip_type'))
        queryset = queryset.filter(zip_type__exact=sel_opts.get('zip_type'))
    if sel_opts.get('tku_name'):
        # log.debug("queryset sort: tku_name %s", sel_opts.get('tku_name'))
        queryset = queryset.filter(tku_name__exact=sel_opts.get('tku_name'))
    # Tests:
    if sel_opts.get('test_mode'):
        # log.debug("queryset sort: test_mode %s", sel_opts.get('test_mode'))
        queryset = queryset.filter(test_mode__exact=sel_opts.get('test_mode'))
    if sel_opts.get('tku_type'):
        # log.debug("queryset sort: tku_type %s", sel_opts.get('tku_type'))
        queryset = queryset.filter(tku_type__exact=sel_opts.get('tku_type'))
    if sel_opts.get('mode_key'):
        # log.debug("queryset sort: mode_key %s", sel_opts.get('mode_key'))
        queryset = queryset.filter(mode_key__exact=sel_opts.get('mode_key'))
    if sel_opts.get('addm_name'):
        # log.debug("queryset sort: addm_name %s", sel_opts.get('addm_name'))
        queryset = queryset.filter(addm_name__exact=sel_opts.get('addm_name'))
    if sel_opts.get('package_type'):
        # log.debug("queryset sort: package_type %s", sel_opts.get('package_type'))
        queryset = queryset.filter(package_type__exact=sel_opts.get('package_type'))
    if sel_opts.get('upload_test_status'):
        # log.debug("queryset sort: upload_test_status %s", sel_opts.get('upload_test_status'))
        queryset = queryset.filter(upload_test_status__exact=sel_opts.get('upload_test_status'))
    return queryset


# TKU Upload test workbench:
class TKUUpdateWorkbenchView(TemplateView):
    __url_path = '/octo_tku_upload/tku_workbench/'
    model = TkuPackagesNew
    template_name = 'workbench.html'
    context_object_name = 'objects'

    def get_context_data(self, **kwargs):
        UserCheck().logator(self.request, 'info', "<=TKUUpdateWorkbenchView=> TKU Upload workbench")
        context = super(TKUUpdateWorkbenchView, self).get_context_data(**kwargs)
        context.update(
            selector=compose_selector(self),
            selector_str='',
            objects=self.get_queryset(),
        )
        return context

    def get_queryset(self):
        UserCheck().logator(self.request, 'info', "<=TKUUpdateWorkbenchView=> TKU Workbench queries")

        # Select packages for workbench:
        packages_qs = TkuPackagesNew.objects.all()
        max_released = packages_qs.filter(tku_type__exact='released_tkn').latest('tku_type', 'updated_at')
        max_ga = packages_qs.filter(tku_type__exact='ga_candidate').latest('tku_type', 'updated_at')
        max_cont_main = packages_qs.filter(tku_type__exact='tkn_main_continuous').latest('tku_type', 'updated_at')
        max_cont_ship = packages_qs.filter(tku_type__exact='tkn_ship_continuous').latest('tku_type', 'updated_at')

        # Select most latest tests dates and package type for workbench:
        tests_qs = UploadTestsNew.objects.all()
        latest_cont_ship = tests_qs.filter(
            mode_key__exact='tkn_ship_continuous_install').values('test_date_time', 'package_type').latest(
            'test_date_time')
        latest_cont_main = tests_qs.filter(
            mode_key__exact='tkn_main_continuous_install').values('test_date_time', 'package_type').latest(
            'test_date_time')
        latest_ga_fresh = tests_qs.filter(
            mode_key__exact='ga_candidate_install').values('test_date_time', 'package_type').latest(
            'test_date_time')
        latest_ga_upgrade = tests_qs.filter(
            mode_key__exact='ga_candidate_install_step_2').values('test_date_time', 'package_type').latest(
            'test_date_time')
        latest_ga_prep = tests_qs.filter(
            mode_key__exact='released_tkn_install_step_1').values('test_date_time', 'package_type').latest(
            'test_date_time')

        # Now select package type upload tests with related dates from above:
        upload_cont_ship = tests_qs.filter(
            mode_key__exact='tkn_ship_continuous_install',
            test_date_time__gte=latest_cont_ship[
                'test_date_time'
            ].replace(hour=0, minute=0, second=0, microsecond=0)
        )
        upload_cont_main = tests_qs.filter(
            mode_key__exact='tkn_main_continuous_install',
            test_date_time__gte=latest_cont_main[
                'test_date_time'
            ].replace(hour=0, minute=0, second=0, microsecond=0)
        )
        upload_ga_fresh = tests_qs.filter(
            mode_key__exact='ga_candidate_install',
            test_date_time__gte=latest_ga_fresh[
                'test_date_time'
            ].replace(hour=0, minute=0, second=0, microsecond=0)
        )
        upload_ga_upgrade = tests_qs.filter(
            mode_key__exact='ga_candidate_install_step_2',
            test_date_time__gte=latest_ga_upgrade[
                'test_date_time'
            ].replace(hour=0, minute=0, second=0, microsecond=0)
        )
        upload_ga_prep = tests_qs.filter(
            mode_key__exact='released_tkn_install_step_1',
            test_date_time__gte=latest_ga_upgrade[
                'test_date_time'
            ].replace(hour=0, minute=0, second=0, microsecond=0)
        )

        selections = dict(
            # MAX latest packages in DB
            max_released=max_released,
            max_ga=max_ga,
            max_cont_main=max_cont_main,
            max_cont_ship=max_cont_ship,
            # Latest dates of upload tests for each type:
            latest_cont_ship=latest_cont_ship,
            latest_cont_main=latest_cont_main,
            latest_ga_fresh=latest_ga_fresh,
            latest_ga_upgrade=latest_ga_upgrade,
            latest_ga_prep=latest_ga_prep,
            # Latest upload test logs for selected dates
            upload_cont_ship=upload_cont_ship,
            upload_cont_main=upload_cont_main,
            upload_ga_fresh=upload_ga_fresh,
            upload_ga_upgrade=upload_ga_upgrade,
            upload_ga_prep=upload_ga_prep,
        )

        return selections


# TKU packages view:
class TKUPackagesListView(ListView):
    __url_path = '/octo_tku_upload/tku_packages_index/'
    model = TkuPackagesNew
    context_object_name = 'tku_packages'
    template_name = 'packages/packages_index.html'

    def get_context_data(self, **kwargs):
        UserCheck().logator(self.request, 'info', "<=TKUPackagesListView=> test cases table context")
        context = super(TKUPackagesListView, self).get_context_data(**kwargs)
        context.update(selector=compose_selector(self), selector_str='')
        return context

    def get_queryset(self):
        UserCheck().logator(self.request, 'info', "<=TKUPackagesListView=> test cases table queryset")
        sel_opts = compose_selector(self)
        queryset = TkuPackagesNew.objects.all()
        queryset = upload_case_query_selector(queryset, sel_opts)
        return queryset.order_by('-updated_at')


# Test History Latest View:
class UploadTestArchiveIndexView(ArchiveIndexView):
    __url_path = '/octo_tku_upload/upload_index/'
    model = UploadTestsNew
    date_field = "test_date_time"
    allow_future = False
    template_name = 'digests/upload_tests_index.html'

    def get_context_data(self, **kwargs):
        UserCheck().logator(self.request, 'info',
                            "<=UploadTestArchiveIndexView=> upload test history index")
        context = super(UploadTestArchiveIndexView, self).get_context_data(**kwargs)
        context.update(selector=compose_selector(self), selector_str='')
        return context

    def get_queryset(self):
        # UserCheck().logator(self.request, 'info', "<=UploadTestArchiveIndexView=> get_queryset")
        sel_opts = compose_selector(self)
        queryset = UploadTestsNew.objects.all()
        queryset = upload_case_query_selector(queryset, sel_opts)
        # log.debug("UploadTestArchiveIndexView queryset explain \n%s", queryset.explain())
        return queryset.order_by('-test_date_time')


# Test History Daily View:
class UploadTestDayArchiveView(DayArchiveView):
    __url_path = '/octo_tku_upload/upload_day/<int:year>/<str:month>/<int:day>/'
    # model = UploadTestsNew
    date_field = "test_date_time"
    allow_future = False
    template_name = 'digests/upload_tests_daily.html'

    def get_context_data(self, **kwargs):
        UserCheck().logator(self.request, 'info', "<=UploadTestDayArchiveView=> upload test history by day")
        context = super(UploadTestDayArchiveView, self).get_context_data(**kwargs)
        context.update(selector=compose_selector(self), selector_str='')
        return context

    def get_queryset(self):
        # UserCheck().logator(self.request, 'info', "<=UploadTestDayArchiveView=> get_queryset")
        sel_opts = compose_selector(self)
        self.queryset = UploadTestsNew.objects.all()
        queryset = upload_case_query_selector(self.queryset, sel_opts)
        # log.debug("UploadTestDayArchiveView queryset explain \n%s", queryset.explain())
        # log.debug("<=UploadTestDayArchiveView=> selected len: %s query: \n%s", queryset.count(), queryset.query)
        return queryset.order_by('-addm_name')


# Test History Today View:
class UploadTestTodayArchiveView(TodayArchiveView):
    __url_path = '/octo_tku_upload/upload_today/'
    model = UploadTestsNew
    date_field = "test_date_time"
    allow_future = False
    template_name = 'digests/upload_tests_today.html'

    def get_context_data(self, **kwargs):
        UserCheck().logator(self.request, 'info',
                            "<=UploadTestTodayArchiveView=> upload test history today")
        context = super(UploadTestTodayArchiveView, self).get_context_data(**kwargs)
        context.update(selector=compose_selector(self), selector_str='')
        return context

    def get_queryset(self):
        # UserCheck().logator(self.request, 'info', "<=UploadTestTodayArchiveView=> get_queryset")
        sel_opts = compose_selector(self)
        queryset = UploadTestsNew.objects.all()
        queryset = upload_case_query_selector(queryset, sel_opts)
        # log.debug("UploadTestTodayArchiveView queryset explain \n%s", queryset.explain())
        return queryset.order_by('-addm_name')
