"""
Template tags intra-template selections and small queries
"""
import logging
from operator import itemgetter

from django import template
from django.template import loader

from run_core.models import ADDMCommands
from octo.helpers.tasks_oper import TasksOperations

register = template.Library()
log = logging.getLogger("octo.octologger")


@register.simple_tag
def worker_queues_short():
    workers_t = loader.get_template('main/workers_queue.html')
    workers_list = TasksOperations().workers_enabled
    workers_list = workers_list.get('option_value', '').split(',')
    workers_list = [worker+'@tentacle' for worker in workers_list]
    # log.debug("workers_list: %s", workers_list)
    # noinspection PyBroadException
    try:
        inspected = TasksOperations().check_active_reserved_short(workers_list=workers_list)
        workers_short_stat = workers_t.render(dict(WORKERS=inspected))
        return workers_short_stat
    # Update exception based on Null workers
    except Exception as e:
        log.debug("worker_queues_short e: %s", e)
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


@register.simple_tag
def select_addm_commands():
    commands = ADDMCommands.objects.filter(private__isnull=True)
    return commands
