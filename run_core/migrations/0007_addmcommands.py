# Generated by Django 2.2.1 on 2019-11-27 14:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('run_core', '0006_auto_20191113_1447'),
    ]

    operations = [
        migrations.CreateModel(
            name='ADDMCommands',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('command_key', models.CharField(max_length=120, unique=True, verbose_name='command key unique')),
                ('command_value', models.TextField(blank=True, null=True, verbose_name='command value')),
                ('private', models.NullBooleanField(verbose_name='private value')),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'octo_addm_commands',
                'managed': True,
            },
        ),
    ]