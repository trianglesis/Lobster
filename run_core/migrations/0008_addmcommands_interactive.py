# Generated by Django 2.2.1 on 2019-12-17 15:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('run_core', '0007_addmcommands'),
    ]

    operations = [
        migrations.AddField(
            model_name='addmcommands',
            name='interactive',
            field=models.NullBooleanField(verbose_name='interactive mode'),
        ),
    ]
