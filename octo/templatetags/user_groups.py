"""
Template tags to check users access levels and groups.
"""

import logging
from django import template

register = template.Library()
log = logging.getLogger("octo.octologger")


@register.simple_tag(takes_context=True)
def is_member(context, group):
    user = context['user']
    return user.groups.filter(name=group).exists()

@register.simple_tag(takes_context=True)
def is_user_perm(context, perm):
    user = context['user']
    # log.debug(f"User permission: {user}:{perm} - {user.has_perm(perm)}")
    user.has_perm(perm)