"""
Template tags to check users access levels and groups.
"""

import logging
from django import template

register = template.Library()
log = logging.getLogger("octo.octologger")


def is_member(user, group):
    return user.groups.filter(name=group).exists()


@register.simple_tag(takes_context=True)
def is_user_log_in(context):
    """
    Check if is logged in.

    ['__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__',
    '__getattribute__', '__gt__', '__hash__', '__init__', '__le__', '__lt__', '__module__', '__ne__', '__new__',
    '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '
    __weakref__', '_groups', '_user_permissions', 'check_password', 'delete', 'get_all_permissions',
    'get_group_permissions', 'get_username', 'groups', 'has_module_perms', 'has_perm', 'has_perms',
    'id', 'is_active', 'is_anonymous', 'is_authenticated', 'is_staff', 'is_superuser', 'pk', 'save',
    'set_password', 'user_permissions', 'username']

    :param context:
    :return:
    """
    user = context['user']

    # log.debug('context["user"]: %s', user)
    # log.debug('user.id: %s', user.id)
    # log.debug('user dir: %s', dir(user))
    # log.debug('user.is_anonymous: %s', user.is_anonymous)
    # log.debug('user.groups: %s', user.groups)
    # log.debug('user.username: %s', user.username)
    # log.debug('user.get_username: %s', user.get_username)
    # log.debug('user.is_anonymous: %s', user.is_anonymous)
    # log.debug('user.is_authenticated: %s', user.is_authenticated)
    # log.debug('user.is_staff: %s', user.is_staff)
    # log.debug('user.is_superuser: %s', user.is_superuser)
    # log.debug('user.user_permissions: %s', user.user_permissions)
    # log.debug('user.id: %s', user.id)

    return user.is_anonymous


@register.simple_tag(takes_context=True)
def is_power_user(context):
    """
    Check if user is in 'power_users' group

    :param context:
    :return:
    """
    user = context['user']
    if user.id:
        if is_member(user, 'power_users'):
            return True
        else:
            return False
    else:
        return False


@register.simple_tag(takes_context=True)
def is_admin_user(context):
    """
    Check if user is in 'admin_users' group

    :param context:
    :return:
    """
    user = context['user']
    if user.id:
        if is_member(user, 'admin_users'):
            return True
        else:
            return False
    else:
        return False


@register.simple_tag(takes_context=True)
def is_group_user(context, group):
    """
    Check if user is in 'power_users' group

    :param context:
    :param group:
    :return:
    """
    user = context['user']
    if user.id:
        if is_member(user, group):
            return True
        else:
            return False
    else:
        return False


@register.simple_tag(takes_context=True)
def is_user_staff(context):
    """
    Check if is logged in.

    ['__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__',
    '__getattribute__', '__gt__', '__hash__', '__init__', '__le__', '__lt__', '__module__', '__ne__', '__new__',
    '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '
    __weakref__', '_groups', '_user_permissions', 'check_password', 'delete', 'get_all_permissions',
    'get_group_permissions', 'get_username', 'groups', 'has_module_perms', 'has_perm', 'has_perms',
    'id', 'is_active', 'is_anonymous', 'is_authenticated', 'is_staff', 'is_superuser', 'pk', 'save',
    'set_password', 'user_permissions', 'username']

    :param context:
    :return:
    """
    user = context['user']

    # log.debug('context["user"]: %s', user)
    # log.debug('user.id: %s', user.id)
    # log.debug('user dir: %s', dir(user))
    # log.debug('user.is_anonymous: %s', user.is_anonymous)

    return user.is_staff
