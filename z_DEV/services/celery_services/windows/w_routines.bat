D:\perforce\addm\tkn_sandbox\o.danylchenko\projects\PycharmProjects\lobster\venv\Scripts\activate.bat && activate.bat && celery -A octo.octo_celery:app worker --pool=eventlet --loglevel=INFO --concurrency=1 -E -n w_routines@tentacle