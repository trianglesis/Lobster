"""
Store here local functions to parse, obtain, compose operations for database details.

"""
from django.utils import timezone
# New
from operator import itemgetter
from typing import Dict, List, Any
import datetime

from django.db.models import Q, Max, Min
from django.db.models.query import RawQuerySet

from octo_tku_patterns.models import TestLast, TestHistory, TestCases


# Python logger
import logging
log = logging.getLogger("octo.octologger")


class PatternsDjangoModelRaw:

    def __init__(self):
        self.last_tests_tb = 'octo_test_last'
        self.history_tests_tb = 'octo_test_history'
        self.tku_patterns_table = 'octo_tku_patterns'
        self.octo_test_cases = 'octo_test_cases'
        self.database = 'octopus_dev_copy'

    @staticmethod
    def select_latest_long_tests(branch):
        """

        GROUP BY {tb}.pattern_folder_name
        GROUP BY {tb}.addm_host

        ORDER BY {tb}.time_spent_test DESC
        ORDER BY {tb}.time_spent_test

        LIMIT 20;
        :param branch:
        :return:
        """

        query = '''
        SELECT 
            {tb}.id,
            {tb}.pattern_library,
            {tb}.pattern_folder_name,
            {tb}.time_spent_test,
            {tb}.tst_status,
            {tb}.tst_class,
            {tb}.addm_name,
            {tb}.addm_group,
            {tb}.addm_host,
            {tb}.tkn_branch,
            {tb}.test_date_time
        FROM octopus_dev_copy.{tb}
        WHERE {tb}.tkn_branch = '{branch}'
        GROUP BY {tb}.addm_host, {tb}.test_py_path
        '''.format(tb='octo_test_last', branch=branch)

        tests_top = TestLast.objects.raw(query)
        tests_top_list = []
        for test_item in tests_top:
            # log.debug("test_item %s", test_item.test_py_path)
            try:
                test_item_d = dict(
                    pattern_library=test_item.pattern_library,
                    pattern_folder_name=test_item.pattern_folder_name,
                    ordering_by_ts=round(float(test_item.time_spent_test), 1),
                    time_spent_test=test_item.time_spent_test,
                    tst_status=test_item.tst_status,
                    tst_class=test_item.tst_class,
                    addm_name=test_item.addm_name,
                    addm_group=test_item.addm_group,
                    addm_host=test_item.addm_host,
                    tkn_branch=test_item.tkn_branch,
                    test_date_time=test_item.test_date_time,
                )
                tests_top_list.append(test_item_d)
            except AttributeError as e:
                # Ignore items where attr is not set:
                log.error("This test item has no attribute %s", e)

        tests_top_sort = sorted(tests_top_list, key = itemgetter('ordering_by_ts'), reverse = True)

        return tests_top_sort

    def sel_history_by_latest_all(self, query_args):
        """
        Select last N days test records for pattern:

        :param query_args:
        :return:
        """
        from django.utils import timezone
        now = datetime.datetime.now(tz=timezone.utc)
        tomorrow = now + datetime.timedelta(days=1)

        date_from = now - datetime.timedelta(days=int(query_args['last_days']))

        log.debug("Selecting days %s between: %s %s", query_args['last_days'],
                  date_from.strftime('%Y-%m-%d'), tomorrow.strftime('%Y-%m-%d'))

        query = """SELECT {tb}.id,
                          {tb}.time_spent_test,
                          {tb}.test_py_path,
                          {tb}.test_date_time
                   FROM {db}.{tb}
                   WHERE {tb}.test_date_time BETWEEN '{date_from}' AND '{tomorrow}'
                   AND {tb}.addm_name = 'double_decker'
                   GROUP BY day({tb}.test_date_time), {tb}.test_py_path
                   ORDER BY {tb}.test_py_path;
                   """.format(db=self.database,
                              tb=self.history_tests_tb,
                              date_from=date_from.strftime('%Y-%m-%d'),
                              tomorrow=tomorrow.strftime('%Y-%m-%d'))
        log.debug("Using query: \n%s", query)

        history_recs = TestHistory.objects.raw(query)

        return history_recs


