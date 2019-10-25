"""
Celery tasks.
All celery tasks should be collected here.
- Task should execute only separate case or case_routine.
- Task should not execute any code itself.
- Task should have exception handler which output useful data or send mail.

Note:
    - Be careful with recursive import.
    - Do not import case routines which import tasks from here.
"""
from __future__ import absolute_import, unicode_literals

import os
import datetime
import logging
import collections

from time import time, sleep

from octo.octo_celery import app

from run_core.models import AddmDev

from run_core.addm_operations import ADDMOperations
from run_core.p4_operations import PerforceOperations
from run_core.local_operations import LocalPatternsP4Parse, LocalPatternsParse

from octo_tku_patterns.models import TkuPatterns, TestLast, TestCases, TestCasesDetails
from octo_tku_patterns.test_executor import TestExecutor
from octo_tku_patterns.table_oper import PatternsDjangoTableOperDel

from octo.helpers.tasks_helpers import exception
from octo.helpers.tasks_oper import TasksOperations
from octo.helpers.tasks_helpers import TMail

from octo.helpers.tasks_run import Runner
from octo.tasks import TSupport

from octo_tku_patterns.night_test_balancer import BalanceNightTests
from octo_tku_patterns.user_test_balancer import WorkerGetAvailable, OptionalTestsSelect

log = logging.getLogger("octo.octologger")


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


# noinspection PyUnusedLocal
class TPatternRoutine:

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TRoutine.t_routine_night_tests',
              soft_time_limit=HOURS_1, task_time_limit=HOURS_2)
    @exception
    def t_routine_night_tests(t_tag, **kwargs):
        log.debug("t_tag: %s", t_tag)
        return PatternRoutineCases.nightly_test(**kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TRoutine.t_routine_user_tests',
              soft_time_limit=MIN_90, task_time_limit=HOURS_2)
    @exception
    def t_routine_user_tests(t_tag, **kwargs):
        log.debug("t_tag: %s", t_tag)
        return PatternRoutineCases.user_test(t_tag, **kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TRoutine.t_routine_night_tests',
              soft_time_limit=HOURS_1, task_time_limit=HOURS_2)
    @exception
    def t_routine_optional_test(t_tag, **kwargs):
        log.debug("t_tag: %s", t_tag)
        return PatternRoutineCases.optional_test(t_tag, **kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TRoutine.t_test_prep',
              soft_time_limit=MIN_90, task_time_limit=HOURS_2)
    @exception
    def t_test_prep(t_tag, **kwargs):
        log.warning("<=TPatternRoutine=> RUN TaskPrepare.run_tku_patterns %s", t_tag)
        TaskPrepare(kwargs['obj']).run_tku_patterns()


class TPatternExecTest:

    @staticmethod
    @app.task(routing_key='addm_group.TExecTest.t_test_exec_threads.pattern_folder',
              max_retries=1, autoretry_for=(AttributeError,),
              soft_time_limit=MIN_90, task_time_limit=HOURS_2)
    @exception
    def t_test_exec_threads(t_tag, **kwargs):
        log.debug("t_tag: %s", t_tag)
        return TestExecutor().test_run_threads(**kwargs)


class TPatternParse:

    # New:
    @staticmethod
    @app.task(queue='w_parsing@tentacle.dq2', routing_key='parsing.perforce.TExecTest.t_p4_sync_NEW',
              soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_p4_sync(t_tag):
        log.debug("t_tag: %s", t_tag)
        return LocalPatternsP4Parse().last_changes_get()

    @staticmethod
    @app.task(queue='w_parsing@tentacle.dq2', routing_key='parsing.perforce.TExecTest.t_p4_info',
              soft_time_limit=MIN_1, task_time_limit=MIN_10)
    @exception
    def t_p4_info(t_tag):
        log.debug("t_tag: %s", t_tag)
        return PerforceOperations().p4_info()

    @staticmethod
    @app.task(queue='w_parsing@tentacle.dq2', routing_key='parsing.perforce.TExecTest.t_p4_sync_smart',
              soft_time_limit=MIN_20, task_time_limit=MIN_40)
    @exception
    def t_p4_sync_smart(t_tag, branch):
        log.debug("t_tag: %s", t_tag)
        return PerforceOperations().sync_last(branch)

    @staticmethod
    @app.task(queue='w_parsing@tentacle.dq2', routing_key='parsing.perforce.TExecTest.t_p4_sync_force',
              soft_time_limit=MIN_20, task_time_limit=MIN_40)
    @exception
    def t_p4_sync_force(t_tag, depot_path):
        log.debug("t_tag: %s", t_tag)
        return PerforceOperations().sync_force(depot_path)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TRoutine.t_routine_addm_sync',
              soft_time_limit=MIN_40, task_time_limit=MIN_90)
    @exception
    def t_routine_addm_sync(t_tag, **kwargs):
        log.debug("t_tag: %s", t_tag)
        return PatternTestExecCases.sync_addm(**kwargs)

    @staticmethod
    @app.task(routing_key='parsing.TExecTest.make_addm_sync_threads.addm_group',
              soft_time_limit=MIN_20, task_time_limit=HOURS_2)
    @exception
    def t_addm_rsync_threads(t_tag, **kwargs):
        log.debug("t_tag: %s", t_tag)
        return ADDMOperations().make_addm_sync_threads(**kwargs)

    @staticmethod
    @app.task(queue='w_parsing@tentacle.dq2', routing_key='parsing.TExecTest.t_p4_changes_threads',
              soft_time_limit=MIN_20, task_time_limit=MIN_40)
    @exception
    def t_p4_changes_threads(t_tag, branch):
        log.debug("t_tag: %s", t_tag)
        return PatternTestExecCases().p4_changes_multi(branch)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TRoutine.t_routine_cron_parse_patt',
              soft_time_limit=MIN_20, task_time_limit=MIN_40)
    @exception
    def t_routine_cron_parse_patt(t_tag, **kwargs):
        log.debug("t_tag: %s", t_tag)
        return PatternTestExecCases().auto_p4_parse_sync(**kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.TRoutine.t_routine_user_parse_patt',
              soft_time_limit=MIN_20, task_time_limit=MIN_40)
    @exception
    def t_routine_user_parse_patt(t_tag, **kwargs):
        log.debug("t_tag: %s", t_tag)
        return PatternTestExecCases().case_p4_parse_sync(**kwargs)

    @staticmethod
    @app.task(queue='w_routines@tentacle.dq2', routing_key='routines.t_pattern_weight_index',
              soft_time_limit=MIN_10, task_time_limit=MIN_20)
    @exception
    def t_pattern_weight_index(t_tag, last_days):
        log.debug("t_tag: %s", t_tag)
        PatternTestExecCases.patterns_weight_compute(last_days)


