import os
import datetime

from octo_tku_patterns.models import TestLast, TestCases

from run_core.models import AddmDev

from octo_tku_patterns.tasks import TPatternParse, TPatternExecTest

from octo.helpers.tasks_run import Runner
from octo.helpers.tasks_oper import TasksOperations
from octo.helpers.tasks_helpers import TMail

from octo.tasks import TSupport

# Python logger
import logging

log = logging.getLogger("octo.octologger")


# class TaskPrepare(object):
#
#     def __init__(self, obj):
#         # Initial view requests:
#         if hasattr(obj.request, 'GET'):
#             self.options = obj.request.GET
#             # Assign generated context for further usage:
#             self.selector = obj.context.get('selector', {})
#             self.user_name = obj.request.user
#             self.user_email = obj.request.user.email
#         else:
#             self.options = obj.request
#             self.user_name = self.options.get('user_name', 'octopus_super')
#             self.user_email = self.options.get('user_email', None)
#             self.selector = self.options.get('selector', {})
#
#         # Define fake run:
#         self.fake_run = False
#         self.fake_fun()
#
#         # Get user and mail:
#         self.start_time = datetime.datetime.now()
#         log.info("<=TaskPrepare=> Prepare tests for user: %s - %s", self.user_name, self.user_email)
#
#         # It's only single test run can include wiping for test_function.
#         self.test_function = self.options.get('test_function', None)
#
#         # Internal statuses:
#         self.silent = False
#         self.refresh = False
#         self.wipe = False
#
#         self.p4_synced = False  # We care about to wait for p4 to finish its work, to be sure we teat actual data.
#         self.addm_synced = False  # We could do not care if this, just add addm_sync before any test task.
#         self.test_balanced = False
#
#         # Sorted\grouped test set:
#         self.tests_grouped = dict()
#
#         # NOTE: It can change during process current class!!!!
#         self.t_tag = ''
#
#     def fake_fun(self):
#         if os.name == "nt":  # Always fake run on local test env:
#             self.fake_run = True
#         elif self.options.get('fake_run'):
#             self.fake_run = True
#         log.debug("<=TaskPrepare=> Fake run = %s", self.fake_run)
#
#     def silent_run(self):
#         if self.options.get('silent'):
#             self.silent = True
#         log.debug("<=TaskPrepare=> Silent run = %s", self.silent)
#
#     # TODO: This should be executed as separate task:
#     def run_tku_patterns(self):
#         """
#         Method to run 'tku_patterns' tests.
#         :return:
#         """
#         self.task_tag_generate()
#
#         # 0. Init test mail?
#         self.mail_init()
#
#         # 1. Select cases for test
#         cases_to_test = self.case_selection()
#
#         # 2. Filter cases grouped by types/branches:
#         self.tests_grouped = self.case_sort(cases_to_test)
#
#         # 3. Fire last for p4 sync if needed.
#         self.sync_depot()
#
#         # 4. Balance grouped tests on workers based on test_type, tkn_branch
#         self.tku_patterns_tests_balance(self.tests_grouped)
#
#         # 8. Start tests mail send:
#         log.info("<=TaskPrepare=> HERE: make single mail task to confirm tests were started")
#
#         # 9. Wipe logs when worker is free, if needed
#         self.wipe_logs(cases_to_test)
#
#         # 10. Finish all test mail? If we want to show this routine finished, but tests are still run...
#         log.info("<=TaskPrepare=> HERE: make single mail task and the end of addm_worker queue")
#
#     def sync_depot(self):
#         """
#         Run p4 sync.
#         If this function called - then surely wipe latest logs for selected tests.
#
#         When this called - we have already a probably outdated list of cases to test,
#             because during p4 sync actual dates and change numbers might change.
#         Never mind, user wanted to test selected items, so we will test them even if any
#             those cases became unsuitable for previous select (by date, user, change or so).
#
#         :return:
#         """
#         if self.options.get('refresh'):
#             self.wipe = True
#             self.refresh = True
#             self.p4_synced = False  # To be synced
#             log.debug("<=TaskPrepare=> Will execute p4 sync before run tests")
#         else:
#             self.p4_synced = True  # Let's think we already synced everything:
#
#         # Only sync and parse depot, no ADDM Sync here!
#         p4_sync_task = Runner.fire_t(TPatternParse.t_p4_sync, fake_run=self.fake_run, t_args=['<=TaskPrepare=> p4 sync'])
#         if not self.fake_run:
#             log.debug("<=TaskPrepare=> Start waiting for p4_sync_task...")
#             if TasksOperations().task_wait_success(p4_sync_task, 'p4_sync_task'):
#                 log.debug("<=TaskPrepare=> Wait for p4_sync_task is finished, lock released!")
#                 self.p4_synced = True
#                 # return self.p4_synced
#         else:
#             # On fake run we just show this p4 sync is finished OK
#             self.p4_synced = True
#             # return self.p4_synced
#
#     def wipe_logs(self, test_items):
#         if self.test_balanced:
#             log.info("<=TaskPrepare=> All tests are balanced and assigned to workers, we now can wipe logs?")
#
#         deleted = []
#         if self.options.get('wipe'):
#             self.wipe = True
#             log.debug("<=TaskPrepare=> Will wipe old logs for selected case(s)")
#         elif self.wipe and self.refresh:
#             log.debug("<=TaskPrepare=> Forced: Will wipe old logs for selected case(s). By: self.refresh = %s", self.refresh)
#
#         if self.fake_run:
#             return []
#
#         for test_item in test_items:
#             deleted_log = self.db_logs_wipe(test_item)
#             deleted.append(deleted_log)
#         return deleted
#
#     def db_logs_wipe(self, test_item):
#         test_item_deleted = 'None'
#         try:
#             if self.test_function:
#                 log.debug("<=TaskPrepare=> Wipe logs for only test unit: %s", self.test_function)
#                 test_arg = self.test_function.split(' ')
#                 test_item_deleted = TestLast.objects.filter(
#                     test_py_path__exact=test_item['test_py_path'],
#                     tst_class__exact=test_arg[0],
#                     tst_name__exact=test_arg[1]).delete()
#             else:
#                 test_item_deleted = TestLast.objects.filter(
#                     test_py_path__exact=test_item['test_py_path']).delete()
#         except Exception as e:
#             log.error("<=DjangoTableOperDel=> delete_old_solo_test_logs Error: %s", e)
#         return test_item_deleted
#
#     def case_selection(self):
#         """
#         Select cases to test using different options.
#         At the very end of sorting - sort out by branch or test type.
#         Most of internal selections is better to do via TeasCases id field! (Because we always know Cases IDs from backend)
#         - Only in exceptional cases use words to sort.
#         :return:
#         """
#
#         # TODO: Not actually select ALL if we don't get/understand request args?
#         queryset = TestCases.objects.all()
#         # Most common and usual way to select cases for tests:
#         log.debug("self.selector: %s", self.selector)
#         if self.selector.get('cases_ids'):
#             id_list = self.selector['cases_ids'].split(',')
#             log.debug("<=TaskPrepare=> Selecting cases by id: %s", id_list)
#             queryset = queryset.filter(id__in=id_list)
#         # Older but useful from search perspectives???
#         elif self.selector.get('pattern_folder_names'):
#             pattern_folder_names = self.selector['pattern_folder_names']
#             if isinstance(pattern_folder_names, str):
#                 pattern_folder_names.split(',')
#             log.debug("<=TaskPrepare=> Selecting cases by 'pattern_folder_names: %s", pattern_folder_names)
#             queryset = queryset.filter(pattern_folder_name__in=pattern_folder_names)
#         # Not sure this is the best solution to sort out
#         elif self.selector.get('pattern_folder_name') and not self.selector['pattern_library']:
#             log.debug("<=TaskPrepare=> Selecting cases by 'pattern_folder_name': %s", self.selector['pattern_folder_name'])
#             queryset = queryset.filter(pattern_folder_name__exact=self.selector['pattern_folder_name'])
#         # Current implemented way, but remove it later?
#         elif self.selector.get('pattern_folder_name') and self.selector['pattern_library']:
#             log.debug("<=TaskPrepare=> Selecting cases by 'pattern_library' AND 'pattern_folder_name': %s", self.selector['pattern_folder_name'])
#             queryset = queryset.filter(
#                 pattern_folder_name__exact=self.selector['pattern_folder_name'],
#                 pattern_library__exact=self.selector['pattern_library'])
#         # Test all cases related to p4 change:
#         elif self.selector.get('change'):
#             log.debug("<=TaskPrepare=> Selecting cases by 'change': %s", self.selector['change'])
#             queryset = queryset.filter(change__exact=self.selector['change'])
#         # Test all cases related to p4 change user:
#         elif self.selector.get('change_user'):
#             log.debug("<=TaskPrepare=> Selecting cases by 'change_user': %s", self.selector['change_user'])
#             queryset = queryset.filter(change_user__exact=self.selector['change_user'])
#         # Test all cases related to change review if any:
#         elif self.selector.get('change_review'):
#             log.debug("<=TaskPrepare=> Selecting cases by 'change_review': %s", self.selector['change_review'])
#             queryset = queryset.filter(change_review__exact=self.selector['change_review'])
#         # Test all cases related to change ticket if any:
#         elif self.selector.get('change_ticket'):
#             log.debug("<=TaskPrepare=> Selecting cases by 'change_ticket': %s", self.selector['change_ticket'])
#             queryset = queryset.filter(change_ticket__exact=self.selector['change_ticket'])
#         # Test case with selected test_py - to be removed maybe later?:
#         elif self.selector.get('test_py_path'):
#             log.debug("<=TaskPrepare=> Selecting cases by 'test_py_path': %s", self.selector['test_py_path'])
#             queryset = queryset.filter(test_py_path__exact=self.selector['test_py_path'])
#         else:
#             # Ignore any unused options:
#             pass
#
#         # Queryset strict by branch if needed:
#         if self.selector.get('tkn_branch'):
#             log.debug("<=TaskPrepare=> Selecting cases by 'tkn_branch': %s", self.selector['tkn_branch'])
#             queryset = queryset.filter(tkn_branch__exact=self.selector['tkn_branch'])
#         # Queryset strict by test_type:
#         if self.selector.get('test_type'):
#             log.debug("<=TaskPrepare=> Selecting cases by 'test_type': %s", self.selector['test_type'])
#             queryset = queryset.filter(test_type__exact=self.selector['test_type'])
#
#         # log.debug("<=TaskPrepare=> queryset: %s", queryset.query)
#         log.debug("<=TaskPrepare=> cases_to_test: %s", queryset.count())
#         log.debug("<=TaskPrepare=> Items: %s", queryset)
#         return queryset.order_by('tkn_branch')
#
#     @staticmethod
#     def case_sort(to_test_queryset):
#         """
#         If user select case(s) to test:
#         - split selected on groups by:
#         -- test type: tku_patterns/main_python/octo_tests(TBA)
#         -- then on groups (for tku_patterns) by branches: tkn_main/tkn_ship
#
#         Later this dict will be used to assign ADDM group for each.
#
#         Note: "octo_tests" should never run in this class!
#         :return:
#         """
#         grouped = dict(
#             tku_patterns=dict(
#                 tkn_main=to_test_queryset.filter(tkn_branch__exact='tkn_main').values(),
#                 tkn_ship=to_test_queryset.filter(tkn_branch__exact='tkn_ship').values(),
#             ),
#             main_python=to_test_queryset.filter(test_type__exact='main_python').values(),
#             octo_tests=to_test_queryset.filter(test_type__exact='octo_tests').values(),
#         )
#         log.debug("<=TaskPrepare=> grouped: %s", grouped)
#         return grouped
#
#     def tku_patterns_tests_balance(self, tests_grouped):
#         """
#         Balance selected and grouped tests between worker groups.
#
#         :param tests_grouped:
#         :return:
#         """
#
#         tku_patterns_tests = tests_grouped.get('tku_patterns', {})
#         log.debug("<=TaskPrepare=> tku_patterns_tests: %s", tku_patterns_tests)
#
#         for branch_k, branch_cases in tku_patterns_tests.items():
#             if branch_cases:
#                 log.debug("<=TaskPrepare=> Balancing tests for branch: '%s'", branch_k)
#                 # 5. Assign free worker for test cases run
#                 addm_group = self.addm_group_get_available(tkn_branch=branch_k)
#                 addm_set = self.addm_set_select(addm_group=addm_group)
#
#                 # 6. Sync current ADDM set with actual data from Octopus, after p4 sync finished it's work:
#                 self.addm_rsync(addm_set)
#
#                 for test_item in branch_cases:
#                     log.debug("<=TaskPrepare=> test_item: %s", test_item)
#
#                     # 7.1 Fire task for test starting
#                     self.mail_start(addm_set, test_item)
#
#                     # 7.2 Fire task for test execution
#                     self.test_exec(addm_set, test_item)
#
#                     # 7.3 Add mail task after one test, so it show when one test was finished.
#                     log.info("<=TaskPrepare=> HERE: for test item make test task")
#                     self.mail_finish(addm_set, test_item)
#             else:
#                 log.debug("<=TaskPrepare=> This branch had no selected tests to run: '%s'", branch_k)
#
#     def addm_group_get_available(self, tkn_branch):
#         """
#         Check addm groups for available and mininal loaded worker.
#         Depends on branch.
#             TBA: Later add dependency on test_type, 'main_python' OR 'tku_patterns' OR 'octo_tests'
#
#         :param tkn_branch:
#         :return:
#         """
#
#         """DEBUG:"""
#         from octo_tku_patterns.user_test_balancer import WorkerGetAvailable
#         branch_w = WorkerGetAvailable.branched_w(tkn_branch)
#         addm_group = branch_w[0]
#
#         if not self.fake_run:
#             addm_group = WorkerGetAvailable().user_test_available_w(branch=tkn_branch, user_mail=self.user_email)
#         log.debug("<=TaskPrepare=> Get available addm_group: '%s'", addm_group)
#         return addm_group
#
#     def addm_set_select(self, addm_group=None):
#         queryset = AddmDev.objects.all()
#         if self.options.get('addm_group'):
#             log.info("<=TaskPrepare=> ADDM_GROUP from request params: '%s'", self.options.get('addm_group'))
#             addm_set = queryset.filter(
#                 addm_group__exact=self.options.get('addm_group'),
#                 disables__isnull=True).values()
#         else:
#             addm_set = queryset.filter(
#                 addm_group__exact=addm_group,
#                 disables__isnull=True
#             ).values()
#         log.info("<=TaskPrepare=> Will use selected addm_set to run test: %s",  addm_set)
#         return addm_set
#
#     def addm_rsync(self, addm_set):
#         """
#         Run task for ADDM rsync command to actualize data on test env from Octopus, after p4 sync finished.
#         Task is adding on worker where test would run, so we don't wait this task to finish.
#
#         :param addm_set:
#         :return:
#         """
#         # Only if p4 sync correctly OR we forced it to True:
#         addm = addm_set.first()
#         if self.p4_synced:
#             log.debug("<=TaskPrepare=> Adding task to sync addm group: '%s'", addm['addm_group'])
#             t_tag = "{};addm_group={}".format('t_addm_rsync_threads', addm['addm_group'])
#             Runner.fire_t(TPatternParse().t_addm_rsync_threads, fake_run=self.fake_run,
#                           t_args=[t_tag], t_kwargs=dict(addm_items=list(addm_set)),
#                           t_queue=addm['addm_group'] + '@tentacle.dq2',
#                           t_routing_key='TExecTest.t_addm_rsync_threads.{0}'.format(addm['addm_group']))
#
#     def mail_init(self):
#         """
#         Indicates when this routine was started.
#         :return:
#         """
#         # Send initial mail:
#         if not self.fake_run and not self.silent:
#             log.info("<=TaskPrepare=> Send mail - routine now in progress...")
#             TMail().user_t(mode='added', options=self.options, test_item=self.tests_grouped)
#         else:
#             log.info("<=TaskPrepare=> FAKE Send mail - routine now in progress...")
#
#     def mail_start(self, addm_set, test_item):
#         if not self.silent:
#             # Start test mail:
#             addm = addm_set.first()
#             log.info("<=TaskPrepare=> Add task - test started. Not executing now, just log!")
#
#             mail_r_key = '{}.TSupport.t_user_mail.start.{}'.format(addm['addm_group'], test_item["pattern_folder_name"])
#             t_tag = f'tag=t_user_mail;branch={test_item["tkn_branch"]};' \
#                     f'addm_group={addm["addm_group"]};user_name={self.user_name};' \
#                     f'refresh={self.refresh};test_py_path={test_item["test_py_path"]}'
#
#             Runner.fire_t(TSupport.t_user_mail, fake_run=self.fake_run,
#                           t_args=[t_tag],
#                           t_kwargs=dict(mode='start',
#                                         test_item=test_item,
#                                         addm_group=addm['addm_group'],
#                                         start_time=self.start_time,
#                                         options=self.options),
#                           t_queue=addm['addm_group']+'@tentacle.dq2',
#                           t_routing_key=mail_r_key)
#
#     def mail_finish(self, addm_set, test_item):
#         if not self.silent:
#             # Finish mail:
#             addm = addm_set.first()
#             log.info("<=TaskPrepare=> Add task - test finish. Not executing now, just log!")
#
#             mail_r_key = '{}.TSupport.t_user_mail.finish.{}'.format(addm['addm_group'], test_item["pattern_folder_name"])
#             t_tag = f'tag=t_user_mail;branch={test_item["tkn_branch"]};' \
#                     f'addm_group={addm["addm_group"]};user_name={self.user_name};' \
#                     f'refresh={self.refresh};test_py_path={test_item["test_py_path"]}'
#
#             Runner.fire_t(TSupport.t_user_mail, fake_run=self.fake_run, t_args=[t_tag],
#                           t_kwargs=dict(mode='finish',
#                                         test_item=test_item,
#                                         addm_group=addm['addm_group'],
#                                         start_time=self.start_time,
#                                         options=self.options),
#                           t_queue=addm['addm_group']+'@tentacle.dq2',
#                           t_routing_key=mail_r_key)
#
#     def test_exec(self, addm_set, test_item):
#         """
#         Fire task of test execution.
#             TODO: Maybe assign soft time limit based on test weight + some minutes?
#         :param addm_set:
#         :param test_item:
#         :return:
#         """
#         addm = addm_set.first()
#         log.info("<=TaskPrepare=> Add task - test exec. Not executing now, just log!")
#
#         task_r_key = '{}.TExecTest.t_test_exec_threads.{}'.format(addm['addm_group'], test_item["pattern_folder_name"])
#         t_tag = f'tag=t_test_exec_threads;type=routine;branch={test_item["tkn_branch"]};' \
#                 f'addm_group={addm["addm_group"]};user_name={self.user_name};' \
#                 f'refresh={self.refresh};test_py_path={test_item["test_py_path"]}'
#
#         # Test task exec:
#         Runner.fire_t(TPatternExecTest.t_test_exec_threads, fake_run=self.fake_run,
#                       t_queue=addm['addm_group'] + '@tentacle.dq2', t_args=[t_tag],
#                       t_kwargs=dict(addm_items=list(addm_set), test_item=test_item,
#                                     test_function=self.test_function),
#                       t_routing_key=task_r_key, t_soft_time_limit=7200)
#
#     def task_tag_generate(self):
#         """Just make a task tag for this routine"""
#         task_string = 'tag=t_routine_user_tests;type=routine;branch={tkn_branch};' \
#                       'addm_group={addm_group};user_name={user_name};refresh={refresh};{pattern_library}/{pattern_folder_name}'
#         t_tag_d = task_string.format(
#             tkn_branch=self.selector.get('tkn_branch'),
#             addm_group=self.selector.get('addm_group'),
#             pattern_library=self.selector.get('pattern_library'),
#             pattern_folder_name=self.selector.get('pattern_folder_name'),
#             user_name=self.user_name,
#             refresh=self.options.get('refresh'),
#         )
#         log.debug("<=TaskPrepare=> User test test_execute_web: \n%s", t_tag_d)
#         self.t_tag = t_tag_d
#
#     # TODO: ????
#     def test_and_addm_check(self, addm_set, test_item):
#         if not addm_set or not test_item:
#             log.debug("<=TaskPrepare=> test_execute_web: "
#                       "Cannot start user test no addm set or test item can be found in database %s", self.user_name)
#             msg = "Cannot get addm_set or test_item from local database."
#             Runner.fire_t(TSupport.t_user_mail, fake_run=self.fake_run, t_args=[self.t_tag],
#                           t_kwargs=dict(mode='failed', start_time=self.start_time, options=self.options,
#                                         err_out='Test cannot be added to queue - no addm set or test items found in DB! ' + msg))
