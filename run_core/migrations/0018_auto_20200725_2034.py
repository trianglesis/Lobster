# Generated by Django 3.1rc1 on 2020-07-25 19:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('run_core', '0017_auto_20200717_0722'),
    ]

    operations = [
        migrations.AlterField(
            model_name='addmcommands',
            name='interactive',
            field=models.BooleanField(null=True, verbose_name='interactive mode'),
        ),
        migrations.AlterField(
            model_name='addmcommands',
            name='private',
            field=models.BooleanField(null=True, verbose_name='private value'),
        ),
        migrations.AlterField(
            model_name='addmdev',
            name='disables',
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name='mailstexts',
            name='private',
            field=models.BooleanField(null=True, verbose_name='private value'),
        ),
        migrations.AlterField(
            model_name='options',
            name='private',
            field=models.BooleanField(null=True, verbose_name='private value'),
        ),
    ]
