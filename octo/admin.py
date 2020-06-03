from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.forms import TextInput, Textarea, SelectMultiple

from .model_views import *
from .models import *
from run_core.models import *
from octo_tku_upload.models import *
from octo_tku_patterns.models import *
from django_ftpserver.models import *

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from octo.common.paginator import TimeLimitedPaginator


# Define an inline admin descriptor for Employee model
# which acts a bit like a singleton
class UserAdprodInline(admin.StackedInline):
    model = UserAdprod
    can_delete = False
    verbose_name_plural = 'ADPROD Username'


# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (UserAdprodInline,)


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# Octopus
# Octopus ADDM
@admin.register(AddmDev)
class AddmDevAdmin(admin.ModelAdmin):
    """ https://djangobook.com/mdj2-django-admin/ """
    # https://djangoguide.readthedocs.io/en/latest/django/admin.html#editable-fields
    # list_editable = ('disables', 'addm_ip', 'addm_name', 'addm_group', 'branch_lock', 'addm_full_version')

    list_display = ('id',
                    'addm_name', 'addm_host', 'addm_ip',
                    'addm_group',
                    'branch_lock',
                    'addm_v_int',
                    'addm_full_version',
                    'role',
                    'disables',
                    'tideway_user',
                    'tideway_pdw',
                    )
    list_filter = ('addm_name', 'addm_group', 'branch_lock', 'addm_full_version', 'vm_cluster', 'role')
    ordering = ('addm_group',)
    search_fields = ('addm_host', 'addm_ip', 'addm_name', 'addm_group')

    fieldsets = (
        ('ADDM Group', {
            'description': "ADDM Group - used for select and threading!",
            'fields': ('addm_group', 'branch_lock', 'role')}),
        ('ADDM Host', {
            'description': "ADDM Useful information. Do not change if not sure!",
            'fields': (
                ('addm_host', 'addm_ip'),
            )
        }),
        ('ADDM Version', {
            'description': "ADDM Useful information. Do not change if not sure!",
            'fields': (
                ('addm_name', 'addm_full_version',),
            )
        }),
        ('ADDM Disabled and excluded from run', {
            'description': "ADDM Useful information. Do not change if not sure!",
            'fields': (
                'disables',
            )
        }),
        ('Optional Information', {
            'classes': ('collapse', 'open'),
            'fields': (
                ('addm_v_int'),
                ('tideway_user', 'tideway_pdw'),
                'vm_cluster',
                'vm_id',
                'description',
            )
        }),
    )


@admin.register(AddmDevProxy)
class AddmDevProxyAdmin(admin.ModelAdmin):
    """ https://djangobook.com/mdj2-django-admin/ """
    # https://djangoguide.readthedocs.io/en/latest/django/admin.html#editable-fields
    list_editable = ('addm_host', 'addm_ip', 'disables', 'addm_name', 'addm_group', 'branch_lock', 'role', 'addm_full_version')
    list_display = ('id', 'addm_host', 'addm_ip', 'disables', 'addm_name', 'addm_group', 'branch_lock', 'role', 'addm_full_version')
    list_filter = ('addm_name', 'addm_group', 'branch_lock', 'role', 'addm_full_version', 'disables',)
    ordering = ('addm_group',)
    search_fields = ('addm_host', 'addm_ip', 'addm_name', 'addm_group')

    fieldsets = (
        ('ADDM Group', {
            'description': "ADDM Group - used for select and threading!",
            'fields': ('addm_group', 'branch_lock', 'role')}),
        ('ADDM Host', {
            'description': "ADDM Useful information. Do not change if not sure!",
            'fields': (
                ('addm_host', 'addm_ip'),
            )
        }),
        ('ADDM Version', {
            'description': "ADDM Useful information. Do not change if not sure!",
            'fields': (
                ('addm_name', 'addm_full_version',),
            )
        }),
        ('ADDM Disabled and excluded from run', {
            'description': "ADDM Useful information. Do not change if not sure!",
            'fields': (
                'disables',
            )
        }),
        ('Optional Information', {
            'classes': ('collapse', 'open'),
            'fields': (
                ('addm_v_int'),
                ('tideway_user', 'tideway_pdw'),
                'description',
            )
        }),
    )


