"""
Script to execute local operations like:
Parse configs and save data to tables.
Parse patterns.

Everything which run on MNG VM

"""

import collections
import itertools
import hashlib
import logging
import os
import os.path
import re
import subprocess
from datetime import datetime, timezone, timedelta
from time import time

import pytz
from django.conf import settings
from django.db.models import Max
from django.db.models.query import QuerySet

from octo_tku_patterns.models import TestCases
from octo_tku_patterns.table_oper import PatternsDjangoModelRaw
from octo_tku_upload.models import TkuPackagesNew as TkuPackages
from run_core.models import AddmDev, ADDMCommands
from run_core.p4_operations import PerforceOperations

# Python logger
log = logging.getLogger("octo.octologger")


class LocalPatternsParse:
    """
    This is local parsing procedure.
    It run the process like file walker, but simpler. Get all files stored on Octopus file system, update database
    and compose paths to test file, folder and depot path to each product folder. Later those parts will be used
    in tests and gathering perforce information - changes, mod. dates etc.
    """

    @staticmethod
    def is_test(pattern, text):
        return pattern.search(text) is not None

    def walk_fs_tests(self, local_depot_path):
        """
        Use os.filewalk to build all paths to test.py and attributes such as:
            Pattern library if any, Pattern folder, or name of folder where tests/test.py was found.

        Main depot: /home/user/TH_Octopus/perforce/addm/
            Can include test.py from patterns of even code base:
            Save full path to test.py and all needed attributes:
                If no pattern - save as just dir?

            {
            "test_py_path": "/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE/Windows/tests/test.py",
            "test_py_path_template": "{}/addm/tkn_main/tku_patterns/STORAGE/Windows/tests/test.py",
            "test_dir_path": "/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE/Windows/tests",
            "test_dir_path_template": "{}/addm/tkn_main/tku_patterns/STORAGE/Windows/tests",
            "test_type": "tku_patterns",
            "tkn_branch": "tkn_main",
            "pattern_library": "STORAGE",
            "pattern_folder_name": "Windows",
            "pattern_folder_path": "/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE/Windows",
            "test_case_depot_path": "//addm/tkn_main/tku_patterns/STORAGE/Windows",
            "pattern_library_path": "/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE"
          }

        :param local_depot_path: path to local depot were start to find all test.py
        :return: show amount of tests data were parsed
        """

        pattern = re.compile(r'^test[\w]*\.py')
        if settings.DEV:
            p4_workspace = "/mnt/g/perforce"
        else:
            p4_workspace = "/home/user/TH_Octopus/perforce"

        octo_workspace = p4_workspace
        iters = 0
        log.info(f"Parsing local FS: {octo_workspace} depot: {local_depot_path}")

        walked_test_data = []
        for root, dirs, files in os.walk(local_depot_path, topdown=False):
            iters += 1
            for name in files:  # Iter over all files in path:
                if self.is_test(pattern, name):  # Check only test.py files
                    test_py_path = os.path.join(root, name)  # Compose full path to test.py path
                    test_dict = dict(
                        test_py_path=test_py_path,
                        test_py_path_template=test_py_path.replace(octo_workspace, "{}"),
                        test_dir_path=root,
                        test_dir_path_template=root.replace(octo_workspace, "{}"),
                    )
                    # Find branch in path:
                    if 'tkn_main' in root:
                        tkn_branch = 'tkn_main'
                    elif 'tkn_ship' in root:
                        tkn_branch = 'tkn_ship'
                    else:
                        tkn_branch = 'not_set'

                    if 'tku_patterns' in root:  # Check if current path is related to tku_patterns:
                        split_root = root.split(os.sep)[
                                     6:]  # Cut first n dirs until 'tkn_main' /home/user/TH_Octopus/perforce/addm/tkn_main
                        test_dict.update(
                            test_type='tku_patterns',
                            tkn_branch=tkn_branch,
                            pattern_library=os.path.basename(os.path.dirname(os.path.dirname(root))),
                            pattern_folder_name=os.path.basename(os.path.dirname(root)),
                            pattern_folder_path=os.path.dirname(root),
                            test_case_depot_path=os.path.dirname(root).replace(octo_workspace, '/'),
                            test_case_dir='/'.join(split_root),
                            pattern_library_path=os.path.dirname(os.path.dirname(root)),
                        )
                        # Temporary fix fot cases when CLOUD lib have two different dir hierarchy levels
                        if 'CLOUD' in root:
                            test_dict['pattern_library'] = 'CLOUD'
                    elif 'main/code/python' in root:
                        log.info(root.split(os.sep))
                        split_root = root.split(os.sep)[5:]  # Cut n dirs until //addm/main/code/python
                        # log.info(f"code -  case dir: {split_root} path: {root}")
                        test_dict.update(
                            test_type='main_python',
                            tkn_branch=tkn_branch,
                            test_case_dir='/'.join(split_root),
                            test_case_depot_path=root.replace(octo_workspace, '/')
                        )
                    elif 'addm/rel/branches' in root:
                        split_root = root.split(os.sep)[5:]
                        test_dict.update(
                            test_type='addm_rel',
                            tkn_branch=tkn_branch,
                            test_case_dir='/'.join(split_root),
                            test_case_depot_path=os.path.dirname(root).replace(octo_workspace, '/')
                        )
                    elif 'tkn_sandbox' in root:
                        # split_root = root.split(os.sep)[5:]
                        pass
                    elif 'product_content' in root:
                        # Cut n dirs until product_content in  /home/user/TH_Octopus/perforce/addm/tkn_ship/product_content
                        split_root = root.split(os.sep)[6:]
                        # log.info(f"product_content - case dir: {split_root} path: {root} ")
                        test_dict.update(
                            test_type='product_content',
                            tkn_branch=tkn_branch,
                            test_case_dir='/'.join(split_root),
                            test_case_depot_path=os.path.dirname(root).replace(octo_workspace, '/'),
                        )
                    elif 'edp' in root:
                        # Cut n dirs until product_content in  /home/user/TH_Octopus/perforce/addm/tkn_ship/edp
                        split_root = root.split(os.sep)[6:]
                        test_dict.update(
                            test_type='epd',
                            tkn_branch=tkn_branch,
                            test_case_dir='/'.join(split_root),
                            test_case_depot_path=os.path.dirname(root).replace(octo_workspace, '/'),
                        )
                    # If any other place:
                    else:
                        # Cut just first 4 dirs
                        split_root = root.split(os.sep)[5:]
                        test_dict.update(
                            test_type='other',
                            tkn_branch=tkn_branch,
                            test_case_dir='/'.join(split_root),
                            test_case_depot_path=os.path.dirname(root).replace(octo_workspace, '/')
                        )
                    walked_test_data.append(test_dict)

        return walked_test_data

    @staticmethod
    def ins_or_upd_test_case(dict_test_case):
        assert isinstance(dict_test_case, dict)
        try:
            updated, create_new = TestCases.objects.update_or_create(
                test_py_path=dict_test_case.get('test_py_path'),
                defaults=dict(dict_test_case),
            )
            if create_new:
                print(f"New pattern saved: updated {updated}, create_new {create_new}, details {dict_test_case}")
            # if updated:
            #     print("Pattern info has been updated {}".format(updated))
        except Exception as e:
            msg = "<=LocalOper=> get_all_files: Error: {} Details {} ".format(e, dict_test_case)
            print(msg)
            raise Exception(msg)


