"""
OCTO DEV views only
"""

from django.http import HttpResponse
from django.template import loader
from django.contrib.auth.decorators import permission_required

from octo_adm.user_operations import UserCheck
from octo_tku_patterns.model_views import TestLatestDigestAll
from octo_tku_patterns.models import TestLast, TestCases
from octo.win_settings import SITE_DOMAIN, SITE_SHORT_NAME

# Python logger
import logging

log = logging.getLogger("octo.octologger")


class DevAdminViews:

    @staticmethod
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def index(request):
        """
        Draw useful widgets for OCTO ADMIN page.

        REMOTE_ADDR – The IP address of the client.
        REMOTE_HOST – The hostname of the client.

        :param request:
        :return:
        """
        page_widgets = loader.get_template('dev_debug_workbench/dev_main.html')
        user_name, user_str = UserCheck().user_string_f(request)

        subject = "Hello  here you can manage Octopus tasks and see stats".format(user_name)

        log.debug("<=WEB OCTO AMD=> Allowed to admin page: %s", user_str)

        widgets = dict(SUBJECT=subject)
        # widgets_page = page_widgets.render(widgets)
        # https://docs.djangoproject.com/en/2.0/topics/http/shortcuts/
        return HttpResponse(page_widgets.render(widgets, request))

    @staticmethod
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def dev_user_test_finished(request):

        # OPTIONS MANUAL SET
        log_html = ''
        test_item = dict(
            test_py_path='/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE/HP_P2000/tests/test.py')
        mail_opts = dict(mode='finish')
        request = dict(cases_ids='67,68,569')
        # =========================================================================

        test_added = loader.get_template('service/emails/statuses/test_added.html')
        test_log_html = loader.get_template('digests/tables_details/test_details_table_email.html')
        mode = mail_opts.get('mode')  # Mode decision

        # Select and show all cases by id
        cases_selected = []
        if mode == 'init':
            cases_selected = TestCases.objects.filter(id__in=request.get("cases_ids", '').split(','))
            log.info(f"Selected cases for test: {cases_selected}")

        tests_digest = []
        if mode == 'finish':
            tests_digest = TestLatestDigestAll.objects.filter(test_py_path__exact=test_item['test_py_path']).order_by(
                '-addm_name').distinct()
            log.info(f"Test results selected by: {test_item['test_py_path']} are {tests_digest}")
            # Compose raw log and attach to email:
            test_logs = TestLast.objects.filter(test_py_path__exact=test_item['test_py_path']).order_by(
                '-addm_name').distinct()
            log_html = test_log_html.render(dict(test_detail=test_logs, domain=SITE_DOMAIN, ))

        mail_html = test_added.render(
            dict(
                subject='DEV EMAIL',
                domain=SITE_DOMAIN,
                mail_opts=mail_opts,
                tests_digest=tests_digest,
                cases_selected=cases_selected,
            )
        )
        return HttpResponse(log_html)

    @staticmethod
    @permission_required('run_core.superuser', login_url='/unauthorized_banner/')
    def failed_pattern_test_user_daily_digest(request):
        """
        Send failed test warnings to users related to change of failed patterns.
        One mail per user will all failed tests log.
        :return:
        """
        from django.db.models import Q
        from itertools import groupby
        from operator import itemgetter
        from run_core.models import UserAdprod

        mail_body = loader.get_template('digests/user_nonpass_digest_email.html')
        test_log_html = loader.get_template('digests/tables_details/test_details_table_email.html')

        all_nonpass_tests = TestLatestDigestAll.objects.filter(Q(fails__gte=1) | Q(error__gte=1)).values().order_by('-change_user')
        all_nonpass_tests = groupby(all_nonpass_tests, itemgetter('change_user'))
        log.info(f"Selected non passed tests grouped: {all_nonpass_tests}")

        # Iter each user and set of failed tests:
        for user_k, test_v in all_nonpass_tests:
            # Select user email:
            try:
                user = UserAdprod.objects.get(adprod_username__exact=user_k)
                user_email = user.user.email
                log.info(f"User: {user_k}: {user.user.email}")
            except:
                user_email = None
                log.info(f"This user doesn't have an ADPROD: {user_k}")

            if user_email:
                tests_digest = []
                sel_test_py = []
                for test in test_v:
                    log.info(f"TEST: {test} {test['test_py_path']}")
                    sel_test_py.append(test['test_py_path'])
                    tests_digest.append(test)
                log.info(f"Selected IDs: {sel_test_py}")

                # Compose short test latest digest
                subject = 'This is the digest of not passed tests, see attachment for detailed log.'

                mail_html = mail_body.render(
                    dict(
                        subject=subject,
                        domain=SITE_DOMAIN,
                        user=user_k,
                        tests_digest=tests_digest
                    )
                )
                test_logs = TestLast.objects.filter(test_py_path__in=sel_test_py).order_by('-addm_name')
                log.info(f"Selected test_logs: {test_logs}")

                test_log_html_attach = test_log_html.render(dict(test_detail=test_logs, domain=SITE_DOMAIN))
                # return HttpResponse(test_log_html.render(dict(test_detail=test_logs, domain=SITE_DOMAIN), request))
                # return HttpResponse(test_log_html_attach, request)
                return HttpResponse(mail_html, request)
