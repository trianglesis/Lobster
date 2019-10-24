from typing import List, Any, Dict

if __name__ == "__main__":
    import logging
    import django

    django.setup()

    import datetime
    from run_core.models import Options
    from octo.helpers.tasks_mail_send import Mails
    from octo.helpers.tasks_oper import TasksOperations, WorkerOperations
    from octo_tku_patterns.tasks import PatternRoutineCases
    # from octo.helpers.tasks_run import Runner
    from octo.helpers.tasks_run import Runner
    from octo.config_cred import mails

    log = logging.getLogger("octo.octologger")
    log.info("\n\n\n\n\nRun dev_site/test_task_user_balancer_branch.py")

    class WorkerGetAvailable:

        @staticmethod
        def branched_w(branch):
            """
            Select only workers are related to branch
            :type branch: str
            """

            tkn_main_w = Options.objects.get(option_key__exact='branch_workers.tkn_main')
            tkn_ship_w = Options.objects.get(option_key__exact='branch_workers.tkn_ship')

            tkn_main_w = tkn_main_w.option_value.replace(' ', '').split(',')
            tkn_ship_w = tkn_ship_w.option_value.replace(' ', '').split(',')

            workers: Dict[Any, List[str]] = dict(
                tkn_main = list(tkn_main_w),
                tkn_ship = list(tkn_ship_w))
            return workers.get(branch, [])

        @staticmethod
        def excluded_w():
            """
            Select from octopus Options table the list of workers exluded from user test execution.
            :return:
            """
            excluded_option = Options.objects.get(option_key__exact='workers_excluded_list')
            return excluded_option.option_value.replace(' ', '').split(',')

        @staticmethod
        def actualize_w(branch_w, excluded_w):
            """
            Sort out excluded workers from the list of available workers.
            - Add @tentacle to worker name for celery operations. Will replace later.
            :type excluded_w: list
            :type branch_w: list
            """
            actualized_w: List[str] = []
            for w in branch_w:
                if w not in excluded_w:
                    actualized_w.append('{}@tentacle'.format(w))
            return actualized_w

        @staticmethod
        def ping_actual_w(actual_w):
            """
            Ping only included workers, append only worker which responds.
            :type actual_w: list
            """
            w_down = []
            running_w: List[str] = []
            worker_up = WorkerOperations().worker_ping_alt(worker_list=actual_w)
            for w_key, w_val in worker_up.items():
                if 'pong' in w_val:
                    running_w.append(w_key)
                else:
                    w_down.append("Worker is down {}:{}".format(w_key, w_val))

            admin = mails['admin']
            if w_down:
                log.error("Some workers may be down: %s - sending email!", w_down)
                subject = 'Currently some workers are DOWN!'
                body = '''Found some workers are DOWN while run User test pre-checks. List: {}'''.format(w_down)
                Mails.short(subject=subject, body=body, send_to=[admin])

            return running_w

        @staticmethod
        def inspect_w(running_w):
            """
            Get workers tasks: running and reserved.
            :type running_w: List[str]
            """
            inspected = TasksOperations().check_active_reserved_short(workers_list=running_w, tasks_body=True)
            return inspected

        @staticmethod
        def not_locked_w(inspected):
            """
            Exclude workers where task has a lock key in name or args.
            :type inspected: list
            """
            excl = 'lock=True'
            included_list: List[Dict] = []
            for worker in inspected:
                for w_key, w_val in worker.items():
                    all_tasks = w_val.get('all_tasks')
                    if any(excl in d.get('args') for d in all_tasks) or any(excl in d.get('name') for d in all_tasks):
                        log.debug("Exclude worker due task lock: %s", w_key)
                        break
                    else:
                        if worker not in included_list:
                            included_list.append(worker)
            return included_list

        @staticmethod
        def min_w(not_busy_w):
            """
            Get worker with minimal count of active/reserved tasks.
            - Replacing @tentacle from worker name to get addm_group name.
            :type not_busy_w: list
            """
            w_dict: Dict[str, int] = dict()
            for worker in not_busy_w:
                for w_key, w_val in worker.items():
                    w_dict.update({w_key: w_val.get('all_tasks_len')})
            log.debug("All available workers: %s", w_dict)
            worker_min = min(w_dict, key=w_dict.get)
            if '@tentacle' in worker_min:
                worker_min = worker_min.replace('@tentacle', '')
            return worker_min

        def user_test_available_w(self, branch, user_mail):
            log.info("<=WorkerGetAvailable=> Getting available worker to run test for branch %s", branch)

            branch_w = self.branched_w(branch)
            log.debug("<=WorkerGetAvailable=> Branch w: %s = %s", branch, branch_w)

            excluded_w = self.excluded_w()
            log.debug("<=WorkerGetAvailable=> Workers excluded: %s", excluded_w)

            actual_w = self.actualize_w(branch_w, excluded_w)
            if actual_w:
                log.debug("<=WorkerGetAvailable=> Actualized w: %s", actual_w)
                running_w = self.ping_actual_w(actual_w)

                if running_w:
                    log.debug("<=WorkerGetAvailable=> : Running w: %s", running_w)

                    inspected_w = self.inspect_w(running_w)
                    # Do not show debug - it will output all reserved tasks!!!
                    # log.debug("<=WorkerGetAvailable=> Inspected w: %s", inspected_w)

                    not_locked_w = self.not_locked_w(inspected_w)
                    # Do not show debug - it will output all reserved tasks!!!
                    # log.debug("<=WorkerGetAvailable=> Not locked w: %s", not_locked_w)

                    min_w = self.min_w(not_locked_w)
                    log.debug("<=WorkerGetAvailable=> Min w: %s", min_w)
                    log.info("<=WorkerGetAvailable=> Worker has been selected for run test on branch %s - w: %s", branch, min_w)
                    return min_w
                else:
                    log.warning("There is no running workers, may be DOWN!")
                    log.warning("<=WorkerGetAvailable=> Cannot run task, STOP NOW!")
                    subject = 'Cannot get worker to run your test, workers may be down.'
                    body = '''Arguments: \n branch = {} \n branch_w = {} \n excluded_w = {} \n actual_w = {} \n running_w = {}
                    '''.format(branch, branch_w, excluded_w, actual_w, running_w)
                    Mails.short(subject=subject, body=body, send_to=[user_mail])
                    return []
            else:
                log.warning("There is no available workers! All excluded.")
                log.warning("<=WorkerGetAvailable=> Cannot run task, STOP NOW!")
                subject = 'Cannot get worker to run your test, workers may be busy.'
                body = '''Arguments: \n branch = {} \n branch_w = {} \n excluded_w = {} \n actual_w = {}
                '''.format(branch, branch_w, excluded_w, actual_w)
                Mails.short(subject=subject, body=body, send_to=[user_mail])
                return []

    user_mail = mails['admin']

    # worker_addm_group_min_main = WorkerGetAvailable().user_test_available_w('tkn_main', user_mail=user_mail)
    # log.info("Selected MINIMAL worker for tkn_main branch %s\n", worker_addm_group_min_main)
    # worker_addm_group_min_ship = WorkerGetAvailable().user_test_available_w('tkn_ship', user_mail=user_mail)
    # log.info("Selected MINIMAL worker for tkn_ship branch %s\n", worker_addm_group_min_ship)

    class TestCasePatternRoutines(Runner, PatternRoutineCases):

        def fire_t(self, task, **kwargs):
            log.debug("Pretending like running the task!")
            pass

        def fire_case(self, case, **kwargs):
            log.debug("Pretending like running the case!")
            pass

        def test_run_user_test(self):
            test_item = {'tkn_branch': 'tkn_main', 'pattern_library': 'CORE', 'pattern_file_name': '10genMongoDB',
                         'pattern_folder_name': '10genMongoDB',
                         'pattern_file_path': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/CORE/10genMongoDB/10genMongoDB.tplpre',
                         'test_py_path': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/CORE/10genMongoDB/tests/test.py',
                         'pattern_folder_path_depot': '//addm/tkn_main/tku_patterns/CORE/10genMongoDB/...',
                         'pattern_file_path_depot': '//addm/tkn_main/tku_patterns/CORE/10genMongoDB/10genMongoDB.tplpre',
                         'is_key_pattern': True,
                         'test_py_path_template': '{}/addm/tkn_main/tku_patterns/CORE/10genMongoDB/tests/test.py',
                         'test_folder_path_template': '{}/addm/tkn_main/tku_patterns/CORE/10genMongoDB/tests',
                         'test_time_weight': '140'}

            options = {'branch': 'tkn_main', 'pattern_library': 'CORE', 'pattern_folder': '10genMongoDB',
                       'pattern_filename': '10genMongoDB', 'refresh': '1'}

            user_test_opt = dict(
                fake_run=True,
                user_name='test_001',
                addm_group=None,
                refresh=False,
                wipe=None,
                branch=test_item['tkn_branch'],
                pattern_library=test_item['pattern_library'],
                pattern_folder=test_item['pattern_folder_name'],
                pattern_filename=test_item['pattern_file_name'],
                test_function=None,
            )

            r_user_test = PatternRoutineCases.user_test('test_001', **user_test_opt)
            log.debug("r_user_test: %s", r_user_test)

    TestCasePatternRoutines().test_run_user_test()
