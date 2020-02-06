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
    private = models.NullBooleanField(_('private value'), null=True)
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
    private = models.NullBooleanField(_('private value'), null=True)

    class Meta:
        managed = True
        db_table = 'octo_mail_texts'

    def __str__(self):
        return f'{self.id} - {self.mail_key}'


class ADDMCommands(models.Model):
    command_key = models.CharField(_('command key unique'), max_length=120, unique=True)
    command_value = models.TextField(_('command value'), blank=True, null=True)

    private = models.NullBooleanField(_('private value'), null=True)
    interactive = models.NullBooleanField(_('interactive mode'), null=True)
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
    addm_host = models.CharField(max_length=255)
    addm_name = models.CharField(max_length=255)
    tideway_user = models.CharField(max_length=255)
    tideway_pdw = models.CharField(max_length=255)
    addm_ip = models.CharField(max_length=255)
    addm_v_code = models.CharField(max_length=255)
    addm_v_int = models.CharField(max_length=255)
    addm_full_version = models.CharField(max_length=255, blank=True, null=True)
    addm_branch = models.CharField(max_length=255)
    addm_owner = models.CharField(max_length=255)
    addm_group = models.CharField(max_length=255)
    disables = models.NullBooleanField(null=True)
    branch_lock = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    vm_cluster = models.CharField(max_length=255, blank=True, null=True)
    vm_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'octo_addm_dev'
        unique_together = (('addm_host', 'addm_name', 'addm_v_int', 'addm_group'),)

    def __str__(self):
        return f'{self.id} - {self.addm_group}:{self.addm_name} - {self.addm_host}'


class AddmDevProxy(AddmDev):

    class Meta:
        proxy = True


class RoutineExecutionLog(models.Model):
    routine_key = models.CharField(primary_key=True, max_length=255)
    routine_name = models.CharField(max_length=255)
    routine_time_spent = models.CharField(blank=True, null=True, max_length=255)
    routine_args = models.CharField(blank=True, null=True, max_length=255)
    routine_kwargs = models.CharField(blank=True, null=True, max_length=255)
    routine_desc_details = models.TextField(blank=True, null=True)
    # Left it in ITC by default, then will convert to UK or UA:
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'ROUTINES_LOG'
        unique_together = (('routine_key', 'created_at'),)


class ServiceLog(models.Model):
    log_key = models.CharField(max_length=255)
    # Left it in ITC by default, then will convert to UK or UA:
    created_at = models.DateTimeField(auto_now=True)
    # Ags from executed cmd, routine
    log_args = models.TextField(blank=True, null=True)
    log_kwargs = models.TextField(blank=True, null=True)
    # If ADDM related:
    addm_name = models.TextField(max_length=255, blank=True, null=True)
    addm_host = models.TextField(max_length=255, blank=True, null=True)
    # All informative inputs and outputs.
    log_out = models.TextField(blank=True, null=True)
    log_err = models.TextField(blank=True, null=True)
    log_input = models.TextField(blank=True, null=True)
    # Optional output from any PIPE - non formatted.
    log_outputs_raw = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'SERVICE_LOG'
        unique_together = (('log_key', 'created_at'),)