@admin.register(ADDMCommands)
class ADDMCommandsAdmin(admin.ModelAdmin):
    fields = (
        ('command_key', 'command_value',),
        'description',
        'created_at',
        'private',
        'interactive',
    )
    readonly_fields = ('created_at',)
    list_display = ('command_key', 'command_value', 'created_at', 'private', 'interactive')
    list_filter = ('command_key', 'created_at', 'private', 'interactive')
    ordering = ('command_key',)


@admin.register(Options)
class OptionsAdmin(admin.ModelAdmin):
    fields = (
        ('option_key', 'option_value',),
        'description',
        'created_at',
        'private',
    )
    readonly_fields = ('created_at',)
    list_display = ('option_key', 'option_value', 'created_at', 'private',)
    list_filter = ('option_key', 'created_at', 'private')
    ordering = ('option_key',)


@admin.register(MailsTexts)
class MailsTextsAdmin(admin.ModelAdmin):
    fields = (
        ('mail_key', 'subject',),
        'body',
        'description',
        'created_at',
        'private',
    )
    readonly_fields = ('created_at',)
    list_display = ('mail_key', 'subject', 'created_at', 'private',)
    list_filter = ['created_at']
    ordering = ('mail_key',)


@admin.register(TestOutputs)
class TestOutputsAdmin(admin.ModelAdmin):
    fields = (
        ('option_key', 'option_value',),
        'description',
        'created_at',
    )
    readonly_fields = ('created_at',)
    list_display = ('option_key', 'created_at', 'description')
    list_filter = ('created_at',)
    ordering = ('-created_at',)


@admin.register(TestCases)
class TestCasesAdmin(admin.ModelAdmin):
    """ https://djangobook.com/mdj2-django-admin/ """
    show_full_result_count = True

    readonly_fields = ('created_time', 'change_time')

    # https://djangoguide.readthedocs.io/en/latest/django/admin.html#editable-fields
    # list_editable = ('disables',)
    list_display = (
        'test_type',
        'tkn_branch',
        'pattern_library',
        'pattern_folder_name',
        'change',
        'change_user',
        'change_time',
        'test_time_weight',
        'created_time',
        'test_case_depot_path',
        'cases_details_display',
    )

    list_filter = ('test_type', 'tkn_branch', 'pattern_library', 'change_time', 'change_user')

    ordering = ('-created_time',)

    search_fields = (
        'pattern_library', 'pattern_folder_name', 'change_user', 'change_ticket')

    fieldsets = (
        ('Test Type', {
            'fields': ('test_type',)}),

        ('Pattern test object', {
            # 'description': "Path to pattern file in p4 depot, and Octopus FS, with templates for test execution.",
            'description': "Pattern object consists of Pattern Library / Pattern Folder / ",
            'fields':
                (
                    'tkn_branch',
                    'pattern_library',
                    'pattern_folder_name',
                    'pattern_folder_path',
                    'pattern_library_path'
                )
        }),
        ('Pattern change details', {
            'description': "Pattern change - info gathered from 'p4 fstat' and 'p4 change' commands",
            'fields': (
                'change',
                'change_time',
                ('change_user', 'change_review', 'change_ticket', 'test_case_depot_path',),
                ('change_desc',),
            )
        }),
        ('Pattern and test path', {
            'description': "Path to pattern file in p4 depot, and Octopus FS, with templates for test execution.",
            'fields': (
                ('test_py_path', 'test_dir_path',),
                ('test_py_path_template', 'test_dir_path_template',),
                ('test_case_dir',),
            )
        }),
        ('Optional Information', {
            'description': "Pattern and test path on p4 depot, Octopus FS and templates for test execution.",
            'classes': ('collapse', 'open'),
            'fields': (
                'test_time_weight',
                'created_time',
            )
        }),
    )
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '90'})},
        models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 80})},
    }

    list_per_page = 100

    def cases_details_display(self, obj):
        return ", ".join([
            child.title for child in obj.related_test_cases.all()
        ])

    cases_details_display.short_description = "Cases groups"


