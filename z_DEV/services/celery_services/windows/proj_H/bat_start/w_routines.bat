D:\Projects\PycharmProjects\lobster\venv\Scripts\activate.bat && celery -A octo.octo_celery:app worker --pool=eventlet --loglevel=INFO --concurrency=1 --purge -E -n w_routines@tentacle