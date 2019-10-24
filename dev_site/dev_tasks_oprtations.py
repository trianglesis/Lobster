from typing import List, Any, Dict

if __name__ == "__main__":
    import logging
    import django
    import sys

    django.setup()
    from octo.octo_celery import app

    log = logging.getLogger("octo.octologger")
    log.info("\n\n\n\n\nRun DevTasksOper")

    class recursionlimit:
        def __init__(self, limit):
            self.limit = limit
            self.old_limit = sys.getrecursionlimit()

        def __enter__(self):
            sys.setrecursionlimit(self.limit)

        def __exit__(self, type, value, tb):
            sys.setrecursionlimit(self.old_limit)

    class DevTasksOper:

        @staticmethod
        def tasks_inspect(workers_list=None):
            if workers_list:
                inspect = app.control.inspect(workers_list)
            else:
                inspect = app.control.inspect()
            return inspect

        def tasks_active(self, inspected, workers_list=None):
            if not inspected:
                inspected = self.tasks_inspect(workers_list)
            t_active = inspected.active()
            return t_active

        def tasks_reserved(self, inspected, workers_list=None):
            if not inspected:
                inspected = self.tasks_inspect(workers_list)
            t_reserved = inspected.reserved()
            return t_reserved

        def list_tasks_ids(self, active=False, workers_list=None):
            all_tasks_ids = []

            inspect = self.tasks_inspect(workers_list)
            t_reserved = inspect.reserved()

            log.debug("<=Tasks Len => t_reserved: %s", len(t_reserved))

            for _, worker_v in t_reserved.items():
                for task in worker_v:
                    all_tasks_ids.append(task['id'])

            if active:
                t_active = inspect.active()
                log.debug("<=Tasks Len => t_active: %s", len(t_active))
                for _, worker_v in t_active.items():
                    for task in worker_v:
                        all_tasks_ids.append(task['id'])

            log.debug("All tasks active and reserved len: %s", len(all_tasks_ids))
            return all_tasks_ids

        @staticmethod
        def revoke_ids_l(tasks_ids_list):
            log.info("About to revoke %s task(s)", len(tasks_ids_list))
            app.control.revoke(tasks_ids_list)

        def revoke_all_tasks(self):
            log.info("Will revoke all active and reserved tasks!")
            all_t = self.list_tasks_ids()
            with recursionlimit(int(len(all_t))):
                self.revoke_ids_l(all_t)
            log.info("Revoking all tasks job has finished it's run!")

    DevTasksOper().revoke_all_tasks()