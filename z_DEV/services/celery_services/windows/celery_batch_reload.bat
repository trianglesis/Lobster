D:\perforce\addm\tkn_sandbox\o.danylchenko\projects\PycharmProjects\lobster\venv\Scripts\celery.exe -A octo.octo_celery:app control pool_restart
D:\perforce\addm\tkn_sandbox\o.danylchenko\projects\PycharmProjects\lobster\venv\Scripts\celery.exe -A octo.octo_celery:app control heartbeat
D:\perforce\addm\tkn_sandbox\o.danylchenko\projects\PycharmProjects\lobster\venv\Scripts\celery.exe -A octo.octo_celery:app inspect ping


D:\Projects\PycharmProjects\lobster\venv\Scripts\celery.exe -A octo.octo_celery:app worker --pool=eventlet --loglevel=INFO --concurrency=1 -E -n alpha@tentacle
D:\Projects\PycharmProjects\lobster\venv\Scripts\celery.exe -A octo.octo_celery:app worker --pool=eventlet --loglevel=INFO --concurrency=1 -E -n charlie@tentacle
D:\Projects\PycharmProjects\lobster\venv\Scripts\celery.exe -A octo.octo_celery:app worker --pool=eventlet --loglevel=INFO --concurrency=1 -E -n delta@tentacle
D:\Projects\PycharmProjects\lobster\venv\Scripts\celery.exe -A octo.octo_celery:app worker --pool=eventlet --loglevel=INFO --concurrency=1 -E -n w_parsing@tentacle
D:\Projects\PycharmProjects\lobster\venv\Scripts\celery.exe -A octo.octo_celery:app worker --pool=eventlet --loglevel=INFO --concurrency=1 -E -n w_routines@tentacle
D:\Projects\PycharmProjects\lobster\venv\Scripts\celery.exe -A octo.octo_celery:app worker --pool=eventlet --loglevel=INFO --concurrency=1 -E -n alpha@tentacle