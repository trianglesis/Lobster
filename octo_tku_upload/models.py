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


class TkuPackages(models.Model):
    # noinspection SpellCheckingInspection
    """
        ALter multiple PK:
        ALTER TABLE octopus_dev_copy.TKU_PACKAGES DROP PRIMARY KEY, ADD PRIMARY KEY(zip_file_path,
            zip_file_name, package_type, addm_version, tku_build);
        """
    zip_file_path = models.CharField(primary_key=True, max_length=255)
    zip_file_name = models.CharField(max_length=255)
    package_type = models.CharField(max_length=255)
    tku_type = models.CharField(max_length=255)
    zip_type = models.CharField(max_length=255)
    addm_version = models.CharField(max_length=255)
    tku_name = models.CharField(max_length=255)
    tku_addm_version = models.CharField(max_length=255)
    tku_build = models.CharField(max_length=255)
    tku_date = models.CharField(max_length=255)
    tku_month = models.CharField(max_length=255)
    tku_pack = models.CharField(max_length=255)
    zip_file_md5_digest = models.CharField(max_length=255)

    class Meta:
        managed = True
        db_table = 'TKU_PACKAGES'
        unique_together = (
            (
                'zip_file_path',
                'zip_file_name',
                'package_type',
                'addm_version',
                'tku_build'
            ),
        )


class TkuPackagesNew(models.Model):
    zip_file_path = models.CharField(max_length=255)
    zip_file_name = models.CharField(max_length=255)
    package_type = models.CharField(max_length=50)
    tku_type = models.CharField(max_length=50)
    zip_type = models.CharField(max_length=50)
    addm_version = models.CharField(max_length=50)
    tku_name = models.CharField(max_length=50)
    tku_addm_version = models.CharField(max_length=50)
    tku_build = models.CharField(max_length=50)
    tku_date = models.CharField(max_length=50)
    tku_month = models.CharField(max_length=50)
    tku_pack = models.CharField(max_length=50)
    zip_file_md5_digest = models.CharField(max_length=255)
    # Set only when col created:
    updated_at = models.DateTimeField()
    # updated_at = models.DateTimeField(unique=False, auto_now=True)
    created_at = models.DateTimeField(unique=False, auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'octo_tku_packages'
        unique_together = (
            (
                'zip_file_path',
                'package_type',
                'addm_version',
            ),
        )


class UploadTests(models.Model):
    """
    Alter multiple PK:
    ALTER TABLE octopus_dev_copy.UPLOAD_TESTS DROP PRIMARY KEY, ADD PRIMARY KEY(
        test_case_key, addm_name, addm_v_int, addm_host, tku_type, tku_build, tku_date,
        tku_month, test_mode, mode_key, package_type);
    """
    test_case_key = models.CharField(primary_key=True, max_length=255)
    test_mode = models.CharField(max_length=255)
    mode_key = models.CharField(max_length=255)
    test_date = models.CharField(max_length=255)
    test_time = models.CharField(max_length=255)
    upload_test_status = models.CharField(max_length=255)
    upload_test_str_stdout = models.TextField(blank=True, null=True)
    upload_test_str_stderr = models.TextField(blank=True, null=True)
    important_out = models.TextField(blank=True, null=True)
    all_errors = models.TextField(blank=True, null=True)
    all_warnings = models.TextField(blank=True, null=True)
    upload_warnings = models.TextField(blank=True, null=True)
    upload_errors = models.TextField(blank=True, null=True)
    tku_statuses = models.TextField(blank=True, null=True)
    time_spent_test = models.CharField(max_length=255)
    tested_zips = models.TextField(blank=True, null=True)
    addm_name = models.CharField(max_length=255)
    addm_v_int = models.CharField(max_length=255)
    addm_host = models.CharField(max_length=255)
    addm_ip = models.CharField(max_length=255)
    addm_version = models.CharField(max_length=255)
    tku_type = models.CharField(max_length=255)
    package_type = models.CharField(max_length=255)
    tku_build = models.CharField(max_length=255)
    tku_date = models.CharField(max_length=255)
    tku_month = models.CharField(max_length=255)

    class Meta:
        managed = True
        db_table = 'UPLOAD_TESTS'
        unique_together = (('test_case_key', 'addm_name', 'addm_v_int', 'addm_host',
                            'tku_type', 'tku_build', 'tku_date', 'tku_month', 'test_mode', 'mode_key', 'package_type'),)


class UploadTestsNew(models.Model):
    # Used mode and mode key:
    test_mode = models.CharField(max_length=50)
    mode_key = models.CharField(max_length=50)
    # TKU zip details:
    package_type = models.CharField(max_length=50)
    tku_type = models.CharField(max_length=50)
    tku_build = models.CharField(max_length=50)
    tku_date = models.CharField(max_length=50)
    tku_month = models.CharField(max_length=50)
    # Clean outputs for debug:
    upload_test_status = models.CharField(max_length=50)
    upload_test_str_stdout = models.TextField(blank=True, null=True)
    upload_test_str_stderr = models.TextField(blank=True, null=True)
    # parsed and cleaned output (without extra console and repeated symbols)
    important_out = models.TextField(blank=True, null=True)
    # COUNT of all errors and warnings:
    all_errors = models.TextField(blank=True, null=True)
    all_warnings = models.TextField(blank=True, null=True)
    # Clear warnings and errors during TKU install:
    upload_warnings = models.TextField(blank=True, null=True)
    upload_errors = models.TextField(blank=True, null=True)
    # TKU zips and packages installed: list and statuses, like 'skipped'
    tku_statuses = models.TextField(blank=True, null=True)
    # List of md5sum indexes of TKU zips were used for test
    tested_zips = models.TextField(blank=True, null=True)
    # Addm item details:
    addm_name = models.CharField(max_length=50)
    addm_v_int = models.CharField(max_length=50)
    addm_host = models.CharField(max_length=50)
    addm_ip = models.CharField(max_length=50)
    addm_version = models.CharField(max_length=50)
    # Test lasts
    time_spent_test = models.CharField(max_length=50)
    # Auto field:
    # Left it in ITC by default, then will convert to UK or UA:
    test_date_time = models.DateTimeField(unique=True, auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'octo_tku_test'
        unique_together = (
            (
                'mode_key',
                'tku_type',
                'package_type',
                'test_date_time',
                'addm_host',
                'addm_name',
            ),
        )
