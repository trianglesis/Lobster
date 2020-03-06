# Generated by Django 2.2.1 on 2020-03-06 16:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('run_core', '0014_auto_20200207_1737'),
    ]

    operations = [
        migrations.CreateModel(
            name='RoutinesLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_name', models.CharField(max_length=255)),
                ('t_args', models.TextField(blank=True, null=True)),
                ('t_kwargs', models.TextField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('input', models.TextField(blank=True, null=True)),
                ('out', models.TextField(blank=True, null=True)),
                ('err', models.TextField(blank=True, null=True)),
                ('raw', models.TextField(blank=True, null=True)),
                ('t_start_time', models.DateTimeField(null=True)),
                ('t_finish_time', models.DateTimeField(null=True)),
                ('t_est_time', models.DurationField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'octo_routines_log',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='ServicesLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_name', models.CharField(max_length=255)),
                ('t_args', models.TextField(blank=True, null=True)),
                ('t_kwargs', models.TextField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('input', models.TextField(blank=True, null=True)),
                ('out', models.TextField(blank=True, null=True)),
                ('err', models.TextField(blank=True, null=True)),
                ('raw', models.TextField(blank=True, null=True)),
                ('t_start_time', models.DateTimeField(null=True)),
                ('t_finish_time', models.DateTimeField(null=True)),
                ('t_est_time', models.DurationField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'octo_service_log',
                'managed': True,
            },
        ),
        migrations.DeleteModel(
            name='RoutineExecutionLog',
        ),
        migrations.DeleteModel(
            name='ServiceLog',
        ),
    ]
