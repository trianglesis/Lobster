# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _


class TestOutputs(models.Model):
    option_key = models.CharField(max_length=255)
    option_value = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'dev_octo_test_outputs'

    def __str__(self):
        return f'{self.id} - {self.option_key}'


class Options(models.Model):
    option_key = models.CharField(_('option key unique'), max_length=120, unique=True)
    option_value = models.TextField(_('option value'), blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True)
    private = models.BooleanField(_('private value'), null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'octo_options'

    def __str__(self):
        return f'{self.id} - {self.option_key}'


class MailsTexts(models.Model):
    mail_key = models.CharField(_('key unique'), max_length=120, unique=True)
    subject = models.CharField(_('subject'), max_length=255, unique=True)
    body = models.TextField(_('body'), blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now=True)
    private = models.BooleanField(_('private value'), null=True)

    class Meta:
        managed = True
        db_table = 'octo_mail_texts'

    def __str__(self):
        return f'{self.id} - {self.mail_key}'


class ADDMCommands(models.Model):
    command_key = models.CharField(_('command key unique'), max_length=120, unique=True)
    command_value = models.TextField(_('command value'), blank=True, null=True)

    private = models.BooleanField(_('private value'), null=True)
    interactive = models.BooleanField(_('interactive mode'), null=True)
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'octo_addm_commands'

    def __str__(self):
        return f'{self.id} - {self.command_key}'


class UserAdprod(models.Model):
    user = models.OneToOneField(User, related_name="user_profile", on_delete=models.CASCADE)
    adprod_username = models.CharField(max_length=100)

    class Meta:
        permissions = (
            ("test_run", "User can run tests"),
            ("service_run", "User can run service tasks eg tideway restart"),
            ("routine_run", "User can run routines"),
            ("task_revoke", "User can revoke task"),
            ("task_manage", "User can manage celery tasks, every action"),
            ("superuser", "User can execute everything"),
        )


class AddmDev(models.Model):
    addm_host = models.CharField(max_length=20)
    addm_name = models.CharField(max_length=20)
    tideway_user = models.CharField(max_length=20)
    tideway_pdw = models.CharField(max_length=20)
    addm_ip = models.CharField(max_length=20)
    addm_v_int = models.CharField(max_length=20)
    addm_full_version = models.CharField(max_length=20, blank=True, null=True)
    addm_group = models.CharField(max_length=20)
    disables = models.BooleanField(null=True)
    branch_lock = models.CharField(max_length=20)
    description = models.TextField(blank=True, null=True)
    role = models.CharField(max_length=50, blank=True, null=True)
    vm_cluster = models.CharField(max_length=20, blank=True, null=True)
    vm_id = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'octo_addm_dev'
        unique_together = (('addm_host', 'addm_name', 'addm_v_int', 'addm_group'),)

    def __str__(self):
        return f'{self.id} - {self.addm_group}:{self.addm_name} - {self.addm_host}'


class AddmDevProxy(AddmDev):

    class Meta:
        proxy = True


class RoutinesLog(models.Model):
    """
    Save here routine execution logs for night tests, upload routines, user test
    """

    task_name = models.CharField(max_length=255)  # Name of task - to group by kind of tasks
    # TODO: Add foreign key to user instance?
    user = models.CharField(max_length=60, blank=True, null=True)

    t_args = models.TextField(blank=True, null=True)  # task args for debug
    t_kwargs = models.TextField(blank=True, null=True)  # task kwargs for debug

    description = models.TextField(blank=True, null=True)  # Readable useful information.

    input = models.TextField(blank=True, null=True)  # optional - what was passed to run
    out = models.TextField(blank=True, null=True)  # optional -
    err = models.TextField(blank=True, null=True)  # optional -
    raw = models.TextField(blank=True, null=True)  # optional -

    t_start_time = models.DateTimeField(null=True)
    t_finish_time = models.DateTimeField(null=True)
    t_est_time = models.DurationField(blank=True, null=True)  # datetime.timedelta(days =-1, seconds = 68400)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'octo_routines_log'


class ServicesLog(models.Model):
    """
    Save here internal events: service tasks, addm related, parsing, wget and so on.
    """
    task_name = models.CharField(max_length=255)  # Name of task - to group by kind of tasks
    # TODO: Add foreign key to user instance?
    user = models.CharField(max_length=60, blank=True, null=True)

    t_args = models.TextField(blank=True, null=True)  # task args for debug
    t_kwargs = models.TextField(blank=True, null=True)  # task kwargs for debug

    description = models.TextField(blank=True, null=True)  # Readable useful information.

    input = models.TextField(blank=True, null=True)  # optional - what was passed to run
    out = models.TextField(blank=True, null=True)  # optional -
    err = models.TextField(blank=True, null=True)  # optional -
    raw = models.TextField(blank=True, null=True)  # optional -

    t_start_time = models.DateTimeField(null=True)
    t_finish_time = models.DateTimeField(null=True)
    t_est_time = models.DurationField(blank=True, null=True)  # datetime.timedelta(days =-1, seconds = 68400)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'octo_service_log'
