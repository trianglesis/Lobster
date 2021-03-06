# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from __future__ import unicode_literals

import pickle

from django.db import models

"""THOSE ARE ONLY FOR DEBUG:"""


class OctoCacheStore(models.Model):
    name = models.CharField(blank=True, null=True, max_length=155)
    key = models.CharField(max_length=155)
    hashed = models.CharField(unique=True, max_length=100)
    query = models.TextField(blank=True, null=True)
    ttl = models.IntegerField(blank=True, null=True)
    counter = models.IntegerField(default=0)
    created_time = models.DateTimeField(
        unique=False, auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'octo_cache_store'
        indexes = [
            models.Index(fields=['hashed'], name='item_hashed'),
            models.Index(fields=['key'], name='item_key'),
        ]


class CeleryTaskmeta(models.Model):
    task_id = models.CharField(unique=True, max_length=155, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    result = models.BinaryField(blank=True, null=True)
    date_done = models.DateTimeField(blank=True, null=True)

    traceback = models.TextField(blank=True, null=True)

    name = models.CharField(max_length=155, blank=True, null=True)

    args = models.BinaryField(blank=True, null=True)
    kwargs = models.BinaryField(blank=True, null=True)

    worker = models.CharField(max_length=155, blank=True, null=True)
    retries = models.IntegerField(blank=True, null=True)
    queue = models.CharField(max_length=155, blank=True, null=True)

    # def get_kwargs(self):
    #     if self.kwargs:
    #         kwargs_p = pickle.loads(self.kwargs)
    #     else:
    #         kwargs_p = ''
    #     print(f"Kwargs{kwargs_p}")
    #     return str(kwargs_p)

    class Meta:
        managed = True
        db_table = 'celery_taskmeta'


class CeleryTasksetmeta(models.Model):
    taskset_id = models.CharField(unique=True, max_length=155, blank=True, null=True)
    result = models.BinaryField(blank=True, null=True)
    date_done = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'celery_tasksetmeta'
