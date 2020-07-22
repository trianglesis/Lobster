"""
Template tags for saving time and space in templates
"""
import re
import logging
import time
import datetime
from django import template
from django.template import loader, Template, Context

from octo.config_cred import cred

from run_core.models import AddmDev

import json
from django.core import serializers as django_serializers
from octo_tku_patterns.api.serializers import *
from octo_adm.serializers import AddmDevSerializer

register = template.Library()
log = logging.getLogger("octo.octologger")


@register.filter(name='remove_dash')
def remove_dash(value):
    return value.replace("#", "")


@register.filter()
def f_sec(s):
    try:
        return time.strftime('%H:%M:%S', time.gmtime(round(float(s))))
    except ValueError:
        return s
    # When None
    except TypeError:
        return 0


@register.simple_tag()
def load_host_names():
    hostnames = dict(
        LOBSTER_SITE_DOMAIN=cred['LOBSTER_SITE_DOMAIN'],
        OCTOPUS_SITE_DOMAIN=cred['OCTOPUS_SITE_DOMAIN'],
    )
    return hostnames


@register.simple_tag()
def percent_pass_test(test_pass, test_skip, test_all):
    passed_percent = round(100 * (int(test_pass) + int(test_skip)) / float(test_all), 2)
    return passed_percent


@register.simple_tag()
def select_branch_icon(branch, size):
    if branch == "tkn_main":
        html = Template('{% load static %}<img style="height:{{size}}px;width:{{size}}px;" src="{% static "octicons/icons/git-branch-16.svg" %}" alt="branch_main" />')
    elif branch == "tkn_ship":
        html = Template('{% load static %}<img style="height:{{size}}px;width:{{size}}px;" src="{% static "octicons/icons/git-merge-16.svg" %}" alt="merge_ship" />')
    else:
        html = Template('{% load static %}<img style="height:{{size}}px;width:{{size}}px;" src="{% static "octicons/icons/repo-forked-16.svg" %}" alt="unknown_branch" />')
    c = Context(dict(size=size))
    return html.render(c)


@register.simple_tag()
def select_icon(icon_name, size, side=None, margin=None):
    if side and margin:
        html = Template('{% load static %}<img style="height:{{size}}px;width:{{size}}px;margin-{{side}}: {{margin}}em;" src="/static/octicons/icons/{{icon_name}}-16.svg" alt="{{icon_name}}" />')
        c = Context(dict(size=size, side=side, margin=margin, icon_name=icon_name))
    else:
        html = Template('{% load static %}<img style="height:{{size}}px;width:{{size}}px;" src="/static/octicons/icons/{{icon_name}}-16.svg" alt="{{icon_name}}" />')
        c = Context(dict(size=size, icon_name=icon_name))
    return html.render(c)


@register.simple_tag()
def select_icon_patt_kw_library(kw_library):
    library_icons = dict(
        BLADE_ENCLOSURE='<i class="fas fa-tape"></i>',
        CLOUD='<i class="fas fa-cloud"></i>',
        CORE='<i class="fas fa-cube"></i>',
        LOAD_BALANCER='<i class="fas fa-balance-scale"></i>',
        MANAGEMENT_CONTROLLERS='<i class="fas fa-truck-loading"></i>',
        NETWORK='<i class="fas fa-network-wired"></i>',
        STORAGE='<i class="fas fa-hdd"></i>',
        SYSTEM='<i class="fab fa-centos"></i>',
    )
    html = Template(library_icons.get(kw_library))
    c = Context(dict())
    return html.render(c)


@register.simple_tag()
def tooltip(toggle, placement, title, content='', data_html=False):
    html = Template('''
    tabindex="0" 
    data-toggle="{{toggle}}" 
    data-placement="{{placement}}" 
    title="{{title}}"
    data-content="{{content}}"
    ''')
    if data_html:
        html += ' data-html="true"'
    c = Context(dict(toggle=toggle, placement=placement, title=title, content=content))
    return html.render(c)


@register.simple_tag()
def popover(toggle, placement, title=None, content=None):
    html_str = '''
    tabindex="0" 
    data-toggle="{{toggle}}" 
    data-placement="{{placement}}"'''
    contxt = dict(toggle=toggle, placement=placement)
    if content:
        html_str += ' data-content="{{content}}"'
        contxt.update(content=content)
    if title:
        html_str += ' title="{{title}}"'
        contxt.update(title=title)
    html = Template(html_str)
    c = Context(contxt)
    return html.render(c)


