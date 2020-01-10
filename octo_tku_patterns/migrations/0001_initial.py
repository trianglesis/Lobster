# Generated by Django 2.2.1 on 2019-10-01 09:51

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TestCases',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('test_type', models.CharField(max_length=120)),
                ('tkn_branch', models.CharField(blank=True, max_length=10, null=True)),
                ('pattern_library', models.CharField(blank=True, max_length=120, null=True)),
                ('pattern_folder_name', models.CharField(blank=True, max_length=120, null=True)),
                ('pattern_folder_path', models.CharField(blank=True, max_length=255, null=True)),
                ('pattern_library_path', models.CharField(blank=True, max_length=255, null=True)),
                ('test_case_dir', models.CharField(max_length=120)),
                ('change', models.CharField(blank=True, max_length=20, null=True)),
                ('change_desc', models.TextField(blank=True, null=True)),
                ('change_user', models.CharField(blank=True, max_length=20, null=True)),
                ('change_review', models.CharField(blank=True, max_length=20, null=True)),
                ('change_ticket', models.CharField(blank=True, max_length=20, null=True)),
                ('change_time', models.DateTimeField(blank=True, null=True)),
                ('test_case_depot_path', models.CharField(max_length=255)),
                ('test_py_path', models.CharField(max_length=255, unique=True)),
                ('test_py_path_template', models.CharField(max_length=255)),
                ('test_dir_path', models.CharField(max_length=255)),
                ('test_dir_path_template', models.CharField(max_length=255)),
                ('test_time_weight', models.CharField(blank=True, max_length=35, null=True)),
                ('created_time', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'octo_test_cases',
                'ordering': ['-change_time'],
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='TestLast',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tkn_branch', models.CharField(max_length=10)),
                ('pattern_library', models.CharField(max_length=255)),
                ('pattern_file_name', models.CharField(max_length=255)),
                ('pattern_folder_name', models.CharField(max_length=255)),
                ('pattern_file_path', models.CharField(blank=True, max_length=255, null=True)),
                ('test_py_path', models.CharField(blank=True, max_length=255, null=True)),
                ('pattern_folder_path_depot', models.CharField(blank=True, max_length=255, null=True)),
                ('pattern_file_path_depot', models.TextField(blank=True, null=True)),
                ('is_key_pattern', models.NullBooleanField()),
                ('tst_message', models.TextField(blank=True, null=True)),
                ('tst_name', models.CharField(max_length=255)),
                ('tst_module', models.CharField(max_length=255)),
                ('tst_class', models.CharField(max_length=255)),
                ('tst_status', models.TextField(blank=True, null=True)),
                ('fail_status', models.TextField(blank=True, null=True)),
                ('fail_name', models.TextField(blank=True, null=True)),
                ('fail_module', models.TextField(blank=True, null=True)),
                ('fail_class', models.TextField(blank=True, null=True)),
                ('fail_message', models.TextField(blank=True, null=True)),
                ('addm_name', models.CharField(max_length=20)),
                ('addm_group', models.CharField(max_length=10)),
                ('addm_v_int', models.CharField(blank=True, max_length=20, null=True)),
                ('addm_host', models.CharField(max_length=50)),
                ('addm_ip', models.CharField(blank=True, max_length=20, null=True)),
                ('time_spent_test', models.CharField(blank=True, max_length=20, null=True)),
                ('test_date_time', models.DateTimeField(auto_now_add=True, unique=True)),
            ],
            options={
                'db_table': 'octo_test_last',
                'managed': True,
                # 'unique_together': {('tkn_branch', 'pattern_library', 'pattern_folder_name', 'pattern_file_name', 'tst_name', 'tst_module', 'tst_class', 'test_date_time', 'addm_name', 'addm_host')},
            },
        ),
        migrations.CreateModel(
            name='TestHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tkn_branch', models.CharField(max_length=10)),
                ('pattern_library', models.CharField(max_length=255)),
                ('pattern_file_name', models.CharField(max_length=255)),
                ('pattern_folder_name', models.CharField(max_length=255)),
                ('pattern_file_path', models.CharField(blank=True, max_length=255, null=True)),
                ('test_py_path', models.CharField(blank=True, max_length=255, null=True)),
                ('pattern_folder_path_depot', models.CharField(blank=True, max_length=255, null=True)),
                ('pattern_file_path_depot', models.TextField(blank=True, null=True)),
                ('is_key_pattern', models.NullBooleanField()),
                ('tst_message', models.TextField(blank=True, null=True)),
                ('tst_name', models.CharField(max_length=255)),
                ('tst_module', models.CharField(max_length=255)),
                ('tst_class', models.CharField(max_length=255)),
                ('tst_status', models.TextField(blank=True, null=True)),
                ('fail_status', models.TextField(blank=True, null=True)),
                ('fail_name', models.TextField(blank=True, null=True)),
                ('fail_module', models.TextField(blank=True, null=True)),
                ('fail_class', models.TextField(blank=True, null=True)),
                ('fail_message', models.TextField(blank=True, null=True)),
                ('addm_name', models.CharField(max_length=20)),
                ('addm_group', models.CharField(max_length=10)),
                ('addm_v_int', models.CharField(blank=True, max_length=20, null=True)),
                ('addm_host', models.CharField(max_length=50)),
                ('addm_ip', models.CharField(blank=True, max_length=20, null=True)),
                ('time_spent_test', models.CharField(blank=True, max_length=20, null=True)),
                ('test_date_time', models.DateTimeField(auto_now_add=True, unique=True)),
            ],
            options={
                'db_table': 'octo_test_history',
                'managed': True,
                # 'unique_together': {('tkn_branch', 'pattern_library', 'pattern_folder_name', 'pattern_file_name', 'tst_name', 'tst_module', 'tst_class', 'test_date_time', 'addm_name', 'addm_host')},
            },
        ),
        migrations.CreateModel(
            name='TestCasesDetails',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('pub_date', models.DateTimeField(auto_now_add=True)),
                ('changed_date', models.DateTimeField(auto_now=True)),
                ('author', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('test_cases', models.ManyToManyField(related_name='related_test_cases', to='octo_tku_patterns.TestCases')),
            ],
            options={
                'db_table': 'octo_test_cases_details',
                'managed': True,
            },
        ),
    ]