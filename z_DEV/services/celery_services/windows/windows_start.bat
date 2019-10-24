D:\perforce\addm\tkn_sandbox\o.danylchenko\projects\PycharmProjects\lobster\venv\Scripts
D:\perforce\addm\tkn_sandbox\o.danylchenko\projects\PycharmProjects\lobster\

celery -A octo.octo_celery:app worker --loglevel=INFO --concurrency=1 -E -n w_parsing@tentacle &
celery -A octo.octo_celery:app worker --loglevel=INFO --concurrency=1 -E -n w_routines@tentacle &
celery -A octo.octo_celery:app worker --loglevel=INFO --concurrency=1 -E -n alpha@tentacle &
celery -A octo.octo_celery:app worker --loglevel=INFO --concurrency=1 -E -n charlie@tentacle &
celery flower --broker=amqp://octo_user:hPoNaEb7@localhost:5672/tentacle --broker_api=http://octo_user:hPoNaEb7@localhost:15672/api/