@register.simple_tag()
def tooltip_case(toggle, placement, case):
    html = Template('''
    tabindex="0" 
    data-toggle="{{toggle}}" 
    data-placement="{{placement}}" 
    data-html="true" 
    title="{{case.id}} {{case.test_type}} {% if case.tkn_branch%}{{case.tkn_branch}}{%else%}{{ case.test_case_dir }}{%endif%}"
    data-content="
    <div class='test_case_depot_path'><span>{{case.test_case_depot_path}}</span></div>
    <div class='pattern_library'><span>{{case.pattern_library}}/{{case.pattern_folder_name}}</span></div>
    <div class='change_user'><span>{{case.change_user}} {{case.change}}</span></div>
    <div class='change_time'><span>UTC: {{case.change_time}}</span></div>
    <div class='change_ticket'><span>{{case.change_review}} JIRA: {{case.change_ticket}}</span></div>
    <div class='change_desc'><span class='sm-txt'>{{case.change_desc}}</span></div>
    <div class='test_time_weight'><span>{{case.test_time_weight}}</span></div>
    <div class='test_py_path_template'><span class='sm-txt'>{{case.test_py_path_template}}</span></div>
    <div class='test_dir_path_template'><span class='sm-txt'>{{case.test_dir_path_template}}</span></div>
    "
    ''')
    # TOO RECURSIVE!
    # <div class='related_test_cases'><span class='sm-txt'>{% if case.related_test_cases %}{% for group in case.related_test_cases.all %}{{ group.title }}, {% endfor %}{% endif %}</span></div>
    c = Context(dict(toggle=toggle, placement=placement, case=case))
    return html.render(c)


@register.simple_tag()
def tooltip_tku_test(toggle, placement, test):
    html = Template('''{% load tz %}{% load humanize %}{% load template_simplify %}
    tabindex="0" 
    data-toggle="{{toggle}}" 
    data-placement="{{placement}}" 
    data-html="true" 
    title="{{ test.tkn_branch }}/{{test.pattern_library}}/{{test.pattern_folder_name}}"
    data-content="
    <div class='test_case_depot_path'><span>{{test.test_case_depot_path}}</span></div>
    <div class='pattern_library'><span>{{test.pattern_library}}/{{test.pattern_folder_name}}</span></div>
    <div class='change_user'><span>{{test.change_user}} {{ test.change }}</span></div>
    <div class='change_time'><span>Change: {{test.change_time|timezone:"Europe/London"|naturaltime}}</span></div>
    <div class='test_date_time'><span>Test: {{test.test_date_time|timezone:"Europe/London"|naturaltime}}</span></div>
    <div class='change_ticket'><span>{{test.change_review}} JIRA: {{test.change_ticket}}</span></div>
    <div class='change_desc'><span>{{test.change_desc}}</span></div>
    <div class='addm_v_int'><span>{{test.addm_v_int}} {{ test.addm_name }}</span></div>
    <div class='test_items_prepared'><span> Unit tests: {{test.test_items_prepared}}</span></div>
    <div class='fails'><span>Failed: {{test.fails}}</span></div>
    <div class='error'><span>Error: {{test.error}}</span></div>
    <div class='passed'><span>Passed: {{test.passed}}</span></div>
    <div class='skipped'><span>Skipped: {{test.skipped}}</span></div>
    <div class='time_spent_test'><span>Run: {{test.time_spent_test | f_sec}}</span></div>
    <div class='test_time_weight'><span>Weight: {{test.test_time_weight | f_sec}}</span></div>
    <div class='test_py_path'><span>{{test.test_py_path}}</span></div>
    "
    ''')
    c = Context(dict(toggle=toggle, placement=placement, test=test))
    return html.render(c)


