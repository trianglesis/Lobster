import json
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from django_celery_beat.models import IntervalSchedule, CrontabSchedule, SolarSchedule

import logging
log = logging.getLogger("octo.octologger")

User = get_user_model()


class PeriodicSchedulers:

    @staticmethod
    def get_interval(p_task_obj, user):
        interval = IntervalSchedule.objects.filter(periodictask=p_task_obj).values()
        json_posts = json.dumps(list(interval))
        log.debug("interval: %s", json_posts)
        return json_posts

    def get_crontab(p_task_obj, user):
        crontab = CrontabSchedule.objects.filter(periodictask=p_task_obj).values()
        log.debug("crontab: %s", crontab)
        return crontab

    def get_solar(p_task_obj, user):
        solar = SolarSchedule.objects.filter(periodictask=p_task_obj).values()
        log.debug("solar: %s", solar)
        return solar