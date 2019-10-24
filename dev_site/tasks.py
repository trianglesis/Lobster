from __future__ import absolute_import, unicode_literals

import logging
import datetime
from django.conf import settings

from octo.octo_celery import app
from octo.helpers.tasks_helpers import exception
from octo.tasks import TSupport

from octo_tku_patterns.models import TkuPatterns


log = logging.getLogger("octo.octologger")
curr_hostname = getattr(settings, 'CURR_HOSTNAME', None)

# Tasks time limits:
DAY_LIMIT = 172800
HOURS_2 = 7200
HOURS_1 = 3600
MIN_90 = 5400
MIN_40 = 2400
MIN_20 = 1200
MIN_10 = 600
MIN_1 = 60
SEC_10 = 10
SEC_1 = 1


class DevRunner:

    @staticmethod
    @exception
    def fire_t(task, **kwargs):
        """
        This method will execute task object.
        Based on kwargs
        - will execute task in usual manner.
        - will show debug info or simulate task execution with fake task with sleep timer.


        :param task:
        :param kwargs:
        :return:
        """
        # Debug and test options:
        fake_run = kwargs.get('fake_run', False)
        to_debug = kwargs.get('to_debug', False)

        this_t = 'FireTasks.fire_t.{}'.format(task.__name__)
        # Task related options:
        t_args = kwargs.get('t_args', [this_t])
        t_kwargs = kwargs.get('t_kwargs', {'t_kwargs': this_t})
        t_queue = kwargs.get('t_queue', None)
        t_routing_key = kwargs.get('t_routing_key', this_t)
        t_soft_time_limit = kwargs.get('t_soft_time_limit', None)
        t_task_time_limit = kwargs.get('t_task_time_limit', None)

        # Show debug messages:
        if to_debug:
            log.debug("<=DevRunner=> REAL DEBUG: About to fire a task %s", task.name)

        task_options = dict()
        if t_args:
            task_options.update(args=t_args)
        if t_kwargs:
            task_options.update(kwargs=t_kwargs)
        if t_queue:
            task_options.update(queue=t_queue)
        if t_routing_key:
            task_options.update(routing_key=t_routing_key)
        if t_soft_time_limit:
            task_options.update(soft_time_limit=t_soft_time_limit)
        if t_task_time_limit:
            task_options.update(task_time_limit=t_task_time_limit)

        # Do not really send a task if fake=True
        if not fake_run:
            return task.apply_async(**task_options)
        else:
            to_sleep = kwargs.get('to_sleep', 10)
            log.debug("<=DevRunner=> FAKE: About to fire a task Name %s", task.name)
            log.debug("<=DevRunner=> FAKE: Task passed arguments: \n\t\t t_queue=%s \n\t\t t_args=%s \n\t\t t_kwargs=%s "
                      "\n\t\t t_routing_key=%s", t_queue, t_args, t_kwargs, t_routing_key)
            return TSupport.t_occupy_w.apply_async(
                args=['fire_t', to_sleep], kwargs=dict(t_args=t_args, t_kwargs=t_kwargs), queue=t_queue, routing_key=t_routing_key)

    @staticmethod
    def fire_case(case, **kwargs):
        """
        Execute routine case passed as argument.
        Use for fake, debug or usual executions.
        :param case:
        :param kwargs:
        :return:
        """
        # Debug and test options:
        fake_run = kwargs.get('fake_run', False)
        to_debug = kwargs.get('to_debug', False)
        # Real case kwargs:
        c_kwargs = kwargs.get('c_kwargs', {})

        # Show debug messages:
        if to_debug:
            log.debug("<=DevRunner=> REAL DEBUG: About to fire a case %s", case.__name__)

        if not fake_run:
            return case(**c_kwargs)
        else:
            log.debug("<=DevRunner=> FAKE: About to fire a function %s", case.__name__)
            return True