@register.simple_tag()
def tooltip_tku_unittest(toggle, placement, test):
    test_case = TestCases.objects.filter(test_py_path=test.test_py_path)
    html = Template('''{% load tz %}{% load humanize %}
    tabindex="0" 
    data-toggle="{{toggle}}" 
    data-placement="{{placement}}" 
    data-html="true" 
    title="{{ test_case.test_case_depot_path }}"
    data-content="
    <div class='tkn_branch'><span>{{test_case.tkn_branch}}</span></div>
    <div class='test_case_depot_path'><span>{{test_case.test_case_depot_path}}</span></div>
    <div class='pattern_library'><span>{{test.pattern_library}}/{{test.pattern_folder_name}}</span></div>
    <div class='change_user'><span>{{test_case.change_user}} {{ test_case.change }}</span></div>
    <div class='change_time'><span>Change: {{test_case.change_time|timezone:"Europe/London"|naturaltime}}</span></div>
    <div class='test_date_time'><span>Test: {{test.test_date_time|timezone:"Europe/London"|naturaltime}}</span></div>
    <div class='change_ticket'><span>{{test_case.change_review}} JIRA: {{test_case.change_ticket}}</span></div>
    <div class='change_desc'><span>{{test_case.change_desc}}</span></div>
    <div class='addm_v_int'><span>{{test.addm_v_int}} {{ test.addm_name }}</span></div>
    <div class='addm_group'><span>{{ test.addm_group }}</span></div>
    <div class='addm_host'><span>{{ test.addm_host }} {{ test.addm_ip }}</span></div>
    <div class='time_spent_test'><span>Run: {{test.time_spent_test }}</span></div>
    <div class='test_time_weight'><span>Weight: {{test_case.test_time_weight }}</span></div>
    <div class='test_py_path'><span>{{test.test_py_path}}</span></div>
    "
    ''')
    # TOO RECURSIVE!
    # <div class='case_group'><span>{% if test_case.related_test_cases %}{% for group in test_case.related_test_cases.all %}{{ group.title }}, {% endfor %}{% endif %}</span></div>
    c = Context(dict(toggle=toggle, placement=placement, test=test, test_case=test_case[0]))
    return html.render(c)


@register.simple_tag()
def tooltip_tku_upload(toggle, placement, test):
    html = Template('''{% load tz %}{% load humanize %}
    tabindex="0" 
    data-trigger="focus"
    data-toggle="{{toggle}}" 
    data-placement="{{placement}}" 
    data-html="true" 
    tabindex="0"
    title="{{ test.tku_type }}"
    data-content="
    <div class='addm_name'><span>Addm: {{test.addm_name}} {{test.addm_v_int}} zip: {{test.addm_version}}</span></div>
    <div class='test_mode'><span>Mode: {{test.test_mode}}</span></div>
    <div class='mode_key'><span>Key: {{test.mode_key}}</span></div>
    <div class='package_type'><span>Zip: {{test.package_type}}</span></div>
    <div class='tku_type'><span>TKU: {{test.tku_type}}</span></div>
    <div class='tku_build'><span>Release: {{test.release}}</span></div>
    <div class='upload_test_status'><span>Status: {{test.upload_test_status}}</span></div>
    <div class='upload_test_str_stderr'><span> Stderr: {{test.upload_test_str_stderr}}</span></div>
    <div class='all_errors'><span>Err #: {{test.all_errors}}</span></div>
    <div class='upload_errors'><span>Upload err: {{test.upload_errors}}</span></div>
    <div class='all_warnings'><span>Warning #: {{test.all_warnings}}</span></div>
    <div class='upload_warnings txt-micro'><span>Upload warnings: {{test.upload_warnings}}</span></div>
    <div class='tested_zips txt-micro'><span>Zip md5sum: {{test.tested_zips}}</span></div>
    <div class='addm_host'><span>VM: {{test.addm_host}} {{test.addm_ip}}</span></div>
    <div class='time_spent_test'><span>Spent: {{test.time_spent_test}}</span></div>
    <div class='test_date_time'><span>Date: {{test.test_date_time}}</span></div>
    "
    ''')
    c = Context(dict(toggle=toggle, placement=placement, test=test))
    return html.render(c)