class PatternTestExecCases:

    @staticmethod
    def patterns_weight_compute(last_days):
        """
        Use history tests records to compute average test run time for each.
        :return:
        """
        from run_core.local_operations import LocalDB
        # Select and group history records:
        patterns_weight = LocalDB.history_weight(last_days=last_days)
        # Insert sorted in TKU Patterns table:
        LocalDB.insert_patt_weight(patterns_weight)

    # noinspection PyPep8Naming
    @staticmethod
    def chunkIt(seq, num):
        avg = len(seq) / float(num)
        out = collections.deque()
        last = 0.0

        while last < len(seq):
            out.append(seq[int(last):int(last + avg)])
            # log.debug("<=TestPrepCases=> chunk - seq[%s:int(%s)]", int(last), int(last + avg))
            last += avg
        return out

    @exception
    def p4_changes_multi(self, branch):
        # noinspection PyCompatibility
        from queue import Queue
        from threading import Thread

        ts = time()
        patterns_threads = collections.OrderedDict()
        thread_list = []
        test_outputs = []
        test_q = Queue()

        log.debug("Start parsing threads! %s", ts)
        parse_stat = LocalPatternsParse().compose_tree_paths(tkn_branch=branch)  # Run local parsing procedure:
        log.debug("<=p4_changes_multi=> Local parsed 'compose_tree_paths' status is: %s ", parse_stat)
        patterns = TkuPatterns.objects.filter(tkn_branch__exact=branch).values()  # Select parsed from table and run perforce parsing procedure:
        log.debug("Patterns selected len: %s", patterns.count())

        w = 5
        threads = list(range(w))
        split_patt = self.chunkIt(patterns, len(threads))
        log.debug("Threads for parse patterns len: %s", len(threads))

        # Thread-patterns pairs:
        for thread_i, patterns_list in zip(threads, split_patt):
            patterns_threads.update({'thread-{}'.format(str(thread_i)): dict(patterns_list=collections.deque(patterns_list), thread=thread_i)})

        log.debug("Filling threads with jobs...")
        for thread_i, patterns in patterns_threads.items():       # Iter each thread and patterns in it:

            conn_q = Queue()                                      # Separate Queue for p4 connection store
            p4_conn = PerforceOperations().p4_initialize()        # Init p4 connection for single thread-worker
            conn_q.put(p4_conn)                                   # Put active connection in queue for all threads

            log.debug("Filling threads for thread: %s", thread_i)
            patterns_list = patterns.get('patterns_list')       # Choose patterns list from dict of threads+patterns

            while 0 < len(patterns_list):                       # Each pattern generates own process
                pattern_item = patterns_list.popleft()          # When assigned to thread - delete item
                th_name = 'Parse thread: {} pattern: {}'.format(thread_i, pattern_item['pattern_folder_name'])  # type: str
                args_d = dict(pattern_d=pattern_item, th_name=th_name, test_q=test_q, conn_q=conn_q)
                parse_thread = Thread(target=LocalPatternsP4Parse().p4_changes_run, name=th_name, kwargs=args_d)
                thread_list.append(parse_thread)                 # Save list of threads for further execution

        # Execute threads:
        log.debug("Executing saved threads!")
        for parse_thread in thread_list:
            parse_thread.start()

        # Sync wait:
        log.debug("Wait for all threads!")
        for parse_thread in thread_list:
            parse_thread.join()
            test_outputs.append(test_q.get())

        msg = "Finish all threads in - {} ! Patterns parsed - {}".format(time() - ts, len(test_outputs))
        log.debug(msg)
        return msg

    @exception
    def case_p4_parse_sync(self, **kwargs):
        """
        Refresh file and patterns before run user test.
        If user use option refresh.
        Auto-wait until all of these are finished. Then proceed further.
        NOTE: Must return True or something valuable to allow user test run further.

        :return:
        """

        user_name = kwargs.get('user_name')
        branch = kwargs.get('branch')
        sync_shares = kwargs.get('sync_shares', False)
        addm_group = kwargs.get('addm_group', None)
        addm_set = kwargs.get('addm_set', None)
        fake_run = kwargs.get('fake_run', False)
        addm_synced = False

        # Select ADDM set if group is present but not set was passed:
        if not addm_set and addm_group:
            addm_set = AddmDev.objects.filter(addm_group__exact=addm_group, disables__isnull=True).values()

        tsk_msg = 'tag={};{};'
        tag_item = 'branch={br};user_name={usr};sync_shares={sync} | on: "{addm}"'.format(
            usr=user_name, br=branch, addm=addm_group, sync=sync_shares)

        p4_info = Runner.fire_t(TPatternParse().t_p4_info, fake_run=fake_run,
                                t_args=['tag=p4_parse_sync;'])
        # Wait for success:
        if TasksOperations().task_wait_success(p4_info, 't_p4_info'):
            log.debug("<=TestExecCases=> P4 Check: p4_info: %s ", p4_info.status)
            t_tag = tsk_msg.format('p4_parse_sync', tag_item)
            Runner.fire_t(TPatternParse().t_p4_sync_smart, fake_run=fake_run,
                          t_args=[t_tag],
                          t_kwargs={'branch': branch},
                          t_queue='w_parsing@tentacle.dq2',
                          )
            log.info("<=TestExecCases=> t_p4_sync_smart: Added to queue.")

            """ Now parse patterns for local changes. Parse all files change lists from p4 """
            t_tag = tsk_msg.format('t_p4_changes_threads', tag_item)
            changes_parse_task = Runner.fire_t(TPatternParse().t_p4_changes_threads, fake_run=fake_run,
                                               t_args=[t_tag],
                                               t_kwargs={'branch': branch},
                                               t_queue='w_parsing@tentacle.dq2',
                                               )
            log.info("<=TestExecCases=> t_p4_changes_threads: Added to queue.")
        else:
            log.error("<=TestExecCases=> P4 check task fail p4_info: %s and sync stopped here!", p4_info.status)
            msg = "P4 Sync task was not finished with expected result. Cancel further test execution routine!"
            log.debug("<=user_test=> test_execute_web: Cannot start user test no addm set or test item can be found in database %s", user_name)
            Runner.fire_t(TSupport.t_user_mail, fake_run=fake_run,
                          t_args=['case_p4_parse_sync'],
                          t_kwargs=dict(mode='failed', addm_group=addm_group, start_time=datetime.datetime.now(),
                                        options=kwargs,
                                        err_out='Test cannot be added to queue - no addm set or test items found in DB! ' + msg))
            return False
        if sync_shares:
            # Wait for success:
            if changes_parse_task and TasksOperations().task_wait_success(changes_parse_task, 't_p4_changes_threads'):
                log.info("<=TestExecCases=> All files now p4-synced and parsed! Can run ADDM rsync if needed.")
                log.debug("<=TestExecCases=> case_p4_parse_sync: parse_n_changes finished!")
                # ADDM sync task will wait for success itself:`
                addm_synced = self.sync_addm(addm_set=addm_set, addm_group=addm_group)
            if not fake_run:
                return addm_synced
            else:
                return True
        else:
            return True

    @exception
    def auto_p4_parse_sync(self, **kwargs):
        """
        Refresh file and patterns before run user test.
        If user use option refresh.
        Auto-wait until all of these are finished. Then proceed further.
        NOTE: Must return True or something valuable to allow user test run further.

        :return:
        """
        branch = kwargs.get('branch')
        fake_run = kwargs.get('fake_run')
        tsk_msg = 'tag={};{};'
        tag_item = 'branch={br};auto_sync_p4;cron'.format(br=branch)

        p4_info = Runner.fire_t(TPatternParse().t_p4_info, fake_run=fake_run,
                                t_args=['tag=p4_parse_sync;'])
        # Wait for success:
        if TasksOperations().task_wait_success(p4_info, 't_p4_info'):
            log.debug("<=auto_p4_parse_sync=> P4 Check: p4_info: %s ", p4_info.status)
            t_tag = tsk_msg.format('p4_parse_sync', tag_item)
            Runner.fire_t(TPatternParse().t_p4_sync_smart, fake_run=fake_run,
                          t_args=[t_tag],
                          t_kwargs={'branch': branch},
                          t_queue='w_parsing@tentacle.dq2',
                          )
            log.info("<=auto_p4_parse_sync=> t_p4_sync_smart: Added to queue.")
            """ Now parse patterns for local changes. Parse all files change lists from p4 """
            t_tag = tsk_msg.format('t_p4_changes_threads', tag_item)
            Runner.fire_t(TPatternParse().t_p4_changes_threads, fake_run=fake_run,
                          t_args=[t_tag],
                          t_kwargs={'branch': branch},
                          t_queue='w_parsing@tentacle.dq2',
                          )
            log.info("<=auto_p4_parse_sync=> t_p4_changes_threads: Added to queue.")
        else:
            state = p4_info.state
            status = p4_info.status
            log.error("<=auto_p4_parse_sync=> P4 fail p4_info: %s - %s stopped here!", state, status)
            msg = "<=auto_p4_parse_sync=> P4 Info task won't finished well, stopping!"
            return msg

    @staticmethod
    @exception
    def sync_addm(**kwargs):
        addm_set = kwargs.get('addm_set', None)
        addm_group = kwargs.get('addm_group', None)
        fake_run = kwargs.get('fake_run')

        if not addm_set:
            if not addm_group:
                msg = "Cannot select addm items without addm_group argument!"
                log.error(msg)
                raise Exception(msg)
            addm_set = ADDMOperations.select_addm_set(addm_group=addm_group)

        t_tag = "{};addm_group={}".format('t_addm_rsync_threads', addm_set[0]['addm_group'])
        addm_sync_task = Runner.fire_t(TPatternParse().t_addm_rsync_threads, fake_run=fake_run,
                                       t_args=[t_tag],
                                       t_kwargs=dict(addm_items=addm_set),
                                       t_queue=addm_set[0]['addm_group'] + '@tentacle.dq2',
                                       t_routing_key='TExecTest.t_addm_rsync_threads.{0}'.format(
                                           addm_set[0]['addm_group'])
                                       )

        if addm_sync_task and TasksOperations().task_wait_success(addm_sync_task, 't_addm_rsync_threads'):
            log.info("<=sync_addm=> Task finished %s ADDM tests now actual.", addm_sync_task.status)
            return True
        else:
            msg = "<=sync_addm=> Task fail: '{}'!".format(addm_sync_task.status)
            log.error(msg)
            raise Exception(msg)