@admin.register(TestCasesDetails)
class TestCasesDetailsAdmin(admin.ModelAdmin):
    show_full_result_count = True
    readonly_fields = ('pub_date', 'changed_date')
    list_display = (
        'title',
        'author',
        # 'test_cases',
        'description',
        'pub_date',
        'changed_date',
    )
    list_filter = ('title', 'author', 'changed_date')
    search_fields = (
        'title', 'author', 'test_cases')
    ordering = ('-changed_date',)

    fieldsets = (
        ('Test case group and details', {
            'description': "User created custom group of test cases with description",
            'fields':
                (
                    'title',
                    'author',
                    'test_cases',
                    'description',
                    'pub_date',
                    'changed_date',
                )
        }),
    )

    filter_vertical = ('test_cases',)

    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '90'})},
        models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 80})},
        # Not working?
        # models.ManyToManyField: {'widget': SelectMultiple(attrs={'size': '40'})},
    }


# Octopus Tests
@admin.register(TestLast)
class TestLastAdmin(admin.ModelAdmin):
    readonly_fields = ('test_date_time',)

    list_display = (
        'tkn_branch',
        'pattern_library',
        'pattern_folder_name',
        'tst_status',
        'tst_class',
        'tst_name',
        'addm_name',
        'addm_group',
        'time_spent_test',
        'test_date_time'
    )

    list_filter = ('tkn_branch', 'pattern_library', 'addm_name', 'addm_group')

    search_fields = ('pattern_library', 'pattern_folder_name', 'test_py_path', 'tst_status')

    fieldsets = (
        (None, {
            'fields': (
                ('tkn_branch',),
                ('pattern_library', 'pattern_folder_name', ),
                ('test_py_path',),
                ()
            )
        }),
        ('Test results', {
            'fields': (
                'tst_module', 'tst_class', 'tst_name',
                ('tst_message', 'tst_status', 'fail_message'),
            )
        }),
        (None, {
            'fields': (
                ('addm_group', 'addm_name', 'addm_v_int'),
                ('addm_host', 'addm_ip'),
            )
        }),
        (None, {
            'classes': ('collapse', 'open'),
            'fields': (
                'time_spent_test',

                'test_date_time',
            )
        }),
    )
    list_per_page = 100


@admin.register(TestHistory)
class TestHistoryAdmin(admin.ModelAdmin):
    paginator = TimeLimitedPaginator

    readonly_fields = ('test_date_time',)

    list_display = (
        'tkn_branch',
        'pattern_library',
        'pattern_folder_name',
        'tst_status',
        'tst_class',
        'tst_name',
        'addm_name',
        'addm_group',
        # 'time_spent_test',
        'test_date_time'
    )

    list_filter = ('tkn_branch', 'pattern_library', 'addm_name')
    search_fields = ('pattern_library', 'pattern_folder_name', 'test_py_path',
                     'tst_name', 'tst_status')

    fieldsets = (
        (None, {
            'fields': (
                ('tkn_branch',),
                ('pattern_library', 'pattern_folder_name', ),
                ('test_py_path',),
                ()
            )
        }),
        ('Test results', {
            'fields': (
                'tst_module', 'tst_class', 'tst_name',
                ('tst_message', 'tst_status', 'fail_message'),
            )
        }),
        (None, {
            'fields': (
                ('addm_group', 'addm_name', 'addm_v_int'),
                ('addm_host', 'addm_ip'),
            )
        }),
        (None, {
            'classes': ('collapse', 'open'),
            'fields': (
                'time_spent_test',

                'test_date_time',
            )
        }),
    )
    list_per_page = 100