# noinspection PyUnusedLocal
class DevTRoutine:

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.DevTRoutine.dev_t_routine_night_tests',
              soft_time_limit=HOURS_1, task_time_limit=HOURS_2)
    @exception
    def dev_t_routine_night_tests(t_tag, **kwargs):
        log.debug("t_tag: %s", t_tag)
        # return DevRoutineCases.dev_nightly_test(**kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.DevTRoutine.dev_t_routine_user_tests',
              soft_time_limit=MIN_90, task_time_limit=HOURS_2)
    @exception
    def dev_t_routine_user_tests(t_tag, **kwargs):
        log.debug("t_tag: %s", t_tag)
        # return DevRoutineCases.dev_user_test(t_tag, **kwargs)


class DevRoutineCases:

    @staticmethod
    def select_pattern_test(branch, pattern_library, pattern_folder):
        test_item = TkuPatterns.objects.filter(
            tkn_branch__exact=branch,
            pattern_library__exact=pattern_library,
            pattern_folder_name__exact=pattern_folder,
        ).values(
            # For test data save:
            'tkn_branch',
            'pattern_library',
            'pattern_folder_name',
            'test_py_path',
            'pattern_folder_path_depot',
            'pattern_file_path_depot',
            'is_key_pattern',
            # For test execution
            'test_py_path_template',
            'test_folder_path_template',
            'test_time_weight',
        )
        return test_item

    # @staticmethod
    # def dev_nightly_test(**kwargs):
    #     """
    #     Full copy of usual NIGHT tests!
    #     Will run as night routine BUT only occupy worker with fake test tasks.
    #     Use this to test celery/flower behaviour
    #
    #     NOTE: DO NOT USE TABLE WIPE OPTION!
    #     NOTE: And also do not send status emails.
    #
    #     :return: bool
    #     """
    #     from octo_tku_patterns.table_oper import PatternsDjangoTableOper
    #     # from octo.helpers.tasks_helpers import BalanceNightTests
    #     from octo_tku_patterns.tasks import PatternTestExecCases, BalanceNightTests
    #     from run_core.addm_operations import ADDMOperations
    #     from octo_tku_patterns.tasks import TPatternParse, TPatternExecTest
    #
    #     fake_run = kwargs.get('fake_run', False)
    #     branch = kwargs.get('branch', None)
    #     user_name = kwargs.get('user_name', 'cron')
    #     excluded_seq = kwargs.get('excluded_seq', None)
    #     test_output_mode = kwargs.get('test_output_mode', False)
    #
    #     start_time = datetime.datetime.now()
    #     log.debug("<=nightly_test=> Setting start time: %s", start_time)
    #     all_tests_w = 0
    #
    #     if isinstance(excluded_seq, str):
    #         excluded_seq = excluded_seq.split(',')
    #
    #     """ 1. Select tests for run. This should be made after previously run of p4 sync and parse"""
    #     sorted_tests_l = BalanceNightTests().select_patterns_to_test(branch=branch, excluded_seq=excluded_seq)
    #
    #     log.debug("<=nightly_test=> TESTS ALL: Overall tests to run: %s", len(sorted_tests_l))
    #     """ 2. Chunk tests on even groups for selected amount of addms """
    #     addm_group_l = BalanceNightTests().get_available_addm_groups(branch=branch, user_name=user_name)
    #     addm_tests_balanced = BalanceNightTests().test_weight_balancer(addm_group=addm_group_l, test_items=sorted_tests_l)
    #
    #     """ 2.1 Start filling queues with selected tests for selected ADDM items (queryset) """
    #     addm_set = ADDMOperations.select_addm_set(addm_group=addm_group_l)               # Select and validate addm and assign corresponding balanced collection of tests:
    #
    #     for addm_item in addm_set:
    #         _addm_group = addm_item[0]['addm_group']
    #         addm_coll = addm_tests_balanced.get(_addm_group)
    #         addm_tests = addm_coll.get('tests', [])
    #         if addm_tests:
    #             addm_tests_weight = addm_coll.get('all_tests_weight')
    #             tent_avg = addm_coll.get('tent_avg')
    #             log.debug("ADDM: %s tests: %s ~t: %s avg: %s", _addm_group, len(addm_tests), addm_tests_weight, tent_avg)
    #             # log.debug("Tests for %s -> %s", addm_group, addm_tests)
    #
    #             # Send mail about tests assigning for this worker:
    #             mail_task_arg = 'tag=night_routine;lock=True;lvl=auto;type=send_mail'
    #             mail_kwargs = dict(mode="run",
    #                                r_type='Night',
    #                                branch=branch,
    #                                start_time=start_time,
    #                                addm_group=_addm_group,
    #                                addm_group_l=addm_group_l,
    #                                addm_test_pairs=len(addm_tests_balanced),
    #                                test_items_len=len(addm_tests),
    #                                all_tests=len(sorted_tests_l),
    #                                addm_used=len(addm_set),
    #                                all_tests_weight=addm_tests_weight,
    #                                tent_avg=tent_avg)
    #             """ MAIL send mail when routine tests selected: """
    #             DevRunner.fire_t(TSupport.t_long_mail, fake_run=True,
    #                              t_queue=_addm_group + '@tentacle.dq2',
    #                              t_args=[mail_task_arg],
    #                              t_kwargs=mail_kwargs,
    #                              t_routing_key='z_{}.night_routine_mail'.format(_addm_group))
    #
    #             """ Sync every available ADDM with Rsync """
    #             DevRunner.fire_t(TPatternParse.t_addm_rsync_threads, fake_run=True,
    #                              t_queue=_addm_group + '@tentacle.dq2',
    #                              t_args=[mail_task_arg],
    #                              t_kwargs=dict(addm_items=addm_item))
    #
    #             """ TEST EXECUTION: Init loop for test execution. Each test for each ADDM item. """
    #             for test_item in addm_tests:
    #                 test_t_w = round(float(test_item['test_time_weight']))
    #                 tsk_msg = 'tag=night_routine;lock=True;type=routine {}/{}/{} t:{} on: "{}" by: {}'
    #                 r_key = '{}.TExecTest.nightly_routine_case.{}'.format(_addm_group, test_item['pattern_folder_name'])
    #                 t_tag = tsk_msg.format(test_item['tkn_branch'], test_item['pattern_library'],
    #                                        test_item['pattern_folder_name'], test_t_w, _addm_group, user_name)
    #
    #                 # LIVE:
    #                 DevRunner.fire_t(TPatternExecTest().t_test_exec_threads, fake_run=True,
    #                                  t_queue=_addm_group + '@tentacle.dq2',
    #                                  t_args=[t_tag],
    #                                  t_kwargs=dict(addm_items=addm_item, test_item=test_item,
    #                                                test_output_mode=test_output_mode),
    #                                  t_routing_key=r_key,
    #                                  t_soft_time_limit=HOURS_2,
    #                                  t_task_time_limit=HOURS_2 + 900)
    #
    #             else:
    #                 """ 5.1. SLEEP before add task for mail send when finish tests and log save: """
    #                 mail_kwargs.update(mode='fin')
    #                 DevRunner.fire_t(TSupport.t_long_mail, fake_run=True,
    #                                  t_queue=_addm_group + '@tentacle.dq2',
    #                                  t_args=[mail_task_arg],
    #                                  t_kwargs=mail_kwargs,
    #                                  t_routing_key='z_{}.night_routine_mail'.format(_addm_group))
    #             # Show this in task output when finish.
    #             all_tests_w += addm_tests_weight
    #         else:
    #             log.info("ADDM %s has no tasks to run now.", _addm_group)
    #
    #     msg = '''Night routine has been executed. Options used:
    #              ADDM input: {addm_arg} |
    #              ADDM actual: {addm_act} |
    #              Excluded: {excl} |
    #              Test output {tst_outp} |
    #              Branch {branch} |
    #              Overall tests to run: {tst_len} |
    #              Overall tests time weight: {tst_w_t} |
    #              Start at: {start_time} |'''.format(
    #         addm_arg=kwargs.get('addm_group', []),
    #         addm_act=addm_group_l,
    #         excl=excluded_seq,
    #         tst_outp=test_output_mode,
    #         branch=branch,
    #         tst_len=len(sorted_tests_l),
    #         tst_w_t=all_tests_w,
    #         start_time=start_time,
    #     )
    #     return msg

    # @staticmethod
    # def dev_user_test(t_tag, **kwargs):
    #     # noinspection SpellCheckingInspection
    #     """
    #         Full copy of usual USER test run
    #
    #         NOTE: Do not send emails.
    #         NOTE: Do not wipe last tests.
    #         NOTE: Do not run test - make sleep task!
    #     """
    #     from octo.helpers.tasks_run import Runner
    #     from octo.tasks import TSupport
    #     from run_core.models import AddmDev
    #     from octo_tku_patterns.models import TkuPatterns
    #     from octo_tku_patterns.tasks import TPatternExecTest
    #     from octo_tku_patterns.tasks import PatternTestExecCases
    #     # from octo.helpers.tasks_helpers import WorkerGetAvailable
    #     from octo_tku_patterns.tasks import WorkerGetAvailable
    #     from octo_tku_patterns.table_oper import PatternsDjangoTableOperDel
    #
    #     user_name        = kwargs.get('user_name')
    #     addm_group       = kwargs.get('addm_group', None)
    #     refresh          = kwargs.get('refresh', None)
    #     wipe             = kwargs.get('wipe', None)
    #     branch           = kwargs.get('branch')
    #     pattern_library  = kwargs.get('pattern_library')
    #     pattern_folder   = kwargs.get('pattern_folder')
    #     pattern_filename = kwargs.get('pattern_filename')
    #     test_function    = kwargs.get('test_function', '')
    #     start_time = datetime.datetime.now()
    #
    #     """ 1. Select free/minimal queued worker: """
    #     if not addm_group:
    #         addm_group = WorkerGetAvailable().user_test_available_w(branch=branch, user_mail=kwargs.get('user_email'))
    #
    #     """ 2 Select ADDM machines and test item from DB and then send an initial mail: """
    #     addm_set = PatternTestExecCases().select_addm(addm_group)
    #     test_item = DevRoutineCases().select_pattern_test(branch, pattern_library, pattern_folder, pattern_filename)
    #
    #     # Last check:
    #     if not addm_set or not test_item:
    #         log.debug(
    #             "<=user_test=> test_execute_web: Cannot start user test no addm set or test item can be found in database %s",
    #             user_name)
    #         msg = "Cannot get addm_set or test_item from local database."
    #         DevRunner.fire_t(TSupport.t_user_mail, fake_run=True,
    #                          t_args=[t_tag],
    #                          t_kwargs=dict(mode='failed', addm_group=addm_group, start_time=start_time,
    #                                        options=kwargs,
    #                                        err_out='Test cannot be added to queue - no addm set or test items found in DB! ' + msg))
    #
    #     # Routing keys for mail and test tasks:
    #     # sync_r_key = '{}.TExecTest.t_addm_rsync_threads'.format(addm_set[0]['addm_group'])
    #     mail_r_key = '{}.TSupport.t_user_mail.{}'.format(addm_set[0]['addm_group'], test_item[0]['pattern_folder_name'])
    #     task_r_key = '{}.TExecTest.t_test_exec_threads.{}'.format(addm_set[0]['addm_group'], test_item[0]['pattern_folder_name'])
    #
    #     # Send initial mail:
    #     DevRunner.fire_t(TSupport.t_user_mail, fake_run=True,
    #                      t_args=[t_tag],
    #                      t_kwargs=dict(mode='added', test_item=test_item[0], addm_group=addm_set[0]['addm_group'],
    #                                    start_time=start_time, options=kwargs),
    #                      t_queue=addm_set[0]['addm_group'] + '@tentacle.dq2',
    #                      t_routing_key=mail_r_key)
    #
    #     """ 3. Delete previous logs or not: when p4 refresh or when wipe only"""
    #     if refresh or wipe:
    #         # To delete previous test run logs:
    #         delete_query_args = dict(branch=branch, pattern_library=test_item[0]['pattern_library'],
    #                                  pattern_folder=test_item[0]['pattern_folder_name'],
    #                                  pattern_filename=test_item[0]['pattern_file_name'])
    #         if test_function:
    #             # Only delete one test function record:
    #             test_arg = test_function.split(' ')  # request will clear extra symbol '+'
    #             delete_query_args.update(tst_class=test_arg[0], tst_name=test_arg[1])
    #         log.info("<=user_test=> (DEV) NOT Will delete following test logs: %s", delete_query_args)
    #         '''
    #         log.info("<=user_test=> Will delete following test logs: %s", delete_query_args)
    #         PatternsDjangoTableOperDel.delete_old_solo_test_logs(delete_query_args)
    #         '''
    #     """ 3.1 Run p4 sync"""
    #     if refresh:
    #         # Parse p4 data, sync changes and sync test files on selected ADDM set:
    #         addm_synced = DevRunner.fire_case(PatternTestExecCases().case_p4_parse_sync, fake=True,
    #                                        c_kwargs=dict(info_str_d=t_tag, branch=branch, sync_shares=True, addm_group=addm_set[0]['addm_group'],
    #                                                         addm_set=addm_set, user_name=user_name))
    #         addm_synced = dict(addm_synced=True)
    #         if addm_synced.get('addm_synced', False):
    #             # Start test mail:
    #             DevRunner.fire_t(TSupport.t_user_mail, fake_run=True,
    #                           t_args=[t_tag],
    #                           t_kwargs=dict(mode='start', test_item=test_item[0], addm_group=addm_set[0]['addm_group'], start_time=start_time, options=kwargs),
    #                           t_queue=addm_set[0]['addm_group']+'@tentacle.dq2',
    #                           t_routing_key=mail_r_key)
    #             # Test task exec:
    #             DevRunner.fire_t(TPatternExecTest.t_test_exec_threads, fake_run=True,
    #                           t_queue=addm_set[0]['addm_group'] + '@tentacle.dq2',
    #                           t_args=[t_tag],
    #                           t_kwargs=dict(addm_items=addm_set, test_item=test_item[0], test_function=test_function),
    #                           t_routing_key=task_r_key, t_soft_time_limit=HOURS_2)
    #         else:
    #             msg = "<=user_test=> SYNC task failed, should not run test in that case, Will raise error and stop."
    #             log.error(msg)
    #
    #     else:  # No sync will be executed and not ADDM sync also:
    #         # Start test mail:
    #         Runner.fire_t(TSupport.t_user_mail, fake_run=True,
    #                       t_args=[t_tag],
    #                       t_kwargs=dict(mode='start', test_item=test_item[0], addm_group=addm_set[0]['addm_group'], start_time=start_time, options=kwargs),
    #                       t_queue=addm_set[0]['addm_group']+'@tentacle.dq2', t_routing_key=mail_r_key, )
    #         # Test task exec:
    #         Runner.fire_t(TPatternExecTest.t_test_exec_threads, fake_run=True,
    #                       t_queue=addm_set[0]['addm_group'] + '@tentacle.dq2', t_args=[t_tag],
    #                       t_kwargs=dict(addm_items=addm_set, test_item=test_item[0],
    #                                        test_function=test_function),
    #                       t_routing_key=task_r_key, t_soft_time_limit=HOURS_2)
    #     # Finish mail:
    #     DevRunner.fire_t(TSupport.t_user_mail, fake_run=True,
    #                      t_args=[t_tag],
    #                      t_kwargs=dict(mode='finish', test_item=test_item[0], addm_group=addm_set[0]['addm_group'],
    #                                    start_time=start_time, options=kwargs),
    #                      t_queue=addm_set[0]['addm_group'] + '@tentacle.dq2',
    #                      t_routing_key=mail_r_key)
    #
    #     return 'Executed test kwargs: {} selected ADDM group: {}'.format(kwargs, addm_group)