class PatternRoutineCases:

    # noinspection SpellCheckingInspection
    @staticmethod
    def nightly_test(**kwargs):
        """
        This is usual nightly test run routine.
        Should use same scenario as "run_executor" in main Octopus.
        Later can be modified and optimized, but now just duplicate same logic but in backend.

        Start dates:
        - main "2017-09-25"
        - ship "2017-10-12"

        kwargs:
            - branch            : tkn_main / tkn_ship / both
            - send_mail         : True / False
            - start_date        : custom select tests only from this date
            - excluded_seq   : Exclude pattern folder, list (can be any: folder or library)
            - included_seq : Sort only selected pattern folders, list (can be any: folder or library)
            - addm_group_l      : string of addm groups use
          debug:
            - test_output_mode  : silent / verbose (verbose as default)
            - slice_arg         : Integer to slice db select results - for debug

        :return: bool
        """
        fake_run = kwargs.get('fake_run', False)
        branch = kwargs.get('branch', None)
        user_name = kwargs.get('user_name', 'cron')
        excluded_seq = kwargs.get('excluded_seq', None)
        test_output_mode = kwargs.get('test_output_mode', False)

        start_time = datetime.datetime.now()
        log.debug("<=nightly_test=> Setting start time: %s", start_time)
        all_tests_w = 0

        if isinstance(excluded_seq, str):
            excluded_seq = excluded_seq.split(',')

        """ 1. Select tests for run. This should be made after previously run of p4 sync and parse"""
        sorted_tests_l = BalanceNightTests().select_patterns_to_test(branch=branch, excluded_seq=excluded_seq, fake_run=fake_run)

        log.debug("<=nightly_test=> TESTS ALL: Overall tests to run: %s", len(sorted_tests_l))
        """ 2. Chunk tests on even groups for selected amount of addms """
        addm_group_l = BalanceNightTests().get_available_addm_groups(branch=branch, user_name=user_name)
        addm_tests_balanced = BalanceNightTests().test_weight_balancer(addm_group=addm_group_l, test_items=sorted_tests_l)

        """ 2.1 Start filling queues with selected tests for selected ADDM items (querysets) """
        addm_set = ADDMOperations.select_addm_set(addm_group=addm_group_l)               # Select and validate addm and assign corresponding balanced collection of tests:

        for addm_item in addm_set:
            _addm_group = addm_item[0]['addm_group']
            addm_coll = addm_tests_balanced.get(_addm_group)
            addm_tests = addm_coll.get('tests', [])
            if addm_tests:
                addm_tests_weight = addm_coll.get('all_tests_weight')
                tent_avg = addm_coll.get('tent_avg')
                log.debug("ADDM: %s tests: %s ~t: %s avg: %s", _addm_group, len(addm_tests), addm_tests_weight, tent_avg)
                # log.debug("Tests for %s -> %s", addm_group, addm_tests)

                # Send mail about tests assigning for this worker:
                mail_task_arg = 'tag=night_routine;lock=True;lvl=auto;type=send_mail'
                mail_kwargs = dict(mode="run",
                                   r_type='Night',
                                   branch=branch,
                                   start_time=start_time,
                                   addm_group=_addm_group,
                                   addm_group_l=addm_group_l,
                                   addm_test_pairs=len(addm_tests_balanced),
                                   test_items_len=len(addm_tests),
                                   all_tests=len(sorted_tests_l),
                                   addm_used=len(addm_set),
                                   all_tests_weight=addm_tests_weight,
                                   tent_avg=tent_avg)
                """ MAIL send mail when routine tests selected: """
                Runner.fire_t(TSupport.t_long_mail, fake_run=fake_run,
                              t_queue=_addm_group+'@tentacle.dq2',
                              t_args=[mail_task_arg],
                              t_kwargs=mail_kwargs,
                              t_routing_key='z_{}.night_routine_mail'.format(_addm_group))

                """ Sync every available ADDM with Rsync """
                Runner.fire_t(TPatternParse.t_addm_rsync_threads, fake_run=fake_run,
                              t_queue=_addm_group+'@tentacle.dq2',
                              t_args=[mail_task_arg],
                              t_kwargs=dict(addm_items=addm_item))

                """ TEST EXECUTION: Init loop for test execution. Each test for each ADDM item. """
                for test_item in addm_tests:
                    test_t_w = round(float(test_item['test_time_weight']))
                    tsk_msg = 'tag=night_routine;lock=True;type=routine {}/{}/{} t:{} on: "{}" by: {}'
                    r_key = '{}.TExecTest.nightly_routine_case.{}'.format(_addm_group, test_item['pattern_folder_name'])
                    t_tag = tsk_msg.format(test_item['tkn_branch'], test_item['pattern_library'],
                                           test_item['pattern_folder_name'], test_t_w, _addm_group, user_name)

                    # LIVE:
                    Runner.fire_t(TPatternExecTest().t_test_exec_threads, fake_run=fake_run,
                                  t_queue=_addm_group + '@tentacle.dq2',
                                  t_args=[t_tag],
                                  t_kwargs=dict(addm_items=addm_item, test_item=test_item, test_output_mode=test_output_mode),
                                  t_routing_key=r_key,
                                  t_soft_time_limit=HOURS_2,
                                  t_task_time_limit=HOURS_2+900)

                else:
                    """ 5.1. SLEEP before add task for mail send when finish tests and log save: """
                    mail_kwargs.update(mode='fin')
                    Runner.fire_t(TSupport.t_long_mail, fake_run=fake_run,
                                  t_queue=_addm_group+'@tentacle.dq2',
                                  t_args=[mail_task_arg],
                                  t_kwargs=mail_kwargs,
                                  t_routing_key = 'z_{}.night_routine_mail'.format(_addm_group))
                # Show this in task output when finish.
                all_tests_w += addm_tests_weight
            else:
                log.info("ADDM %s has no tasks to run now.", _addm_group)

        msg = '''Night routine has been executed. Options used:
                 ADDM input: {addm_arg} | 
                 ADDM actual: {addm_act} | 
                 Excluded: {excl} | 
                 Test output {tst_outp} | 
                 Branch {branch} | 
                 Overall tests to run: {tst_len} | 
                 Overall tests time weight: {tst_w_t} | 
                 Start at: {start_time} |'''.format(
            addm_arg=kwargs.get('addm_group', []),
            addm_act=addm_group_l,
            excl=excluded_seq,
            tst_outp=test_output_mode,
            branch=branch,
            tst_len=len(sorted_tests_l),
            tst_w_t=all_tests_w,
            start_time=start_time,
        )
        return msg

    @staticmethod
    @exception
    def user_test(t_tag, **kwargs):
        # noinspection SpellCheckingInspection
        fake_run         = kwargs.get('fake_run', False)
        user_name        = kwargs.get('user_name')
        addm_group       = kwargs.get('addm_group', None)
        refresh          = kwargs.get('refresh', None)
        wipe             = kwargs.get('wipe', None)
        branch           = kwargs.get('branch')
        pattern_library  = kwargs.get('pattern_library')
        pattern_folder   = kwargs.get('pattern_folder')
        test_function    = kwargs.get('test_function', '')
        start_time = datetime.datetime.now()

        # Always fake on local test env:
        if os.name == "nt":
            fake_run = True

        """ 1. Select free/minimal queued worker: """
        if not addm_group:
            addm_group = WorkerGetAvailable().user_test_available_w(branch=branch, user_mail=kwargs.get('user_email'))

        """ 2 Select ADDM machines and test item from DB and then send an initial mail: """
        addm_set = AddmDev.objects.filter(addm_group__exact=addm_group, disables__isnull=True).values()
        test_item = TkuPatterns.objects.filter(tkn_branch__exact=branch,
                                               pattern_library__exact=pattern_library,
                                               pattern_folder_name__exact=pattern_folder).values()
        # Last check:
        if not addm_set or not test_item:
            log.debug("<=user_test=> test_execute_web: Cannot start user test no addm set or test item can be found in database %s", user_name)
            msg = "Cannot get addm_set or test_item from local database."
            Runner.fire_t(TSupport.t_user_mail, fake_run=fake_run,
                          t_args=[t_tag],
                          t_kwargs=dict(mode='failed', addm_group=addm_group, start_time=start_time,
                                        options=kwargs,
                                        err_out='Test cannot be added to queue - no addm set or test items found in DB! ' + msg))

        # Routing keys for mail and test tasks:
        # sync_r_key = '{}.TExecTest.t_addm_rsync_threads'.format(addm_set[0]['addm_group'])
        mail_r_key = '{}.TSupport.t_user_mail.{}'.format(addm_set[0]['addm_group'], test_item[0]['pattern_folder_name'])
        task_r_key = '{}.TExecTest.t_test_exec_threads.{}'.format(addm_set[0]['addm_group'], test_item[0]['pattern_folder_name'])
        # Send initial mail:
        Runner.fire_t(TSupport.t_user_mail, fake_run=fake_run,
                      t_args=[t_tag],
                      t_kwargs=dict(mode='added', test_item=test_item[0], addm_group=addm_set[0]['addm_group'], start_time=start_time, options=kwargs),
                      t_queue=addm_set[0]['addm_group']+'@tentacle.dq2',
                      t_routing_key=mail_r_key)

        """ 3. Delete previous logs or not: when p4 refresh or when wipe only"""
        if refresh or wipe:
            # To delete previous test run logs:
            delete_query_args = dict(branch=branch, pattern_library=test_item[0]['pattern_library'],
                                     pattern_folder=test_item[0]['pattern_folder_name'])
            if test_function:
                # Only delete one test function record:
                test_arg = test_function.split(' ')  # request will clear extra symbol '+'
                delete_query_args.update(tst_class=test_arg[0], tst_name=test_arg[1])

            log.info("<=user_test=> Will delete following test logs: %s", delete_query_args)
            if not fake_run:
                PatternsDjangoTableOperDel.delete_old_solo_test_logs(delete_query_args)
        """ 3.1 Run p4 sync"""
        if refresh:
            # Parse p4 data, sync changes and sync test files on selected ADDM set:
            addm_synced = Runner.fire_case(PatternTestExecCases().case_p4_parse_sync, fake_run=fake_run,
                                           c_kwargs=dict(info_str_d=t_tag, branch=branch, sync_shares=True,
                                                         addm_group=addm_set[0]['addm_group'],
                                                         addm_set=addm_set, user_name=user_name))
            if addm_synced:
                # Start test mail:
                Runner.fire_t(TSupport.t_user_mail, fake_run=fake_run,
                              t_args=[t_tag],
                              t_kwargs=dict(mode='start', test_item=test_item[0], addm_group=addm_set[0]['addm_group'], start_time=start_time, options=kwargs),
                              t_queue=addm_set[0]['addm_group']+'@tentacle.dq2',
                              t_routing_key=mail_r_key)
                # Test task exec:
                Runner.fire_t(TPatternExecTest.t_test_exec_threads, fake_run=fake_run,
                              t_queue=addm_set[0]['addm_group'] + '@tentacle.dq2',
                              t_args=[t_tag],
                              t_kwargs=dict(addm_items=addm_set, test_item=test_item[0], test_function=test_function),
                              t_routing_key=task_r_key, t_soft_time_limit=HOURS_2)
            else:
                msg = "<=user_test=> SYNC task failed, should not run test in that case, Will raise error and stop."
                log.error(msg)
        else:  # No sync will be executed and not ADDM sync also:
            # Start test mail:
            Runner.fire_t(TSupport.t_user_mail, fake_run=fake_run,
                          t_args=[t_tag],
                          t_kwargs=dict(mode='start', test_item=test_item[0], addm_group=addm_set[0]['addm_group'], start_time=start_time, options=kwargs),
                          t_queue=addm_set[0]['addm_group']+'@tentacle.dq2', t_routing_key=mail_r_key, )
            # Test task exec:
            Runner.fire_t(TPatternExecTest.t_test_exec_threads, fake_run=fake_run,
                          t_queue=addm_set[0]['addm_group'] + '@tentacle.dq2', t_args=[t_tag],
                          t_kwargs=dict(addm_items=addm_set, test_item=test_item[0],
                                        test_function=test_function),
                          t_routing_key=task_r_key, t_soft_time_limit=HOURS_2)
        # Finish mail:
        Runner.fire_t(TSupport.t_user_mail, fake_run=fake_run,
                      t_args=[t_tag],
                      t_kwargs=dict(mode='finish', test_item=test_item[0], addm_group=addm_set[0]['addm_group'], start_time=start_time, options=kwargs),
                      t_queue=addm_set[0]['addm_group']+'@tentacle.dq2',
                      t_routing_key=mail_r_key)
        return True

    @staticmethod
    def optional_test(t_tag, **kwargs):
        """
        Run test for user's chosen set:
        - Sets could be defined by:
        -- user name
        -- last days
        -- from date
        and etc.

        Sync P4 in separate task on routine worker. Early before run this one!

        :return:
        """
        fake_run = kwargs.get('fake_run', False)
        wipe = kwargs.get('wipe', False)
        user_name = kwargs.get('user_name')
        addm_name = kwargs.get('addm_name', 'double_decker')
        addm_group = kwargs.get('addm_group', None)
        branch = kwargs.get('branch')
        test_items_l = kwargs.get('test_items_l', None)
        patterns_dir_list = kwargs.get('patterns_dir_list', None)
        start_time = datetime.datetime.now()

        """ 1. Select free/minimal queued worker: """
        if not addm_group:
            addm_group = WorkerGetAvailable().user_test_available_w(branch=branch, user_mail=kwargs.get('user_email'))

        """ 2 Select ADDM machines and test item from DB and then send an initial mail: """
        addm_set = AddmDev.objects.filter(addm_group__exact=addm_group, disables__isnull=True).values()

        """2.1 Here we're selecting set of patterns to test. Later move it to separate logic to allow us to run
        different cases, such as: all failed, all user, by change, etc."""
        if not test_items_l and not patterns_dir_list:
            test_items_l, patterns_dir_list = OptionalTestsSelect().select_latest_failed_sort(branch=branch, addm_name=addm_name)

        # Last check:
        if not addm_set or not test_items_l:
            log.debug("<=user_test=> test_execute_web: Cannot start user test no addm set or test item can be found in database %s", user_name)
            msg = "Cannot get addm_set or test_item from local database."
            Runner.fire_t(TSupport.t_user_mail, fake_run=fake_run,
                          t_args=[t_tag],
                          t_kwargs=dict(mode='failed', addm_group=addm_group, start_time=start_time,
                                        options=kwargs,
                                        err_out='Test cannot be added to queue - no addm set or test items found in DB! ' + msg))

        mail_r_key = '{}.TSupport.t_optional_test_mail'.format(addm_set[0]['addm_group'])
        # Send initial mail:
        Runner.fire_t(TSupport.t_user_mail, fake_run=fake_run,
                      t_args=[t_tag],
                      t_kwargs=dict(mode='added_optional', test_item=patterns_dir_list,
                                    addm_group=addm_set[0]['addm_group'],
                                    start_time=start_time, options=kwargs),
                      t_queue=addm_set[0]['addm_group']+'@tentacle.dq2',
                      t_routing_key=mail_r_key)

        """HERE: Wipe old logs for selected items"""
        if wipe:
            OptionalTestsSelect.wipe_last_selected_logs(branch, addm_name, patterns_dir_list)

        for test_composed in test_items_l:
            # TODO: Calc sum of execution time for all selected tests:
            test_w = test_composed.pop('test_time_weight')
            task_r_key = '{}.TExecTest.t_test_exec_threads.{}.t{}'.format(
                addm_set[0]['addm_group'], test_composed.get('pattern_folder_name', 'pattern_folder_name'), test_w)

            for test_item in test_composed.values():
                Runner.fire_t(TPatternExecTest.t_test_exec_threads, fake_run=fake_run, to_sleep=int(test_w),
                              t_queue=addm_set[0]['addm_group'] + '@tentacle.dq2', t_args=[t_tag],
                              t_kwargs=dict(addm_items=addm_set, test_item=test_item),
                              t_routing_key=task_r_key, t_soft_time_limit=HOURS_2)

        # Finish mail:
        Runner.fire_t(TSupport.t_user_mail, fake_run=fake_run,
                      t_args=[t_tag],
                      t_kwargs=dict(mode='finish_optional', test_item=patterns_dir_list,
                                    addm_group=addm_set[0]['addm_group'],
                                    start_time=start_time, options=kwargs),
                      t_queue=addm_set[0]['addm_group']+'@tentacle.dq2',
                      t_routing_key=mail_r_key)
        return True


