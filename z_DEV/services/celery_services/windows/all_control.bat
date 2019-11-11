celery -A octo.octo_celery:app inspect active
celery -A octo.octo_celery:app inspect reserved
celery -A octo.octo_celery:app control heartbeat
celery -A octo.octo_celery:app control pool_restart
celery -A octo.octo_celery:app control shutdown
celery -A octo.octo_celery:app purge
celery -A octo.octo_celery:app list