class LocalPatternsP4Parse:
    """
    This is perforce parsing procedure.
    It run usual perforce commands like 'changes', 'fstat' - to get pattern details like: date of change, number
    of p4 change and description with tickets and jira.
    This information stores in same database as local parsing, and number of changes and dates of changes are used
    to select the proper amount of patterns to test for any period of time.
    """

    def __init__(self):
        """ New """
        self.dep_path = '/home/user/TH_Octopus/perforce/addm/'
        self.lon_tz = pytz.timezone('Europe/London')
        # Regexes for parsing:
        self.ticket_r = re.compile(r"(?P<ticket>(?:DRDC|DRUD)\d+-\d+|(?i)Esc\s+\d+)")
        self.escalation_r = re.compile(r"(?P<ticket>(?i)Esc\s+\d+)")
        self.review_r = re.compile(r"(?i)(?:Review\s+#|@)(?P<review>\d+)")

    # noinspection PyPep8Naming
    @staticmethod
    def chunkIt(seq, num):
        avg = len(seq) / float(num)
        out = collections.deque()
        last = 0.0

        while last < len(seq):
            out.append(seq[int(last):int(last + avg)])
            # print("<=TestPrepCases=> chunk - seq[%s:int(%s)]", int(last), int(last + avg))
            last += avg
        return out

    def parse_local_test(self, path_to_depot=None):
        """
        Parse local file system with os.filewalker.
        :type path_to_depot: basestring
        :return list of test cases dicts
        """
        if not path_to_depot:
            path_to_depot = self.dep_path
        parsed_test_files = LocalPatternsParse().walk_fs_tests(local_depot_path=path_to_depot)
        return parsed_test_files

    def parse_p4_change_text(self, change):
        """
        Parse single changelist for desc.
        Change is the list of latest changes for all files in pattern folder path.
        It include all files and any first item is enough to use for parsing.

        This func use output of > p4 changes -t -m1 -l //addm/tkn_main/tku_patterns/CORE/ActuateeReports/...
        Only one latest change will be shown by this cmd.

        Examples for parsing:
        Esc 111986 - HostContainer name attributes | Approved in CC by Duncan and Dima O.
        INTERNAL|RFE|DRDC1-7352|Report compatibility level of SQL Server database|@706102
        Internal|TESTS|NO JIRA|Added additional test option|@NOREVIEW
        DRUD1-21651, Fix Mirantis OpenStack
        CUSTOMER | BUG | DRDC1-10021 | TELSTRA - Do not get CPE IDs for ambiguous W2K3 servers | @718820
        DRUD1-21527, Add linkage support for cloud file systems. Review #715400 by Craig


        :param change:
        :return:
        """
        assert isinstance(change, list)

        change_desc_dict = dict(description="None",
                                change_user="None",
                                change_num="None",
                                review="None",
                                ticket="None")
        # description = 'None'
        if isinstance(change, list):
            first_change = change[0]
            assert isinstance(first_change, dict)
            if first_change.get('desc'):
                description_raw = first_change['desc']
                change_user = first_change['user']
                change_num = first_change['change']
                review = re.search(self.review_r, description_raw)
                ticket = re.search(self.ticket_r, description_raw)
                escalation = re.match(self.escalation_r, description_raw)
                description = description_raw.replace('\n', "").replace('"', "").replace("'", '')

                if not review:
                    review = ""  # Better to leave empty
                else:
                    review = "#" + str(review.group('review'))

                if not ticket:
                    if escalation:
                        ticket = escalation.group('ticket')
                    else:
                        ticket = ""  # Better to leave empty
                else:
                    ticket = ticket.group('ticket')
                change_desc_dict.update(description=description,
                                        change_user=change_user,
                                        change_num=change_num,
                                        review=review,
                                        ticket=ticket)
            else:
                pass
                # description = "No description for this change."+str(first_change['change'])
                # change_desc_dict['description'] = description
        else:
            log.info("There is no description for change %s", change)
        return change_desc_dict

    @staticmethod
    def insert_parsed_test(parsed_test_files):
        """
        Inserting parsed test cases dicts into DB with update_or_create method.
        :type parsed_test_files: list
        """
        assert isinstance(parsed_test_files, list)
        for item in parsed_test_files:
            LocalPatternsParse.ins_or_upd_test_case(item)

    def compare_changes_iter(self, test_cases, sync_force=False, p4_conn=None):
        """
        Compare local changes # with remote p4 depot change. Then parse if remote > local and save new.
        This run with list of cases at once.
        :param test_cases:
        :param sync_force:
        :param p4_conn:
        :return:
        """
        assert isinstance(test_cases, QuerySet)

        iters = 0
        for test_case in test_cases:
            iters += 1
            # get latest change from depot
            ts = time()
            latest_change = PerforceOperations().get_p4_changes(path=test_case.test_case_depot_path, p4_conn=p4_conn)[0]

            if int(latest_change.get('change', 0)) > int(test_case.change if test_case.change else 0):
                log.debug("Parsing ans saving new change! %s", iters)
                self.parse_and_save_changes(test_case, latest_change, sync_force, p4_conn=p4_conn)
                log.debug('Processing p4 changes and save took: %s ', time() - ts)
            else:
                log.debug("Skip, changes are eq! %s", iters)
                log.debug('Processing p4 changes took: %s ', time() - ts)
                # print("Change is latest - skip update and sync steps! {} {}".format(
                #     test_case.change, test_case_name))
                pass

    def compare_change_thread(self, test_case, sync_force, th_name, test_q, conn_q):
        """
        Compare local changes # with remote p4 depot change. Then parse if remote > local and save new.
        This run with one case item at once.

        NOTE: Somehow it update Tripwire and TripwireEnterprise as same P4 details...

        :param test_case:
        :param sync_force:
        :param th_name:
        :param test_q:
        :param conn_q:
        :return:
        """
        msg = ''
        p4_conn = conn_q.get()
        assert isinstance(test_case, TestCases)

        latest_change = PerforceOperations().get_p4_changes(path=test_case.test_case_depot_path, p4_conn=p4_conn)
        if latest_change:
            latest_change = latest_change[0]
            if int(latest_change.get('change', 0)) > int(test_case.change if test_case.change else 0):
                self.parse_and_save_changes(test_case, latest_change, sync_force, p4_conn=p4_conn)
                log.debug("%s Change update in db", th_name)
                msg = 'Updated: {} -> {} -> {}'.format(latest_change.get('change', 0), test_case.test_case_depot_path,
                                                       test_case.change)
        test_q.put(msg)  # Mark finished parsing
        conn_q.put(p4_conn)  # Put active P4 connection back

    def compare_changes_multi(self, test_cases, sync_force=False, p4_conn=None):
        """
        Compare p4 change with local change number and run sync + parse if p4 change > GT local change.
        Run in threading.

        :param test_cases:
        :param sync_force:
        :param p4_conn:
        :return:
        """
        assert isinstance(test_cases, QuerySet)

        from queue import Queue
        from threading import Thread

        ts = time()
        cases_threads = collections.OrderedDict()
        thread_list = []
        test_outputs = []
        test_q = Queue()

        w = 4
        threads = list(range(w))
        split_patt = self.chunkIt(test_cases, len(threads))
        log.debug("Threads for parse patterns len: %s", len(threads))

        # Thread-cases pairs:
        for thread_i, cases_list in zip(threads, split_patt):
            cases_threads.update(
                {'thread-{}'.format(str(thread_i)): dict(cases_list=collections.deque(cases_list), thread=thread_i)})

        log.debug("Filling threads with jobs...")
        for thread_i, cases in cases_threads.items():  # Iter each thread and cases in it:

            conn_q = Queue()  # Separate Queue for p4 connection store
            p4_conn = PerforceOperations().p4_initialize()  # Init p4 connection for single thread-worker
            conn_q.put(p4_conn)  # Put active connection in queue for all threads

            log.debug("Filling threads for thread: {}".format(thread_i))
            cases_list = cases.get('cases_list')  # Choose cases list from dict of threads+cases

            while 0 < len(cases_list):  # Each pattern generates own process
                test_case = cases_list.popleft()  # When assigned to thread - delete item
                th_name = 'Parse thread: {} test case: {}'.format(thread_i, test_case.test_case_depot_path)  # type: str
                args_d = dict(test_case=test_case, th_name=th_name, test_q=test_q, conn_q=conn_q, sync_force=sync_force)
                parse_thread = Thread(target=LocalPatternsP4Parse().compare_change_thread, name=th_name, kwargs=args_d)
                thread_list.append(parse_thread)  # Save list of threads for further execution

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
        log.info(msg)
        log.debug(f'Synced matrix: {test_outputs}')
        return msg

    def parse_and_save_changes(self, test_case, latest_change, sync_force=False, p4_conn=None):
        """
        Parse changes from p4 depot and update table row with new data for each.

        :param p4_conn:
        :param sync_force: to run p4 sync -f or not
        :type test_case: TestCases
        :param latest_change: dict
        """
        assert isinstance(test_case, TestCases)
        assert isinstance(latest_change, dict)
        p4_change = int(latest_change.get('change', None))
        p4_time = latest_change.get('time', None)
        p4_user = latest_change.get('user', None)
        p4_desc = latest_change.get('desc', None)
        test_case_depot_path_ = test_case.test_case_depot_path + '...'

        test_case_name = test_case.pattern_folder_name if test_case.pattern_folder_name else test_case.test_case_dir
        log.debug("Change is not latest - RUN update and sync steps! %s %s", test_case.change, test_case_name)

        if sync_force:
            log.info("p4_change: %s > %s :local_change - run p4 sync_force: %s",
                     p4_change, test_case.change, test_case_depot_path_)

            # Sync folder to be sure we'll have the latest version:
            sync_force = PerforceOperations().p4_sync(path=test_case_depot_path_, force=True, p4_conn=p4_conn)
            if not sync_force:
                raise Exception("Path cannot be p4 synced! {}".format(test_case_depot_path_))
        else:
            log.info("p4_change: %s > %s :local_change - update only!", p4_change, test_case.change)

        # When sync is OK - save latest change data to table for current test case:
        change_desc_dict = self.parse_p4_change_text(change=[latest_change])

        # Convert p4 timestamp to datetime:
        p4_utc_dt = pytz.utc.localize(datetime.utcfromtimestamp(int(p4_time)))  # get UTC frm p4 time
        change_time = p4_utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=self.lon_tz)  # set London time

        # Save newly parsed data to table:
        test_case.change = p4_change
        test_case.change_desc = p4_desc
        test_case.change_user = p4_user
        test_case.change_review = change_desc_dict.get('review', None)
        test_case.change_ticket = change_desc_dict.get('ticket', None)
        test_case.change_time = change_time

        # test_case.save()
        test_case.save(update_fields=[
            'change',
            'change_desc',
            'change_user',
            'change_review',
            'change_ticket',
            'change_time',
        ])

    def get_latest_filelog(self, change_max, depot_path=None, p4_conn=None):
        """
        Get changes from p4 depot by p4 python command.
        Only changes in between from MAX latest in DB to @now current last in P4 depot
        :param p4_conn:
        :type change_max: str
        :type depot_path:
        :return list with dict of changes
        """
        if not depot_path:
            depot_path = self.dep_path
        return PerforceOperations().get_p4_filelog(short=True, change_max=change_max, path=depot_path, p4_conn=p4_conn)

    @staticmethod
    def get_test_cases(**kwargs):
        """
        Select test cases from table for further processing.
        Use kwargs to specify set or not - to select everything.

        :type kwargs: dict
        """
        test_cases = []
        test_type = kwargs.get('test_type', None)
        # tkn_branch = kwargs.get('tkn_branch', None)
        # pattern_library = kwargs.get('pattern_library', None)
        # pattern_folder_name = kwargs.get('pattern_folder_name', None)
        # pattern_folder_path = kwargs.get('pattern_folder_path', None)
        # test_py_path = kwargs.get('test_py_path', None)
        # test_dir_path = kwargs.get('test_dir_path', None)
        # change = kwargs.get('change', None)
        # change_user = kwargs.get('change_user', None)
        # change_time = kwargs.get('change_time', None)

        """
        Select only: test_py_path, test_case_depot_path, change, pattern_folder_name, test_case_dir
        """
        # TODO: Select different cases types to sync.
        if kwargs:
            if test_type:
                test_cases = TestCases.objects.filter(test_type__exact=test_type).only(
                    'test_py_path',
                    'test_case_depot_path',
                    'change',
                    'pattern_folder_name',
                    'test_case_dir'
                )
        else:
            test_cases = TestCases.objects.only(
                'test_py_path',
                'test_case_depot_path',
                'change',
                'pattern_folder_name',
                'test_case_dir'
            )
        return test_cases

    def parse_and_changes_routine(self, full=False, sync_force=True, selectables=None, p4_conn=None):
        """
        get p4 data for each test case in local table
        Running full:
            - Clean p4 workspace
            - Fast sync p4 workspace
            - Parse all local files - update/add if new found
            - Insert in DB
            - Get latest MAX change # from DB
            - Compare changes remote > local and additionally sync and parse changes.
        Running not full:
            - Get latest MAX change # from DB
            - Compare changes remote > local and additionally sync and parse changes.

        :param full:
        :param sync_force:
        :param selectables:
        :param p4_conn:
        :return:
        """
        if selectables is None:
            selectables = {}

        if full:
            """ Clean workspace - delete old files, add lost files, etc."""
            PerforceOperations().p4_clean(p4_conn=p4_conn)
            log.debug("DEBUG: P4 Clean!")
            """ Initial sync by default - no matter, just update everything"""
            PerforceOperations().p4_sync(path='//addm/', p4_conn=p4_conn)
            log.debug("DEBUG: P4 Sync initial!")
            """ Run parse local """
            results = self.parse_local_test()
            log.debug("Local files has been parsed!")
            """ Insert parted data in table """
            self.insert_parsed_test(results)
            log.debug("New files from local parse has been saved!")

        """ /Select items from table, get change for each, sync, update """
        test_cases = self.get_test_cases(**selectables)
        log.debug("Test cases has been selected to get latest changes!")
        """ Get perforce data for each and then save if new"""
        self.compare_changes_multi(test_cases, sync_force=sync_force, p4_conn=p4_conn)
        msg = "Test cases changes compared and refreshed!"
        return msg

    def last_changes_get(self):
        """
        Get only diff between MAX change from local DB and actual changes on p4 depot
        If no change found, use default change from 2015. This will be used as initial point to rebuild database.

        Run sync -f for all found changes.
        :return:
        """
        _files_synced_plan = []
        _files_synced_actually = []

        p4_conn = PerforceOperations().p4_initialize(debug=True)
        change_max_q = TestCases.objects.all().aggregate(Max('change'))
        change_max = change_max_q.get('change__max', '312830')  # default change from 2015
        log.debug(f"change_max: {change_max}")

        p4_filelog = self.get_latest_filelog(depot_path=None, change_max=change_max, p4_conn=p4_conn)
        if p4_filelog:

            for p4_file in p4_filelog:
                file_path = p4_file.get('depotFile', None)
                if not p4_file.get('action', None) == 'delete':
                    synced = PerforceOperations().p4_sync(path=file_path, force=True, p4_conn=p4_conn)
                    _files_synced_plan.append(file_path)
                    if synced and synced[0]:
                        _files_synced_actually.append(synced[0].get('clientFile', ['']))
                    log.debug(f"This will be synced: {file_path} - {p4_file.get('action', None)}")
                else:
                    log.debug(f"This should be deleted: {file_path}")

        log.debug(f"Synced files_synced_plan: {len(_files_synced_plan)}\n\t{_files_synced_plan}")
        log.debug(f"Synced files_synced_actually: {len(_files_synced_actually)}\n\t{_files_synced_actually}")
        # Both should be equal:
        if len(_files_synced_plan) == len(_files_synced_actually):
            log.info("Change / synced files lists are equal")
        else:
            log.warning("Change / synced files lists are NOT equal!")

        self.parse_and_changes_routine(sync_force=False, full=True, p4_conn=p4_conn)
        return True