@register.simple_tag()
def tooltip_tku_package(toggle, placement, package):
    html = Template('''{% load tz %}{% load humanize %}
    tabindex="0" 
    data-trigger="focus"
    data-toggle="{{toggle}}" 
    data-placement="{{placement}}" 
    data-html="true" 
    tabindex="0"
    title="{{ package.tku_type }}"
    data-content="
    <div class='package_type'><span>{{package.package_type}}</span></div>
    <div class='tku_type'><span>type: {{package.tku_type}} zip: {{package.zip_type}}</span></div>
    <div class='addm_name'><span>ADDM: {{package.addm_version}} - {{package.tku_addm_version}}</span></div>
    <div class='tku_name'><span>{{package.tku_name}}</span></div>
    <div class='tku_build'><span>Build: {{package.tku_build}}.{{package.tku_month}}.{{package.tku_date}}</span></div>
    <div class='tku_build'><span>Release: {{package.release}}</span></div>
    {% if package.tku_pack %}<div class='tku_pack'><span>{{package.tku_pack}}</span></div>{% endif %}
    <div class='zip_file_md5_digest'><span>md5sum: {{package.zip_file_md5_digest}}</span></div>
    <div class='updated_at'><span>Updated: {{package.updated_at}}</span></div>
    <div class='created_at'><span>Created: {{package.created_at}}</span></div>
    <div class='zip_file_path txt-micro'><span>{{package.zip_file_path}}</span></div>
    <div class='zip_file_name'><span>{{package.zip_file_name}}</span></div>
    "
    ''')
    c = Context(dict(toggle=toggle, placement=placement, package=package))
    return html.render(c)


@register.simple_tag(takes_context=True)
def is_active(context, check_key, check_val, false_attr, active_attr):
    selector = context.get('selector')
    if selector[check_key] == check_val:
        return active_attr
    else:
        return false_attr


@register.simple_tag(takes_context=True)
def log_levels(context):
    """Draw template for log level selections"""
    log_lvl = loader.get_template('small_blocks/template_tags/log_lvl.html')
    sel_contxt = dict(
        PASS_ONLY        = context.get('PASS_ONLY', False),
        FAIL_ONLY        = context.get('FAIL_ONLY', False),
        SKIP_ONLY        = context.get('SKIP_ONLY', False),
        ERROR_ONLY       = context.get('ERROR_ONLY', False),
        NOT_PASS_ONLY    = context.get('NOT_PASS_ONLY', False),)
    return log_lvl.render(sel_contxt)


@register.simple_tag(takes_context=True)
def select_pattern_items(context):
    """Draw temp for patten tests, items selections"""
    pattern_sel = loader.get_template('small_blocks/template_tags/select_pattern_items.html')
    sel_contxt = dict(
        PATTERN_LIBRARY  = context.get('PATTERN_LIBRARY', False),
        PATTERN_FOLDER   = context.get('PATTERN_FOLDER', False),
        PATTERN_FILENAME = context.get('PATTERN_FILENAME', False),
        START_DATE       = context.get('START_DATE', False),
        END_DATE         = context.get('END_DATE', False),
        ADPROD_USER      = context.get('ADPROD_USER', False),
    )
    return pattern_sel.render(sel_contxt)


# noinspection PyUnusedLocal
@register.simple_tag(takes_context=True)
def row_pattern_items(context, pattern_library, pattern_folder):
    """Draw temp for patten tests, items selections"""
    pattern_sel = loader.get_template('small_blocks/template_tags/select_pattern_items.html')
    sel_contxt = dict(
        PATTERN_LIBRARY  = pattern_library,
        PATTERN_FOLDER   = pattern_folder,
    )
    return pattern_sel.render(sel_contxt)


@register.simple_tag(takes_context=True)
def request_path_search(context, check_path):
    """ """
    request       = context['request']
    # log.debug("<=TAG=> request_path_search - request %s", request)
    request_path  = request.path
    # log.debug("<=TAG=> request_path_search - request_path %s", request_path)
    path_checking = re.search(check_path, request_path)
    # log.debug("<=TAG=> request_path_search - path_checking %s", path_checking)
    if path_checking:
        return True
    else:
        return False


@register.simple_tag()
def pattern_digest_color(fails, error):
    if fails > 0 or error > 0:
        bckgrnd = "danger"
        status = "FAIL"
    else:
        bckgrnd = "success"
        status = "PASS"
    return dict(bckgrnd=bckgrnd, status=status)


@register.simple_tag()
def assign_color(status):
    if status == "FAIL":
        color = "danger"
    elif status == "ERROR":
        color = "warning"
    elif "skipped" in status:
        color = "info"
    elif "unexpected" in status:
        color = "danger"
    elif "expected failure" in status:
        color = "success"
    elif "ok" in status:
        color = "success"
    else:
        color = "light"
    return color


