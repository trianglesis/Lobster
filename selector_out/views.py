"""
Input requests - output pages with some results.

"""

import datetime

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
from django.template import loader

from octo_adm.user_operations import UserCheck
from octo_tku_patterns.table_oper import PatternsDjangoTableOper
from selector_out.forms import GlobalSearch

# Python logger
import logging

log = logging.getLogger("octo.octologger")


class Searches:
    """
    Different search options.
    """

    # Custom search:
    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def search_history(request):
        """
        Request form for history search.
        If filled incorrectly - return just empty itself.

        TODO: Should add ALL_ADDMS option to show logs for each addm.

        """
        from selector_out.forms import DevTestRequest
        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=VIEW SELECTOR=> search_history(): %s", user_str)

        request_form = loader.get_template('OLD/search_history.html')
        tests_summary = loader.get_template('OLD/pattern_logs.html')
        fail_only = False
        skip_only = False
        error_only = False
        pass_only = False
        not_pass_only = False

        if request.method == 'POST':
            test_select = DevTestRequest(request.POST)
            if test_select.is_valid():
                tkn_branch_select = test_select.cleaned_data['tkn_branch_select']
                addm_name_select = test_select.cleaned_data['addm_name_select']

                pattern_library = test_select.cleaned_data['pattern_library_drop']
                pattern_folder = test_select.cleaned_data['pattern_folder']
                log_status = test_select.cleaned_data['log_status']

                if log_status == "fail":
                    fail_only = True
                elif log_status == "skipped":
                    skip_only = True
                elif log_status == "error":
                    error_only = True
                elif log_status == "passed":
                    pass_only = True
                elif log_status == "not_pass_only":
                    not_pass_only = True
                else:
                    pass

                # Oct. 3, 2017 - right format in code.
                date_from_web = test_select.cleaned_data['date_from']
                end_date_web = test_select.cleaned_data['date_to']
                start_date = date_from_web
                end_date = end_date_web

                if (pattern_library or pattern_folder or date_from_web) == "None":
                    # TODO: Draw here an warning popup.
                    log.info("There are some args absent.")
                    log.debug("Args used: "
                              "pattern_library_drop '%s', "
                              "pattern_folder '%s', "
                              "log_status '%s' "
                              "tkn_branch_select '%s' "
                              "addm_name_select '%s' "
                              "date_from_web '%s' "
                              "end_date_web '%s'",
                              pattern_library,
                              pattern_folder,
                              log_status,
                              tkn_branch_select,
                              addm_name_select,
                              date_from_web,
                              end_date_web)
                    test_select = DevTestRequest()
                else:
                    query_args = dict(branch=tkn_branch_select,
                                      start_date=start_date,
                                      end_date=end_date,
                                      addm_name=addm_name_select,
                                      pattern_library=pattern_library,
                                      pattern_folder=pattern_folder,
                                      fail_only=fail_only,
                                      skip_only=skip_only,
                                      error_only=error_only,
                                      pass_only=pass_only,
                                      not_pass_only=not_pass_only)

                    # log.debug("<=DEV FORM=> search_history form args %s", query_args)

                    # SELECT by django - with selected attrs:
                    log.debug("<=VIEW SELECTOR=> search_history() query_args; %s", query_args)
                    history_records = PatternsDjangoTableOper().select_history_records_by_pattern(query_args=query_args)

                    # compose_args = dict(latest_records = history_records,
                    #     branch         = tkn_branch_select,
                    #     user_name      = user_name,
                    #     date_time_now  = '',
                    #     addm_name      = addm_name_select,
                    #     detailed_log   = False,
                    #     sort_date_exec = '',
                    # )
                    # tst_patt_contxt  = self.select_helper.patterns_detailed_log_draw(compose_args)
                    # tst_patt_contxt = self.select_helper.patterns_detailed_log_draw(history_records, False)

                    subject = 'Search in history - {}/{}'.format(start_date, end_date)
                    tests_pattern_context = dict(
                        LATEST_TESTS=history_records,
                        DATE_FROM=start_date,
                        DATE_LAST=end_date,
                        START_DATE=start_date,
                        END_DATE=end_date,
                        BRANCH=tkn_branch_select,
                        TABLE="History",
                        ADDM_GENERAL_LINK="#",
                        ADDM_NAME_LINK="#",
                        FAIL_ONLY=fail_only,
                        SKIP_ONLY=skip_only,
                        ERROR_ONLY=error_only,
                        PASS_ONLY=pass_only,
                        NOT_PASS_ONLY=not_pass_only,
                        PATTERN_LIBRARY=pattern_library,
                        PATTERN_FOLDER=pattern_folder if not pattern_folder == '.' else False,
                        ADDM_NAME=addm_name_select,
                        NAV_HEAD_DRAW=True,
                        TABS_DRAW=True,
                        ADDM_NAVS_LINK="#",
                        DEBUG_DATA=False,
                        HAV_PLACE=subject)
                    return HttpResponse(tests_summary.render(tests_pattern_context, request))
        else:
            test_select = DevTestRequest()
        return HttpResponse(request_form.render(dict(search_history_form=test_select), request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def history_select(request):
        """
        Select all records from tests history table.
        choose branch as arg.
        choose addm as arg?
        Format as usual patterns report.
        Make links to test report?

        :param request:
        :return:
        """
        user_name, user_str = UserCheck().user_string_f(request)
        log.debug("<=VIEW SELECTOR=> history_select(): %s", user_str)

        history_rec_t = loader.get_template('OLD/pattern_logs.html')
        date_today = datetime.datetime.now()

        # Query and request:
        branch = request.GET.get('branch', 'tkn_main')
        addm_name = request.GET.get('addm_name', 'double_decker')

        fail_only = request.GET.get('fail_only', '')
        skip_only = request.GET.get('skip_only', '')
        error_only = request.GET.get('error_only', '')
        pass_only = request.GET.get('pass_only', '')
        not_pass_only = request.GET.get('not_pass_only', '')

        pattern_library = request.GET.get('pattern_library', '')
        pattern_folder = request.GET.get('pattern_folder', '.')

        go_back = request.GET.get('go_back', False)
        go_ahead = request.GET.get('go_ahead', False)
        web_start_date = request.GET.get('start_date', False)
        web_end_date = request.GET.get('end_date', False)

        debug_flag = request.GET.get('debug_flag', '')

        if not web_start_date or not web_end_date:
            # Choose default yesterday and today:
            start_date = date_today - datetime.timedelta(days=1)
            end_date = start_date + datetime.timedelta(days=1)
        else:
            # Convert date from args to python time
            start_date = datetime.datetime.strptime(web_start_date, '%Y-%m-%d')
            end_date = datetime.datetime.strptime(web_end_date, '%Y-%m-%d')

        # Date from which start to:
        if go_back:
            start_date = start_date - datetime.timedelta(days=1)
            end_date = end_date - datetime.timedelta(days=1)
            log.debug("<=GO DAY=> go_back = %s | start_date - %s end_date %s",
                      go_back, start_date, end_date)
        elif go_ahead:
            start_date = start_date + datetime.timedelta(days=1)
            end_date = end_date + datetime.timedelta(days=1)
            log.debug("<=GO DAY=> go_ahead = %s | start_date - %s end_date %s",
                      go_ahead, start_date, end_date)
        else:
            log.debug("<=GO DAY=> go_back, go_ahead = <empty> | start_date - %s end_date %s",
                      go_back, go_ahead, start_date, end_date)

        # log.debug("<=VIEW SELECTOR=> history_select(): "
        #           "go_back %s, go_ahead %s, start_date %s, end_date %s, web_start_date %s, web_end_date %s",
        #           go_back, go_ahead, start_date, end_date, web_start_date, web_end_date)

        subject = 'History {}/{}'.format(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        query_args = dict(branch=branch,
                          start_date=start_date,
                          end_date=end_date,
                          addm_name=addm_name,
                          pattern_library=pattern_library,
                          pattern_folder=pattern_folder,
                          fail_only=fail_only,
                          skip_only=skip_only,
                          error_only=error_only,
                          pass_only=pass_only,
                          not_pass_only=not_pass_only)

        if pattern_folder and pattern_library:
            history_tests = PatternsDjangoTableOper().select_history_records_by_pattern(query_args=query_args)
        else:
            history_tests = PatternsDjangoTableOper().select_history_records(query_args=query_args)

        # compose_args = dict(
        #     latest_records = history_tests,
        #     branch         = branch,
        #     user_name      = user_name,
        #     date_time_now  = '',
        #     addm_name      = addm_name,
        #     detailed_log   = False,
        #     sort_date_exec = '',
        # )
        # history_tests_contxt  = self.select_helper.__patterns_detailed_log_draw(compose_args)

        contxt = dict(
            LATEST_TESTS=history_tests,
            DATE_FROM=start_date,
            DATE_LAST=end_date,
            HAV_PLACE=subject,
            BRANCH=branch,
            START_DATE=start_date,
            END_DATE=end_date,
            ADDM_NAME=addm_name,
            ADDM_NAVS_LINK="pattern_logs",
            PATTERN_LIBRARY=pattern_library,
            PATTERN_FOLDER=pattern_folder if not pattern_folder == '.' else False,
            FAIL_ONLY=fail_only,
            SKIP_ONLY=skip_only,
            ERROR_ONLY=error_only,
            PASS_ONLY=pass_only,
            NOT_PASS_ONLY=not_pass_only,
            DEBUG_DATA=debug_flag,
            NAV_HEAD_DRAW=True,
            TABS_DRAW=True,
        )
        return HttpResponse(history_rec_t.render(contxt, request))

    # Custom search:
    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def global_search(request):
        """
        Search by pattern folder name or pattern name.
        Group results and show only on separate page for each.
        :param request:
        :return:
        """
        global_search = loader.get_template('global_search_main.html')
        # search_sting = request.GET.get('search_sting', None)

        user_name, user_string = UserCheck().user_string_f(request)

        search_results_d = dict(
            search_sting='',
            tku_patterns='',
            test_last='',
            test_history='',
        )
        page_context = dict(
            search_form=GlobalSearch(),
            search_results_d=search_results_d,
            SUBJECT='',
            USER_NAME=user_name
        )
        if request.method == 'POST':
            search_form = GlobalSearch(request.POST)
            if search_form.is_valid():
                search_sting = search_form.cleaned_data['search_string']
                subject = "Search everything by: {}".format(search_sting)

                tku_patterns, test_last, test_history = PatternsDjangoTableOper().select_global_by_pattern(search_sting)
                search_results_d.update(tku_patterns=tku_patterns)

                search_results_d.update(test_last=test_last[:500])
                search_results_d.update(test_history=test_history[:200])
                page_context.update(SEARCH_STING=search_sting)
                page_context.update(SUBJECT=subject)
                return HttpResponse(global_search.render(page_context, request))

        return HttpResponse(global_search.render(page_context, request))

    @staticmethod
    @login_required(login_url='/unauthorized_banner/')
    def full_history(request):
        """
        Search by pattern folder name or pattern name.
        Group results and show only on separate page for each.
        :param request:
        :return:
        """
        global_search = loader.get_template('global_search_full_history.html')
        search_sting = request.GET.get('search_sting', None)
        page = request.GET.get('page', 1)

        user_name, user_string = UserCheck().user_string_f(request)

        page_context = dict(search_form=GlobalSearch(),
                            test_history='',
                            SUBJECT='',
                            USER_NAME=user_name)
        # Retugn empty page:
        if not search_sting:
            page_context.update(SUBJECT="Search string is not set")
            return HttpResponse(global_search.render(page_context, request))

        _, _, test_history = PatternsDjangoTableOper().select_global_by_pattern(search_sting)
        page_context.update(SUBJECT="Showing full history for search: {}".format(search_sting))

        # Paginator:
        test_history_p = Paginator(test_history, 200)
        # test_history = test_history_p.get_page(page)

        try:
            test_history = test_history_p.page(page)
        except PageNotAnInteger:
            test_history = test_history_p.page(1)
        except EmptyPage:
            test_history = test_history_p.page(test_history_p.num_pages)

        page_context.update(test_history=test_history)
        page_context.update(SEARCH_STING=search_sting)

        return HttpResponse(global_search.render(page_context, request))
