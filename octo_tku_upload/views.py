"""
OCTO ADM - pages and widgets and functions.
"""
import logging
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.template import loader
from django.views.generic import TemplateView, ListView
from django.views.generic.dates import ArchiveIndexView, DayArchiveView, TodayArchiveView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from django.views.decorators.vary import vary_on_headers
from django.views.decorators.cache import cache_control

from django.utils.decorators import method_decorator

from octo.helpers.tasks_run import Runner
from octo.cache import OctoCache
from octo_adm.user_operations import UserCheck
from octo_tku_upload.api.serializers import TkuPackagesNewSerializer
from octo_tku_upload.models import *
from octo_tku_upload.table_oper import UploadTKUTableOper
from octo_tku_upload.tasks import TUploadExec

from octo_tku_upload.tasks import UploadTaskPrepare, TestCases

log = logging.getLogger("octo.octologger")
curr_hostname = getattr(settings, 'SITE_DOMAIN', None)


# Classical views requests, keep them here for some time.
class UploadTKU:

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


def compose_selector(request_data):
    selector = dict()
    selector.update(
        # Packages:
        # package_type already in
        # tku_type already in
        addm_version=request_data.get('addm_version', None),
        zip_type=request_data.get('zip_type', None),
        tku_name=request_data.get('tku_name', None),
        # Tests:
        test_mode=request_data.get('test_mode', None),
        tku_type=request_data.get('tku_type', None),
        mode_key=request_data.get('mode_key', None),
        addm_name=request_data.get('addm_name', None),
        package_type=request_data.get('package_type', None),
        upload_test_status=request_data.get('upload_test_status', None),
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
        log.debug("queryset sort: tku_type %s", sel_opts.get('tku_type'))
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
@method_decorator(cache_control(max_age=60 * 5), name='dispatch')
class TKUUpdateWorkbenchView(TemplateView):
    __url_path = '/octo_tku_upload/tku_workbench/'
    # model = TkuPackagesNew
    template_name = 'workbench.html'
    context_object_name = 'objects'

    def get_context_data(self, **kwargs):
        # UserCheck().logator(self.request, 'info', "<=TKUUpdateWorkbenchView=> TKU Upload workbench")
        context = super(TKUUpdateWorkbenchView, self).get_context_data(**kwargs)
        context.update(
            selector=compose_selector(self.request.GET),
            selector_str='',
            objects=self.get_queryset(),
        )
        return context

    def get_queryset(self):
        # Select packages for workbench:
        packages_qs = TkuPackagesNew.objects.all()

        max_released = packages_qs.filter(tku_type__exact='released_tkn')
        if max_released:
            max_released = max_released.latest('tku_type', 'updated_at')

        max_ga = packages_qs.filter(tku_type__exact='ga_candidate')
        if max_ga:
            max_ga = max_ga.latest('tku_type', 'updated_at')

        max_cont_main = packages_qs.filter(tku_type__exact='tkn_main_continuous')
        max_cont_main = max_cont_main.latest('tku_type', 'updated_at')

        max_cont_ship = packages_qs.filter(tku_type__exact='tkn_ship_continuous')
        max_cont_ship = max_cont_ship.latest('tku_type', 'updated_at')

        # Select most latest tests dates and package type for workbench:
        tests_qs = UploadTestsNew.objects.all()

        latest_cont_ship = tests_qs.filter(
            Q(mode_key__exact='tkn_ship_continuous_install') |
            Q(mode_key__exact='tkn_ship_continuous.fresh.step_1')).values('test_date_time', 'package_type')
        latest_cont_ship = latest_cont_ship.latest('test_date_time')

        latest_cont_main = tests_qs.filter(
            Q(mode_key__exact='tkn_main_continuous_install') |
            Q(mode_key__exact='tkn_main_continuous.fresh.step_1')).values('test_date_time', 'package_type')
        latest_cont_main = latest_cont_main.latest('test_date_time')

        latest_ga_fresh = tests_qs.filter(
            Q(mode_key__exact='ga_candidate_install') |
            Q(mode_key__exact='ga_candidate.fresh.step_1')).values('test_date_time', 'package_type')
        latest_ga_fresh = latest_ga_fresh.latest('test_date_time')

        latest_ga_upgrade = tests_qs.filter(
            Q(mode_key__exact='ga_candidate_install_step_2') |
            Q(mode_key__exact='ga_candidate.update.step_2')).values('test_date_time', 'package_type')
        latest_ga_upgrade = latest_ga_upgrade.latest('test_date_time')

        latest_ga_prep = tests_qs.filter(
            Q(mode_key__exact='released_tkn_install_step_1') |
            Q(mode_key__exact='released_tkn.update.step_1')).values('test_date_time', 'package_type')
        latest_ga_prep = latest_ga_prep.latest('test_date_time')

        # Uncomment when ready:
        # product_content_ship = tests_qs.filter(
        #     mode_key__exact='tkn_ship_continuous.fresh.step_1.TKU-Product-Content'
        # ).values('test_date_time', 'package_type').latest(
        #     'test_date_time')

        # product_content_main = tests_qs.filter(
        #     mode_key__exact='tkn_main_continuous.fresh.step_1.TKU-Product-Content'
        # ).values('test_date_time', 'package_type').latest(
        #     'test_date_time')

        # Now select package type upload tests with related dates from above:`
        upload_cont_ship = tests_qs.filter(
            Q(mode_key__exact='tkn_ship_continuous_install') |
            Q(mode_key__exact='tkn_ship_continuous.fresh.step_1'),
            test_date_time__gte=latest_cont_ship['test_date_time'].replace(hour=0, minute=0, second=0, microsecond=0)
        )

        upload_cont_main = tests_qs.filter(
            Q(mode_key__exact='tkn_main_continuous_install') |
            Q(mode_key__exact='tkn_main_continuous.fresh.step_1'),
            test_date_time__gte=latest_cont_main['test_date_time'].replace(hour=0, minute=0, second=0, microsecond=0)
        )
        upload_ga_fresh = tests_qs.filter(
            Q(mode_key__exact='ga_candidate_install') |
            Q(mode_key__exact='ga_candidate.fresh.step_1'),
            test_date_time__gte=latest_ga_fresh['test_date_time'].replace(hour=0, minute=0, second=0, microsecond=0)
        )
        upload_ga_upgrade = tests_qs.filter(
            Q(mode_key__exact='ga_candidate_install_step_2') |
            Q(mode_key__exact='ga_candidate.update.step_2'),
            test_date_time__gte=latest_ga_upgrade['test_date_time'].replace(hour=0, minute=0, second=0, microsecond=0)
        )
        upload_ga_prep = tests_qs.filter(
            Q(mode_key__exact='released_tkn_install_step_1') |
            Q(mode_key__exact='released_tkn.update.step_1'),
            test_date_time__gte=latest_ga_upgrade['test_date_time'].replace(hour=0, minute=0, second=0, microsecond=0)
        )

        # upload_product_content_ship = tests_qs.filter(
        #     mode_key__exact='tkn_ship_continuous.fresh.step_1.TKU-Product-Content',
        #     test_date_time__gte=product_content_main['test_date_time'].replace(hour=0, minute=0, second=0, microsecond=0)
        # )
        # upload_product_content_main = tests_qs.filter(
        #     mode_key__exact='tkn_main_continuous.fresh.step_1.TKU-Product-Content',
        #     test_date_time__gte=product_content_main['test_date_time'].replace(hour=0, minute=0, second=0, microsecond=0)
        # )

        upload_product_content_ship = []
        upload_product_content_main = []

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
            upload_cont_ship=upload_cont_ship.order_by('-addm_version'),
            upload_cont_main=upload_cont_main.order_by('-addm_version'),
            upload_ga_fresh=upload_ga_fresh.order_by('-addm_version'),
            upload_ga_upgrade=upload_ga_upgrade.order_by('-addm_version'),
            upload_ga_prep=upload_ga_prep.order_by('-addm_version'),
            # Test logs for product content update:
            upload_product_content_ship=upload_product_content_ship,
            upload_product_content_main=upload_product_content_main,
        )

        return selections


