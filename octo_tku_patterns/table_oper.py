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

from octo_tku_patterns.models import TkuPatterns, TestLast, TestHistory, TestCases, TestCasesDetails


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

    def addm_summary(self, query_args):
        """
        Select summary information about test stats grouped by ADDM

        :param query_args:
        :return:
        """
        addm_name = query_args['addm_name']
        branch = query_args['branch']

        fail_r = r'^(FAIL|fail|unexpected|failure)'
        # not_pass_r = r'^(FAIL|fail|unexpected|failure|ERROR)'

        # Compose query:
        query = """SELECT 
                         {tb}.id,
                         {tb}.addm_host,
                         {tb}.addm_name,
                         {tb}.addm_v_int,
                         COUNT({tb}.test_py_path) AS tests_count,
                         COUNT(DISTINCT {tb}.pattern_folder_name) AS patterns_count,
                         SUM({tb}.tst_status REGEXP '{fail_r}') AS fails,
                         SUM({tb}.tst_status = 'ERROR') AS error,
                         SUM({tb}.tst_status = 'ok') AS passed,
                         SUM({tb}.tst_status REGEXP '(skipped|expected)') AS skipped
                   FROM {db}.{tb}
                   WHERE {tb}.addm_name = '{addm_name}' AND {tb}.tkn_branch = '{branch}'
                   ORDER BY {tb}.pattern_folder_name;
                   """.format(db=self.database,
                              tb=self.last_tests_tb,
                              fail_r=fail_r,
                              branch=branch,
                              addm_name=addm_name)

        addm_sorted_tests = TestLast.objects.raw(query)

        log.debug("<=TABLE OPER=> DjangoModelRaw() "
                  "query_args: %s"
                  "addm_sorted_tests.query: \n%s", query_args, addm_sorted_tests.query)

        return addm_sorted_tests

    def addm_summary_new(self, branch):
        """
        Select summary information about test stats grouped by ADDM

        :param branch:
        :return:
        """
        fail_r = r'^(FAIL|fail|unexpected|failure)'
        # not_pass_r = r'^(FAIL|fail|unexpected|failure|ERROR)'

        # Compose query:
        query = """SELECT
                       {tb}.id,
                       {tb}.tkn_branch,
                       {tb}.addm_host,
                       {tb}.addm_name,
                       {tb}.addm_v_int,
                       COUNT({tb}.test_py_path) AS tests_count,
                       COUNT(DISTINCT {tb}.pattern_folder_name) AS patterns_count,
                       SUM({tb}.tst_status REGEXP '{fail_r}') AS tests_fails,
                       SUM({tb}.tst_status = 'ERROR') AS tests_error,
                       SUM({tb}.tst_status = 'ok') AS tests_passed,
                       SUM({tb}.tst_status REGEXP '(skipped|expected)') AS tests_skipped,
                       ROUND((((SUM({tb}.tst_status = 'ok') + SUM({tb}.tst_status REGEXP '(skipped|expected)')) / COUNT({tb}.test_py_path)) * 100),2) AS tests_passed_percent
                   FROM {db}.{tb}
                   WHERE {tb}.tkn_branch = '{branch}'
                   GROUP BY {tb}.addm_name
                   ORDER BY {tb}.pattern_folder_name;
                   """.format(db=self.database, tb=self.last_tests_tb, fail_r=fail_r, branch=branch)

        addm_sorted_tests = TestLast.objects.raw(query)

        # log.debug("<=TABLE OPER=> DjangoModelRaw() "
        #           "addm_sorted_tests.query: \n%s", addm_sorted_tests.query)

        return addm_sorted_tests

    @staticmethod
    def patterns_for_test_both(**kwargs) -> list:
        """
        Use branch and release window dates to run raw SQL query to octo_tku_patterns table.
        Selected item is RawQuerySet later converted to dict.

        :rtype: list
        """
        slice_arg = kwargs.get('slice_arg', False)
        # Should not be defined for both:
        excluded_list = kwargs.get('excluded_seq', [])
        sorted_list = kwargs.get('included_seq', [])

        last_day = datetime.datetime.now() + datetime.timedelta(days = 1)

        # log.info("<=TABLE OPER=> patterns_for_test_both() excluded_list: %s, sorted_list: %s", excluded_list, sorted_list)

        additions = ''
        if excluded_list:
            excluded_list.append('')  # Close sequence tuple with empty value.
            additions = "AND {tb}.pattern_folder_name NOT IN {additions_tuple} " \
                        "AND {tb}.pattern_library NOT IN {additions_tuple}".format(
                            tb='octo_tku_patterns',
                            additions_tuple=tuple(item for item in excluded_list))

        # TODO: Test to sort only selected.
        if sorted_list:
            sorted_list.append('')  # Close sequence tuple with empty value.
            additions = "AND {tb}.pattern_folder_name IN {additions_tuple} " \
                        "OR {tb}.pattern_library IN {additions_tuple}".format(
                            tb='octo_tku_patterns',
                            additions_tuple=tuple(item for item in sorted_list))

        # log.info("<=TABLE OPER=> patterns_for_test_both() excluded_list: %s, sorted_list: %s, additions: %s", additions, excluded_list, sorted_list)

        # noinspection PyPep8
        # TODO: pattern_folder_mod_time -> change_time
        raw_q = """
        SELECT {tb}.id,
               {tb}.tkn_branch,
               {tb}.pattern_library,
               {tb}.pattern_folder_name,
               {tb}.pattern_file_path,
               {tb}.test_py_path,
               {tb}.test_py_path_template,
               {tb}.test_folder_path_template,
               {tb}.pattern_folder_path_depot,
               {tb}.pattern_file_path_depot,
               {tb}.is_key_pattern
        FROM {tb}
        WHERE ({tb}.tkn_branch = 'tkn_main' 
           AND {tb}.test_py_path REGEXP 'tests/test\.py'
           AND {tb}.test_py_path_template REGEXP 'tests/test\.py'
           AND {tb}.pattern_folder_mod_time BETWEEN '2017-09-25' AND '{end_date}'
           {additions}
           )
        OR    ({tb}.tkn_branch = 'tkn_ship' 
           AND {tb}.test_py_path REGEXP 'tests/test\.py'
           AND {tb}.test_py_path_template REGEXP 'tests/test\.py'
           AND {tb}.pattern_folder_mod_time BETWEEN '2017-10-12' AND '{end_date}'
           {additions}
           )
        OR    ({tb}.test_py_path REGEXP 'tests/test\.py'
           AND {tb}.test_py_path_template REGEXP 'tests/test\.py'
           AND {tb}.is_key_pattern = True
           {additions}
           )
        GROUP BY {tb}.test_py_path""".format(tb='octo_tku_patterns', end_date=last_day,
                                             additions=additions if additions else '')

        tests_set_q = TkuPatterns.objects.raw(raw_q)  # type: RawQuerySet

        # log.debug("<=TABLE OPER=> DjangoModelRaw() "
        #           "addm_sorted_tests.query: \n%s", tests_set_q.query)

        if slice_arg:
            tests_set_q = tests_set_q[:int(slice_arg)]  # type: RawQuerySet
        # Primitive RawQuerySet to Dict conversion:
        test_items_list = []  # type: List[Dict[Any, Any]]
        for test_item in tests_set_q:
            # log.debug("test_item %s", test_item.test_py_path)
            try:
                test_item_d = dict(
                    tkn_branch=test_item.tkn_branch,
                    pattern_library=test_item.pattern_library,
                    pattern_folder_name=test_item.pattern_folder_name,
                    pattern_file_path=test_item.pattern_file_path,
                    test_py_path=test_item.test_py_path,
                    test_py_path_template=test_item.test_py_path_template,
                    test_folder_path_template=test_item.test_folder_path_template,
                    pattern_folder_path_depot=test_item.pattern_folder_path_depot,
                    pattern_file_path_depot=test_item.pattern_file_path_depot,
                    is_key_pattern=test_item.is_key_pattern,
                )
                test_items_list.append(test_item_d)
            except AttributeError as e:
                # Ignore items where attr is not set:
                log.error("This test item has no attribute %s", e)
        return test_items_list

    def patterns_tests_latest_digest(self, query_args):
        """
        Select summary information about test stats grouped by ADDM

        :param query_args:
        :return:
        """
        # patterns_tests_latest_digest = ['table', 'branch', 'patterns_tests_latest_digest', 'addm_name']
        """ Query for composing short pattern digest and count overall fails. """
        # Args:
        branch    = query_args.get('branch', '')
        addm_name = query_args.get('addm_name', '')

        fail_k = query_args.get('fail_only', '')
        skip_k = query_args.get('skip_only', '')
        err_k = query_args.get('error_only', '')
        pass_k = query_args.get('pass_only', '')
        un_pass_k = query_args.get('not_pass_only', '')
        by_user = query_args.get('by_user', '')

        date_start = query_args.get('date_start', False)
        date_end = query_args.get('date_end', False)
        date_k = ''

        fail_r = r'^(FAIL|fail|unexpected|failure)'
        not_pass_r = r'^(FAIL|fail|unexpected|failure|ERROR)'

        if branch:
            branch = "\nAND {lt}.tkn_branch = '{branch}' ".format(lt=self.last_tests_tb, branch=branch)

        if addm_name:
            addm_name = "\nAND {lt}.addm_name = '{addm}' ".format(lt=self.last_tests_tb, addm=addm_name)

        if fail_k:
            fail_k = "\nAND {lt}.tst_status REGEXP '{fail_r}'".format(
                lt=self.last_tests_tb, fail_r=fail_r)

        if skip_k:
            skip_k = "\nAND {lt}.tst_status REGEXP '(skipped|expected)'".format(
                lt=self.last_tests_tb)

        if err_k:
            err_k = "\nAND {lt}.tst_status = 'ERROR'".format(
                lt=self.last_tests_tb)

        if un_pass_k:
            un_pass_k = "\nAND {lt}.tst_status REGEXP '{not_pass_r}'".format(
                lt=self.last_tests_tb, not_pass_r=not_pass_r)

        if pass_k:
            pass_k = "\nAND {lt}.tst_status = 'ok' AND NOT {lt}.tst_status REGEXP '{fail_r}'".format(
                lt=self.last_tests_tb, fail_r=fail_r)

        if by_user:
            # TODO: Change to octo_test_cases
            by_user = "\nAND {pt}.change_user = '{by_user}'".format(pt=self.tku_patterns_table, by_user=by_user)

        if date_start and date_end:
            date_k = "\nAND {lt}.test_date BETWEEN '{start}' AND '{end}'".format(
                lt=self.last_tests_tb, start=date_start, end=date_end)

        # noinspection SyntaxError,PyUnusedLocal,ExpressionExpected
        raw_query_1 = '''
        SELECT {lt}.id,
               {lt}.pattern_library,
               {lt}.pattern_folder_name,
               {lt}.test_py_path,
               {lt}.tst_status,
               {lt}.time_spent_test,
               {lt}.test_date_time,
               {lt}.addm_name,
               {lt}.addm_v_int,
               {pt}.id,
               {pt}.pattern_folder_change,
               {pt}.pattern_folder_mod_time,
               {pt}.change_desc,
               {pt}.change_user,
               {pt}.change_review,
               {pt}.change_ticket,
               {pt}.pattern_folder_path_depot,
               {pt}.pattern_folder_change,
               {pt}.is_key_pattern,
        COUNT({pt}.pattern_file_path) AS patterns_count,
        COUNT(DISTINCT {lt}.tst_name, {lt}.tst_class) AS test_items_prepared,
          ROUND(SUM( {lt}.tst_status REGEXP '{fail_r}')  / COUNT(DISTINCT {pt}.pattern_file_path),0) AS fails,
          ROUND(SUM( {lt}.tst_status REGEXP 'ERROR') / COUNT(DISTINCT {pt}.pattern_file_path),0) AS error,
          ROUND(SUM( {lt}.tst_status REGEXP 'ok')    / COUNT(DISTINCT {pt}.pattern_file_path),0) AS passed,
          ROUND(SUM( {lt}.tst_status REGEXP '(skipped|expected)')/COUNT(DISTINCT {pt}.pattern_file_path),0) AS skipped,
          ROUND((SUM({lt}.tst_status REGEXP 'ok')/COUNT(DISTINCT {pt}.pattern_file_path) / COUNT( DISTINCT {lt}.tst_name, {lt}.tst_class) * 100),2) AS passed_percent
        FROM {db}.{lt}, {db}.{pt}
        WHERE {lt}.test_py_path = {pt}.test_py_path
        AND {lt}.tkn_branch = '{branch}'
        AND {lt}.addm_name = '{addm}' 
          {fail_k} {skip_k} {pass_k} {un_pass_k} {err_k} {date_q}
        GROUP BY {lt}.test_py_path,{lt}.addm_name
                '''

        # noinspection SyntaxError
        raw_query_dev = '''
        SELECT 
          {lt}.id,
          {lt}.pattern_library,
          {lt}.pattern_folder_name,
          {lt}.time_spent_test,
          {lt}.test_date_time,
          {lt}.addm_name,
          {lt}.addm_v_int,
          {pt}.pattern_folder_change,
          {pt}.change_user,
          {pt}.change_review,
          {pt}.change_ticket,
          {pt}.pattern_folder_change,
        COUNT({pt}.pattern_file_path) AS patterns_count,
        COUNT(DISTINCT {lt}.tst_name, {lt}.tst_class) AS test_items_prepared,
          ROUND(SUM( {lt}.tst_status REGEXP '{fail_r}')  / COUNT(DISTINCT {pt}.pattern_file_path),0) 
            AS fails,
          ROUND(SUM( {lt}.tst_status REGEXP 'ERROR') / COUNT(DISTINCT {pt}.pattern_file_path),0) 
            AS error,
          ROUND(SUM( {lt}.tst_status REGEXP 'ok')    / COUNT(DISTINCT {pt}.pattern_file_path),0) 
            AS passed,
          ROUND(SUM( {lt}.tst_status REGEXP '(skipped|expected)')/COUNT(DISTINCT {pt}.pattern_file_path),0) 
            AS skipped,
          ROUND((SUM({lt}.tst_status REGEXP 'ok') / COUNT(DISTINCT {pt}.pattern_file_path) / COUNT( DISTINCT {lt}.tst_name, {lt}.tst_class) * 100),2) 
            AS passed_percent
        FROM {db}.{lt}, {db}.{pt}
        WHERE {lt}.test_py_path = {pt}.test_py_path
        {branch}
        {addm} 
        {fail_k} {skip_k} {pass_k} {un_pass_k} {err_k} {date_q} {by_user}
        GROUP BY {lt}.test_py_path,{lt}.addm_name
                '''

        # Compose query:
        query = raw_query_dev.format(
            db=self.database,
            lt=self.last_tests_tb,
            pt=self.tku_patterns_table,
            branch=branch,
            addm=addm_name,
            fail_r=fail_r,
            fail_k=fail_k,
            skip_k=skip_k,
            pass_k=pass_k,
            un_pass_k=un_pass_k,
            by_user=by_user,
            err_k=err_k,
            date_q=date_k)

        addm_sorted_tests = TestLast.objects.raw(query)
        # log.debug("<=TABLE OPER=> DjangoModelRaw() "
        #           "query_args: %s"
        #           "addm_sorted_tests.query: \n%s", query_args, addm_sorted_tests.query)
        return addm_sorted_tests

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

    def sel_history_by_latest(self, query_args):
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
                   WHERE {tb}.test_py_path = '{test_py_path}'
                   AND {tb}.test_date_time BETWEEN '{date_from}' AND '{tomorrow}'
                   AND {tb}.addm_name = 'double_decker'
                   GROUP BY day({tb}.test_date_time);
                   """.format(db=self.database,
                              tb=self.history_tests_tb,
                              test_py_path=query_args['test_py_path'],
                              date_from=date_from.strftime('%Y-%m-%d'),
                              tomorrow=tomorrow.strftime('%Y-%m-%d'))
        # log.debug("Using query: \n%s", query)

        history_recs = TestHistory.objects.raw(query)

        return history_recs

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

    def select_history_test_last(self, query_args):
        from django.utils import timezone
        now = datetime.datetime.now(tz=timezone.utc)
        yesterday = now + datetime.timedelta(days=1)

        log.debug("Selecting between: %s %s", yesterday, now)
        query = """SELECT {tb}.id,
                          {tb}.time_spent_test,
                          {tb}.test_py_path,
                          {tb}.test_date_time
                   FROM {db}.{tb}
                   WHERE {tb}.test_py_path = '{test_py_path}'
                   AND {tb}.test_date_time BETWEEN '{date_from}' AND '{date_to}'
                   GROUP BY day({tb}.test_date_time), {tb}.test_py_path
                   ORDER BY {tb}.test_py_path
                   ;
                   """.format(db=self.database,
                              tb=self.history_tests_tb,
                              test_py_path=query_args['test_py_path'],
                              date_from=yesterday.strftime('%Y-%m-%d'),
                              date_to=now.strftime('%Y-%m-%d'))
        # log.debug("Using query: \n%s", query)

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

    @staticmethod
    def latest_tests_minmax_date(branch):
        """
        Select latest test min and max dates

        :return:
        """
        minmax_test_date = TestLast.objects.filter(
            tkn_branch__exact=branch).aggregate(Max('test_date_time'), Min('test_date_time'))

        return dict(min_test_date = minmax_test_date.get('test_date_time__min', "N/A"),
                    max_test_date = minmax_test_date.get('test_date_time__max', "N/A"),
                    )

    def select_all_patterns(self, query_args):
        """
        Select only patterns in time window.
        Usual options:
            - from last GA date till today.
            - from sept 25th till today
        SHIP
            - only from 2017-10-12 because branch was shipped at 2017-10-11
            https://jira/browse/DRDC1-11450

        :param query_args:
        :return:
        """
        latest_date = self.release_db_date()['today']

        date_start = "2017-09-25"
        if query_args.get('release', False):
            if query_args['branch'] == "tkn_ship":
                date_start = "2017-10-12"
            else:
                date_start = self.release_db_date()['start_date']

        if not query_args.get('pattern_library', False):
            pattern_library = '.'
        else:
            pattern_library = query_args.get('pattern_library', False)

        # Later ordered by date of last change?
        patterns_sorted = TestCases.objects.filter(
            test_type__exact='tku_patterns'
        )
        if query_args.get('release', False):
            release_patters = patterns_sorted.filter(tkn_branch__exact=query_args['branch'],
                                                     change_time__range=(date_start, latest_date),
                                                     pattern_library__iregex=pattern_library,
                                                     )
            all_patterns = release_patters

        elif query_args.get('everything', False):
            all_patterns = patterns_sorted.filter(tkn_branch__exact=query_args['branch'])

        else:
            all_patterns = patterns_sorted.filter(tkn_branch__exact=query_args['branch'],
                                                  pattern_library__iregex=pattern_library)

        # log.debug("<=TABLE OPER=> select_all_patterns() "
        #           "query_args: %s"
        #           "all_patterns.query: \n%s", query_args, all_patterns.query)

        return all_patterns, date_start, latest_date

    @staticmethod
    def select_tku_test_patterns(**kwargs):
        """
        Select patterns with test.py and group by it's path.
        :param kwargs:
        :return:
        """

        branch = kwargs.get('branch', False)
        pattern_library = kwargs.get('pattern_library', False)
        select_release = kwargs.get('select_release', False)

        date_from = kwargs.get('date_from')
        date_to = kwargs.get('date_to')

        # Ignore dates, choose release only:
        if select_release:
            date_from = PatternsDjangoTableOper.release_db_date()['start_date']
            date_to = PatternsDjangoTableOper.release_db_date()['today']
            log.debug("Selecting for release window: %s - %s", date_from, date_to)
        # Now use dates passed:
        else:
            if not date_from:
                date_from = '1970-01-01'
            else:
                date_from.strftime('%Y-%m-%d')

            if not date_to:
                date_to = PatternsDjangoTableOper.release_db_date()['today']
            else:
                date_to.strftime('%Y-%m-%d')

            log.debug("Selecting for custom window: %s - %s", date_from, date_to)

        all_patterns = TestCases.objects.filter(test_type__exact='tku_patterns')
        # all_patterns = TkuPatterns.objects.values().annotate(dcount=Count('test_py_path'))
        log.debug("All patterns with test.py len: %s", all_patterns.count())

        if branch:
            all_patterns = all_patterns.filter(tkn_branch__exact=branch)
            log.debug("Filtering from all by branch: %s len: %s", branch, all_patterns.count())

        if pattern_library:
            all_patterns = all_patterns.filter(pattern_library__exact=pattern_library)
            log.debug("Filtering from all by pattern_library: %s len: %s", pattern_library, all_patterns.count())

        if select_release:
            all_patterns = all_patterns.filter(change_time__range=[date_from, date_to])
            log.debug("Filtering from all by select_release: %s len: %s", select_release, all_patterns.count())

        return date_from, date_to, all_patterns

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

    @staticmethod
    def sel_test_key(exclude=None, branch=None):
        """
        Only select key patterns
        :return:
        """
        log.debug("<=Django Model key_select=> Selecting key patterns only. Branch: %s", branch)
        if branch:
            key_patterns = TkuPatterns.objects.filter(test_py_path__iendswith='test.py',
                                                      tkn_branch__exact=branch,
                                                      is_key_pattern__exact=True)
        else:
            key_patterns = TkuPatterns.objects.filter(test_py_path__iendswith='test.py',
                                                      is_key_pattern__exact=True)
        if exclude:
            key_patterns.exclude(pattern_folder_name__in=exclude)

        log.debug("<=Django Model key_select=> Selected key patterns len %s", key_patterns.count())
        return key_patterns

    @staticmethod
    def select_latest_records(query_args, regex_q):
        """
        Select all history rec for selected table (or addm)
        :return:
        """

        pattern_library  = query_args.get('pattern_library', False)
        pattern_folder   = query_args.get('pattern_folder', False)

        addm_name        = query_args.get('addm_name', False)
        fail_only        = query_args.get('fail_only', '')
        skip_only        = query_args.get('skip_only', '')
        error_only       = query_args.get('error_only', '')
        pass_only        = query_args.get('pass_only', '')
        not_pass_only    = query_args.get('not_pass_only', '')

        # Assign tst statuses:
        if fail_only:
            tst_status = 'FAIL'
        elif skip_only:
            tst_status = '(skipped|expected)'
        elif error_only:
            tst_status = 'ERROR'
        elif pass_only:
            tst_status = 'ok'
        elif not_pass_only:
            tst_status = '(ERROR|FAIL)'
        else:
            tst_status = '.'

        if not pattern_library:
            pattern_library         = '.'
        if not pattern_folder:
            pattern_folder          = '.'
        if not addm_name:
            addm_name               = '.'

        # Sort out by BETWEEN DATES, sort out by ADDM codename:
        if regex_q:
            latest_records = TestLast.objects.filter(
                # test_date_time__range=(start_date, end_date),
                tkn_branch__exact           = query_args['branch'],
                pattern_library__iregex     = str(pattern_library),
                pattern_folder_name__iregex = str(pattern_folder),
                tst_status__iregex          = str(tst_status),
                addm_name__exact            = addm_name
            )
        else:
            latest_records = TestLast.objects.filter(
                # test_date_time__range=(start_date, end_date),
                tkn_branch__exact          = query_args['branch'],
                pattern_library__exact     = pattern_library,
                pattern_folder_name__exact = pattern_folder,
                tst_status__exact          = tst_status,
                addm_name__exact           = addm_name
            )
        # log.debug("<=TABLE OPER=> select_history_records() "
        #           "query_args: %s"
        #           "latest_records.query: \n%s", query_args, latest_records.query)
        return latest_records

    @staticmethod
    def select_latest_records_by_pattern(query_args):
        """
        Select all latest rec for selected table (or addm) or pattern details
        :return:
        """
        # start_date       = query_args['start_date']
        # end_date         = query_args['end_date']
        fail_only        = query_args.get('fail_only', '')
        skip_only        = query_args.get('skip_only', '')
        error_only       = query_args.get('error_only', '')
        pass_only        = query_args.get('pass_only', '')
        not_pass_only    = query_args.get('not_pass_only', '')

        # Assign tst statuses:
        regex_q = False
        if fail_only:
            tst_status = 'FAIL'
        elif skip_only:
            tst_status = '(skipped|expected)'
            regex_q    = True
        elif error_only:
            tst_status = 'ERROR'
        elif pass_only:
            tst_status = 'ok'
        elif not_pass_only:
            tst_status = '(ERROR|FAIL)'
            regex_q    = True
        else:
            tst_status = '.'
            regex_q    = True

        # Sort out by by ADDM codename, by pattern folder name:
        if regex_q:
            latest_results = TestLast.objects.filter(
                tkn_branch__exact          = query_args['branch'],
                tst_status__iregex         = str(tst_status),
                addm_name__exact           = query_args.get('addm_name', 'custard_cream'),
                pattern_library__exact     = query_args.get('pattern_library', 'CORE'),
                pattern_folder_name__exact = query_args.get('pattern_folder', ''),
                )
        else:
            latest_results = TestLast.objects.filter(
                tkn_branch__exact          = query_args['branch'],
                tst_status__exact          = tst_status,
                addm_name__exact           = query_args.get('addm_name', 'custard_cream'),
                pattern_library__exact     = query_args.get('pattern_library', 'CORE'),
                pattern_folder_name__exact = query_args.get('pattern_folder', ''),
                )
        # log.debug("<=TABLE OPER=> select_latest_records_by_pattern() "
        #           "query_args: %s"
        #           "latest_results.query: \n%s", query_args, latest_results.query)
        return latest_results

    @staticmethod
    def select_history_records(query_args):
        """
        Select all history rec for selected table (or addm)
        :return:
        """

        start_date    = query_args['start_date']
        end_date      = query_args['end_date']
        fail_only     = query_args.get('fail_only', '')
        skip_only     = query_args.get('skip_only', '')
        error_only    = query_args.get('error_only', '')
        pass_only     = query_args.get('pass_only', '')
        not_pass_only = query_args.get('not_pass_only', '')

        # Assign tst statuses:
        regex_q = False
        if fail_only:
            tst_status = 'FAIL'
        elif skip_only:
            tst_status = '(skipped|expected)'
            regex_q    = True
        elif error_only:
            tst_status = 'ERROR'
        elif pass_only:
            tst_status = 'ok'
        elif not_pass_only:
            tst_status = '(ERROR|FAIL)'
            regex_q    = True
        else:
            tst_status = '.'
            regex_q    = True

        if regex_q:
            history_recs = TestHistory.objects.filter(
                tkn_branch__exact=query_args['branch'],
                test_date_time__range=(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')),
                tst_status__iregex=str(tst_status),
                addm_name__exact=query_args.get('addm_name', 'custard_cream'))
        else:
            history_recs = TestHistory.objects.filter(
                tkn_branch__exact=query_args['branch'],
                test_date_time__range=(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')),
                tst_status__iregex=tst_status,
                addm_name__exact=query_args.get('addm_name', 'custard_cream'))

        return history_recs

    @staticmethod
    def select_history_records_by_pattern(query_args):
        """
        Select all history rec for selected table (or addm)
        :return:
        """

        start_date = query_args['start_date']
        end_date = query_args['end_date']
        addm_name = query_args.get('addm_name', 'custard_cream')
        fail_only = query_args.get('fail_only', '')
        skip_only = query_args.get('skip_only', '')
        error_only = query_args.get('error_only', '')
        pass_only = query_args.get('pass_only', '')
        not_pass_only = query_args.get('not_pass_only', '')

        pattern_folder = query_args.get('pattern_folder', '')

        # Assign tst statuses:
        if fail_only:
            tst_status = 'FAIL'
        elif skip_only:
            tst_status = '(skipped|expected)'
        elif error_only:
            tst_status = 'ERROR'
        elif pass_only:
            tst_status = 'ok'
        elif not_pass_only:
            tst_status = '(ERROR|FAIL)'
        else:
            tst_status = '.'

        # Sort out by BETWEEN DATES, sort out by ADDM codename, by pattern folder name:
        # Date should be year month day - without hours - to show all items between dates.
        if pattern_folder == ".":
            history_recs = TestHistory.objects.filter(
                tkn_branch__exact           = query_args['branch'],
                test_date_time__range            = (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')),
                tst_status__iregex          = tst_status,
                addm_name__exact            = addm_name,
                pattern_library__exact      = query_args.get('pattern_library', ''),
                pattern_folder_name__iregex = pattern_folder,
            )
        else:
            history_recs = TestHistory.objects.filter(
                tkn_branch__exact          = query_args['branch'],
                test_date_time__range           = (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')),
                tst_status__iregex         = tst_status,
                addm_name__exact           = addm_name,
                pattern_library__exact     = query_args.get('pattern_library', ''),
                pattern_folder_name__exact = pattern_folder,
            )
        # log.debug("<=TABLE OPER=> select_history_records_by_pattern() "
        #           "query_args: %s"
        #           "history_recs.query: \n%s", query_args, history_recs.query)
        return history_recs

    @staticmethod
    def select_history_test_last_success(query_args):
        """

        :param query_args:
        :return:
        """
        branch = query_args.get('branch', '')
        pattern_library = query_args.get('pattern_library', '')
        pattern_folder = query_args.get('pattern_folder', '')
        test_function = query_args.get('test_function', '')
        addm_name = query_args.get('addm_name', '')

        test_function = test_function.split(" ")
        latest_results = TestHistory.objects.filter(
            tkn_branch__exact = branch,
            pattern_library__exact=pattern_library,
            pattern_folder_name__exact=pattern_folder,
            addm_name__exact=addm_name,
            tst_class__exact=test_function[0],
            tst_name__exact=test_function[1],
        ).order_by('-test_date_time')
        # log.debug("<=TABLE OPER=> select_history_test_last_success() "
        #           "query_args: %s"
        #           "latest_results.query: \n%s", query_args, latest_results.query)
        return latest_results

    @staticmethod
    def select_global_by_pattern(search_sting):
        tku_patterns = TkuPatterns.objects.filter(
            Q(pattern_folder_name__exact=search_sting)
            | Q(pattern_folder_name__contains=search_sting)
            | Q(pattern_folder_name__iregex=search_sting)
        ).values()
        test_last = TestLast.objects.filter(
            Q(pattern_folder_name__exact=search_sting)
            | Q(pattern_folder_name__contains=search_sting)
            | Q(pattern_folder_name__iregex=search_sting)
        ).values()
        test_history = TestHistory.objects.filter(
            Q(pattern_folder_name__exact=search_sting)
            | Q(pattern_folder_name__contains=search_sting)
        ).order_by('-id').values()
        return tku_patterns, test_last, test_history

    @staticmethod
    def select_solo_test_item(query_args):
        test_item = TkuPatterns.objects.filter(
                tkn_branch__exact          = query_args['branch'],
                pattern_library__exact     = query_args['pattern_library'],
                pattern_folder_name__exact = query_args['pattern_folder'],
        )
        return test_item


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