class TaskPrepare:

    def __init__(self, obj):
        # Initial view requests:
        self.view_obj = obj
        if isinstance(self.view_obj, dict):
            self.options = self.view_obj.get('context')
            self.request = self.view_obj.get('request')
            # Assign generated context for further usage:
            self.selector = self.options.get('selector', {})
            self.user_name = self.view_obj.get('user_name')
            self.user_email = self.view_obj.get('user_email')
        else:
            self.request = obj.request
            self.options = obj.request
            self.user_name = self.request.get('user_name', 'octopus_super')
            self.user_email = self.request.get('user_email', None)
            self.selector = self.request.get('selector', {})

        # Define fake run:
        self.fake_run = False
        self.fake_fun()

        # Get user and mail:
        self.start_time = datetime.datetime.now()
        log.info("<=TaskPrepare=> Prepare tests for user: %s - %s", self.user_name, self.user_email)

        # It's only single test run can include wiping for test_function.
        self.test_function = self.selector.get('test_function', None)

        # Internal statuses:
        self.silent = False
        self.silent_run()
        self.exclude = False
        self.excluding()

        self.refresh = False
        self.wipe = False

        self.p4_synced = False  # We care about to wait for p4 to finish its work, to be sure we teat actual data.
        self.addm_synced = False  # We could do not care if this, just add addm_sync before any test task.
        self.test_balanced = False

        # Sorted\grouped test set:
        self.tests_grouped = dict()

        # NOTE: It can change during process current class!!!!`
        self.t_tag = ''

    def fake_fun(self):
        """
        For debug purposes, just run all tasks as fake_task with showing all inputs and outputs: args, kwargs.
        :return:
        """
        if os.name == "nt":  # Always fake run on local test env:
            self.fake_run = True
            log.debug("<=TaskPrepare=> Fake run self.options: %s", self.options)
            log.debug("<=TaskPrepare=> Fake run self.request: %s", self.request)

        elif self.options.get('fake_run'):
            self.fake_run = True
        log.debug("<=TaskPrepare=> Fake run = %s", self.fake_run)

    def silent_run(self):
        """
        Indicates when do not send any mails.
        :return:
        """
        if self.options.get('silent'):
            self.silent = True
        log.debug("<=TaskPrepare=> Silent run = %s", self.silent)

    def excluding(self):
        """
        Indicates when to use cases group 'excluded' to exclude mentioned test cases from current test run.
        False by default, only useful case to use when run routines or numerous tests with multiple cases.
        :return:
        """
        if self.options.get('exclude'):
            self.exclude = True
        log.debug("<=TaskPrepare=> Will exclude some tests = %s", self.exclude)

    def run_tku_patterns(self):
        """
        Method to run 'tku_patterns' tests.
        :return:
        """
        self.task_tag_generate()
        log.warning("TASK PSEUDO RUNNING in TaskPrepare.run_tku_patterns")

        # 0. Init test mail?
        # self.mail_status(mail_opts=dict(mode='init', view_obj=self.view_obj))

        # 1. Select cases for test
        cases_to_test = self.case_selection()

        # 2. Filter cases grouped by types/branches:
        self.tests_grouped = self.case_sort(cases_to_test)

        # 3. Fire last for p4 sync if needed.
        self.sync_depot()

        # 4. Balance grouped tests on workers based on test_type, tkn_branch
        self.tku_patterns_tests_balance(self.tests_grouped)

        # 8. Start tests mail send:
        log.info("<=TaskPrepare=> HERE: make single mail task to confirm tests were started")

        # 9. Wipe logs when worker is free, if needed
        self.wipe_logs(cases_to_test)

        # 10. Finish all test mail? If we want to show this routine finished, but tests are still run...
        log.info("<=TaskPrepare=> HERE: make single mail task and the end of addm_worker queue")
        return "Finish this run"

    def sync_depot(self):
        """
        Run p4 sync.
        If this function called - then surely wipe latest logs for selected tests.

        When this called - we have already a probably outdated list of cases to test,
            because during p4 sync actual dates and change numbers might change.
        Never mind, user wanted to test selected items, so we will test them even if any
            those cases became unsuitable for previous select (by date, user, change or so).

        :return:
        """
        if self.request.get('refresh'):
            self.wipe = True
            self.refresh = True
            self.p4_synced = False  # To be synced
            log.debug("<=TaskPrepare=> Will execute p4 sync before run tests")
        else:
            self.p4_synced = True  # Let's think we already synced everything:

        # Only sync and parse depot, no ADDM Sync here!
        t_tag = f'tag=t_p4_sync;user_name={self.user_name};fake={self.fake_run};start_time={self.start_time}'
        p4_sync_task = Runner.fire_t(TPatternParse.t_p4_sync, fake_run=self.fake_run, t_args=[t_tag])
        if not self.fake_run:
            log.debug("<=TaskPrepare=> Start waiting for p4_sync_task...")
            if TasksOperations().task_wait_success(p4_sync_task, 'p4_sync_task'):
                log.debug("<=TaskPrepare=> Wait for p4_sync_task is finished, lock released!")
                self.p4_synced = True
                # return self.p4_synced
        else:
            # On fake run we just show this p4 sync is finished OK
            self.p4_synced = True
            # return self.p4_synced

    def wipe_logs(self, test_items):
        if self.test_balanced:
            log.info("<=TaskPrepare=> All tests are balanced and assigned to workers, we now can wipe logs?")

        deleted = []
        if self.request.get('wipe'):
            self.wipe = True
            log.debug("<=TaskPrepare=> Will wipe old logs for selected case(s)")
        elif self.wipe and self.refresh:
            log.debug("<=TaskPrepare=> Forced: Will wipe old logs for selected case(s). By: self.refresh = %s", self.refresh)

        if self.fake_run:
            return []

        for test_item in test_items:
            deleted_log = self.db_logs_wipe(test_item)
            deleted.append(deleted_log)
        return deleted

    def db_logs_wipe(self, test_item):
        test_item_deleted = 'None'
        try:
            if self.test_function:
                log.debug("<=TaskPrepare=> Wipe logs for only test unit: %s", self.test_function)
                test_arg = self.test_function.split(' ')
                test_item_deleted = TestLast.objects.filter(
                    test_py_path__exact=test_item['test_py_path'],
                    tst_class__exact=test_arg[0],
                    tst_name__exact=test_arg[1]).delete()
            else:
                test_item_deleted = TestLast.objects.filter(
                    test_py_path__exact=test_item['test_py_path']).delete()
        except Exception as e:
            log.error("<=DjangoTableOperDel=> delete_old_solo_test_logs Error: %s", e)
        return test_item_deleted

    def case_selection(self):
        """
        Select cases to test using different options.
        At the very end of sorting - sort out by branch or test type.
        Most of internal selections is better to do via TeasCases id field! (Because we always know Cases IDs from backend)
        - Only in exceptional cases use words to sort.
        :return:
        """

        # TODO: Not actually select ALL if we don't get/understand request args?
        # TODO: Sort only pattern test cases?
        queryset = TestCases.objects.all()
        # Most common and usual way to select cases for tests:
        log.debug("self.selector: %s", self.selector)
        if self.selector.get('cases_ids'):
            id_list = self.selector['cases_ids'].split(',')
            log.debug("<=TaskPrepare=> Selecting cases by id: %s", id_list)
            queryset = queryset.filter(id__in=id_list)
        # Older but useful from search perspectives???
        elif self.selector.get('pattern_folder_names'):
            pattern_folder_names = self.selector['pattern_folder_names']
            if isinstance(pattern_folder_names, str):
                pattern_folder_names.split(',')
            log.debug("<=TaskPrepare=> Selecting cases by 'pattern_folder_names: %s", pattern_folder_names)
            queryset = queryset.filter(pattern_folder_name__in=pattern_folder_names)
        # Not sure this is the best solution to sort out
        elif self.selector.get('pattern_folder_name') and not self.selector['pattern_library']:
            log.debug("<=TaskPrepare=> Selecting cases by 'pattern_folder_name': %s", self.selector['pattern_folder_name'])
            queryset = queryset.filter(pattern_folder_name__exact=self.selector['pattern_folder_name'])
        # Current implemented way, but remove it later?
        elif self.selector.get('pattern_folder_name') and self.selector['pattern_library']:
            log.debug("<=TaskPrepare=> Selecting cases by 'pattern_library' AND 'pattern_folder_name': %s", self.selector['pattern_folder_name'])
            queryset = queryset.filter(
                pattern_folder_name__exact=self.selector['pattern_folder_name'],
                pattern_library__exact=self.selector['pattern_library'])
        # Test all cases related to p4 change:
        elif self.selector.get('change'):
            log.debug("<=TaskPrepare=> Selecting cases by 'change': %s", self.selector['change'])
            queryset = queryset.filter(change__exact=self.selector['change'])
        # Test all cases related to p4 change user:
        elif self.selector.get('change_user'):
            log.debug("<=TaskPrepare=> Selecting cases by 'change_user': %s", self.selector['change_user'])
            queryset = queryset.filter(change_user__exact=self.selector['change_user'])
        # Test all cases related to change review if any:
        elif self.selector.get('change_review'):
            log.debug("<=TaskPrepare=> Selecting cases by 'change_review': %s", self.selector['change_review'])
            queryset = queryset.filter(change_review__exact=self.selector['change_review'])
        # Test all cases related to change ticket if any:
        elif self.selector.get('change_ticket'):
            log.debug("<=TaskPrepare=> Selecting cases by 'change_ticket': %s", self.selector['change_ticket'])
            queryset = queryset.filter(change_ticket__exact=self.selector['change_ticket'])
        # Test case with selected test_py - to be removed maybe later?:
        elif self.selector.get('test_py_path'):
            log.debug("<=TaskPrepare=> Selecting cases by 'test_py_path': %s", self.selector['test_py_path'])
            queryset = queryset.filter(test_py_path__exact=self.selector['test_py_path'])
        else:
            # Ignore any unused options:
            pass

        # Queryset strict by branch if needed:
        if self.selector.get('tkn_branch'):
            log.debug("<=TaskPrepare=> Selecting cases by 'tkn_branch': %s", self.selector['tkn_branch'])
            queryset = queryset.filter(tkn_branch__exact=self.selector['tkn_branch'])
        # Queryset strict by test_type:
        if self.selector.get('test_type'):
            log.debug("<=TaskPrepare=> Selecting cases by 'test_type': %s", self.selector['test_type'])
            queryset = queryset.filter(test_type__exact=self.selector['test_type'])

        # log.debug("<=TaskPrepare=> queryset: %s", queryset.query)
        log.debug("<=TaskPrepare=> cases_to_test: %s", queryset.count())
        # log.debug("<=TaskPrepare=> Items: %s", queryset)
        return queryset.order_by('tkn_branch')

    def case_exclusion(self, queryset):
        """
        Should check custom groups for option 'exclude=True'
        and then exclude members of those groups from test routine run.
        Or, maybe only exclude when this was executed by CRON and night routine?
        :return:
        """
        if self.exclude:
            log.info("<=TaskPrepare=> About to exclude some tests which are added to group exclude!")
            log.debug("<=TaskPrepare=> Before exclude: %s", queryset.count())
            excluded_group = TestCasesDetails.objects.get(title__exact='excluded')
            excluded_ids = excluded_group.test_cases.values('id')
            log.debug("Excluded cases are: %s", excluded_ids)
            queryset = queryset.exclude(id__in=excluded_ids)
            log.debug("<=TaskPrepare=> After exclude: %s", queryset.count())
        return queryset

    def case_sort(self, to_test_queryset):
        """
        If user select case(s) to test:
        - split selected on groups by:
        -- test type: tku_patterns/main_python/octo_tests(TBA)
        -- then on groups (for tku_patterns) by branches: tkn_main/tkn_ship

        Later this dict will be used to assign ADDM group for each.

        Note: "octo_tests" should never run in this class!
        :return:
        """

        if self.exclude:
            to_test_queryset = self.case_exclusion(to_test_queryset)

        grouped = dict(
            tku_patterns=dict(
                tkn_main=to_test_queryset.filter(tkn_branch__exact='tkn_main').values(),
                tkn_ship=to_test_queryset.filter(tkn_branch__exact='tkn_ship').values(),
            ),
            main_python=to_test_queryset.filter(test_type__exact='main_python').values(),
            octo_tests=to_test_queryset.filter(test_type__exact='octo_tests').values(),
        )
        # log.debug("<=TaskPrepare=> grouped: %s", grouped)
        return grouped

    def tku_patterns_tests_balance(self, tests_grouped):
        """
        Balance selected and grouped tests between worker groups.

        :param tests_grouped:
        :return:
        """

        tku_patterns_tests = tests_grouped.get('tku_patterns', {})
        log.debug("<=TaskPrepare=> tku_patterns_tests: %s", tku_patterns_tests)

        for branch_k, branch_cases in tku_patterns_tests.items():
            if branch_cases:
                log.debug("<=TaskPrepare=> Balancing tests for branch: '%s'", branch_k)
                # 5. Assign free worker for test cases run
                addm_group = self.addm_group_get_available(tkn_branch=branch_k)
                addm_set = self.addm_set_select(addm_group=addm_group)

                # 6. Sync current ADDM set with actual data from Octopus, after p4 sync finished it's work:
                self.addm_rsync(addm_set)

                for test_item in branch_cases:
                    log.debug("<=TaskPrepare=> test_item: %s", test_item)

                    # 7.1 Fire task for test starting
                    self.mail_status(mail_opts=dict(
                        mode='start', view_obj=self.view_obj, test_item=test_item, addm_set=addm_set))

                    # 7.2 Fire task for test execution
                    self.test_exec(addm_set, test_item)

                    # 7.3 Add mail task after one test, so it show when one test was finished.
                    log.info("<=TaskPrepare=> HERE: for test item make test task")
                    self.mail_status(mail_opts=dict(
                        mode='finish', view_obj=self.view_obj, test_item=test_item, addm_set=addm_set))
            else:
                log.debug("<=TaskPrepare=> This branch had no selected tests to run: '%s'", branch_k)

    def addm_group_get_available(self, tkn_branch):
        """
        Check addm groups for available and mininal loaded worker.
        Depends on branch.
            TBA: Later add dependency on test_type, 'main_python' OR 'tku_patterns' OR 'octo_tests'

        :param tkn_branch:
        :return:
        """

        """DEBUG:"""
        from octo_tku_patterns.user_test_balancer import WorkerGetAvailable
        branch_w = WorkerGetAvailable.branched_w(tkn_branch)
        addm_group = branch_w[0]

        if not self.fake_run:
            addm_group = WorkerGetAvailable().user_test_available_w(branch=tkn_branch, user_mail=self.user_email)
        log.debug("<=TaskPrepare=> Get available addm_group: '%s'", addm_group)
        return addm_group

    def addm_set_select(self, addm_group=None):
        queryset = AddmDev.objects.all()
        if self.options.get('addm_group'):
            log.info("<=TaskPrepare=> ADDM_GROUP from request params: '%s'", self.options.get('addm_group'))
            addm_set = queryset.filter(
                addm_group__exact=self.options.get('addm_group'),
                disables__isnull=True).values()
        else:
            addm_set = queryset.filter(
                addm_group__exact=addm_group,
                disables__isnull=True
            ).values()
        log.info("<=TaskPrepare=> Will use selected addm_set to run test: %s",  addm_set)
        return addm_set

    def addm_rsync(self, addm_set):
        """
        Run task for ADDM rsync command to actualize data on test env from Octopus, after p4 sync finished.
        Task is adding on worker where test would run, so we don't wait this task to finish.

        :param addm_set:
        :return:
        """
        # Only if p4 sync correctly OR we forced it to True:
        addm = addm_set.first()
        if self.p4_synced:
            log.debug("<=TaskPrepare=> Adding task to sync addm group: '%s'", addm['addm_group'])
            t_tag = f'tag=t_addm_rsync_threads;addm_group={addm["addm_group"]};user_name={self.user_name};' \
                    f'fake={self.fake_run};start_time={self.start_time}'
            Runner.fire_t(TPatternParse().t_addm_rsync_threads, fake_run=self.fake_run,
                          t_args=[t_tag], t_kwargs=dict(addm_items=list(addm_set)),
                          t_queue=addm['addm_group'] + '@tentacle.dq2',
                          t_routing_key='TExecTest.t_addm_rsync_threads.{0}'.format(addm['addm_group']))

    def mail_status(self, mail_opts):
        mode = mail_opts.get('mode')

        if not self.silent:
            log.info("<=TaskPrepare=> Mail sending, mode: %s", mode)
            if mail_opts.get('addm_set') and mail_opts.get('test_item'):
                log.debug("<=TaskPrepare=> MAIL when test item and addm set is TRUE")

                addm = mail_opts.get('addm_set').first()
                test_item = mail_opts.get('test_item')

                mail_r_key = f'{addm["addm_group"]}.TSupport.t_user_mail.{mode}'
                t_tag = f'tag=t_user_mail;mode={mode};addm_group={addm["addm_group"]};user_name={self.user_name};' \
                        f'test_py_path={test_item["test_py_path"]}'

                Runner.fire_t(TSupport.t_user_test, fake_run=self.fake_run, t_args=[t_tag],
                              t_kwargs=dict(mail_opts=mail_opts),
                              t_queue=addm['addm_group']+'@tentacle.dq2', t_routing_key=mail_r_key)

            elif mode == 'init':
                log.debug("<=TaskPrepare=> MAIL when INIT")
                TMail().user_test(mail_opts)
            else:
                log.debug("<=TaskPrepare=> MAIL when ELSE")
                TMail().user_test(mail_opts)
        else:
            log.info("<=TaskPrepare=> Mail silent mode. Do not send massages. Current stage: %s", mode)

    def test_exec(self, addm_set, test_item):
        """
        Fire task of test execution.
            TODO: Maybe assign soft time limit based on test weight + some minutes?
        :param addm_set:
        :param test_item:
        :return:
        """
        addm = addm_set.first()
        log.info("<=TaskPrepare=> Add task - test exec. Not executing now, just log!")

        task_r_key = '{}.TExecTest.t_test_exec_threads.{}'.format(addm['addm_group'], test_item["pattern_folder_name"])
        t_tag = f'tag=t_test_exec_threads;type=user_routine;branch={test_item["tkn_branch"]};' \
                f'addm_group={addm["addm_group"]};user_name={self.user_name};' \
                f'refresh={self.refresh};test_py_path={test_item["test_py_path"]}'

        # Test task exec:
        Runner.fire_t(TPatternExecTest.t_test_exec_threads, fake_run=self.fake_run,
                      t_queue=addm['addm_group'] + '@tentacle.dq2', t_args=[t_tag],
                      t_kwargs=dict(addm_items=list(addm_set), test_item=test_item,
                                    test_function=self.test_function),
                      t_routing_key=task_r_key, t_soft_time_limit=7200)

    def task_tag_generate(self):
        """Just make a task tag for this routine"""
        task_string = 'tag=t_routine_user_tests;type=routine;branch={tkn_branch};' \
                      'addm_group={addm_group};user_name={user_name};refresh={refresh};{pattern_library}/{pattern_folder_name}'
        t_tag_d = task_string.format(
            tkn_branch=self.selector.get('tkn_branch'),
            addm_group=self.selector.get('addm_group'),
            pattern_library=self.selector.get('pattern_library'),
            pattern_folder_name=self.selector.get('pattern_folder_name'),
            user_name=self.user_name,
            refresh=self.request.get('refresh'),
        )
        # log.debug("<=TaskPrepare=> User test user_test_add: \n%s", t_tag_d)
        self.t_tag = t_tag_d

    # TODO: ????
    def test_and_addm_check(self, addm_set, test_item):
        if not addm_set or not test_item:
            log.debug("<=TaskPrepare=> test_execute_web: "
                      "Cannot start user test no addm set or test item can be found in database %s", self.user_name)
            msg = "Cannot get addm_set or test_item from local database."
            Runner.fire_t(TSupport.t_user_mail, fake_run=self.fake_run, t_args=[self.t_tag],
                          t_kwargs=dict(mode='failed', start_time=self.start_time, options=self.options,
                                        err_out='Test cannot be added to queue - no addm set or test items found in DB! ' + msg))