# Generated by Django 2.2.1 on 2019-11-13 12:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('run_core', '0005_auto_20191112_1924'),
    ]

    operations = [
        migrations.AlterField(
            model_name='testoutputs',
            name='option_key',
            field=models.CharField(max_length=255),
        ),
    ]
