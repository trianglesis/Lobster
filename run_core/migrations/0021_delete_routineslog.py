# Generated by Django 3.1rc1 on 2020-07-27 11:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('run_core', '0020_delete_serviceslog'),
    ]

    operations = [
        migrations.DeleteModel(
            name='RoutinesLog',
        ),
    ]
