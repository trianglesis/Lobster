# Generated by Django 2.2.1 on 2019-11-12 17:24

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('run_core', '0004_auto_20190531_0909'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestOutputs',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('option_key', models.CharField(max_length=255, unique=True)),
                ('option_value', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('description', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'dev_octo_test_outputs',
                'managed': True,
            },
        ),
        migrations.AlterField(
            model_name='useradprod',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='user_profile', to=settings.AUTH_USER_MODEL),
        ),
    ]