# Generated by Django 2.2.1 on 2020-07-16 08:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('run_core', '0015_auto_20200306_1604'),
    ]

    operations = [
        migrations.AlterField(
            model_name='routineslog',
            name='t_est_time',
            field=models.DurationField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='serviceslog',
            name='t_est_time',
            field=models.DurationField(blank=True, null=True),
        ),
    ]
