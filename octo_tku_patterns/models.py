# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from __future__ import unicode_literals

from django.db import models
from django import forms

from django.contrib.auth.models import User


class TestLast(models.Model):
    # Pattern details:
    test_type = models.CharField(max_length=120)
    tkn_branch = models.CharField(max_length=10)

    pattern_library = models.CharField(max_length=100, blank=True, null=True)
    pattern_folder_name = models.CharField(max_length=255, blank=True, null=True)
    test_case_dir = models.CharField(max_length=255, blank=True, null=True)
    test_py_path = models.CharField(max_length=255)

    # Test details:
    tst_name = models.CharField(max_length=255)
    tst_module = models.CharField(max_length=255)
    tst_class = models.CharField(max_length=255)
    tst_message = models.TextField(blank=True, null=True)
    tst_status = models.TextField(blank=True, null=True)
    fail_message = models.TextField(blank=True, null=True)
    # ADDM details:
    addm_name = models.CharField(max_length=20)
    addm_group = models.CharField(max_length=10)
    addm_v_int = models.CharField(max_length=20, blank=True, null=True)
    addm_host = models.CharField(max_length=20)
    addm_ip = models.CharField(max_length=20, blank=True, null=True)
    # Time & date details:
    # TODO: https://docs.djangoproject.com/en/3.0/ref/models/fields/#durationfield later next round.
    # TODO: Change for timeField?
    time_spent_test = models.DecimalField(max_digits=19, decimal_places=10, blank=True, null=True)
    # Left it in ITC by default, then will convert to UK or UA:
    test_date_time = models.DateTimeField(unique=False, auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'octo_test_last'
        indexes = [
            models.Index(fields=['test_py_path'], name='test_last_test_py_path'),
            models.Index(fields=['test_date_time'], name='test_last_date_time'),
            models.Index(fields=[
                'tkn_branch',
                'pattern_library',
                'pattern_folder_name',
                'tst_name',
                'tst_class',
                'addm_name',
            ], name='test_last_test_unique'),
        ]


class TestHistory(models.Model):
    # Pattern details:
    test_type = models.CharField(max_length=120)
    tkn_branch = models.CharField(max_length=10)

    pattern_library = models.CharField(max_length=100, blank=True, null=True)
    pattern_folder_name = models.CharField(max_length=255, blank=True, null=True)
    test_case_dir = models.CharField(max_length=255, blank=True, null=True)
    test_py_path = models.CharField(max_length=255)

    # Test details:
    tst_name = models.CharField(max_length=255)
    tst_module = models.CharField(max_length=255)
    tst_class = models.CharField(max_length=255)
    tst_message = models.TextField(blank=True, null=True)
    tst_status = models.TextField(blank=True, null=True)

    fail_message = models.TextField(blank=True, null=True)
    # ADDM details:
    addm_name = models.CharField(max_length=20)
    addm_group = models.CharField(max_length=10)
    addm_v_int = models.CharField(max_length=20, blank=True, null=True)
    addm_host = models.CharField(max_length=20)
    addm_ip = models.CharField(max_length=20, blank=True, null=True)
    # Time & date details:
    # TODO: https://docs.djangoproject.com/en/3.0/ref/models/fields/#durationfield later next round.
    # TODO: Change for timeField?
    time_spent_test = models.DecimalField(max_digits=19, decimal_places=10, blank=True, null=True)
    # Left it in ITC by default, then will convert to UK or UA:
    test_date_time = models.DateTimeField(unique=False, auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'octo_test_history'
        indexes = [
            models.Index(fields=['test_py_path'], name='test_history_test_py_path'),
            models.Index(fields=['test_date_time'], name='test_history_date_time'),
            models.Index(fields=[
                'tkn_branch',
                'pattern_library',
                'pattern_folder_name',
                'tst_name',
                'tst_class',
                'addm_name',
            ], name='test_history_test_unique'),
        ]


class TestCases(models.Model):
    # Indicates test type: tku_patterns, product_content, addm_code or sth. else.
    test_type = models.CharField(max_length=120)

    # For tku_patterns test type:
    tkn_branch = models.CharField(max_length=10, blank=True, null=True)
    pattern_library = models.CharField(max_length=120, blank=True, null=True)
    pattern_folder_name = models.CharField(max_length=120, blank=True, null=True)
    pattern_folder_path = models.CharField(max_length=255, blank=True, null=True)
    pattern_library_path = models.CharField(max_length=255, blank=True, null=True)
    # For other test type:
    test_case_dir = models.CharField(max_length=120, blank=True, null=True)  # Indicates test parent folder, like pattern's one.

    # P4 Revision data:
    change = models.CharField(max_length=20, blank=True, null=True)
    change_desc = models.TextField(blank=True, null=True)
    change_user = models.CharField(max_length=20, blank=True, null=True)
    change_review = models.CharField(max_length=20, blank=True, null=True)
    change_ticket = models.CharField(max_length=20, blank=True, null=True)
    # From p4 offset:
    change_time = models.DateTimeField(blank=True, null=True)
    test_case_depot_path = models.CharField(max_length=255)

    # Details:
    # Set branch based on test path only:
    test_py_path = models.CharField(max_length=255, unique=True)
    test_py_path_template = models.CharField(max_length=255)  # AKA test_py_path

    test_dir_path = models.CharField(max_length=255)
    test_dir_path_template = models.CharField(max_length=255)  # AKA test_working_dir

    # Fill it basing on previous tests run time:
    # TODO: https://docs.djangoproject.com/en/3.0/ref/models/fields/#durationfield later next round.
    test_time_weight = models.DecimalField(max_digits=19, decimal_places=10, blank=True, null=True)

    # System dates and times:
    created_time = models.DateTimeField(
        unique=False, auto_now_add=True)  # Set only when this entry was created!

    # Disable, because DB will rewrite this each time:
    # modified_time = models.DateTimeField(unique=False, auto_now=True)  # Set and change each time this was updated!

    class Meta:
        ordering = ["-change_time"]

        managed = True
        db_table = 'octo_test_cases'

        indexes = [
            models.Index(fields=['test_py_path'], name='case_test_py_path'),
            models.Index(fields=['change_time'], name='case_change_time'),
            models.Index(fields=[
                'tkn_branch',
                'pattern_library',
                'pattern_folder_name',
            ], name='case_unique'),
        ]

    def __str__(self):
        return 'id:{0}-{1}'.format(self.pk, self.test_case_depot_path)


class TestCasesDetails(models.Model):
    title = models.CharField(max_length=25)
    author = models.ForeignKey(User, on_delete=models.CASCADE, blank=True)
    test_cases = models.ManyToManyField(TestCases, related_name='related_test_cases')
    description = models.TextField(null=True, blank=True)
    pub_date = models.DateTimeField(unique=False, auto_now_add=True)
    changed_date = models.DateTimeField(unique=False, auto_now=True)

    class Meta:
        managed = True
        db_table = 'octo_test_cases_details'

    def __str__(self):
        return '{0} - {1}'.format(self.title, self.author)

    # def get_test_cases(self):
    #     return f'{self.test_cases.test_type}'


class TestReports(models.Model):
    test_type = models.CharField(max_length=255, blank=True, null=True)
    tkn_branch = models.CharField(max_length=100, blank=True, null=True)
    pattern_library = models.CharField(max_length=100, blank=True, null=True)
    addm_name = models.CharField(max_length=100, blank=True, null=True)
    addm_v_int = models.CharField(max_length=100, blank=True, null=True)
    tests_count = models.CharField(max_length=100, blank=True, null=True)
    patterns_count = models.CharField(max_length=100, blank=True, null=True)
    fails = models.CharField(max_length=100, blank=True, null=True)
    error = models.CharField(max_length=100, blank=True, null=True)
    passed = models.CharField(max_length=100, blank=True, null=True)
    skipped = models.CharField(max_length=100, blank=True, null=True)

    # Make auto now
    # report_date_time = models.DateTimeField(unique=False, auto_now_add=True)
    report_date_time = models.DateTimeField(unique=False)

    class Meta:
        managed = True
        db_table = 'octo_test_report'

# For reference.
class TestCasesDetailsForm(forms.ModelForm):
    class Meta:
        model = TestCasesDetails
        fields = [
            'title',
            'author',
            'test_cases',
            'description',
        ]
        readonly_fields = ['pub_date', 'changed_date']

    pub_date = forms.DateTimeField()
    changed_date = forms.DateTimeField()


class TestLastSingleViewForm(forms.ModelForm):
    class Meta:
        model = TestLast
        fields = [
            'tkn_branch',
            'pattern_library',
            'pattern_folder_name',
            'tst_name',
            'tst_module',
            'tst_class',
            'addm_name',
            'addm_group',
            'addm_v_int',
            'addm_host',
            'addm_ip',
            'test_py_path',
        ]
        readonly_fields = ['pub_date', 'changed_date']

    pub_date = forms.DateTimeField()
    changed_date = forms.DateTimeField()
