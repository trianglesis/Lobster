# Generated by Django 3.1rc1 on 2020-07-26 11:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('run_core', '0018_auto_20200723_1143'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskPrepareLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(max_length=255)),
                ('user_email', models.CharField(max_length=255)),
                ('details', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'octo_task_prep_log',
                'managed': True,
            },
        ),
    ]