# TKU packages view:
@method_decorator(cache_control(max_age=60 * 5), name='dispatch')
class TKUPackagesListView(ListView):
    context_object_name = 'tku_packages'
    template_name = 'packages/packages_index.html'
    allow_empty = True

    def get_context_data(self, **kwargs):
        # UserCheck().logator(self.request, 'info', "<=TKUPackagesListView=> test cases table context")
        context = super(TKUPackagesListView, self).get_context_data(**kwargs)
        context.update(selector=compose_selector(self.request.GET), selector_str='')
        return context

    def get_queryset(self):
        # UserCheck().logator(self.request, 'info', "<=TKUPackagesListView=> test cases table queryset")
        sel_opts = compose_selector(self.request.GET)
        queryset = TkuPackagesNew.objects.all()
        queryset = upload_case_query_selector(queryset, sel_opts)
        return queryset.order_by('-updated_at')


# Test History Latest View:
@method_decorator(cache_control(max_age=60 * 5), name='dispatch')
class UploadTestArchiveIndexView(ArchiveIndexView):
    __url_path = '/octo_tku_upload/upload_index/'
    model = UploadTestsNew
    date_field = "test_date_time"
    allow_future = False
    allow_empty = True
    template_name = 'digests/upload_tests_index.html'

    def get_context_data(self, **kwargs):
        # UserCheck().logator(self.request, 'info', "<=UploadTestArchiveIndexView=> upload test history index")
        context = super(UploadTestArchiveIndexView, self).get_context_data(**kwargs)
        context.update(selector=compose_selector(self.request.GET), selector_str='')
        return context

    def get_queryset(self):
        # UserCheck().logator(self.request, 'info', "<=UploadTestArchiveIndexView=> get_queryset")
        sel_opts = compose_selector(self.request.GET)
        queryset = UploadTestsNew.objects.all()
        queryset = upload_case_query_selector(queryset, sel_opts)
        # log.debug("UploadTestArchiveIndexView queryset explain \n%s", queryset.explain())
        return queryset.order_by('-test_date_time')


