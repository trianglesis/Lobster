# Generated by Django 2.2.1 on 2019-11-13 15:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('octo_tku_upload', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='uploadtestsnew',
            name='tested_zips',
        ),
        migrations.RemoveField(
            model_name='uploadtestsnew',
            name='tku_build',
        ),
        migrations.RemoveField(
            model_name='uploadtestsnew',
            name='tku_date',
        ),
        migrations.RemoveField(
            model_name='uploadtestsnew',
            name='tku_month',
        ),
        migrations.AlterField(
            model_name='uploadtestsnew',
            name='mode_key',
            field=models.CharField(max_length=100),
        ),
    ]