class PatternsDjangoTableOper:

    @staticmethod
    def release_db_date():
        """ Just generate time window from last month 26th till today +1 day
        Because p4 would not show all today changes

        Start dates:
        - main "2017-09-25"
        - ship "2017-10-12"
        """
        # TODO: Here update dates also!
        import datetime
        date_time_now = datetime.datetime.now()

        # CURRENT day date
        last_day = date_time_now + datetime.timedelta(days=1)
        tomorrow = last_day.strftime('%Y-%m-%d')

        # 25th date of previous month:
        first_day_month  = datetime.date.today().replace(day=1)
        lastMonth = first_day_month - datetime.timedelta(days=6)
        last_month_release = lastMonth.strftime('%Y-%m-%d')

        release_window = dict(
            today      = tomorrow,
            start_date = last_month_release)

        return release_window

    # TODO: CHANGE EVERYWHERE where is relation to this
    @staticmethod
    def sel_tests_dynamical(**kwargs):
        """
        Based on options from kwargs - select patterns for test routine.
        Possible options:

        - include: list of pattern folder names should be selected anyway;
        - exclude: list of pattern folder names should NOT be selected anyway;
        - last_days: datetime window converted from int of last days changes to select patterns;
        - date_from: datetime str from what date to start;
            - date_to: if set - the latest date of changes, if not - use tomorrow date
        - branch: tkn_main or tkn_ship or both if none
        - user: user_adprod name - to choose only those patterns;
        - change: str - number of p4 change
        - library: CORE, CLOUD etc

        :param kwargs:
        :return:
        """
        from django.utils import timezone
        import datetime
        sel_opts = kwargs.get('sel_opts', {})

        now = datetime.datetime.now(tz=timezone.utc)
        tomorrow = now + datetime.timedelta(days=1)

        # switch-case:
        selectables = dict(
            # sel_k = sel_v
            # Experimental options:
            pattern_folder_name='pattern_folder_name__in',
            # Dynamical options:
            last_days='change_time__range',
            date_from='change_time__range',
            # Strict options:
            exclude='pattern_folder_name__in',
            branch='tkn_branch__exact',
            user='change_user__exact',
            change='change__exact',
            library='pattern_library__exact',
        )

        log.debug("<=Django Model intra_select=> Select sel_opts %s", sel_opts)

        # Select everything valid for test:
        all_patterns = TestCases.objects.filter(test_type__exact='tku_patterns')

        def intra_select(queryset, option_key, option_value):
            sel_k = selectables.get(option_key)
            select_d = {sel_k: option_value}

            # # NOT Work fine, NOT excluding by pattern's folder
            # TODO: Exclude by checking if pattern is member of "Excluded" group.
            if option_key == 'exclude':
                # log.debug("<=Django Model intra_select=> Select exclude: %s", select_d)
                intra_filtered = queryset.exclude(**select_d)

            # Select from last N-days, till today(tomorrow)
            elif option_key == 'last_days':
                date_from = now - datetime.timedelta(days=int(option_value))
                # log.debug("<=Django Model intra_select=> Select for the last %s days. %s %s", option_value, date_from, tomorrow)
                select_d.update(change_time__range=[date_from, tomorrow])
                # log.debug("<=Django Model intra_select=> Select last_days: %s", select_d)
                intra_filtered = queryset.filter(**select_d)

            # Select from strict date till today(tomorrow)
            elif option_key == 'date_from':
                date_from = datetime.datetime.strptime(option_value, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                # log.debug("<=Django Model intra_select=> Select date_from %s %s to %s", option_value, date_from, tomorrow)
                select_d.update(change_time__range=[date_from, tomorrow])
                # log.debug("<=Django Model intra_select=> Select date_from: %s", select_d)
                intra_filtered = queryset.filter(**select_d)

            # All other strict options:
            else:
                # log.debug("<=Django Model intra_select=> Select %s: %s", sel_k, select_d)
                intra_filtered = queryset.filter(**select_d)

            return intra_filtered

        for opt_k, opt_v in sel_opts.items():
            # When key value is present and not None
            if opt_v:
                # log.info("<=Django Model=> Using this option: %s value is %s", opt_k, opt_v)
                all_patterns = intra_select(all_patterns, opt_k, opt_v)
            else:
                # log.info("<=Django Model=> Skipping this option: %s value is %s", opt_k, opt_v)
                pass

        # log.debug("<=Django Model intra_select=> sel_tests_dynamical() "
        #           "selected len: %s "
        #           "history_recs.query: \n%s", all_patterns.count(), all_patterns.query)

        log.debug("sel_tests_dynamical queryset explain \n%s", all_patterns.explain())
        return all_patterns

    @staticmethod
    def sel_dynamical(model, **kwargs):
        """
        Based on options from kwargs - select patterns for test routine.
        Possible options:

        - include: list of pattern folder names should be selected anyway;
        - exclude: list of pattern folder names should NOT be selected anyway;
        - last_days: datetime window converted from int of last days changes to select patterns;
        - date_from: datetime str from what date to start;
            - date_to: if set - the latest date of changes, if not - use tomorrow date
        - branch: tkn_main or tkn_ship or both if none
        - user: user_adprod name - to choose only those patterns;
        - change: str - number of p4 change
        - library: CORE, CLOUD etc

        :param model:
        :param kwargs:
        :return:
        """
        sel_opts = kwargs.get('sel_opts', {})

        now = datetime.datetime.now(tz=timezone.utc)
        tomorrow = now + datetime.timedelta(days=1)

        # switch-case:
        selectables = dict(
            test_type='test_type__exact',
            tkn_branch='tkn_branch__exact',
            change_user='change_user__exact',
            change_review='change_review__contains',
            change_ticket='change_ticket__exact',
            pattern_library='pattern_library__exact',
            pattern_folder_name='pattern_folder_name__exact',
            pattern_folder_names='pattern_folder_name__in',  # list()
            change='change__exact',
            # Test related:
            addm_name='addm_name__exact',
            addm_group='addm_group__exact',
            addm_v_int='addm_v_int__exact',
            addm_host='addm_host__exact',
            addm_ip='addm_ip__exact',
            # Dynamical options:
            last_days='change_time__range',
            date_from='change_time__range',
            # Strict options:
            exclude='pattern_folder_name__in',  # list()

            # For single test.py record sorting:
            test_py_path='test_py_path__exact',
            # For single test item sorting:
            tst_name='tst_name__exact',
            tst_class='tst_class__exact',
            # TBA:
            # test_time_weight='test_time_weight',
            # TODO: Try to add here queryset.filter(Q(fails__gte=1) | Q(error__gte=1)) and so on
            # tst_status
        )
        # log.debug("<=Django Model intra_select=> Select sel_opts %s", sel_opts)
        all_qs = model.objects.all()

        def intra_select(queryset, option_key, option_value):
            sel_k = selectables.get(option_key)
            select_d = {sel_k: option_value}

            # # NOT Work fine, NOT excluding by pattern's folder
            # TODO: Exclude by checking if pattern is member of "Excluded" group.
            if option_key == 'exclude':
                # log.debug("<=Django Model intra_select=> Select exclude: %s", select_d)
                intra_qs = queryset.exclude(**select_d)

            # Select from last N-days, till today(tomorrow)
            elif option_key == 'last_days':
                date_from = now - datetime.timedelta(days=int(option_value))
                # log.debug("<=Django Model intra_select=> Select for the last %s days. %s %s", option_value, date_from, tomorrow)
                select_d.update(change_time__range=[date_from, tomorrow])
                # log.debug("<=Django Model intra_select=> Select last_days: %s", select_d)
                intra_qs = queryset.filter(**select_d)

            # Select from strict date till today(tomorrow)
            elif option_key == 'date_from':
                date_from = datetime.datetime.strptime(option_value, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                # log.debug("<=Django Model intra_select=> Select date_from %s %s to %s", option_value, date_from, tomorrow)
                select_d.update(change_time__range=[date_from, tomorrow])
                # log.debug("<=Django Model intra_select=> Select date_from: %s", select_d)
                intra_qs = queryset.filter(**select_d)
            elif option_key == 'tst_status':
                log.debug("Going to sort selected tests with status '%s' only.", option_value)
                if option_value == 'pass':
                    log.debug("use: pass_only")
                    intra_qs = queryset.filter(~Q(tst_status__iregex='FAIL$') & ~Q(tst_status__iregex='ERROR$'))
                elif option_value == 'fail':
                    log.debug("use: fail_only")
                    intra_qs = queryset.filter(tst_status__iregex='FAIL$')
                elif option_value == 'notpass':
                    log.debug("use: not_pass_only")
                    intra_qs = queryset.filter(
                        Q(tst_status__iregex='FAIL$') | Q(tst_status__iregex='ERROR$') | Q(tst_status__iregex='unexpected'))
                elif option_value == 'error':
                    log.debug("use: error_only")
                    intra_qs = queryset.filter(tst_status__iregex='ERROR$')
                elif option_value == 'skip':
                    log.debug("use: skip_only")
                    intra_qs = queryset.filter(
                        Q(tst_status__iregex='skipped') | Q(tst_status__iregex='expected failure'))
                else:
                    log.warning("Unknown option_value '%s' for '%s' Do not select - return as is.",
                              option_value, option_key)
                    intra_qs = queryset

            # All other strict options:
            else:
                # log.debug("<=Django Model intra_select=> Select %s: %s", sel_k, select_d)
                intra_qs = queryset.filter(**select_d)

            return intra_qs

        for opt_k, opt_v in sel_opts.items():
            # When key value is present and not None
            if opt_v:
                # log.info("<=Django Model=> Using this option: %s value is %s", opt_k, opt_v)
                all_qs = intra_select(all_qs, opt_k, opt_v)
            else:
                # log.info("<=Django Model=> Skipping this option: %s value is %s", opt_k, opt_v)
                pass
        # log.debug("<=Django Model intra_select=> sel_tests_dynamical() "
        #           "selected len: %s "
        #           "history_recs.query: \n%s", all_qs.count(), all_qs.query)
        #
        # log.debug("sel_dynamical queryset explain \n%s", all_qs.explain())
        return all_qs


class PatternsDjangoTableOperDel:

    """
    Routine to delete logs older than 400 days.
    DELETE FROM `octopus_dev_copy`.`octo_test_history`
        WHERE test_date_time < DATE_SUB(NOW(),INTERVAL 400 DAY);
    """

    @staticmethod
    def delete_old_solo_test_logs(query_args):
        test_item_deleted = 'None'
        try:
            if query_args.get('tst_class') and query_args.get('tst_name'):
                test_item_deleted = TestLast.objects.filter(
                    tkn_branch__exact          = query_args['branch'],
                    pattern_library__exact     = query_args['pattern_library'],
                    pattern_folder_name__exact = query_args['pattern_folder'],
                    tst_name__exact            = query_args['tst_name'],
                    tst_class__exact           = query_args['tst_class']
                ).delete()
            else:
                test_item_deleted = TestLast.objects.filter(
                    tkn_branch__exact          = query_args['branch'],
                    pattern_library__exact     = query_args['pattern_library'],
                    pattern_folder_name__exact = query_args['pattern_folder'],
                )
        except Exception as e:
            log.error("<=DjangoTableOperDel=> delete_old_solo_test_logs Error: %s", e)
        return test_item_deleted
