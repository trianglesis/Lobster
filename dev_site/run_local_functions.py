if __name__ == "__main__":
    import logging
    import django
    import pytz
    import copy
    import collections
    import datetime
    from itertools import groupby
    from operator import itemgetter

    django.setup()
    from django.utils import timezone
    from django.template import loader
    from django.db.models import Q

    from octo.win_settings import SITE_DOMAIN

    from octo_tku_patterns.models import TestLast
    from octo_tku_patterns.model_views import TestLatestDigestAll
    from run_core.models import UserAdprod

    from octo.helpers.tasks_mail_send import Mails

    log = logging.getLogger("octo.octologger")

    def failed_pattern_test_user_daily_digest():
        """
        Send failed test warnings to users related to change of failed patterns.
        One mail per user will all failed tests log.
        :return:
        """

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
                log.warning(f"This user doesnt have an ADPROD: {user_k}")

            # Compose and send email to current user will his digest
            if user_email:
                tests_digest = []  # Usual test
                sel_test_py = []  # Only py
                for test in test_v:
                    sel_test_py.append(test['test_py_path'])
                    tests_digest.append(test)

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
                # Select detailed test logs:
                test_logs = TestLast.objects.filter(test_py_path__in=sel_test_py).order_by('-addm_name')
                # Compose detailed test latest digest
                test_log_html_attachment = test_log_html.render(dict(test_detail=test_logs, domain=SITE_DOMAIN,))

                time_stamp = datetime.datetime.now(tz=timezone.utc).strftime('%Y-%m-%d_%H-%M')
                Mails.short(subject=subject,
                    send_to=['oleksandr_danylchenko_cw@bmc.com'],
                    send_cc=['oleksandr_danylchenko_cw@bmc.com'],
                    mail_html=mail_html,
                    attach_content=test_log_html_attachment,
                    attach_content_name=f'{user_k}_digest_{time_stamp}.html',
                    )
                break
            else:
                # Send a warning email about user ADPROD
                log.warning(f"User has no adprod record! {user_k}: {user_email}")


    def all_pattern_test_team_daily_digest():
        """
        Daily digest of overall pattern tests status, same as ADDM Digest.
        :return:
        """

    def upload_test_failed_warning():
        """
        Managers and team warning when upload test failed.
        Consider different functions for each upload type, or use args
        :return:
        """


    failed_pattern_test_user_daily_digest()