# Test History Daily View:
@method_decorator(cache_control(max_age=60 * 5), name='dispatch')
class UploadTestDayArchiveView(DayArchiveView):
    __url_path = '/octo_tku_upload/upload_day/<int:year>/<str:month>/<int:day>/'
    # model = UploadTestsNew
    date_field = "test_date_time"
    allow_future = False
    allow_empty = True
    template_name = 'digests/upload_tests_daily.html'

    def get_context_data(self, **kwargs):
        # UserCheck().logator(self.request, 'info', "<=UploadTestDayArchiveView=> upload test history by day")
        context = super(UploadTestDayArchiveView, self).get_context_data(**kwargs)
        context.update(selector=compose_selector(self.request.GET), selector_str='')
        return context

    def get_queryset(self):
        # UserCheck().logator(self.request, 'info', "<=UploadTestDayArchiveView=> get_queryset")
        sel_opts = compose_selector(self.request.GET)
        self.queryset = UploadTestsNew.objects.all()
        queryset = upload_case_query_selector(self.queryset, sel_opts)
        # log.debug("UploadTestDayArchiveView queryset explain \n%s", queryset.explain())
        # log.debug("<=UploadTestDayArchiveView=> selected len: %s query: \n%s", queryset.count(), queryset.query)
        return queryset.order_by('-addm_name')