# UPLOAD:
@admin.register(TkuPackagesNew)
class TkuPackagesNewAdmin(admin.ModelAdmin):

    readonly_fields = ('zip_file_md5_digest', 'updated_at', 'created_at', 'release',)

    list_display = (
        'tku_type',
        'package_type',
        'tku_name',
        'addm_version',
        'tku_build',
        'tku_month',
        'tku_date',
        'zip_type',
        'release',
        'zip_file_md5_digest', 'updated_at',
    )
    list_filter = ('tku_type', 'addm_version', 'tku_build', 'zip_type', 'updated_at', 'created_at', 'release',)

    search_fields = ('tku_type', 'addm_version', 'tku_build', 'release')
    fieldsets = (
        (None, {
            'fields': (
                ('tku_type',),
                ('package_type',),
                ('zip_file_name', 'zip_file_path'),
                ('addm_version', 'tku_addm_version',),
                ('tku_build', 'tku_month', 'tku_date',),
                ('zip_type', 'tku_name', 'tku_pack',),
                'zip_file_md5_digest', 'release',
                'updated_at',
                'created_at',
            )
        }),
    )
    list_per_page = 100


@admin.register(UploadTestsNew)
class UploadTestsNewAdmin(admin.ModelAdmin):

    readonly_fields = ('time_spent_test', 'test_date_time')

    list_display = (
        'tku_type',
        'package_type',
        'test_mode',
        'upload_test_status',
        'addm_name',
        'addm_host',
        # 'addm_ip',
        # 'addm_version',
        'mode_key',
        'time_spent_test',
        'test_date_time',
        'zip_file_md5_digest',
        'release',
    )
    list_filter = ('test_mode', 'mode_key', 'package_type', 'tku_type', 'addm_name', 'test_date_time')

    search_fields = ('test_mode', 'mode_key', 'package_type', 'tku_type', 'addm_name', 'release',)

    fieldsets = (
        (None, {
            'fields': (
                (
                    'test_mode',
                    'mode_key'
                ),
                (
                    'tku_type',
                    'package_type',
                    'zip_file_md5_digest',
                    'release',
                ),
                ('upload_test_status',),
                (
                    'upload_test_str_stdout',
                    'upload_test_str_stderr',
                ),
                (
                    'important_out'
                ),
                (
                    'all_errors',
                    'all_warnings',
                    'upload_warnings',
                    'upload_errors',
                ),
                (
                    'tku_statuses',
                ),
                (
                    'addm_name',
                    'addm_v_int',
                    'addm_version',
                    'addm_host',
                    'addm_ip',
                ),
                'time_spent_test',
                'test_date_time',
            )
        }),
    )
    list_per_page = 100


@admin.register(CeleryTaskmeta)
class CeleryTaskmetaAdmin(admin.ModelAdmin):
    fields = (
        ('task_id', 'status',),
        ('result', 'traceback',),
        'date_done',
    )
    list_display = ('task_id', 'status', 'date_done')
    list_filter = ('status', 'date_done')

@admin.register(DjangoContentType)
class DjangoContentTypeAdmin(admin.ModelAdmin):
    fields = (
        ('id', 'app_label',),
        ('model',)
    )
    list_display = ('app_label', 'model')
    list_filter = ('app_label', 'model')

@admin.register(DjangoMigrations)
class DjangoMigrationsAdmin(admin.ModelAdmin):
    fields = (
        ('id', 'app',),
        ('name',),
        ('applied',),
    )
    list_display = ('id', 'app', 'name', 'applied')
    list_filter = ('id', 'app', 'name', 'applied')

admin.site.register(CeleryTasksetmeta)
# admin.site.register(FTPUserGroup)
# admin.site.register(FTPUserAccount)
