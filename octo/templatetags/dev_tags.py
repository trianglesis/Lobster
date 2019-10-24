"""
Testing tags
"""

import logging
import datetime
from django import template
from django.template import loader

register = template.Library()
log = logging.getLogger("octo.octologger")


@register.simple_tag
def current_time(format_string):
    return datetime.datetime.now().strftime(format_string)


@register.simple_tag(takes_context=True)
def debug_info(context):
    """
    Render debug code in footer of page

    :param context:
    :return:
    """
    request         = context['request']
    user            = context['user']
    debug_info_t    = loader.get_template('small_blocks/template_tags/debug_info.html')
    debug_info_flag = request.GET.get('debug_info', False)
    # log.debug("debug_info_flag %s", debug_info_flag)

    if debug_info_flag or debug_info_flag == 1:
        sel_contxt = dict(
            user = user,
            ATTRIBUTES = dict(
                debug_info       = debug_info_flag,
                request_path     = request.path,

                table            = request.GET.get('table', False),

                branch           = request.GET.get('branch', 'tkn_main'),
                addm_name        = request.GET.get('addm_name', 'double_decker'),

                fail_only        = request.GET.get('fail_only', False),
                skip_only        = request.GET.get('skip_only', False),
                error_only       = request.GET.get('error_only', False),
                pass_only        = request.GET.get('pass_only', False),
                not_pass_only    = request.GET.get('not_pass_only', False),

                pattern_library  = request.GET.get('pattern_library', False),
                pattern_folder   = request.GET.get('pattern_folder', False),

                go_back          = request.GET.get('go_back', False),
                go_ahead         = request.GET.get('go_ahead', False),

                web_start_date   = request.GET.get('start_date', False),
                web_end_date     = request.GET.get('end_date', False),
                date_from        = request.GET.get('date_from', False),
                date_last        = request.GET.get('date_last', False),

                BRANCH_SWITCH_URL  = context.get('BRANCH_SWITCH_URL', False),
                ADDM_DIGEST_URL    = context.get('ADDM_DIGEST_RES', False),
                PATTERN_DIGEST_URL = context.get('PATTERN_DIGEST_RES', False),
                HISTORY_SELECT_URL = context.get('HISTORY_SELECT_RES', False),
                ADDM_GENERAL_LINK  = context.get('ADDM_GENERAL_LINK', False),
            ),
        )
        # log.debug("<=TAG=> debug_info sel_contxt %s", sel_contxt)
        return debug_info_t.render(sel_contxt)
    return ''