# Test History Today View:
@method_decorator(cache_control(max_age=60 * 5), name='dispatch')
class UploadTestTodayArchiveView(TodayArchiveView):
    __url_path = '/octo_tku_upload/upload_today/'
    model = UploadTestsNew
    date_field = "test_date_time"
    allow_future = False
    allow_empty = True
    template_name = 'digests/upload_tests_today.html'

    def get_context_data(self, **kwargs):
        # UserCheck().logator(self.request, 'info', "<=UploadTestTodayArchiveView=> upload test history today")
        context = super(UploadTestTodayArchiveView, self).get_context_data(**kwargs)
        context.update(selector=compose_selector(self.request.GET), selector_str='')
        return context

    def get_queryset(self):
        # UserCheck().logator(self.request, 'info', "<=UploadTestTodayArchiveView=> get_queryset")
        sel_opts = compose_selector(self.request.GET)
        queryset = UploadTestsNew.objects.all()
        queryset = upload_case_query_selector(queryset, sel_opts)
        # log.debug("UploadTestTodayArchiveView queryset explain \n%s", queryset.explain())
        return queryset.order_by('-addm_name')


# Usual tasks for Upload
class TKUOperationsREST(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAuthenticatedOrReadOnly]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.operation_key = ''
        self.start_time = datetime.now().strftime('%Y-%m-%d_%H-%M')
        self.is_authenticated = ''
        # metadata:
        self.user_name = ''
        self.user_email = ''
        self.manager_user = ''
        self.executer_user = ''
        self.task_id = ''
        #  options:
        self.addm_version = ''

        self.test_mode = ''
        self.tku_type = ''
        self.tku_wget = ''
        self.package_type = ''
        self.test_key = ''

        self.fake_run = False
        self.goto_ = 'http://' + curr_hostname + '/octo_tku_upload/tku_operations/?operation_key='

        self.data = kwargs
        self.jenkins_said = ''

    def task_operations(self):
        """
        Execute task operations or return task operation status.
        If no args passed - return operations dict to show user all possible variants.

        :return:
        """
        operations = dict(
            tku_sync_packages=self.tku_sync_packages,
            tku_parse_packages=self.tku_parse_packages,
            show_latest_tku_type=self.show_latest_tku_type,
            select_latest_tku_type=self.select_latest_tku_type,
            upload_test=self.upload_test,
            jenkins_operations=self.jenkins_operations,
        )
        if self.operation_key:
            actions = operations.get(self.operation_key, 'No such operation key')
        else:
            actions = operations
        return actions

    def metadata_options_set(self):
        if self.request.POST:
            log.debug(f"self.request.POST: {self.request.POST}")
            self.operation_key = self.request.POST.get('operation_key', None)
            self.fake_run = self.request.POST.get('fake_run', False)
            self.task_id = self.request.POST.get('task_id', 'ThisIsNotTheTaskJustSayingYouKnow?')

            self.addm_version = self.request.POST.get('addm_version', None)
            self.test_mode = self.request.POST.get('test_mode', None)
            self.tku_type = self.request.POST.get('tku_type', None)
            self.package_type = self.request.POST.get('package_type', None)
            self.test_key = self.request.POST.get('test_key', None)

            self.jenkins_said = self.request.POST.get('jenkins_said', None)

        elif self.request.GET:
            log.debug(f"self.request.GET: {self.request.GET}")
            self.operation_key = self.request.GET.get('operation_key', None)
            self.fake_run = self.request.GET.get('fake_run', False)
            self.task_id = self.request.GET.get('task_id', '')

            self.addm_version = self.request.GET.get('addm_version', None)
            self.test_mode = self.request.GET.get('test_mode', None)
            self.tku_type = self.request.GET.get('tku_type', None)
            self.package_type = self.request.GET.get('package_type', None)
            self.test_key = self.request.GET.get('test_key', None)

            self.jenkins_said = self.request.GET.get('jenkins_said', None)

        self.is_authenticated = self.request.user.is_authenticated
        self.user_name = self.request.user.get_username()
        self.user_email = self.request.user.email

        self.manager_user = self.request.user.groups.filter(name='manager').exists()
        self.executer_user = self.request.user.groups.filter(name='executer').exists()

        user_status = f'{self.user_name} {self.user_email} manager_user={self.manager_user} executer={self.executer_user}'
        log.info("<=TKUOperationsREST=> Request: %s", user_status)

        request_options = f'operation_key:{self.operation_key} tku_type:{self.tku_type} task_id:{self.task_id}'
        log.debug("<=TKUOperationsREST=> request_options: %s", request_options)

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
                new_all_possible_operations.update(
                    {key: {'doc': value.__doc__.replace('\n', '').replace(' ' * 4, ' '), 'goto': self.goto_ + key}})
            return Response(dict(new_all_possible_operations))
        else:
            operation = self.task_operations()
            if callable(operation):
                response = {self.operation_key: {'doc': operation.__doc__.replace('\n', '').replace(' ' * 4, ' '),
                                                 'goto': self.goto_ + self.operation_key}}
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
            operation = self.task_operations()
            if callable(operation):
                result = operation()
                return Response(result)
            else:
                return Response(dict(error=f'Incorrect params, cannot select routine by provided operation_key!'))
        else:
            log.warning(f"No operation key were provided! data: {self.data}")
            return Response(dict(error='No operation_key were specified!'))

    def upload_test(self):
        """
        Run selected upload test by it's name:
        'test_key=release_ga_upgrade_and_fresh'
        :return:
        """
        kwargs = dict(
            tku_wget=self.tku_wget,
            test_mode=self.test_mode,
            tku_type=self.tku_type,
            user_name=self.user_name,
            user_email=self.user_email,
            test_key=self.test_key
        )
        log.debug(f"Send kwargs to TestCases ->  {kwargs}")
        task = Runner.fire_t(TUploadExec.t_upload_routines,
                             fake_run=self.fake_run,
                             t_kwargs=kwargs,
                             t_args=[str(kwargs)])
        return {'task_id': task.id, 'added': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'routine_kwargs': kwargs}

    def tku_sync_packages(self):
        """
        Run internal routine to get latest tku packages from buildhub server via WGET. Parse downloaded content
        and update packages table with new or re-built packages. Can sync only one TKU by tku_type:(tkn_ship_continuous, ga_candidate, released_tkn, tkn_main_continuous)
        :return:
        """
        task = Runner.fire_t(TUploadExec.t_tku_sync,
                             fake_run=self.fake_run,
                             t_kwargs=dict(tku_type=self.tku_type),
                             t_args=['tag=t_tku_sync;'])
        return {'task_id': task.id}

    def tku_parse_packages(self):
        """
        Parse local TKU packages directory and update local database with new packages if found.

        :return:
        """
        t_tag = 'run_tku_parse'
        options = dict(user_name=self.user_name, tku_type=self.tku_type)
        task = Runner.fire_t(TUploadExec.t_parse_tku,
                             fake_run=self.fake_run,
                             t_kwargs=options,
                             t_args=[t_tag],
                             )
        return {'task_id': task.id}

    def show_latest_tku_type(self):
        """
        Show latest tku packages for tku_type:(tkn_ship_continuous, tkn_main_continuous, ga_candidate, released_tkn)
        and sort addm_version if arg was provided addm_version:(11.3)
        Only provide package data and release details. Show ga_candidate if no tku_type provided.
        Example:
        (operation_key=show_latest_tku_type;tku_type=ga_candidate)
        (operation_key=show_latest_tku_type;tku_type=released_tkn)
        (operation_key=show_latest_tku_type;tku_type=tkn_ship_continuous)
        (operation_key=show_latest_tku_type;tku_type=tkn_main_continuous)
        :return: set with latest known TKU Package details
        """
        selector = compose_selector(self.request.POST)
        queryset = TkuPackagesNew.objects.all()
        queryset = upload_case_query_selector(queryset, selector)
        queryset = queryset.latest('tku_type', 'updated_at')
        serializer = TkuPackagesNewSerializer(queryset)
        return serializer.data

    def select_latest_tku_type(self):
        """
        Select latest tku packages for tku_type:(tkn_ship_continuous, tkn_main_continuous, ga_candidate, released_tkn)
        and sort addm_version if arg was provided addm_version:(11.3)
        Example:
        (operation_key=select_latest_tku_type;tku_type=ga_candidate)
        (operation_key=select_latest_tku_type;tku_type=released_tkn)
        (operation_key=select_latest_tku_type;tku_type=tkn_ship_continuous)
        (operation_key=select_latest_tku_type;tku_type=tkn_main_continuous)
        :return: set with latest selected TKU Package and link to download? (TBA)
        """
        packages_qs = TkuPackagesNew.objects.all()
        max_package = packages_qs.filter(tku_type__exact=self.tku_type).latest('tku_type', 'updated_at')
        packages = packages_qs.filter(package_type__exact=max_package.package_type)
        serializer = TkuPackagesNewSerializer(packages, many=True)
        return serializer.data

    def jenkins_operations(self):
        """
        Give a signal for Octopus, when build is finished - to start download zip files and initiate a TKU Upload test.
        | Uses two arguments:
        | tku_type - this arg run WGET from Octopus for selected type of packages. This arg is also run different Upload approaches:
        |    tku_type=addm_released, OR ga_candidate, released_tkn, tkn_main_continuous, tkn_ship_continuous
        |    ga_candidate: will run upload upgrade and upload fresh routines by default;
        |    tkn_main_continuous: will run simple tku fresh install, and will run product_content update for all ADDM machines for TKN_MAIN branch
        |    tkn_ship_continuous: same as previous, but for ship;
        |    tkn_ship_continuous with test_mode=upgrade - will run TKU Upgrade routine with SHIP continuous same as GA_CANDIDATE
        | test_mode - OPTIONAL, this arg is used only for forced run of UPGRADE routine with tkn_ship_continuous package.
        |    test_mode=update, OR other, but not yet implemented here (fresh, tideway_content, tideway_devices, step)
        | package_type - OPTIONAL, this arg will indicate a package which will be installed.
        |    package_type=TKN-Release-0000-00-0-227, OR TKN_release_2020-08-2-505, tkn_main_continuous_2071-01-1-000, etc.
        | Example request:
        | /octo_tku_upload/tku_operations/?operation_key=jenkins_operations&tku_type=tkn_ship_continuous&package_type=TKN-Release-0000-00-0-227&jenkins_said=IHaveFinished
        - this will run usual fresh upload routine, and product_content update for other machines.
        | /octo_tku_upload/tku_operations/?operation_key=jenkins_operations&tku_type=tkn_ship_continuous&package_type=TKN-Release-0000-00-0-227&test_mode=update
        - this will run UPGRADE upload routine for ship build.
        | Use token auth: curl -X GET /octo_tku_upload/tku_operations/ -H 'Authorization: Token HERE_YOUR_TOKEN'
        | Help: https://www.django-rest-framework.org/api-guide/authentication/#tokenauthentication
        :return:
        """
        kwargs_d = dict(
            user_name=self.user_name,
            user_email=self.user_email,

            test_mode=self.test_mode,
            tku_type=self.tku_type,
            package_type=self.package_type,

            jenkins_said=self.jenkins_said,
        )
        response = {
            'routine_kwargs': kwargs_d,
            'executed': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'message': 'Octopus will execute WGET operation for selected tku_type, then it will select latest package_type or provided by request as TKU Upload test',
            'help': self.jenkins_operations.__doc__.replace('\n', '')
        }

        # TODO: Here run external decider, which will execute predefined routines, based on provided Jenkins params
        if self.tku_type == 'tkn_ship_continuous':
            kwargs_d.update(test_key='jenkins_ship_cont')
        else:
            msg = "I do not know this option yet, please use documented only!"
            response.update(message=msg, error='ERROR - please read the message!')
            return response

        log.debug(f"Send kwargs to TestCases ->  {kwargs_d}")
        task = Runner.fire_t(TUploadExec.t_upload_routines,
                             fake_run=self.fake_run,
                             t_kwargs=kwargs_d,
                             t_args=[str(kwargs_d)])

        log.info(f"<=JenkinsOperations=> Run TKU Upload test by Jenkins request: {kwargs_d}")
        response.update(task_id=task.id, success="Task has been executed!")
        return response


## Short views:
class TKUUpdateWorkbenchViewShort(TKUUpdateWorkbenchView):
    template_name = 'workbench_short.html'
