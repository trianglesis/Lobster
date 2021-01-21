"""
https://www.django-rest-framework.org/tutorial/quickstart/
"""

import pickle

from rest_framework.pagination import PageNumberPagination
from rest_framework import serializers

from octo.models import CeleryTaskmeta
from django_celery_beat.models import PeriodicTask

from django.contrib.auth import get_user_model

import logging
log = logging.getLogger("octo.octologger")

User = get_user_model()


class LargeResultsSetPagination(PageNumberPagination):
    page_size = 1000
    page_size_query_param = 'page_size'
    max_page_size = 3000


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class ShortResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class CeleryTaskmetaSerializer(serializers.ModelSerializer):
    task_args = serializers.SerializerMethodField()
    # NOTE: Object of type ADDMCommands is not JSON serializable
    task_kwargs = serializers.SerializerMethodField()
    task_result = serializers.SerializerMethodField()

    class Meta:
        model = CeleryTaskmeta
        fields = (
            'id',
            'task_id',
            'name',
            'status',

            # 'result',
            'task_result',

            'date_done',

            # 'args',
            'task_args',

            # 'kwargs',
            'task_kwargs',

            'worker',
            'retries',
            'queue',

            # Object of type Exception is not JSON serializable
            # 'traceback',
        )

    @staticmethod
    def get_task_status(obj):
        return obj.status

    @staticmethod
    def get_task_args(obj):
        args_p = pickle.loads(obj.args)
        return str(args_p)

    @staticmethod
    def get_task_kwargs(obj):
        kwargs_p = pickle.loads(obj.kwargs)
        return str(kwargs_p)

    @staticmethod
    def get_task_result(obj):
        result_p = pickle.loads(obj.result)
        return str(result_p)


class PeriodicTaskSerializer(serializers.ModelSerializer):
    # # TODO: Add cron, interval values
    # interval = serializers.SerializerMethodField()
    # crontab = serializers.SerializerMethodField()
    # solar = serializers.SerializerMethodField()

    class Meta:
        model = PeriodicTask
        fields = (
            'id',
            'name',
            'task',
            'interval',
            'crontab',
            'solar',
            'args',
            'kwargs',
            'queue',
            'exchange',
            'routing_key',
            'priority',
            'expires',
            'one_off',
            'start_time',
            'enabled',
            'last_run_at',
            'total_run_count',
            'date_changed',
            'description',
        )

    # # Example method:
    # def get_interval(self, obj):
    #     log.debug("PeriodicTaskSerializer -> get_interval!")
    #     user = self.context.get('request').user
    #     return services.PeriodicSchedulers.get_interval(obj, user)
    #
    # def get_crontab(self, obj):
    #     log.debug("PeriodicTaskSerializer -> get_crontab!")
    #     user = self.context.get('request').user
    #     return services.PeriodicSchedulers.get_crontab(obj, user)
    #
    # def get_solar(self, obj):
    #     log.debug("PeriodicTaskSerializer -> get_solar!")
    #     user = self.context.get('request').user
    #     return services.PeriodicSchedulers.get_solar(obj, user)
