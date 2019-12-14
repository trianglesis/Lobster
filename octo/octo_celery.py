"""
Separate Celery settings file

"""

from __future__ import absolute_import, unicode_literals
import os
import django

from celery import Celery
from kombu import Exchange
from octo.config_cred import cred

# set the default Django settings module for the 'celery' program.
if not os.name == "nt":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'octo.settings')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'octo.win_settings')
# Setup django project
django.setup()
# curr_hostname = getattr(settings, 'CURR_HOSTNAME', None)
#  The backend is specified via the backend argument to Celery,
#  (or via the result_backend setting if you choose to use a configuration module):
app = Celery('octo',
             # http://docs.celeryproject.org/en/latest/userguide/optimizing.html
             broker=cred['broker'],

             # http://docs.celeryproject.org/en/latest/userguide/configuration.html#result-backend
             backend=cred['backend'],
             )

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
# app.config_from_object('django.conf:settings', namespace='CELERY')
#  The backend is specified via the backend argument to Celery,
#  (or via the result_backend setting if you choose to use a configuration module):
# https://docs.celeryproject.org/en/master/userguide/configuration.html

"""
LOBSTER:
"""

app.conf.timezone = 'UTC'
app.conf.enable_utc = True
app.autodiscover_tasks()  # Load task modules from all registered Django app configs.
default_exchange = Exchange('default', type='direct', durable=False)

app.conf.update(
    accept_content=['json', 'pickle', 'application/x-python', 'application/json', 'application/x-python-serialize'],
    task_serializer='pickle',
    result_serializer='json',  # https://docs.celeryproject.org/en/master/userguide/calling.html#calling-serializers
    result_extended=True,  # https://docs.celeryproject.org/en/master/userguide/configuration.html#result-extended
    # Do not set! Or logic will not wait of task OK: # task_ignore_result=True,
    # task_track_started = True,

    # http://docs.celeryproject.org/en/latest/userguide/configuration.html#result-backend
    # http://docs.celeryproject.org/en/latest/userguide/configuration.html#database-url-examples
    # https://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html#keeping-results
    # 1406, "Data too long for column 'result' at row 1" - it's not so important to keep it in DB
    result_backend = cred['result_backend'],
    database_engine_options = {'pool_timeout': 90},

    # http://docs.celeryproject.org/en/latest/userguide/configuration.html#beat-scheduler
    beat_scheduler='django_celery_beat.schedulers:DatabaseScheduler',

    # http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-default-queue
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    task_default_exchange_type='direct',

    task_default_delivery_mode='transient',  # https://docs.celeryproject.org/en/master/userguide/configuration.html#task-default-delivery-mode
    task_create_missing_queues=True,  # By Default  # http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-create-missing-queues

    # http://docs.celeryproject.org/en/latest/userguide/configuration.html#worker-prefetch-multiplier
    worker_prefetch_multiplier=100,  # Keep 100, to lower RAM consume and keep most in RabbitMQ

    worker_disable_rate_limits=True,
    worker_concurrency=1,  # https://docs.celeryproject.org/en/master/userguide/configuration.html#worker-concurrency
    worker_lost_wait=30,  # https://docs.celeryproject.org/en/master/userguide/configuration.html#worker-lost-wait
    worker_max_memory_per_child=120000,  # 120 MB X 10 = 1200 MB
    worker_max_tasks_per_child=100,  # https://docs.celeryproject.org/en/master/userguide/configuration.html#worker-max-tasks-per-child

    # Useful
    # https://docs.celeryproject.org/en/master/userguide/configuration.html#worker-log-format
    worker_timer_precision=5,  # https://docs.celeryproject.org/en/master/userguide/configuration.html#worker-timer-precision
    worker_enable_remote_control=True,  # https://docs.celeryproject.org/en/master/userguide/configuration.html#worker-enable-remote-control
    # task_send_sent_event=True,  # https://docs.celeryproject.org/en/master/userguide/configuration.html#task-send-sent-event
    worker_send_task_events=True,  # -E at worker service # http://docs.celeryproject.org/en/latest/userguide/configuration.html#events
    worker_pool_restarts=True,

    # Maybe this should be disabled to allow workers to get ALL tasks in queue.
    task_acks_late=False,  # By Default # http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-task_acks_late
    acks_late=False,  # http://docs.celeryproject.org/en/master/faq.html#faq-acks-late-vs-retry
    task_acks_on_failure_or_timeout=True,  # http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-acks-on-failure-or-timeout
    # Setting this to true allows the message to be re-queued instead, so that the task will execute again by the same worker, or another worker.
    task_reject_on_worker_lost=False,  # http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-reject-on-worker-lost

    broker_pool_limit=None,  # http://docs.celeryproject.org/en/latest/userguide/configuration.html#broker-pool-limit

    # http://docs.celeryproject.org/en/latest/userguide/configuration.html#broker-connection-timeout
    broker_connection_timeout=60,
    broker_connection_retry=True,
    broker_connection_max_retries=0,

    worker_direct=True,  # http://docs.celeryproject.org/en/latest/userguide/configuration.html#worker-direct

)

if not os.name == "nt":
    app.control.cancel_consumer(
        'default',
        destination=[
            'w_routines@tentacle',
            'alpha@tentacle',
            'beta@tentacle',
            'charlie@tentacle',
            'delta@tentacle',
            'echo@tentacle',
            'foxtrot@tentacle',
            'golf@tentacle',
            'w_development@tentacle',
        ])
else:
    app.control.cancel_consumer(
        'default',
        destination=[
            'w_routines@tentacle',
            'alpha@tentacle',
            'beta@tentacle',
            'charlie@tentacle',
            'delta@tentacle',
            'echo@tentacle',
            'foxtrot@tentacle',
            'golf@tentacle',
            'w_development@tentacle',
        ])
