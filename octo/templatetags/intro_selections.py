"""
Template tags intra-template selections and small queries
"""
import os
import logging
from operator import itemgetter
from django.contrib.auth.models import User
from django.template import loader
from django import template
from django.db.models import Max

from octo_tku_patterns.models import TestCases

from octo_tku_upload.table_oper import UploadTKUTableOper
from octo_tku_patterns.table_oper import PatternsDjangoTableOper, PatternsDjangoModelRaw

from octo.helpers.tasks_oper import TasksOperations
from selector_out.forms import GlobalSearch

register = template.Library()
log = logging.getLogger("octo.octologger")


@register.simple_tag()
def patterns_top_small(branch):
    """
    Get the list of TOP long running tests and show first 6 items in small table on main page
    Each branch in it's block.
    This will render table as HTML item which built in place where TAG was called.

    :param branch:
    :return:
    """
    top_long_t = loader.get_template(
        'small_blocks/intro_selections/small_long_tests_table.html')
    top_long = PatternsDjangoModelRaw().select_latest_long_tests(branch)[:6]

    if top_long:
        user_patterns_summary_t = top_long_t.render(dict(TEST_TOP=top_long))
        return user_patterns_summary_t
    else:
        return ''


@register.simple_tag()
def get_minmax_test_date():
    dates = dict()
    branches = ["tkn_ship", "tkn_main"]
    for branch in branches:
        minmax_test_date = PatternsDjangoTableOper().latest_tests_minmax_date(branch)
        test_date = minmax_test_date.get('min_test_date', None)
        if test_date:
            last_dates = {branch: test_date}
        else:
            last_dates = {branch: '1976-01-01 00:00:00'}
        dates.update(last_dates)
    return dates


@register.simple_tag()
def get_max_changes_tku_patterns():
    max_branches = dict()
    branches = ["tkn_ship", "tkn_main"]
    for branch in branches:
        all_patterns, date_start, latest_date = PatternsDjangoTableOper().select_all_patterns(query_args=dict(branch=branch, everything=True))
        max_branches.update({branch: dict(
            change=all_patterns.aggregate(Max('change'))['change__max'],
            date=all_patterns.aggregate(Max('change_time'))['change_time__max'])})
    return max_branches


@register.simple_tag
def worker_queues_short():

    workers_t = loader.get_template('main/workers_queue.html')
    workers_list = TasksOperations().workers_list[:]
    # noinspection PyBroadException
    # if os.name == "nt":
    #     return ''
    try:
        inspected = TasksOperations().check_active_reserved_short(workers_list=workers_list)
        workers_short_stat = workers_t.render(dict(WORKERS=inspected))
        return workers_short_stat
    # Update exception based on Null workers
    except Exception:
        return ''


@register.simple_tag
def cron_tasks_short_new():
    # from octo.models import DjangoCeleryBeatPeriodictask
    from django_celery_beat.models import PeriodicTask
    cron_t = loader.get_template('main/cron_table_new.html')
    periodic_tasks = PeriodicTask.objects.filter(enabled__exact=1)

    cron_short = cron_t.render(dict(periodic_tasks=periodic_tasks))
    return cron_short

# noinspection PyBroadException
@register.simple_tag
def cron_table():
    try:
        t_active, t_reserved = TasksOperations().get_workers_summary()

        inspected = []
        for t_active_k, t_active_v in t_active.items():
            reserved_d = t_reserved.get(t_active_k)
            parsed = dict(
                WORKER_NAME=t_active_k,
                WORKER_ACTIVE_LEN=len(t_active_v),
                WORKER_RESERVED_LEN=len(reserved_d))
            inspected.append(parsed)

        inspected_sort = sorted(inspected, key = itemgetter('WORKER_NAME'), reverse = False)
        return inspected_sort
    # Update exception based on Null workers
    except Exception:
        return []


@register.simple_tag()
def global_search_form():
    return GlobalSearch()


@register.simple_tag(takes_context=True)
def dynamical_selector_compose(context, exclude_key=None, update_context=False):
    """
    Works with TestCasesListView: allows make a url query string and exclude duplicates.
    Implemented best on '/octo_tku_patterns/test_cases/'
    :param context:
    :param exclude_key:
    :param update_context:
    :return:
    """
    selector = context.get('selector')
    # log.debug("<=dynamical_selector_compose=> selector: %s", selector)
    # log.debug("<=dynamical_selector_compose=> exclude_key: %s", exclude_key)
    sel_str = ''
    for sel_k, sel_v in selector.items():
        if not sel_k == exclude_key:
            if sel_v:
                sel = f'{sel_k}={sel_v};'
                sel_str += sel
    if update_context:
        context[update_context] = sel_str
        return ''
    else:
        return sel_str
