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


# noinspection SpellCheckingInspection
class TkuPatterns(models.Model):
    """
    Table for tku patterns details to store.
    Use items from here to execute tests and show latest changes for selected date window.
    Also stores "key patterns" flag.

    """
    tkn_branch = models.CharField(max_length=10)
    pattern_library = models.CharField(max_length=120)
    pattern_folder_name = models.CharField(max_length=120)
    pattern_file_name = models.CharField(max_length=120)

    pattern_folder_change = models.CharField(max_length=20, blank=True, null=True)
    # This is converted from p4 tzoffset	-18000
    pattern_folder_mod_time = models.DateTimeField(auto_now_add=True)
    change_desc = models.TextField(blank=True, null=True)
    change_user = models.CharField(max_length=20, blank=True, null=True)
    change_review = models.CharField(max_length=20, blank=True, null=True)
    change_ticket = models.CharField(max_length=20, blank=True, null=True)

    pattern_file_path = models.CharField(unique=True, max_length=255)
    pattern_file_path_depot = models.CharField(unique=True, max_length=255)
    pattern_folder_path_depot = models.CharField(max_length=255)

    test_py_path = models.CharField(max_length=255, blank=True, null=True)
    test_py_path_template = models.CharField(max_length=255, blank=True, null=True)  # AKA test_py_path

    test_folder_path = models.CharField(max_length=255, blank=True, null=True)
    test_folder_path_template = models.CharField(max_length=255, blank=True, null=True)  # AKA test_working_dir

    is_key_pattern = models.NullBooleanField(null=True)
    test_time_weight = models.CharField(max_length=35, blank=True, null=True)
    # To indicate when this pattern was updated\inserted last time.
    # Left it in ITC by default, then will convert to UK or UA:
    date_time_auto_now = models.DateTimeField(unique=False, auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'octo_tku_patterns'
        unique_together = (('tkn_branch',
                            'pattern_library',
                            'pattern_folder_name',
                            'pattern_file_name',
                            'pattern_file_path',
                            'test_folder_path',
                            'test_py_path',
                            ))


class TestLast(models.Model):
    # Pattern details:
    tkn_branch = models.CharField(max_length=10)

    pattern_library = models.CharField(max_length=100)
    pattern_folder_name = models.CharField(max_length=255)
    test_py_path = models.CharField(max_length=255)

    # Test details:
    tst_name = models.CharField(max_length=255)
    tst_module = models.CharField(max_length=255)
    tst_class = models.CharField(max_length=255)
    tst_message = models.TextField(blank=True, null=True)
    tst_status = models.TextField(blank=True, null=True)
    fail_status = models.TextField(blank=True, null=True)
    fail_name = models.TextField(blank=True, null=True)
    fail_module = models.TextField(blank=True, null=True)
    fail_class = models.TextField(blank=True, null=True)
    fail_message = models.TextField(blank=True, null=True)
    # ADDM details:
    addm_name = models.CharField(max_length=20)
    addm_group = models.CharField(max_length=10)
    addm_v_int = models.CharField(max_length=20, blank=True, null=True)
    addm_host = models.CharField(max_length=20)
    addm_ip = models.CharField(max_length=20, blank=True, null=True)
    # Time & date details:
    time_spent_test = models.CharField(max_length=20, blank=True, null=True)
    # Left it in ITC by default, then will convert to UK or UA:
    test_date_time = models.DateTimeField(unique=False, auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'octo_test_last'
        # unique_together = (
        #     (
        #         'tkn_branch',
        #         'pattern_library',
        #         'pattern_folder_name',
        #         'test_py_path',
        #         'tst_name',
        #         'tst_module',
        #         'tst_class',
        #         'test_date_time',
        #         'addm_name',
        #         'addm_host',
        #     ),
        # )
        indexes = [
            models.Index(fields=['test_py_path'], name='test_test_py_path'),
            models.Index(fields=['test_date_time'], name='test_date_time'),
            models.Index(fields=[
                'tkn_branch',
                'pattern_library',
                'pattern_folder_name',
                'tst_name',
                'tst_class',
                'addm_name',
            ], name='test_unique'),
        ]


class TestHistory(models.Model):
    # Pattern details:
    tkn_branch = models.CharField(max_length=10)
    pattern_library = models.CharField(max_length=255)
    pattern_file_name = models.CharField(max_length=255)
    pattern_folder_name = models.CharField(max_length=255)
    pattern_file_path = models.CharField(max_length=255, blank=True, null=True)
    test_py_path = models.CharField(max_length=255, blank=True, null=True)
    pattern_folder_path_depot = models.CharField(max_length=255, blank=True, null=True)
    pattern_file_path_depot = models.TextField(blank=True, null=True)
    is_key_pattern = models.NullBooleanField(null=True)
    # Test details:
    tst_message = models.TextField(blank=True, null=True)
    tst_name = models.CharField(max_length=255)
    tst_module = models.CharField(max_length=255)
    tst_class = models.CharField(max_length=255)
    tst_status = models.TextField(blank=True, null=True)
    fail_status = models.TextField(blank=True, null=True)
    fail_name = models.TextField(blank=True, null=True)
    fail_module = models.TextField(blank=True, null=True)
    fail_class = models.TextField(blank=True, null=True)
    fail_message = models.TextField(blank=True, null=True)
    # ADDM details:
    addm_name = models.CharField(max_length=20)
    addm_group = models.CharField(max_length=10)
    addm_v_int = models.CharField(max_length=20, blank=True, null=True)
    addm_host = models.CharField(max_length=50)
    addm_ip = models.CharField(max_length=20, blank=True, null=True)
    # Time & date details:
    time_spent_test = models.CharField(max_length=20, blank=True, null=True)
    # Left it in ITC by default, then will convert to UK or UA:
    test_date_time = models.DateTimeField(unique=True, auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'octo_test_history'
        unique_together = (
            (
                'tkn_branch',
                'pattern_library',
                'pattern_folder_name',
                'pattern_file_name',
                'tst_name',
                'tst_module',
                'tst_class',
                'test_date_time',
                'addm_name',
                'addm_host',
            ),
        )


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
    test_time_weight = models.CharField(max_length=35, blank=True, null=True)  # How long test run

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

# Place for other models tables:
# Table for test cases comments, details, groping and other useful information provided by users


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

    def get_test_cases(self):
        return f'{self.test_cases.test_type}'


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
