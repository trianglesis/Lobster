

if __name__ == "__main__":
    from time import time
    from datetime import datetime, timezone, timedelta
    import pytz
    import logging
    import django
    import os
    import re
    import P4
    import copy
    import collections
    from operator import itemgetter
    # PPRINT
    import json
    from pprint import pformat

    django.setup()
    from django.db.models.query import QuerySet
    from django.conf import settings

    # from run_core.local_operations import TestsParseLocal
    from octo_tku_patterns.models import TestCases
    from run_core.p4_operations import PerforceOperations
    from run_core.local_operations import LocalPatternsP4Parse
    from run_core.local_operations import LocalPatternsParse

    log = logging.getLogger("octo.octologger")
    log.info("Running DEV")

    # Run os file walk on local p4 depot path:
    dep_path = '/home/user/TH_Octopus/perforce/addm/'

    class TestsParseLocal:
        """
            New way to parse test data, only use test.py as entry point for any test case.
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
            tpl_pattern = re.compile(r'^[\w]*\.tplpre')
            if settings.DEV:
                p4_workspace = "/mnt/g/perforce"
            else:
                p4_workspace = "/home/user/TH_Octopus/perforce"

            octo_workspace = p4_workspace
            iters = 0
            log.info("walk_fs_tests START")
            walked_test_data = []
            for root, dirs, files in os.walk(local_depot_path, topdown=False):
                iters += 1
                for name in files:  # Iter over all files in path:
                    # Check test.py files
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
                        # Sorting
                        if 'tku_patterns' in root:  # Check if current path is related to tku_patterns:
                            # Cut first n dirs until 'tkn_main' /home/user/TH_Octopus/perforce/addm/tkn_main
                            split_root = root.split(os.sep)[6:]
                            test_dict.update(
                                test_type='tku_patterns',
                                tkn_branch=tkn_branch,
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
                            test_dict.update(
                                test_type='product_content',
                                tkn_branch=tkn_branch,
                                test_case_dir='/'.join(split_root),
                                test_case_depot_path=os.path.dirname(root).replace(octo_workspace, '/'),
                            )
                            print(f"product_content test_dict: {test_dict}")
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
                    # Check tplpre files
                    elif self.is_test(tpl_pattern, name):
                        pattern_path = os.path.join(root, name)
                        # log.debug(f"This is TPLPRE path {root}")
                        # log.debug(f"This is TPLPRE file {pattern_path}")
                        # If test is there:
                        test_dir = os.path.join(root, 'tests')
                        if os.path.exists(test_dir):
                            # log.debug(f"There is test: {name}")
                            pass
                        else:
                            print(f"There is no test: {pattern_path}")
                    else:
                        pass

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


    class P4ChangesParse:
        """
            Use test cases depot path to get actual last changes data.

            1.
           - get 'have' info and save to table?
           - check if have and latest is not eq
           -- run p4 sync force if not
           -- do nothing if eq
           - save latest change info to table

            2.
            Move to another function:
            Compare with known from database:

            - if none -> p4 sync force -> update change in table
            - if depot change > local change -> p4 sync force -> update change in table
                -- additionally get this change full timestamp and update in table
            - if depot change = local change = do nothing

        """

        @staticmethod
        def p4_initialize(debug):
            p4 = PerforceOperations().p4_initialize(debug)
            return p4

        def p4_cmd_run(self, p4_cmd, args=None, p4_conn=None, path=None, **options):
            """
            Run p4 commands such as: clean, sync, changes, fstat, cstat and so on

            :param p4_cmd: str
            :param args: list
            :param p4_conn: P4()
            :param path: str
            :param options: dict
            :return:
            """
            if args is None:
                args = []
            if not p4_conn:
                p4_conn = self.p4_initialize(debug=True)
            assert isinstance(p4_conn, P4.P4)

            p4_run = []  # Output if any
            debug = options.get('debug', False)

            if debug:
                print("P4 Run CMD: '{}' args: '{}' options: '{}' ".format(p4_cmd, args, options))
            if not path:
                path = ''

            try:
                p4_run = p4_conn.run(p4_cmd, args, path)
            except P4.P4Exception:
                for err in p4_conn.errors:  # Display errors
                    print("ERROR: P4.P4Exception -> cmd: {} ({})".format((p4_cmd, args), err))
                for warn in p4_conn.warnings:  # Display errors
                    print("WARNING: P4.P4Exception -> cmd: {} ({})".format((p4_cmd, args), warn))
            return p4_run

        def p4_clean(self, path=None, p4_conn=None):
            """
            p4 clean -l -n /home/user/TH_Octopus/perforce/addm/
            '-n' - only show - do nothing
            :return:
            """

            args = ['-l']
            if not path:
                path = dep_path

            clean_ = self.p4_cmd_run(p4_cmd='clean', args=args, p4_conn=p4_conn, path=path)
            return clean_

        def p4_sync(self, path, force=False, p4_conn=None):
            """
            P4 synced: [
                {
            'depotFile': '//addm/tkn_ship/tku_patterns/CORE/MicrosoftADDomainServices/MicrosoftADDomainServices.tplpre',
            'clientFile': '/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE/MicrosoftADDomainServices/MicrosoftADDomainServices.tplpre',
            'rev': '4',
            'action': 'refreshed',
            'fileSize': '7794',
            'totalFileSize': '7794',
            'totalFileCount': '1',
            'change': '778849'
            }]

            :param path:
            :param force:
            :param p4_conn:
            :return:
            """

            path = path + '...'
            args = []
            if force:
                args.append('-f')

            sync_depot = self.p4_cmd_run(p4_cmd='sync', args=args, p4_conn=p4_conn, path=path)
            if sync_depot:
                print("<=P4 LAST SYNCING=> sync_depot out: Action {} change #{}".format(sync_depot[0]['action'],
                                                                                        sync_depot[0]['change']))
            return sync_depot

        def get_p4_changes(self, path, short=True, change_max=None, p4_conn=None):
            """
            p4 changes -l -m 1 -s submitted //addm/tkn_main/tku_patterns/CORE/10genMongoDB/...
            Get latest change for each test / pattern folder / depot path
                Output change
                [{
                    'change': '752626',
                    'time': '1541501985',
                    'user': 'mbocharo',
                    'client': 'mbocharo_laptop',
                    'status': 'submitted',
                    'changeType': 'public',
                    'path': '//addm/tkn_main/tku_patterns/STORAGE/Windows/tests/dml/*',
                    'desc': 'Fix dml for versions lower than 11.3\n'
                }]
            :param short:
            :param p4_conn: Instance of p4
            :param path: path to depot
            :type change_max: @ChangeMax,@now
            :return:
            """
            args = ['-t', '-l']
            path = path + '...'

            if short:
                args.append('-m1')
            if change_max:
                path = path + "@" + change_max + ',@now'

            changes_list = self.p4_cmd_run(p4_cmd='changes', args=args, p4_conn=p4_conn, path=path)

            return changes_list

        def get_p4_filelog(self, path, short=True, change_max=None, p4_conn=None):
            """
            p4 changes -l -m 1 -s submitted //addm/tkn_main/tku_patterns/CORE/10genMongoDB/...
            Get latest change for each test / pattern folder / depot path
                Output change
                [{
                    'change': '752626',
                    'time': '1541501985',
                    'user': 'mbocharo',
                    'client': 'mbocharo_laptop',
                    'status': 'submitted',
                    'changeType': 'public',
                    'path': '//addm/tkn_main/tku_patterns/STORAGE/Windows/tests/dml/*',
                    'desc': 'Fix dml for versions lower than 11.3\n'
                }]
            :param short:
            :param p4_conn: Instance of p4
            :param path: path to depot
            :type change_max: @ChangeMax,@now
            :return:
            """
            path = path + '...'
            args = ['-t', '-l']

            if short:
                args.append('-m1')
            if change_max:
                path = path + "@" + change_max + ',@now'

            filelog = self.p4_cmd_run(p4_cmd='filelog', args=args, p4_conn=p4_conn, path=path)
            return filelog


    class LocalOperations:
        """
        Make local parsing
        """

        def __init__(self):
            self.dep_path = '/home/user/TH_Octopus/perforce/addm/'
            self.lon_tz = pytz.timezone('Europe/London')
            ## Regexes for parsing:
            self.ticket_r = re.compile(r"(?P<ticket>(?:DRDC|DRUD)\d+-\d+|(?i)Esc\s+\d+)")
            self.escalation_r = re.compile(r"(?P<ticket>(?i)Esc\s+\d+)")
            self.review_r = re.compile(r"(?i)(?:Review\s+#|@)(?P<review>\d+)")

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
            parsed_test_files = TestsParseLocal().walk_fs_tests(local_depot_path=path_to_depot)
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
                print("There is no description for change %s", change)
            return change_desc_dict

        @staticmethod
        def insert_parsed_test(parsed_test_files):
            """
            Inserting parsed test cases dicts into DB with update_or_create method.
            :type parsed_test_files: list
            """
            assert isinstance(parsed_test_files, list)
            for item in parsed_test_files:
                TestsParseLocal.ins_or_upd_test_case(item)

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
                latest_change = P4ChangesParse().get_p4_changes(path=test_case.test_case_depot_path, p4_conn=p4_conn)[0]

                if int(latest_change.get('change', 0)) > int(test_case.change if test_case.change else 0):
                    print("Parsing ans saving new change! {}".format(iters))
                    self.parse_and_save_changes(test_case, latest_change, sync_force, p4_conn=p4_conn)
                    print('Processing p4 changes and save took: {} '.format(time() - ts))
                else:
                    print("Skip, changes are eq! {}".format(iters))
                    print('Processing p4 changes took: {} '.format(time() - ts))
                    # print("Change is latest - skip update and sync steps! {} {}".format(
                    #     test_case.change, test_case_name))
                    pass

        def compare_change_thread(self, test_case, sync_force, th_name, test_q, conn_q):
            """
            Compare local changes # with remote p4 depot change. Then parse if remote > local and save new.
            This run with one case item at once.

            :param test_case:
            :param sync_force:
            :param th_name:
            :param test_q:
            :param conn_q:
            :return:
            """
            p4_conn = conn_q.get()
            assert isinstance(test_case, TestCases)
            latest_change = P4ChangesParse().get_p4_changes(path=test_case.test_case_depot_path, p4_conn=p4_conn)[0]
            if int(latest_change.get('change', 0)) > int(test_case.change if test_case.change else 0):
                self.parse_and_save_changes(test_case, latest_change, sync_force, p4_conn=p4_conn)
                # print("{} Change update in db".format(th_name))
                msg = 'Updated: {} -> {} -> {}'.format(latest_change.get('change', 0), test_case.test_case_depot_path,
                                                       test_case.change)
            else:
                # print("{} Change is actual - skip".format(th_name))
                msg = ''
                pass
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

            w = 10
            threads = list(range(w))
            split_patt = self.chunkIt(test_cases, len(threads))
            print("Threads for parse patterns len: %s", len(threads))

            # Thread-cases pairs:
            for thread_i, cases_list in zip(threads, split_patt):
                cases_threads.update({'thread-{}'.format(str(thread_i)): dict(cases_list=collections.deque(cases_list),
                                                                              thread=thread_i)})

            print("Filling threads with jobs...")
            for thread_i, cases in cases_threads.items():  # Iter each thread and cases in it:

                conn_q = Queue()  # Separate Queue for p4 connection store
                p4_conn = PerforceOperations().p4_initialize()  # Init p4 connection for single thread-worker
                conn_q.put(p4_conn)  # Put active connection in queue for all threads

                print("Filling threads for thread: {}".format(thread_i))
                cases_list = cases.get('cases_list')  # Choose cases list from dict of threads+cases

                while 0 < len(cases_list):  # Each pattern generates own process
                    test_case = cases_list.popleft()  # When assigned to thread - delete item
                    th_name = 'Parse thread: {} test case: {}'.format(thread_i,
                                                                      test_case.test_case_depot_path)  # type: str
                    args_d = dict(test_case=test_case, th_name=th_name, test_q=test_q, conn_q=conn_q,
                                  sync_force=sync_force)
                    parse_thread = Thread(target=LocalOperations().compare_change_thread, name=th_name, kwargs=args_d)
                    thread_list.append(parse_thread)  # Save list of threads for further execution

            # Execute threads:
            print("Executing saved threads!")
            for parse_thread in thread_list:
                parse_thread.start()

            # Sync wait:
            print("Wait for all threads!")
            for parse_thread in thread_list:
                parse_thread.join()
                test_outputs.append(test_q.get())

            msg = "Finish all threads in - {} ! Patterns parsed - {}".format(time() - ts, len(test_outputs))
            print(msg)
            print(test_outputs)
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
            print("Change is not latest - RUN update and sync steps! {} {}".format(test_case.change, test_case_name))

            if sync_force:
                print("p4_change: {} > {} :local_change - run p4 sync_force: {}".format(
                    p4_change, test_case.change, test_case_depot_path_))

                # Sync folder to be sure we'll have the latest version:
                sync_force = P4ChangesParse().p4_sync(path=test_case_depot_path_, force=True, p4_conn=p4_conn)
                if not sync_force:
                    raise Exception("Path cannot be p4 synced! {}".format(test_case_depot_path_))
            else:
                print("p4_change: {} > {} :local_change - update only!".format(p4_change, test_case.change))

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

        def get_latest_changes(self, change_max, depot_path=None):
            """
            Get changes from p4 depot by p4 python command.
            Only changes in between from MAX latest in DB to @now current last in P4 depot
            :type change_max: str
            :type depot_path:
            :return list with dict of changes
            """
            if not depot_path:
                depot_path = self.dep_path
            return P4ChangesParse().get_p4_changes(short=False, change_max=change_max, path=depot_path)

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
            return P4ChangesParse().get_p4_filelog(short=True, change_max=change_max, path=depot_path, p4_conn=p4_conn)

        @staticmethod
        def get_test_cases(**kwargs):
            """
            Select test cases from table for further processing.
            Use kwargs to specify set or not - to select everything.

            :type kwargs: dict
            """
            test_cases = []
            test_type = kwargs.get('test_type', None)
            tkn_branch = kwargs.get('tkn_branch', None)
            pattern_library = kwargs.get('pattern_library', None)
            pattern_folder_name = kwargs.get('pattern_folder_name', None)
            pattern_folder_path = kwargs.get('pattern_folder_path', None)
            test_py_path = kwargs.get('test_py_path', None)
            test_dir_path = kwargs.get('test_dir_path', None)
            change = kwargs.get('change', None)
            change_user = kwargs.get('change_user', None)
            change_time = kwargs.get('change_time', None)

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
                P4ChangesParse().p4_clean(p4_conn=p4_conn)
                print("DEBUG: P4 Clean!")
                """ Initial sync by default - no matter, just update everything"""
                P4ChangesParse().p4_sync(path='//addm/', p4_conn=p4_conn)
                print("DEBUG: P4 Sync initial!")
                """ Run parse local """
                results = self.parse_local_test()
                print("Local files has been parsed!")
                """ Insert parted data in table """
                self.insert_parsed_test(results)
                print("New files from local parse has been saved!")

            """ /Select items from table, get change for each, sync, update """
            test_cases = self.get_test_cases(**selectables)
            print("Test cases has been selected to get latest changes!")
            """ Get perforce data for each and then save if new"""
            self.compare_changes_multi(test_cases, sync_force=sync_force, p4_conn=p4_conn)
            print("Test cases changes compared and refreshed!")

        def last_changes_get(self):
            """
            Get only diff between MAX change from local DB and actual changes on p4 depot
            Run sync -f for all found changes.
            :return:
            """
            from django.db.models import Max

            p4_conn = P4ChangesParse.p4_initialize(debug=True)

            change_max_q = TestCases.objects.all().aggregate(Max('change'))
            change_max = change_max_q.get('change__max', '312830')  # default change from 2015
            print("change_max: {}".format(change_max))

            _files_synced_plan = []
            _files_synced_actually = []
            p4_filelog = self.get_latest_filelog(depot_path=None, change_max=change_max, p4_conn=p4_conn)
            if p4_filelog:

                for p4_file in p4_filelog:
                    file_path = p4_file.get('depotFile', None)
                    if not p4_file.get('action', None) == 'delete':
                        synced = P4ChangesParse().p4_sync(path=file_path, force=True, p4_conn=p4_conn)
                        _files_synced_plan.append(file_path)
                        _files_synced_actually.append(synced[0].get('clientFile', None))
                        print("This will be synced: {} - {}".format(file_path, p4_file.get('action', None)))
                    else:
                        print("This should be deleted: {}".format(file_path))

            print("Synced files_synced_plan: {} {}".format(len(_files_synced_plan), _files_synced_plan))
            print("Synced files_synced_actually: {} {}".format(len(_files_synced_actually), _files_synced_actually))
            # Both should be equal:
            assert len(_files_synced_plan), len(_files_synced_actually)

            # TODO: Maybe better to get all changes at once?
            self.parse_and_changes_routine(sync_force=False, full=True, p4_conn=p4_conn)


    """
        Executes
    """
    # selectables = dict(test_type='tku_patterns')
    # LocalOperations().parse_and_changes_routine(selectables=selectables)
    # ts = time()
    # LocalOperations().last_changes_get()
    # print('Parsing took: {} '.format(time() - ts))
    # Parsing took: 861.1626603603363
    # Parsing took: 865.2727689743042
    # When passing p4_conn to all chains:
    # Parsing took: 88.95439553260803

    # 11-06-2020 Adding test.py from path like perforce\addm\tkn_main\product_content\r1_0\code\data\installed\tests
    # walked_test_data = TestsParseLocal().walk_fs_tests(local_depot_path='/mnt/g/perforce/')

    # results = TestsParseLocal().walk_fs_tests(local_depot_path="/mnt/g/perforce/")
    results = TestsParseLocal().walk_fs_tests(local_depot_path="/mnt/g/perforce/addm/tkn_main/")
    # results = TestsParseLocal().walk_fs_tests(local_depot_path="/mnt/g/perforce/addm/tkn_main/edp")
    # results = TestsParseLocal().walk_fs_tests(local_depot_path="/mnt/g/perforce/addm/tkn_main/tku_patterns/CLOUD")
    # results = TestsParseLocal().walk_fs_tests(local_depot_path='/home/user/TH_Octopus/perforce')
    for test in results:
        print(f"walked_test_data: {test}")
        break

    # Check live:
    # results = LocalPatternsParse().walk_fs_tests(local_depot_path="/mnt/g/perforce/addm/gargoyle/tku_patterns")
    # results = LocalPatternsP4Parse().parse_local_test(path_to_depot='/mnt/g/perforce')
    # LocalPatternsP4Parse().insert_parsed_test(results)