@register.simple_tag()
def cron_today(periodic_task):
    if_run_today = ''
    from celery.schedules import crontab_parser
    if periodic_task.crontab:
        task_w   = crontab_parser(7).parse(periodic_task.crontab.day_of_week)
        task_d  = crontab_parser(31, 1).parse(periodic_task.crontab.day_of_month)
        task_m = crontab_parser(12, 1).parse(periodic_task.crontab.month_of_year)

        today     = datetime.datetime.now()
        week_day  = today.strftime('%w')
        month_day = today.strftime('%d')
        month     = today.strftime('%m')

        if (int(week_day) in task_w) and (int(month_day) in task_d) and (int(month) in task_m):
            if_run_today = True
        else:
            if_run_today = False
    elif periodic_task.interval:
        if_run_today = True
    return if_run_today


@register.simple_tag()
def addm_color(addm_group, disabled):
    if not disabled:
        if addm_group == "alpha":
            color = "primary"
        elif addm_group == "beta":
            color = "secondary"
        elif "charlie" in addm_group:
            color = "info"
        elif "delta" in addm_group:
            color = "warning"
        elif "echo" in addm_group:
            color = "success"
        elif "foxtrot" in addm_group:
            color = "light"
        else:
            color = "dark"
    else:
        color = "danger"
    return color


@register.simple_tag()
def key_pattern_highlight(is_key_pattern):
    color = "light"
    if is_key_pattern:
        color = "primary"
    return color


@register.simple_tag()
def no_test_pattern_highlight(test_py_path):
    text = ""
    if 'test.py' not in test_py_path:
        text = "text-warning"
    return text


@register.simple_tag()
def pattern_lib_highlight(pattern_library):
    log.debug("<=TAG=> pattern_lib_highlight -> pattern_library %s", pattern_library)

    if pattern_library == "CORE":
        color = "badge-dark"
    else:
        color = "badge-light"
    return color


@register.simple_tag()
def tku_package_color(tku_type):
    if tku_type == "continuous":
        color = "secondary"
    elif tku_type == "nightly":
        color = "warning"
    elif tku_type == "ga_candidate":
        color = "success"
    elif tku_type == "addm_released":
        color = "primary"
    elif tku_type == "released_tkn":
        color = "info"
    else:
        color = "secondary"
    return color


@register.simple_tag()
def tku_package_used(package, ga_candidate_max, released_tkn_max):
    if package.package_type in ga_candidate_max['package_type__max']:
        color = "success"
    elif package.package_type in released_tkn_max['package_type__max']:
        color = "primary"
    else:
        color = "light"
    return color


@register.simple_tag()
def all_addm_groups():
    return AddmDev.objects.all().values_list('addm_group', flat=True).order_by('addm_group').distinct()


@register.filter()
def tku_patterns_json(test_digest_qs, model_name=None):

    if model_name == 'TestCases':
        try:
            serializer = TestCasesSerializer(test_digest_qs, many=True)
            serializer = serializer.data
        except TypeError:
            serializer = TestCasesSerializer(test_digest_qs)
            serializer = serializer.data
    elif model_name == 'TestCasesDetails':
        serializer = TestCasesDetailsSerializer(test_digest_qs, many=True)
        serializer = serializer.data
    elif model_name == 'TestLast':
        serializer = TestLastSerializer(test_digest_qs, many=True)
        serializer = serializer.data
    elif model_name == 'TestLatestDigestAll':
        serializer = TestLatestDigestAllSerializer(test_digest_qs, many=True)
        serializer = serializer.data
    elif model_name == 'TestHistoryDigestDaily':
        serializer = TestHistoryDigestDailySerializer(test_digest_qs, many=True)
        serializer = serializer.data
    elif model_name == 'TestHistory':
        serializer = TestHistorySerializer(test_digest_qs, many=True)
        serializer = serializer.data
    elif model_name == 'AddmDev':
        serializer = AddmDevSerializer(test_digest_qs, many=True)
        serializer = serializer.data
    else:
        serializer = django_serializers.serialize('json', [test_digest_qs])
    # return str(JSONRenderer().render(serializer.data))
    return json.dumps(serializer)