class LocalDownloads:

    def __init__(self):
        """
        Example types:

            addm_items: <QuerySet [<AddmDev: AddmDev object>, <AddmDev: AddmDev object>,
                                    ...]>

        buildhub_paths_d: {
            'release_sprints': 'ftp://buildhub.tideway.com/hub/RELEASED/TKN/',
            'addm_tkn_paths': [
                {'10_2_0_6': 'ftp://buildhub.tideway.com/hub/RELEASED/10_2_0_6/publish/tkn/10.2/tku/'},
                {'11_0_0_4': 'ftp://buildhub.tideway.com/hub/RELEASED/11_0_0_4/publish/tkn/11.0/tku/'},
                {'11_1_0_6': 'ftp://buildhub.tideway.com/hub/RELEASED/11_1_0_6/publish/tkn/11.1/tku/'},
                {'11_2_0_1': 'ftp://buildhub.tideway.com/hub/RELEASED/11_2_0_1/publish/tkn/11.2/tku/'},
                {'11_2_0_2': 'ftp://buildhub.tideway.com/hub/RELEASED/11_2_0_2/publish/tkn/11.2/tku/'},
                {'11_3': 'ftp://buildhub.tideway.com/hub/RELEASED/11_3/publish/tkn/11.3/tku/'}
                ],
            'main_latest': 'ftp://buildhub.tideway.com/hub/main-latest/publish/tkn/11.3/tku/',
            'main_continuous': 'ftp://buildhub.tideway.com/hub/main-continuous/publish/tkn/'}

        download_paths_d: {
            'addm_released': '/home/user/TH_Octopus/UPLOAD/HUB/RELEASED',
            'released_tkn': '/home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN',
            'continuous': '/home/user/TH_Octopus/UPLOAD/HUB/main_continuous',
            'nightly': '/home/user/TH_Octopus/UPLOAD/HUB/main_latest'}


        """
        # self.addm_dev_group = AddmDev.objects.exclude(disables__isnull=True, addm_group__in=['alpha', 'beta', 'charlie', 'delta', 'echo', 'foxtrot']).order_by('addm_full_version')
        # TODO: Save release.txt output
        self.catZipRelease = ADDMCommands.objects.get(command_key__exact='cat.tku_zip.release')
        self.release_re = re.compile(r'release\.txt\D+(\d{5,10})')

    @staticmethod
    def tku_local_paths():
        """
        Set paths to TKU packages on remote hub and local FS
        Use dev ADDM versions to compose paths for only current addm versions.

        TODO: Plan to change this:
          - Use octopus database table: hub_path, download_path pairs and value for CMD
          - Try to download upgrade packages for ADDM

        :return:
        """
        log.debug("<=LocalDownloads=> Composing paths.")

        addm_sort = []
        addm_tkn_paths = []
        addm_versions = AddmDev.objects.filter(
            disables__isnull=True,
            addm_group__in=['alpha', 'beta', 'charlie', 'delta', 'echo', 'foxtrot']
        ).order_by('addm_full_version').values('addm_v_int', 'addm_full_version')

        place = '/home/user/TH_Octopus/UPLOAD/'
        hub_path = 'ftp://buildhub.tideway.com/'

        # RELEASED TKU:
        released = '{}hub/RELEASED/'.format(hub_path)
        released_tkn = '{}HUB/RELEASED/TKN'.format(place)

        for addm_item in addm_versions:
            if addm_item not in addm_sort:
                addm_sort.append(addm_item)
        log.debug("<=tku_local_paths=> Composing paths for TKU builds based on following addm versions: %s", addm_sort)

        # RELEASE GA
        # ftp://buildhub.tideway.com/hub/TKN_release_2018-04-1-91

        # RELEASED ADDM TKU:
        for addm in addm_sort:
            addm_v_int = addm.get('addm_v_int')
            addm_full_version = addm.get('addm_full_version').replace('.', "_")
            # /hub/RELEASED/11_3_0_2/publish/tkn/11.3
            addm_released_tkn = '{}{}/publish/tkn/{}/'.format(released, addm_full_version, addm_v_int)

            current_addm_versions = {addm_full_version: addm_released_tkn}
            if current_addm_versions not in addm_tkn_paths:
                addm_tkn_paths.append(current_addm_versions)

        buildhub_paths = dict(
            # Continuous:
            tkn_main_cont_path='{}hub/tkn_main-continuous/publish/tkn/'.format(hub_path),  # MAIN
            # tkn_ship_cont_path='{}hub/tkn_ship-nightly-latest/publish/tkn/'.format(hub_path),  # SHIP
            tkn_ship_cont_path='{}hub/'.format(hub_path),  # New SHIP
            # Other
            release_sprints='{}TKN/'.format(released),
            addm_tkn_paths=addm_tkn_paths,
            ga_candidate_path='{}hub/'.format(hub_path),
            # DEV: For addm dev code - it is not needed fot TKU.
            # /hub/main-continuous/publish/tkn//tku
            # main_continuous='{}hub/main-continuous/publish/tkn/'.format(hub_path),
            # /hub/main_latest-156/publish/tkn/11.3/tku
            # main_latest='{}hub/main-latest/publish/tkn/'.format(hub_path),
            # ADDM DEV PATHS:
            # scope_latest='{}hub/scope-latest/publish/VAs/unpacked/'.format(hub_path),
            # /hub/tkn_main_continuous/publish/tkn/11.3/tku
        )
        # log.debug("<=BUILDHUB_PATHS=> buildhub_paths: %s", buildhub_paths)

        download_paths = dict(
            # /hub/RELEASED/TKN/TKN_release_2018-02-2-82/publish/tkn/11.3/tku/
            released_tkn=released_tkn,
            addm_released="{}HUB/RELEASED".format(place),
            # /hub/tkn_main_continuous/publish/tkn/11.3/tku
            tkn_main_continuous="{}HUB/tkn_main_continuous".format(place),
            tkn_ship_continuous="{}HUB/TKN_SHIP_CONT".format(place),
            # sftp://user@172.25.144.117/home/user/TH_Octopus/UPLOAD/HUB/GA_CANDIDATE
            ga_candidate="{}HUB/GA_CANDIDATE".format(place),
            # DEV: For addm dev code - it is not needed fot TKU.
            # /hub/main-continuous/publish/tkn//tku
            # main_continuous="{}HUB/main_continuous".format(place),
            # /hub/main_latest-156/publish/tkn/11.3/tku
            # main_latest="{}HUB/main_latest".format(place),
            # ADDM DEV PATHS:
            # scope_latest="{}HUB/scope_latest".format(place),
        )
        # log.debug("<=DOWNLOAD_PATHS=> download_paths: %s", download_paths)

        return buildhub_paths, download_paths

    def tku_wget_cmd_compose(self):
        """
        Prepare list of commands to execute:

        main_continuous:
            wget --no-verbose --continue --recursive --no-host-directories --read-timeout=120
                 --reject='*.log,*log,*com_tkn.log'
                 --exclude-directories='*/*/*/*/*/kickstarts/,*/*/*/*/kickstarts/,*/*/*/kickstarts/,*/*/kickstarts/'
                 --cut-dirs=5 ftp://buildhub.tideway.com/hub/main-continuous/publish/tkn//tku/
                 --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/main_continuous

        main_latest:
            wget --no-verbose --continue --recursive --no-host-directories --read-timeout=120
                 --reject='*.log,*log,*com_tkn.log'
                 --exclude-directories='*/*/*/*/*/kickstarts/,*/*/*/*/kickstarts/,*/*/*/kickstarts/,*/*/kickstarts/'
                 --cut-dirs=5 ftp://buildhub.tideway.com/hub/main-latest/publish/tkn/11.3/tku/
                 --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/main_latest

        tkn_main_continuous:
            wget --no-verbose --continue --recursive --no-host-directories --read-timeout=120
                 --reject='*.log,*log,*com_tkn.log'
                 --exclude-directories='*/*/*/*/*/kickstarts/,*/*/*/*/kickstarts/,*/*/*/kickstarts/,*/*/kickstarts/'
                 --cut-dirs=4 ftp://buildhub.tideway.com/hub/tkn_main_continuous/publish/tkn/
                 --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/tkn_main_continuous

        released_tkn:
            wget --no-verbose --continue --recursive --no-host-directories --read-timeout=120
                 --reject='*.log,*log,*com_tkn.log'
                 --exclude-directories='*/*/*/*/*/kickstarts/,*/*/*/*/kickstarts/,*/*/*/kickstarts/,*/*/kickstarts/'
                 --cut-dirs=3 ftp://buildhub.tideway.com/hub/RELEASED/TKN/TKN_release_2019-02-1-140/
                 --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN

        addm_released:
            wget --no-verbose --continue --recursive --no-host-directories --read-timeout=120
                 --reject='*.log,*log,*com_tkn.log'
                 --exclude-directories='*/*/*/*/*/kickstarts/,*/*/*/*/kickstarts/,*/*/*/kickstarts/,*/*/kickstarts/'
                 --cut-dirs=2 ftp://buildhub.tideway.com/hub/RELEASED/11_3_0_2/publish/tkn/11.3/
                 --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/RELEASED

        Exclude: ftp://buildhub.tideway.com/hub/TKN_release_2019-03-1-141/kickstarts/tkn/tideway-devices/4.3/
                tideway-devices-4.3.2019.03.1-763382.ga.noarch.drpm [2404680]
            -> "/home/user/TH_Octopus/UPLOAD/HUB/GA_CANDIDATE/TKN_release_2019-03-1-141/kickstarts/tkn/tideway-devices/4.3/
                tideway-devices-4.3.2019.03.1-763382.ga.noarch.drpm"

        :return:
        """
        wget_cmd_d = dict()

        # Get usual paths to all TKNs AND:
        buildhub_paths_d, download_paths_d = self.tku_local_paths()

        # WGET options need to be filled with args:
        #            "--timestamping;" \
        exclude_dirs = '*/*/*/*/*/kickstarts/,*/*/*/*/kickstarts/,*/*/*/kickstarts/,*/*/kickstarts/,*/kickstarts/'
        exclude_dirs_main = '*/*/*/*/*/*community,*/*/*/*/*community,*/*/*/*community,*/*/*/*community,*community'
        wget_rec = "wget;" \
                   "--no-verbose;" \
                   "--timestamping;" \
                   "--recursive;" \
                   "--no-host-directories;" \
                   "--read-timeout=120;" \
                   "--reject='*.log,*log,*com_tkn.log';" \
                   "--exclude-directories='{excl}';" \
                   "--cut-dirs={cut};{ftp};" \
                   "--directory-prefix={dir}"

        # Disable some DEV:
        # wget_scope_latest = wget_rec.format(
        #     cut=5, ftp=buildhub_paths_d['scope_latest'], excl=exclude_dirs_main,
        #     dir=download_paths_d['scope_latest'])
        # wget_cmd_d.update(scope_latest=[wget_scope_latest])
        # wget_main_continuous = wget_rec.format(
        #     cut=4, ftp=buildhub_paths_d['main_continuous'], excl=exclude_dirs_main,
        #     dir=download_paths_d['main_continuous'])
        # wget_cmd_d.update(main_continuous=[wget_main_continuous])
        # wget_main_latest = wget_rec.format(
        #     cut=4, ftp=buildhub_paths_d['main_latest'], excl=exclude_dirs_main,
        #     dir=download_paths_d['main_latest'])
        # wget_cmd_d.update(main_latest=[wget_main_latest])

        tkn_main_cont_wget = wget_rec.format(
            cut=4, ftp=buildhub_paths_d['tkn_main_cont_path'], excl=exclude_dirs,
            dir=download_paths_d['tkn_main_continuous'])
        wget_cmd_d.update(tkn_main_continuous=[tkn_main_cont_wget])

        # For TKN_SHIP CONTINUOUS:
        ship_cont_cmd_l = []
        _, ship_cont_urls = self.parse_released_tkn_html(buildhub_paths_d['tkn_ship_cont_path'],
                                                         download_paths_d['tkn_ship_continuous'])
        for _url in ship_cont_urls:
            ship_cont_cmd = wget_rec.format(cut=1, ftp=_url, dir=download_paths_d['tkn_ship_continuous'],
                                            excl=exclude_dirs)
            if ship_cont_cmd not in ship_cont_cmd_l:
                ship_cont_cmd_l.append(ship_cont_cmd)
        wget_cmd_d.update(tkn_ship_continuous=ship_cont_cmd_l)

        # GA Candidate -  Compose download wget cmd for each sprint TKN Get all parsed paths to ga_candidate:
        ga_cmd_l = []
        ga_urls, _ = self.parse_released_tkn_html(buildhub_paths_d['ga_candidate_path'],
                                                  download_paths_d['ga_candidate'])
        for _url in ga_urls:
            ga_cmd = wget_rec.format(cut=1, ftp=_url, dir=download_paths_d['ga_candidate'],
                                     excl=exclude_dirs)
            if ga_cmd not in ga_cmd_l:
                ga_cmd_l.append(ga_cmd)
        wget_cmd_d.update(ga_candidate=ga_cmd_l)

        # Compose download wget cmd for each sprint TKN
        released_cmd_l = []
        released_urls, _ = self.parse_released_tkn_html(buildhub_paths_d['release_sprints'],
                                                        download_paths_d['released_tkn'])
        for _url in released_urls:
            released_cmd = wget_rec.format(cut=3, ftp=_url, dir=download_paths_d['released_tkn'],
                                           excl=exclude_dirs)
            if released_cmd not in released_cmd_l:
                released_cmd_l.append(released_cmd)
        wget_cmd_d.update(released_tkn=released_cmd_l)

        # Compose paths to download separately released packages for ADDM VA:
        addm_va_cmd_l = []
        for addm_va_d_item in buildhub_paths_d['addm_tkn_paths']:
            for va_k, va_v in addm_va_d_item.items():
                wget_addm_va = wget_rec.format(cut=2, ftp=va_v, dir=download_paths_d['addm_released'],
                                               excl=exclude_dirs)
                if wget_addm_va not in wget_cmd_d:
                    addm_va_cmd_l.append(wget_addm_va)
        wget_cmd_d.update(addm_released=addm_va_cmd_l)
        return wget_cmd_d

    def wget_tku_build_hub_option(self, **kwargs):
        """
        Download and parse only selected package:
        available options:
            main_continuous
            main_latest
            tkn_main_continuous
            released_tkn
            addm_released

        :return:
        """
        import subprocess
        tku_key = kwargs.get('tku_type', None)
        outputs_l = []
        cmd_l_nested = []
        wget_cmd_d = self.tku_wget_cmd_compose()

        log.debug(f"All CMDs: {wget_cmd_d}")

        if tku_key:
            cmd_l_nested.append(wget_cmd_d[tku_key])  # tkn_main_continuous, GA and SHIP cont
        else:
            for v in wget_cmd_d.values():
                cmd_l_nested.append(v)

        log.debug(f"WGET Nested CMD list: {cmd_l_nested}")
        command_list = list(itertools.chain(*cmd_l_nested))
        log.debug(f"WGET Flatten CMD list: {command_list}")

        for command in command_list:
            try:
                log.debug("<=LocalDownloads=> RUN cmd_item: '%s'", command.replace(';', ' '))
                run_cmd = subprocess.Popen(command.split(';'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = run_cmd.communicate()
                stdout, stderr = stdout.decode('utf-8'), stderr.decode('utf-8')
                run_cmd.wait()  # wait until command finished
                outputs_l.append([stdout, stderr])
                log.debug("<=LocalDownloads=>  WGET stdout/stderr: \n\tstdout: %s \n\tstderr %s", stdout, stderr)
            except Exception as e:
                log.error("<=LocalDownloads=> Error during operation for: %s %s", command, e)
        log.debug("<=LocalDownloads=> FINISH WGET commands exec!")

        # Get usual paths to all TKNs AND:
        _, download_paths_d = self.tku_local_paths()

        # return "DEBUG: Finish, do not parse!"
        self.tku_packages_parse(download_paths_d)

        # Do not return outputs, because we don't care of saving them to database instead of read logs!
        # return outputs_l
        # return f"Finished WGET, commands run: {command_list}, stderr: {outputs_l[1]}"

    @staticmethod
    def parse_released_tkn_html(buildhub_path, download_path):
        """
        Parse HTML in RELEASED/TKN/index.html to get all located sprint builds in there.
        Compose links ready to download.
          2020 Oct 12 08:30  Directory   <a href="ftp://buildhub.tideway.com:21/hub/RELEASED/TKN/TKN-Release-2020-10-1-5/">TKN-Release-2020-10-1-5/</a>
          ftp://buildhub.tideway.com/hub/TKN-Release-0000-00-0-150

        If TKN-Release-0000-00-0-5 - it's not release.
        If TKN-Release-2020-10-1-5 - it's a release.

        :return:
        """
        import subprocess
        run_cmd = []
        all_last_sprints = []
        ship_ga_builds = []

        last_tkn_r = re.compile(r"(TKN-Release-\d+-\d+-\d+-\d+)")
        ship_ga_r = re.compile(r"(TKN-Release-0{4}-0{2}-\d+-\d+)")
        # Old
        # last_tkn_released_r = re.compile(r"(TKN-Release-\d+-\d+-\d+-\d+)")

        log.debug("<=LocalDownloads=> Parsing index.html for %s to get sprint builds.", download_path)
        try:
            # sftp://user@172.25.144.117/home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN/index.html
            run_cmd = subprocess.Popen(['wget', '--timestamping', buildhub_path, '--directory-prefix', download_path],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            run_cmd.communicate()
            run_cmd.wait()
        except Exception as e:
            log.error("<=LocalDownloads=> Error during operation for: %s %s", run_cmd, e)

        index_file = download_path + "/index.html"
        if os.path.isfile(index_file):
            open_file = open(index_file, "r")
            read_file = open_file.read()

            ship_ga = ship_ga_r.findall(read_file)
            latest_tkn = last_tkn_r.findall(read_file)
            open_file.close()

            # Released TKN-Release-2020-10-1-5 sort
            if not ship_ga:
                for found in latest_tkn:
                    tkn_release_link = buildhub_path + found + '/'
                    if tkn_release_link not in all_last_sprints:
                        all_last_sprints.append(tkn_release_link)
            else:
                # SHIP GA TKN-Release-0000-00-0-5 sort
                for found in ship_ga:
                    ship_ga_link = buildhub_path + found + '/'
                    if ship_ga_link not in ship_ga_builds:
                        ship_ga_builds.append(ship_ga_link)

        # Delete index file from /upload/HUB/GA_CANDIDATE/ folder
        log.debug(f"Removing index_file: {index_file}")
        os.remove(index_file)

        # log.debug(f"all_last_sprints = {all_last_sprints}, ship_ga_builds = {ship_ga_builds}")
        return all_last_sprints, ship_ga_builds

    def tku_packages_parse(self, download_paths_d):
        """
        Parse local packages of TKU and save versions and file info to DB

        Nightly path: '/home/user/TH_Octopus/UPLOAD/HUB/main_latest'
            dir: 'nightly'
                items: '['tku']'

        Released TKN path: '/home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN'
            dir: 'released_tkn'
                items: '['index.html', 'TKN_release_2018-01-1-76', 'TKN_release_2018-02-1-80',
                'TKN_release_2018-02-2-82', 'TKN_release_2018-02-3-85', 'TKN_release_2018-03-1-90']'

        Continuous path: '/home/user/TH_Octopus/UPLOAD/HUB/main_continuous'
            dir: 'continuous'
                items: '['tku']'

        ADDM VA path: '/home/user/TH_Octopus/UPLOAD/HUB/RELEASED'
            dir: 'addm_released'
                items: '['TKN', '10_2_0_6', '11_0_0_4', '11_1_0_6', '11_2_0_1', '11_2_0_2', '11_3']'

        Data examples:

        :param download_paths_d:
        :return:
        """
        log.debug("<=LocalDownloads=> tku_packages_parse.")

        for key, path_v in download_paths_d.items():
            # DEV: For addm dev code - it is not needed fot TKU.
            if key == 'main_latest':
                # /home/user/TH_Octopus/UPLOAD/HUB/main_latest/12.0/tku/Technology-Knowledge-Update-2020-04-2-ADDM-12.0+.zip
                tku_content = os.listdir(path_v)
                for dir_item in tku_content:
                    # log.debug("dir_item %s", dir_item)  # dir_item 12.0
                    # /home/user/TH_Octopus/UPLOAD/HUB/main_latest/12.0
                    path_to_dir_item = os.path.join(path_v, dir_item)
                    if os.path.isdir(path_to_dir_item):
                        # /home/user/TH_Octopus/UPLOAD/HUB/main_latest/12.0/tku/
                        tku_zips = os.path.join(path_to_dir_item, 'tku')
                        if os.path.isdir(tku_zips):
                            tku_content = os.listdir(tku_zips)
                            addm_tku_zip_list = self.compose_tku_args(dir_content=tku_content,
                                                                      tku_zips=tku_zips,
                                                                      dir_key=key,
                                                                      zip_type='tku')
                            log.debug("<=LocalDownloads=> Insert TKU tkn_main_continuous package details in db.")
                            self.insert_tku_package(addm_tku_zip_list)
                        # List all ZIPs in edp folder
                        edp_zips = os.path.join(path_to_dir_item, 'edp')
                        if os.path.isdir(edp_zips):
                            edp_content = os.listdir(edp_zips)
                            addm_edp_zip_list = self.compose_tku_args(dir_content=edp_content,
                                                                      tku_zips=edp_zips,
                                                                      dir_key=key,
                                                                      zip_type='edp')
                            log.debug("<=LocalDownloads=> Insert TKU tkn_main_continuous package details in db.")
                            self.insert_tku_package(addm_edp_zip_list)
            # DEV: For addm dev code - it is not needed fot TKU.
            elif key == 'main_continuous':
                # /home/user/TH_Octopus/UPLOAD/HUB/main_continuous/12.0/tku/Technology-Knowledge-Update-2020-04-2-ADDM-12.0+.zip
                tku_content = os.listdir(path_v)
                for dir_item in tku_content:
                    log.debug("dir_item %s", dir_item)
                    # /home/user/TH_Octopus/UPLOAD/HUB/main_continuous/12.0
                    path_to_dir_item = os.path.join(path_v, dir_item)
                    if os.path.isdir(path_to_dir_item):
                        # /home/user/TH_Octopus/UPLOAD/HUB/main_continuous/12.0/tku/
                        tku_zips = os.path.join(path_to_dir_item, 'tku')
                        if os.path.isdir(tku_zips):
                            tku_content = os.listdir(tku_zips)
                            addm_tku_zip_list = self.compose_tku_args(dir_content=tku_content,
                                                                      tku_zips=tku_zips,
                                                                      dir_key=key,
                                                                      zip_type='tku')
                            log.debug("<=LocalDownloads=> Insert TKU tkn_main_continuous package details in db.")
                            self.insert_tku_package(addm_tku_zip_list)
                        # List all ZIPs in edp folder
                        edp_zips = os.path.join(path_to_dir_item, 'edp')
                        if os.path.isdir(edp_zips):
                            edp_content = os.listdir(edp_zips)
                            addm_edp_zip_list = self.compose_tku_args(dir_content=edp_content,
                                                                      tku_zips=edp_zips,
                                                                      dir_key=key,
                                                                      zip_type='edp')
                            log.debug("<=LocalDownloads=> Insert TKU tkn_main_continuous package details in db.")
                            self.insert_tku_package(addm_edp_zip_list)

            elif key == 'tkn_main_continuous':
                # /home/user/TH_Octopus/UPLOAD/HUB/tkn_main_continuous
                tku_content = os.listdir(path_v)
                for dir_item in tku_content:
                    # log.debug("dir_item %s", dir_item)

                    # /home/user/TH_Octopus/UPLOAD/HUB/tkn_main_continuous/11.3
                    path_to_dir_item = os.path.join(path_v, dir_item)
                    if os.path.isdir(path_to_dir_item):

                        # /home/user/TH_Octopus/UPLOAD/HUB/tkn_main_continuous/11.3/tku/
                        tku_zips = os.path.join(path_to_dir_item, 'tku')
                        if os.path.isdir(tku_zips):
                            tku_content = os.listdir(tku_zips)
                            addm_tku_zip_list = self.compose_tku_args(dir_content=tku_content,
                                                                      tku_zips=tku_zips,
                                                                      dir_key=key,
                                                                      zip_type='tku')
                            # log.debug("<=LocalDownloads=> Insert TKU tkn_main_continuous package details in db.")
                            self.insert_tku_package(addm_tku_zip_list)

                        # List all ZIPs in edp folder
                        edp_zips = os.path.join(path_to_dir_item, 'edp')
                        if os.path.isdir(edp_zips):
                            edp_content = os.listdir(edp_zips)
                            addm_edp_zip_list = self.compose_tku_args(dir_content=edp_content,
                                                                      tku_zips=edp_zips,
                                                                      dir_key=key,
                                                                      zip_type='edp')
                            # log.debug("<=LocalDownloads=> Insert TKU tkn_main_continuous package details in db.")
                            self.insert_tku_package(addm_edp_zip_list)

            elif key == 'tkn_ship_continuous':
                # /home/user/TH_Octopus/UPLOAD/HUB/tkn_ship_continuous
                tku_content = os.listdir(path_v)
                for dir_item in tku_content:
                    # /home/user/TH_Octopus/UPLOAD//HUB/TKN_SHIP_CONT/TKN-Release-0000-00-0-166/publish/tkn/12.1
                    path_to_dir_item = os.path.join(path_v, dir_item)
                    if os.path.isdir(path_to_dir_item):
                        ship_cont_publish = os.path.join(path_to_dir_item, 'publish', 'tkn')
                        # tkn_release_kickstarts = os.path.join(path_to_dir_item, 'kickstarts', 'tkn')
                        # GO in ADDM ver folder:
                        if os.path.isdir(ship_cont_publish):
                            addm_ver_dirs = os.listdir(ship_cont_publish)
                            # Each ADDM ver folder step in:
                            for addm_ver_folder in addm_ver_dirs:
                                # List all ZIPs in tku folder
                                tku_zips = os.path.join(ship_cont_publish, addm_ver_folder, 'tku')
                                if os.path.isdir(tku_zips):
                                    tku_content = os.listdir(tku_zips)
                                    addm_tku_zip_list = self.compose_tku_args(dir_content=tku_content,
                                                                              tku_zips=tku_zips,
                                                                              dir_key=key,
                                                                              pkg=dir_item,
                                                                              zip_type='tku')
                                    # log.debug("<=LocalDownloads=> Insert TKU ga_candidate package details in db.")
                                    self.insert_tku_package(addm_tku_zip_list)

                                # List all ZIPs in edp folder
                                edp_zips = os.path.join(ship_cont_publish, addm_ver_folder, 'edp')
                                if os.path.isdir(edp_zips):
                                    edp_content = os.listdir(edp_zips)
                                    addm_edp_zip_list = self.compose_tku_args(dir_content=edp_content,
                                                                              tku_zips=edp_zips,
                                                                              dir_key=key,
                                                                              pkg=dir_item,
                                                                              zip_type='edp')
                                    # log.debug("<=LocalDownloads=> Insert TKU ga_candidate package details in db.")
                                    self.insert_tku_package(addm_edp_zip_list)
                        # OLD tkn_ship_continuous:
                        # /home/user/TH_Octopus/UPLOAD/HUB/tkn_main_continuous/11.3/tku/
                        # tku_zips = os.path.join(path_to_dir_item, 'tku')
                        # if os.path.isdir(tku_zips):
                        #     tku_content = os.listdir(tku_zips)
                        #     addm_tku_zip_list = self.compose_tku_args(dir_content=tku_content,
                        #                                               tku_zips=tku_zips,
                        #                                               dir_key=key,
                        #                                               zip_type='tku')
                        #     # log.debug("<=LocalDownloads=> Insert TKU tkn_main_continuous package details in db.")
                        #     self.insert_tku_package(addm_tku_zip_list)
                        #
                        # # List all ZIPs in edp folder
                        # edp_zips = os.path.join(path_to_dir_item, 'edp')
                        # if os.path.isdir(edp_zips):
                        #     edp_content = os.listdir(edp_zips)
                        #     addm_edp_zip_list = self.compose_tku_args(dir_content=edp_content,
                        #                                               tku_zips=edp_zips,
                        #                                               dir_key=key,
                        #                                               zip_type='edp')
                        #     # log.debug("<=LocalDownloads=> Insert TKU tkn_main_continuous package details in db.")
                        #     self.insert_tku_package(addm_edp_zip_list)

            elif key == 'ga_candidate':
                # /home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN/TKN_release_2018-01-1-76/publish/tkn/11.3/tku/
                #   Technology-Knowledge-Update-2018-01-1-ADDM-11.3+.zip
                tku_content = os.listdir(path_v)
                for dir_item in tku_content:
                    path_to_dir_item = os.path.join(path_v, dir_item)
                    if os.path.isdir(path_to_dir_item):
                        tkn_release_publish = os.path.join(path_to_dir_item, 'publish', 'tkn')
                        # tkn_release_kickstarts = os.path.join(path_to_dir_item, 'kickstarts', 'tkn')
                        # GO in ADDM ver folder:
                        if os.path.isdir(tkn_release_publish):
                            addm_ver_dirs = os.listdir(tkn_release_publish)
                            # Each ADDM ver folder step in:
                            for addm_ver_folder in addm_ver_dirs:
                                # List all ZIPs in tku folder
                                tku_zips = os.path.join(tkn_release_publish, addm_ver_folder, 'tku')
                                if os.path.isdir(tku_zips):
                                    tku_content = os.listdir(tku_zips)
                                    addm_tku_zip_list = self.compose_tku_args(dir_content=tku_content,
                                                                              tku_zips=tku_zips,
                                                                              dir_key=key,
                                                                              pkg=dir_item,
                                                                              zip_type='tku')
                                    # log.debug("<=LocalDownloads=> Insert TKU ga_candidate package details in db.")
                                    self.insert_tku_package(addm_tku_zip_list)

                                # List all ZIPs in edp folder
                                edp_zips = os.path.join(tkn_release_publish, addm_ver_folder, 'edp')
                                if os.path.isdir(edp_zips):
                                    edp_content = os.listdir(edp_zips)
                                    addm_edp_zip_list = self.compose_tku_args(dir_content=edp_content,
                                                                              tku_zips=edp_zips,
                                                                              dir_key=key,
                                                                              pkg=dir_item,
                                                                              zip_type='edp')
                                    # log.debug("<=LocalDownloads=> Insert TKU ga_candidate package details in db.")
                                    self.insert_tku_package(addm_edp_zip_list)

            elif key == 'released_tkn':
                # /home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN/TKN_release_2018-01-1-76/publish/tkn/11.3/tku/
                #   Technology-Knowledge-Update-2018-01-1-ADDM-11.3+.zip
                tku_content = os.listdir(path_v)
                for dir_item in tku_content:
                    path_to_dir_item = os.path.join(path_v, dir_item)
                    if os.path.isdir(path_to_dir_item):
                        tkn_release_publish = os.path.join(path_to_dir_item, 'publish', 'tkn')
                        # tkn_release_kickstarts = os.path.join(path_to_dir_item, 'kickstarts', 'tkn')
                        # GO in ADDM ver folder:
                        if os.path.isdir(tkn_release_publish):
                            addm_ver_dirs = os.listdir(tkn_release_publish)
                            # Each ADDM ver folder step in:
                            for addm_ver_folder in addm_ver_dirs:
                                # List all ZIPs in tku folder
                                tku_zips = os.path.join(tkn_release_publish, addm_ver_folder, 'tku')
                                if os.path.isdir(tku_zips):
                                    tku_content = os.listdir(tku_zips)
                                    addm_tku_zip_list = self.compose_tku_args(dir_content=tku_content,
                                                                              tku_zips=tku_zips,
                                                                              dir_key=key,
                                                                              pkg=dir_item,
                                                                              zip_type='tku')
                                    # log.debug("<=LocalDownloads=> Insert TKU released_tkn package details in db.")
                                    self.insert_tku_package(addm_tku_zip_list)

                                # List all ZIPs in edp folder
                                edp_zips = os.path.join(tkn_release_publish, addm_ver_folder, 'edp')
                                if os.path.isdir(edp_zips):
                                    edp_content = os.listdir(edp_zips)
                                    addm_edp_zip_list = self.compose_tku_args(dir_content=edp_content,
                                                                              tku_zips=edp_zips,
                                                                              dir_key=key,
                                                                              pkg=dir_item,
                                                                              zip_type='edp')
                                    # log.debug("<=LocalDownloads=> Insert TKU released_tkn package details in db.")
                                    self.insert_tku_package(addm_edp_zip_list)

            elif key == 'addm_released':
                # /home/user/TH_Octopus/UPLOAD/HUB/RELEASED/11_3/publish/tkn/11.3/tku/
                #   Technology-Knowledge-Update-2018-02-3-ADDM-11.3+.zip
                tku_content = os.listdir(path_v)
                for dir_item in tku_content:
                    if not dir_item == 'TKN':
                        path_to_dir_item_va = os.path.join(path_v, dir_item)
                        if os.path.isdir(path_to_dir_item_va):
                            # /home/user/TH_Octopus/UPLOAD/HUB/RELEASED/11_2_0_2/publish/tkn/
                            tkn_addm_va_publish = os.path.join(path_to_dir_item_va, 'publish', 'tkn')
                            # GO in ADDM ver folder:
                            if os.path.isdir(tkn_addm_va_publish):
                                addm_ver_dirs = os.listdir(tkn_addm_va_publish)
                                for addm_ver_folder in addm_ver_dirs:
                                    # /home/user/TH_Octopus/UPLOAD/HUB/RELEASED/11_2_0_2/publish/tkn/11.2/tku/
                                    tku_zips = os.path.join(tkn_addm_va_publish, addm_ver_folder, 'tku')
                                    # List all ZIPs in tku folder
                                    if os.path.isdir(tku_zips):
                                        tku_content = os.listdir(tku_zips)
                                        addm_tku_zip_list = self.compose_tku_args(dir_content=tku_content,
                                                                                  tku_zips=tku_zips,
                                                                                  dir_key=key,
                                                                                  zip_type='tku')
                                        # log.debug("<=LocalDownloads=> Insert TKU addm_released package details in db.")
                                        self.insert_tku_package(addm_tku_zip_list)
                                    # List all ZIPs in edp folder
                                    # /home/user/TH_Octopus/UPLOAD/HUB/RELEASED/11_2_0_2/publish/tkn/11.2/edp/
                                    edp_zips = os.path.join(tkn_addm_va_publish, addm_ver_folder, 'edp')
                                    if os.path.isdir(edp_zips):
                                        edp_content = os.listdir(edp_zips)
                                        addm_edp_zip_list = self.compose_tku_args(dir_content=edp_content,
                                                                                  tku_zips=edp_zips,
                                                                                  dir_key=key,
                                                                                  zip_type='edp')
                                        # log.debug("<=LocalDownloads=> Insert TKU addm_released package details in db.")
                                        self.insert_tku_package(addm_edp_zip_list)

            else:
                log.debug("<=LocalDownloads=> I do not know this dir key: %s and path %s", key, path_v)

    @staticmethod
    def parse_tku_zip(item_zip):
        """
        Parse TKU zip files to get date, revision and ADDM version:
        - Technology-Knowledge-Update-2068-04-1-ADDM-11.3+.zip
        - Technology-Knowledge-Update-Storage-2068-04-1-ADDM-11.3+.zip
        :return:
        """
        tku_zip_parsed_d = dict()
        tku_zip_file_re = re.compile(r'(?P<name>Technology-Knowledge-Update|Extended-Data-Pack)(?:-|)'
                                     r'(?P<type>\S+|)-'
                                     r'(?P<build>\d+)-'
                                     r'(?P<month>\d+)-'
                                     r'(?P<date>\d+)-ADDM-'
                                     r'(?P<addm_version>\d+\.\d+)\+\.zip')
        parsed_zip = re.match(tku_zip_file_re, item_zip)
        if parsed_zip:
            # For test? Maybe not needed here for real?
            # tku_build = parsed_zip.group('build') if '0000' not in parsed_zip.group('build') else datetime.now().strftime('%Y')
            # tku_month = parsed_zip.group('month') if '00' not in parsed_zip.group('month') else datetime.now().strftime('%m')
            tku_zip_parsed_d = dict(
                tku_name=parsed_zip.group('name'),
                tku_pack=parsed_zip.group('type'),
                tku_build=parsed_zip.group('build'),
                tku_month=parsed_zip.group('month'),
                tku_date=parsed_zip.group('date'),
                tku_addm_version=parsed_zip.group('addm_version'),
            )
        # log.debug("<=LocalDownloads=> parsed_zip %s", tku_zip_parsed_d)
        return tku_zip_parsed_d

    def compose_tku_args(self, dir_content, tku_zips, dir_key, zip_type, pkg=None):
        """
        Go through all zip files in passed path and get available info of each.

        :param zip_type:
        :param pkg:
        :param dir_key:
        :param tku_zips:
        :param dir_content:
        :return:
        """
        zip_list = []
        # zip_d = dict()
        package_type_f = dir_key + '_{tku_build}-{tku_month}-{tku_date}-000'

        for item_zip in dir_content:
            if item_zip.endswith('.zip'):
                zip_path = os.path.join(tku_zips, item_zip)
                parsed_zip_d = self.parse_tku_zip(item_zip)
                md5_digest = self.md5(zip_path)
                release = self.get_release(zip_path=zip_path)

                if not pkg:
                    # TKN_release_%tku_build%-%tku_month%-%tku_date%-000
                    package_type = package_type_f.format(tku_build=parsed_zip_d['tku_build'],
                                                         tku_month=parsed_zip_d['tku_month'],
                                                         tku_date=parsed_zip_d['tku_date'])
                else:
                    package_type = pkg
                zip_d = dict(
                    tku_type=dir_key,
                    zip_type=zip_type,
                    zip_file_name=item_zip,
                    zip_file_path=zip_path,
                    md5_digest=md5_digest,
                    release=release,
                    zip_info_d=parsed_zip_d,
                    package_type=package_type,
                    addm_version=parsed_zip_d['tku_addm_version'],
                )
                # log.debug("zip_d: %s md5sum: (%s)", item_zip, md5_digest)
                zip_list.append(zip_d)
        # log.debug("<=LocalDownloads=> CONTINUOUS edp_nightly_zip_d %s", edp_nightly_zip_d)
        return zip_list

    @staticmethod
    def insert_tku_package(parsed_zip_d):
        """
        Simply save all parsed data of each package in Octopus DB.
        Save of not exists in DB or update if md5sum changed

        :return:
        """
        status = dict(saved=True, msg='Record exists in local database.')
        for item in parsed_zip_d:
            package = dict(
                zip_file_md5_digest=item['md5_digest'],
                release=item['release'],
                zip_file_path=item['zip_file_path'],
                zip_file_name=item['zip_file_name'],
                package_type=item['package_type'],
                tku_type=item['tku_type'],
                zip_type=item['zip_type'],
                addm_version=item['addm_version'],
                tku_name=item['zip_info_d']['tku_name'],
                tku_addm_version=item['zip_info_d']['tku_addm_version'],
                tku_build=item['zip_info_d']['tku_build'],
                tku_date=item['zip_info_d']['tku_date'],
                tku_month=item['zip_info_d']['tku_month'],
                tku_pack=item['zip_info_d']['tku_pack'],
                updated_at=datetime.now(tz=pytz.utc),
            )
            # Check exist:
            try:
                get_if_exist = TkuPackages.objects.get(
                    zip_file_path=package.get('zip_file_path'),
                    tku_addm_version=package.get('addm_version'),
                    package_type=package.get('package_type'),
                    tku_type=package.get('tku_type'))
            except TkuPackages.DoesNotExist:
                get_if_exist = None

            # Compare md5sum of current package with get:
            if get_if_exist:
                # When md5sum is different OR release.txt is different - update current record:
                if not get_if_exist.zip_file_md5_digest == package['zip_file_md5_digest'] or not get_if_exist.release == \
                                                                                                 package['release']:

                    if not get_if_exist.zip_file_md5_digest == package['zip_file_md5_digest']:
                        log.debug("<=UPDATE=> MD5SUM (%s) != (%s)", get_if_exist.zip_file_md5_digest,
                                  package['zip_file_md5_digest'])
                    if not get_if_exist.release == package['release']:
                        log.debug("<=UPDATE=> RELEASE (%s) != (%s)", get_if_exist.release, package['release'])

                    try:
                        updated, create_new = TkuPackages.objects.update_or_create(
                            zip_file_path=package.get('zip_file_path'),
                            zip_file_name=package.get('zip_file_name'),
                            tku_addm_version=package.get('addm_version'),
                            package_type=package.get('package_type'),
                            tku_name=package.get('tku_name'),
                            tku_type=package.get('tku_type'),
                            defaults=dict(package))
                        # For debug? It shouldn't be reached because record should always exists here:
                        if create_new:
                            msg = "TKU package update: updated={}, {}, details {}".format(updated, create_new, package)
                            log.info(msg)
                        # In prod - there is no need to indicate this state!
                        # else:
                        #     status.update(saved=False, msg="If not saved - then it already existed in db.")
                    except Exception as e:
                        msg = "<=UPDATE=> insert_tku_package: Error: {}\n-->\t db_model: {}\n-->\t details: {} ".format(
                            e, TkuPackages, package)
                        log.error(msg)
                # In prod - there is no need to indicate this state!
                # else:
                #     status.update(saved=True)
                #     log.debug("<=EXIST=> (%s) = (%s) - %s", get_if_exist.zip_file_md5_digest,
                #               package['zip_file_md5_digest'], get_if_exist.package_type)
            # If there is no such record - create new row for TKU zips:
            else:
                log.debug("<=CREATE=> %s - %s", package['zip_file_md5_digest'], package['package_type'])
                try:
                    tku_package = TkuPackages(**package)
                    tku_package.save(force_insert=True)
                    if tku_package.id:
                        status.update(saved_id=tku_package.id)
                    else:
                        msg = "Test result not saved! Result: {}".format(package)
                        log.error(msg)
                except Exception as e:
                    msg = "<=INSERT=> insert_tku_package: Error: {}\n-->\t db_model: {}\n-->\t details: {} ".format(
                        e, TkuPackages, package)
                    log.error(msg)
        return True

    def only_parse_tku(self, **kwargs):
        """
        Run only parsinf function.
        :return:
        """
        log.debug("only_parse_tku")
        path_key = kwargs.get('tku_type', None)
        if path_key:
            _, download_paths_d = self.tku_local_paths()
            download_paths_d = {path_key: download_paths_d[path_key]}
        else:
            _, download_paths_d = self.tku_local_paths()

        self.tku_packages_parse(download_paths_d)
        return True

    # https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file
    @staticmethod
    def md5(zip_path):
        hash_md5 = hashlib.md5()
        with open(zip_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def get_release(self, zip_path):
        """ Check TKU zip release txt content and save as release value"""
        release = 'None'
        # log.debug(f"Getting release.txt from {zip_path}")
        release_txt = self.catZipRelease.command_value.format(path_to_zip=zip_path)
        run_cmd = subprocess.Popen(release_txt,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   shell=True,
                                   )
        stdout, stderr = run_cmd.communicate()
        stdout, stderr = stdout.decode('utf-8'), stderr.decode('utf-8')
        run_cmd.wait()
        if stdout:
            release_search = self.release_re.search(stdout)
            if release_search:
                release = release_search.group(1)
                # log.debug(f"release: {release}")
        if stderr:
            log.error(f"STDERR {stderr}")
            """
            Sometimes TKU files are corrupted - then, marking build as None - can help to avoid installation:
            STDERR error [/home/user/TH_Octopus/UPLOAD/HUB/tkn_main_continuous/11.3/tku/Technology-Knowledge-Update-2068-12-1-ADDM-11.3+.zip]:  start of central directory not found;
              zipfile corrupt.
              (please check that you have transferred or created the zipfile in the
              appropriate BINARY mode and that you have compiled UnZip properly)
              
            STDERR file #1:  bad zipfile offset (local header sig):  4398211
            """
        return release

    # def _wget_tku_build_hub(self):
    #     """
    #     WGET TKU zips for upload tests
    #
    #     CMD EXAMPLES:
    #
    #     wget,--no-verbose,--timestamping,--recursive,--continue,--no-host-directories,--reject,'*.log',
    #         --cut-dirs=5,ftp://buildhub.tideway.com/hub/main-continuous/publish/tkn//tku/,
    #             --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/main_continuous
    #
    #     wget,--no-verbose,--timestamping,--recursive,--continue,--no-host-directories,--reject,'*.log',
    #         --cut-dirs=5,ftp://buildhub.tideway.com/hub/main-latest/publish/tkn/11.3/tku/,
    #             --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/main_latest
    #
    #     wget,--no-verbose,--timestamping,--recursive,--continue,--no-host-directories,--reject,'*.log',
    #         --cut-dirs=3,ftp://buildhub.tideway.com/hub/RELEASED/TKN/TKN_release_2018-01-1-76/,
    #             --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN
    #
    #     wget,--no-verbose,--timestamping,--recursive,--continue,--no-host-directories,--reject,'*.log',
    #         --cut-dirs=5,{'11_2_0_2': 'ftp://buildhub.tideway.com/hub/RELEASED/11_2_0_2/publish/tkn/11.2/tku/'},
    #             --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN
    #
    #     wget,--no-verbose,--timestamping,--recursive,--continue,--no-host-directories,--reject,'*.log',
    #         --cut-dirs=5,{'11_3': 'ftp://buildhub.tideway.com/hub/RELEASED/11_3/publish/tkn/11.3/tku/'},
    #             --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN
    #
    #     ftp://buildhub.tideway.com/hub/TKN_release_2018-04-1-91
    #
    #
    #     :return:
    #     """
    #     import subprocess
    #     wget_cmd_list = []
    #     outputs_l = []
    #
    #     # Get usual paths to all TKNs AND:
    #     buildhub_paths_d, download_paths_d = self.tku_local_paths()
    #     # Get all parsed paths to release_sprints:
    #     release_sprints = self.parse_released_tkn_html(buildhub_paths_d['release_sprints'],
    #                                                    download_paths_d['released_tkn'])
    #
    #     # Get all parsed paths to ga_candidate:
    #     ga_candidates = self.parse_released_tkn_html(buildhub_paths_d['ga_candidate_path'],
    #                                                  download_paths_d['ga_candidate'])
    #
    #     # WGET options need to be filled with args:
    #     #            "--timestamping;" \
    #     wget_rec = "wget;" \
    #                "--no-verbose;" \
    #                "--timestamping;" \
    #                "--recursive;" \
    #                "--no-host-directories;" \
    #                "--read-timeout=120;" \
    #                "--reject='*.log,*log,*com_tkn.log';" \
    #                "--exclude-directories='*/*/*/*/*/kickstarts/,*/*/*/*/kickstarts/,*/*/*/kickstarts/,*/*/kickstarts/,*/kickstarts/';" \
    #                "--cut-dirs={cut};{ftp};" \
    #                "--directory-prefix={dir}"
    #
    #     # DEV: For addm dev code - it is not needed fot TKU.
    #     # Compose download wget cmd for CONTINUOUS:
    #     # wget_continuous = wget_rec.format(5, buildhub_paths_d['main_continuous'], download_paths_d['continuous'])
    #     # wget_cmd_list.append(wget_continuous)
    #
    #     # DEV: For addm dev code - it is not needed fot TKU.
    #     # Compose download wget cmd for NIGHTLY
    #     # wget_nightly = wget_rec.format(5, buildhub_paths_d['main_latest'], download_paths_d['nightly'])
    #     # wget_cmd_list.append(wget_nightly)
    #
    #     # Compose download wget cmd for tkn_main_continuous
    #     # 4 - do not cut addm version folders
    #     tkn_main_cont_wget = wget_rec.format(cut=4, ftp=buildhub_paths_d['tkn_main_cont_path'],
    #                                          dir=download_paths_d['tkn_main_continuous'])
    #     wget_cmd_list.append(tkn_main_cont_wget)
    #
    #     # Compose download wget cmd for each sprint TKN
    #     for sprint in release_sprints:
    #         wget_sprints_html = wget_rec.format(cut=3, ftp=sprint, dir=download_paths_d['released_tkn'])
    #
    #         if wget_sprints_html not in wget_cmd_list:
    #             wget_cmd_list.append(wget_sprints_html)
    #
    #     # GA Candidate -  Compose download wget cmd for each sprint TKN
    #     for ga_candidate in ga_candidates:
    #         ga_candidate_html = wget_rec.format(cut=1, ftp=ga_candidate, dir=download_paths_d['ga_candidate'])
    #
    #         if ga_candidate_html not in wget_cmd_list:
    #             wget_cmd_list.append(ga_candidate_html)
    #
    #     # Compose paths to download separately released packages for ADDM VA:
    #     for addm_va_d_item in buildhub_paths_d['addm_tkn_paths']:
    #         for va_k, va_v in addm_va_d_item.items():
    #             # local_path_to_zip = download_paths_d['addm_released']+va_k
    #
    #             wget_addm_va = wget_rec.format(cut=2, ftp=va_v, dir=download_paths_d['addm_released'])
    #
    #             if wget_addm_va not in wget_cmd_list:
    #                 # log.debug("<=LocalDownloads=> Download ADDM VA: %s %s", va_k, wget_addm_va)
    #                 wget_cmd_list.append(wget_addm_va)
    #
    #     log.debug("<=LocalDownloads=> START WGET commands exec!")
    #     # noinspection PyBroadException
    #     for cmd_item in wget_cmd_list:
    #         try:
    #             log.debug("<=LocalDownloads=> RUN cmd_item: '%s'", cmd_item.replace(';', ' '))
    #             run_cmd = subprocess.Popen(cmd_item.split(';'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #             stdout, stderr = run_cmd.communicate()
    #             stdout, stderr = stdout.decode('utf-8'), stderr.decode('utf-8')
    #             run_cmd.wait()  # wait until command finished
    #             outputs_l.append([stdout, stderr])
    #             log.debug("<=LocalDownloads=>  WGET stdout/stderr: \n\tstdout: %s \n\tstderr %s", stdout, stderr)
    #         except Exception as e:
    #             log.error("<=LocalDownloads=> Error during operation for: %s %s", cmd_item, e)
    #     log.debug("<=LocalDownloads=> FINISH WGET commands exec!")
    #
    #     self.tku_packages_parse(download_paths_d)
    #
    #     # Do not return outputs, because we don't care of saving them to database instead of read logs!
    #     # return outputs_l
    #     return True


class LocalDB:
    """
    Local operations with database - update, insert, index etc
    """

    @staticmethod
    def history_weight(last_days, addm_name):
        """
        Get historical test records for n days,
        group by test.py path and date, summarize all weights for each

        :return:
        """
        patterns_weight = collections.OrderedDict()
        now = datetime.now(tz=timezone.utc)
        tomorrow = now + timedelta(days=1)
        date_from = now - timedelta(days=int(last_days))
        date_from = date_from.strftime('%Y-%m-%d')
        date_to = tomorrow.strftime('%Y-%m-%d')

        all_history_weight = PatternsDjangoModelRaw().sel_history_by_latest_all(date_to, date_from, addm_name)
        # all_history_weight = TestHistory.objects.filter(
        #     test_date_time__in=[date_from, tomorrow],
        #     addm_group__exact=addm_name,
        # )

        # Make dict with test.py path as key and sum of test time / days(selected items)
        # If nothing was selected - update pattern row with default value of 10 min or do nothing if value is already exists
        log.debug("Found tests len %s", len(all_history_weight))
        if all_history_weight:
            # This should be only one pattern result:
            # count = 0
            for test_res in all_history_weight:

                # log.debug("Test result %s", test_res)
                # log.debug("test_res %s", (test_res.id, test_res.time_spent_test, test_res.test_py_path, test_res.test_date_time))

                # If current test.py IS already in the list of dicts -> update days count, time and time sum abd average:
                if any(test_res.test_py_path in d for d in patterns_weight):
                    already_have = patterns_weight[test_res.test_py_path]

                    already_have['day_rec'] = already_have['day_rec'] + 1
                    already_have['time_sum'] = already_have['time_sum'] + round(float(test_res.time_spent_test))
                    already_have['average'] = round(already_have['time_sum'] / already_have['day_rec'])

                # If current test.py IS NOT in the list of dicts -> only add values
                else:
                    weight = {test_res.test_py_path: dict(day_rec=1, time_sum=round(float(test_res.time_spent_test)),
                                                          average=round(float(test_res.time_spent_test)))}
                    patterns_weight.update(weight)
        else:
            log.error("There are no hist records for selected: %s", last_days)
        return patterns_weight

    @staticmethod
    def insert_patt_weight(patterns_weight):
        """
        Insert composed dict of patterns weight for each pattern with test.py,
        and even duplicates! (For patterns set which can have one test.py for all of them)

        :param patterns_weight:
        :return:
        """
        for patt_k, patt_v in patterns_weight.items():
            # 1. Select all patterns with according test.py path:
            patterns_sel = TestCases.objects.filter(
                test_py_path__exact=patt_k,
            )
            # 1. Iter over each found pattern item with corresponding test.py
            if patterns_sel:
                for pattern in patterns_sel:
                    pattern.test_time_weight = patt_v['average']
                    pattern.save()
            else:
                log.error("No corresponding patterns were found for key %s", patt_k)
