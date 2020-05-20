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
    from django.template import loader
    from django.db.models import Q

    from octo_tku_patterns.models import TestCases, TestCasesDetails
    from octo_tku_patterns.model_views import TestLatestDigestAll
    from run_core.models import UserAdprod

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
        print(f"Selected non passed tests grouped: {all_nonpass_tests}")

        # Iter each user and set of failed tests:
        for user_k, test_v in all_nonpass_tests:
            print()
            # Select user email:
            try:
                user = UserAdprod.objects.get(adprod_username__exact=user_k)
                print(f"User: {user_k}: {user.user.email}")
            except:
                print(f"This user doesn't have an ADPROD: {user_k}")

            # Compose short test latest digest
            mail_body.render(dict(tests_digest=test_v))

            for test in test_v:
                print(f"Test: {test}")
                log.debug(f"Non passed test by user: {test.change_user} - {test.tkn_branch}, {test.pattern_library}, {test.pattern_folder_name}")
            # Compose detailed test log

            print(mail_body)

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
