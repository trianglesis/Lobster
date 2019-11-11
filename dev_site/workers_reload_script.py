if __name__ == "__main__":
    import django
    django.setup()
    import logging
    from octo.octo_celery import app
    log = logging.getLogger("octo.octologger")


def worker_restart(**kwargs):
    """
    Control.pool_restart(modules=None, reload=False, reloader=None, destination=None, **kwargs)[source]
    Restart the execution pools of all or specific workers.

   Keyword Arguments:
        modules (Sequence[str]): List of modules to reload.
        reload (bool): Flag to enable module reloading.  Default is False.
        reloader (Any): Function to reload a module.
        destination (Sequence[str]): List of worker names to send this
            command to.

    :param kwargs:
    :return:
    """
    worker_list = kwargs.get("worker_list", None)  # leave old param here, somewhere it still be used!
    workers = kwargs.get("workers", None)
    my_modules = ['octo.tasks', 'octo_adm.tasks', 'octo_tku_patterns.tasks', 'octo_tku_upload.tasks']

    # TODO: Remove when ready.
    if worker_list:
        workers = worker_list

    if workers and isinstance(workers, list):
        w_restart = app.control.pool_restart(modules=my_modules, destination=workers, reload=True)
        log.info("<=WorkerOperations=> Executing worker_restart(%s): w_restart - %s", workers, w_restart)
    else:
        w_restart = app.control.pool_restart(modules=my_modules, reload=True)
        log.info("<=WorkerOperations=> Executing worker_restart() for all: %s", w_restart)
    return w_restart


w_list = [
    'alpha@tentacle',
    'charlie@tentacle',
    'golf@tentacle',
    'w_parsing@tentacle',
    'w_routines@tentacle',
]
w_restart = worker_restart(worker_list=w_list)
