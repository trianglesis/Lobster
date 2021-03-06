# Generated by Django 2.2.1 on 2020-07-10 09:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('octo', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OctoCacheStore',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=155, null=True)),
                ('key', models.CharField(max_length=155)),
                ('hashed', models.CharField(max_length=100, unique=True)),
                ('query', models.TextField(blank=True, null=True)),
                ('ttl', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'octo_cache_store',
                'managed': True,
            },
        ),
    ]
