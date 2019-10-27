"""
Script to execute local operations like:
Parse configs and save data to tables.
Parse patterns.

Everything which run on MNG VM

"""

# noinspection PyUnresolvedReferences
from time import time
from datetime import datetime, timezone, timedelta
import pytz
import collections

import os
import re
# noinspection PyUnresolvedReferences
import os.path
import hashlib

from django.db.models.query import QuerySet

from run_core.models import AddmDev

from octo_tku_patterns.models import TkuPatterns, TestCases
from octo_tku_patterns.table_oper import PatternsDjangoModelRaw

from octo_tku_upload.models import TkuPackagesNew as TkuPackages
from run_core.p4_operations import PerforceOperations


import logging

# Python logger
log = logging.getLogger("octo.octologger")


class LocalPatternsParse:
    """
    This is local parsing procedure.
    It run the process like file walker, but simpler. Get all files stored on Octopus file system, update database
    and compose paths to test file, folder and depot path to each product folder. Later those parts will be used
    in tests and gathering perforce information - changes, mod. dates etc.
    """

    """ Later remove this, extra old and bad example """
    def compose_tree_paths(self, tkn_branch):
        """
        List all folders in TKN_MAIN and create dict for each foun pattern and test.py in it.
        List is snapshot of all tests and paths to them for selected SYNC branch.

        NOW it will be just /usr/tideway/SYNC/... but we can make numerous snapshots for different places
        in tideway, like /usr/tideway/(DEV|PREBUILD|ETC)...

        /home/user/TH_Octopus/perforce

        :param tkn_branch:
        :return:
        """
        log.debug("Getting path to all folders in branch: %s", tkn_branch)
        tkn_folders, octo_workspace = self.local_paths(tkn_branch)

        log.debug("Composing paths for branch: %s", tkn_branch)
        extra_folders, extra_folders_d = self.check_extra_folders(
            tkn_folders=tkn_folders)

        log.debug("Parsing all local files for branch: %s", tkn_branch)
        status = self.get_all_files(
            octo_workspace=octo_workspace,
            extra_folders_d=extra_folders_d,
            tkn_branch=tkn_branch)
        return status

    # noinspection PyUnresolvedReferences
    @staticmethod
    def local_paths(tkn_branch):
        """
        Make usual path to every local patterns\\scripts folder sets.
        :param tkn_branch:
        :return:
        """

        sep = os.sep
        if os.name == "nt":
            p4_workspace = "d:{os_sep}perforce{os_sep}".format(os_sep=os.sep)
        else:
            p4_workspace = "/home/user/TH_Octopus/perforce"
        octo_workspace = p4_workspace

        # When workspace extracted - compose usual paths to each dev folder used in TKU:
        if tkn_branch == 'tkn_ship':
            tkn_main_t = octo_workspace + sep + 'addm' + sep + 'tkn_ship'
        elif tkn_branch == 'tkn_main':
            tkn_main_t = octo_workspace + sep + 'addm' + sep + 'tkn_main'
        else:
            tkn_main_t = octo_workspace + sep + 'addm' + sep + 'tkn_main'

        # buildscripts_t = tkn_main_t + sep + 'buildscripts'
        tku_patterns_t = tkn_main_t + sep + 'tku_patterns'

        # Path to all pattern libs:
        BLADE_ENCLOSURE_t = tku_patterns_t + sep + 'BLADE_ENCLOSURE'
        CLOUD_t = tku_patterns_t + sep + 'CLOUD'
        CORE_t = tku_patterns_t + sep + 'CORE'
        DBDETAILS_t = tku_patterns_t + sep + 'DBDETAILS'
        EXTRAS_t = tku_patterns_t + sep + 'EXTRAS'
        LOAD_BALANCER_t = tku_patterns_t + sep + 'LOAD_BALANCER'
        MANAGEMENT_CONTROLLERS_t = tku_patterns_t + sep + 'MANAGEMENT_CONTROLLERS'
        MIDDLEWAREDETAILS_t = tku_patterns_t + sep + 'MIDDLEWAREDETAILS'
        STORAGE_t = tku_patterns_t + sep + 'STORAGE'
        SYSTEM_t = tku_patterns_t + sep + 'SYSTEM'
        NETWORK_t = tku_patterns_t + sep + 'NETWORK'

        tkn_folders = collections.OrderedDict(workspace=octo_workspace,
                                              tkn_main_t=tkn_main_t,
                                              tku_patterns_t=tku_patterns_t,
                                              BLADE_ENCLOSURE_t=BLADE_ENCLOSURE_t,
                                              CLOUD_t=CLOUD_t,
                                              CORE_t=CORE_t,
                                              DBDETAILS_t=DBDETAILS_t,
                                              EXTRAS_t=EXTRAS_t,
                                              LOAD_BALANCER_t=LOAD_BALANCER_t,
                                              MANAGEMENT_CONTROLLERS_t=MANAGEMENT_CONTROLLERS_t,
                                              MIDDLEWAREDETAILS_t=MIDDLEWAREDETAILS_t,
                                              NETWORK_t=NETWORK_t,
                                              STORAGE_t=STORAGE_t,
                                              SYSTEM_t=SYSTEM_t,
                                              )

        return tkn_folders, octo_workspace

    @staticmethod
    def check_extra_folders(tkn_folders):
        """
        Check if TKN folders exists.
        ['/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/BLADE_ENCLOSURE',
        '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/CLOUD',
        '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/CORE',
        '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/DBDETAILS',
        '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/LOAD_BALANCER',
        '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/MANAGEMENT_CONTROLLERS',
        '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/MIDDLEWAREDETAILS',
        '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/SYSTEM',
        '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE']


        {'STORAGE_t': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE',
        'LOAD_BALANCER_t': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/LOAD_BALANCER',
        'BLADE_ENCLOSURE_t': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/BLADE_ENCLOSURE',
        'MANAGEMENT_CONTROLLERS_t': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/MANAGEMENT_CONTROLLERS',
        'MIDDLEWAREDETAILS_t': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/MIDDLEWAREDETAILS',
        'DBDETAILS_t': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/DBDETAILS',
        'CORE_t': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/CORE',
        'SYSTEM_t': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/SYSTEM',
        'CLOUD_t': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/CLOUD'}


        :return:
        """
        # Get extra folders from previous parse in full_path_args.
        log.debug("Checking extra folders. Branch: %s", tkn_folders['tkn_main_t'])
        extra_folders = collections.deque()
        extra_folders_keys = ['BLADE_ENCLOSURE_t',
                              'CLOUD_t',
                              'CORE_t',
                              'DBDETAILS_t',
                              'LOAD_BALANCER_t',
                              'MANAGEMENT_CONTROLLERS_t',
                              'MIDDLEWAREDETAILS_t',
                              'SYSTEM_t',
                              'STORAGE_t',
                              'NETWORK_t',
                              ]

        extra_folders_d = collections.OrderedDict()
        # Making list of all possible pattern paths and then search through them all for imports.
        for folder_key in extra_folders_keys:
            if tkn_folders[folder_key]:
                extra_folder = tkn_folders[folder_key]
                # Add only unique folders:
                if extra_folder not in extra_folders:
                    # To be sure I can read files in folder - check_ide folder existence.
                    if os.path.exists(extra_folder) and os.path.isdir(extra_folder):
                        extra_folders.append(extra_folder)
                        extra_folders_d.update({folder_key: extra_folder})
                    else:
                        log.debug("Step 1.1 This path is not exist: " + str(extra_folder))
            else:
                log.debug("Be aware that this folder key is not exist: " + str(folder_key))

        return extra_folders, extra_folders_d

    # noinspection PyPep8
    def get_all_files(self, octo_workspace, extra_folders_d, tkn_branch):
        """
        Walk for all folders in current TH Octopus P4 workspace and compose paths for all files.

        :param tkn_branch:
        :param octo_workspace:
        :param extra_folders_d: dict
        :return:
        """
        listdir = os.listdir
        pattern_d = collections.OrderedDict(
            pattern_file_name='None',
            pattern_library='None',
            pattern_folder_name='None',
            pattern_file_path='None',
            test_py_path='None',
            test_py_path_template='None',
            test_folder_path='None',
            test_folder_path_template='None',
            pattern_file_path_depot='None',
            pattern_folder_path_depot='None',
            tkn_branch=tkn_branch,
        )

        for key, path in extra_folders_d.items():
            # Go through pattern library paths:
            pattern_d.update(pattern_library=os.path.basename(path))
            pattern_lib_content = listdir(path)
            # Initiate separate dict for each new pattern library with key = pattern library name like: CORE, DBDETAILS
            # Got through pattern folders and content foe each.
            for pattern_dir in pattern_lib_content:
                pattern_mod = os.path.join(path, pattern_dir)
                # Ignore extra files from pattern folder libs.
                if os.path.isdir(pattern_mod):
                    # Try to fetch data from p4 for current folder, after change it's path to usual depot place.
                    # Skip if this is db structure patterns, because they have different file tree. Later parse in elif.
                    if not pattern_mod.endswith(("Database_Structure_Patterns", "NVD")):
                        # List content for each found pattern module folder:
                        pattern_folder_content = listdir(pattern_mod)
                        for item in pattern_folder_content:

                            # Ignore folders where no pattern file found:
                            if item.endswith(".tplpre"):
                                # Get first options:
                                patt_f_path = os.path.join(pattern_mod, item)
                                pattern_d.update(pattern_folder_name=os.path.basename(pattern_mod))
                                pattern_d.update(pattern_file_path=patt_f_path)

                                # TODO: Remove in prod:
                                if os.name == "nt":
                                    pattern_d.update(
                                        pattern_folder_path_depot=pattern_mod.replace(octo_workspace, "/").replace('\\',
                                                                                                                   '/') + "/...")
                                    pattern_d.update(
                                        pattern_file_path_depot=patt_f_path.replace(octo_workspace, "/").replace('\\',
                                                                                                                 '/'))
                                else:
                                    pattern_d.update(
                                        pattern_folder_path_depot=pattern_mod.replace(octo_workspace, "/") + "/...")
                                    pattern_d.update(pattern_file_path_depot=patt_f_path.replace(octo_workspace, "/"))

                                pattern_d.update(pattern_file_name=os.path.basename(os.path.splitext(patt_f_path)[0]))
                                # Check for testing only for those folders where I found TPLPRE file.
                                path_to_test_folder = os.path.join(pattern_mod, "tests")
                                pattern_d.update(test_folder_path=path_to_test_folder)
                                pattern_d.update(
                                    test_folder_path_template=path_to_test_folder.replace(octo_workspace, "{}"))
                                if os.path.isdir(path_to_test_folder):
                                    # If pattern folder have no tests folder - we will see placeholders.
                                    tests_content = listdir(path_to_test_folder)
                                    for tests_item in tests_content:
                                        """
                                            Here we also can add parsing for model, dml file and etc.
                                            But I remove it, because it's not needed. 
                                        """
                                        if tests_item.endswith("test.py"):
                                            test_py_path = os.path.join(path_to_test_folder, tests_item)
                                            pattern_d.update(test_py_path=test_py_path)
                                            pattern_d.update(
                                                test_py_path_template=test_py_path.replace(octo_workspace, "{}"))
                                else:
                                    pattern_d.update(test_py_path='test_py_path Not found')
                                    pattern_d.update(test_py_path_template='test_py_path_template Not found')
                                    pattern_d.update(test_folder_path='test_folder_path Not found')
                                    pattern_d.update(test_folder_path_template='test_folder_path_template Not found')

                                self.insert_or_update_pattern(pattern_d)

                    # This lib has another tree format, so I will update set in other way.
                    elif pattern_mod.endswith("Database_Structure_Patterns"):
                        """
                            Database_Structure_Patterns use different hierarchy and have two levels of folders in it.
                            So it should have another way to parse. And it also have no test.py, just patterns.
                        """
                        pattern_folder_content = listdir(pattern_mod)
                        # We will get each pattern file and treat it as separate pattern module:
                        for item in pattern_folder_content:
                            if item.endswith(".tplpre"):
                                patt_f_path = os.path.join(pattern_mod, item)
                                pattern_d.update(pattern_folder_name=os.path.basename(pattern_mod))
                                pattern_d.update(pattern_file_path=patt_f_path)

                                # TODO: Remove in prod:
                                if os.name == "nt":
                                    pattern_d.update(
                                        pattern_folder_path_depot=pattern_mod.replace(octo_workspace, "/").replace('\\',
                                                                                                                   '/') + "/...")
                                    pattern_d.update(
                                        pattern_file_path_depot=patt_f_path.replace(octo_workspace, "/").replace('\\',
                                                                                                                 '/'))
                                else:
                                    pattern_d.update(
                                        pattern_folder_path_depot=pattern_mod.replace(octo_workspace, "/") + "/...")
                                    pattern_d.update(pattern_file_path_depot=patt_f_path.replace(octo_workspace, "/"))

                                pattern_d.update(pattern_file_name=os.path.basename(os.path.splitext(patt_f_path)[0]))
                                pattern_d.update(test_py_path='Database_Structure_Patterns')
                                pattern_d.update(test_py_path_template='Database_Structure_Patterns')
                                pattern_d.update(test_folder_path='Database_Structure_Patterns')
                                pattern_d.update(test_folder_path_template='Database_Structure_Patterns')
                                # TODO: Insert or update
                                self.insert_or_update_pattern(pattern_d)

                    # Check separate case when NVD:
                    elif pattern_mod.endswith("NVD"):
                        """
                            NVD folder is breaking the file hierarchy logic in CORE becase I haven't tplpre in it.
                            So It should have structure like below.
                        """
                        log.debug("Yes, this is Cris NVD folder in CORE, where tplpre file is not found!")
                        # patt_f_path = should be None
                        pattern_d.update(pattern_folder_name=os.path.basename(pattern_mod))
                        pattern_d.update(pattern_file_path='NVD_{}'.format(tkn_branch))

                        # TODO: Remove in prod:
                        if os.name == "nt":
                            pattern_d.update(
                                pattern_folder_path_depot=pattern_mod.replace(octo_workspace, "/").replace('\\',
                                                                                                           '/') + "/...")
                        else:
                            pattern_d.update(
                                pattern_folder_path_depot=pattern_mod.replace(octo_workspace, "/") + "/...")

                        pattern_d.update(pattern_file_path_depot='NVD_{}'.format(tkn_branch))
                        pattern_d.update(pattern_file_name='NVD_{}'.format(tkn_branch))

                        path_to_test_folder = os.path.join(pattern_mod, "tests")
                        pattern_d.update(test_folder_path=path_to_test_folder)
                        pattern_d.update(test_folder_path_template=path_to_test_folder.replace(octo_workspace, "{}"))

                        tests_content = listdir(path_to_test_folder)
                        for tests_item in tests_content:
                            # Get ony test.py file
                            if tests_item.endswith("test.py"):
                                test_py_path = os.path.join(path_to_test_folder, tests_item)
                                pattern_d.update(test_py_path=test_py_path)
                                pattern_d.update(test_py_path_template=test_py_path.replace(octo_workspace, "{}"))
                                pattern_d.update(pattern_file_name='NVD_{}'.format(tkn_branch))
                                # TODO: Insert or update
                                self.insert_or_update_pattern(pattern_d)
                # When pattern was lost:
                elif pattern_dir.endswith(".tplpre"):
                    pattern_file = pattern_dir
                    log.error(" WARN!!!! This is pattern files in 1st level dir: " + pattern_file)
        return True

    @staticmethod
    def insert_or_update_pattern(pattern_dict):
        """
        Use patterns parsed details as dict t insert or update values in TKU_PATTERNS table.

        :param pattern_dict:
        :return:
        """
        TKU_PATTERNS = TkuPatterns

        try:
            updated, create_new = TKU_PATTERNS.objects.update_or_create(
                pattern_file_name=pattern_dict.get('pattern_file_name'),
                pattern_library=pattern_dict.get('pattern_library'),
                pattern_folder_name=pattern_dict.get('pattern_folder_name'),
                pattern_file_path=pattern_dict.get('pattern_file_path'),
                tkn_branch=pattern_dict.get('tkn_branch'),
                defaults=dict(pattern_dict),
            )
            # TODO: Remove in prod:
            if create_new:
                log.debug("New pattern saved: updated %s, create_new %s, details %s",
                          updated,
                          create_new,
                          pattern_dict)
        except Exception as e:
            msg = "<=LocalOper=> get_all_files: Error: {} Details {} ".format(e, pattern_dict)
            log.error(msg)
            raise Exception(msg)

    """
    New parsing methods with walk fs
    """
    @staticmethod
    def walk_fs_tests(local_depot_path):
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

        if os.name == "nt":
            p4_workspace = "d:{os_sep}perforce{os_sep}".format(os_sep=os.sep)
        else:
            p4_workspace = "/home/user/TH_Octopus/perforce"

        octo_workspace = p4_workspace
        iters = 0

        walked_test_data = []
        for root, dirs, files in os.walk(local_depot_path, topdown=False):
            iters += 1
            for name in files:  # Iter over all files in path:
                if name == 'test.py':  # Check only test.py files
                    test_py_path = os.path.join(root, name)  # Compose full path to test.py path
                    test_dict = dict(
                        test_py_path=test_py_path,
                        test_py_path_template=test_py_path.replace(octo_workspace, "{}"),
                        test_dir_path=root,
                        test_dir_path_template=root.replace(octo_workspace, "{}"),
                    )

                    if 'tku_patterns' in root:  # Check if current path is related to tku_patterns:
                        if 'tkn_main' in root:
                            tkn_branch = 'tkn_main'
                        elif 'tkn_ship' in root:
                            tkn_branch = 'tkn_ship'
                        else:
                            tkn_branch = 'not_set'

                        test_dict.update(
                            test_type='tku_patterns',
                            tkn_branch=tkn_branch,
                            pattern_library=os.path.basename(os.path.dirname(os.path.dirname(root))),
                            pattern_folder_name=os.path.basename(os.path.dirname(root)),
                            pattern_folder_path=os.path.dirname(root),
                            test_case_depot_path=os.path.dirname(root).replace(octo_workspace, '/'),
                            pattern_library_path=os.path.dirname(os.path.dirname(root)),
                        )
                    elif '/main/code/python' in root:
                        # print("\tThis is main code test! {}".format(root))
                        test_dict.update(
                            test_type='main_python',
                            test_case_dir=os.path.basename(root),  # Like "pattern_folder_name" but for other tests
                            test_case_depot_path=root.replace(octo_workspace, '/')
                        )
                    # Here: will add something like octo_tests for plug-able mods

                    # If not related to tku_patterns
                    else:
                        print("\tThis is not patterns test! {}".format(root))
                        # HERE: Just compose all needed data for test entry
                        test_dict.update(
                            test_type='other',
                            test_case_dir=os.path.basename(root),  # Like "pattern_folder_name" but for other tests
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
                print("New pattern saved: updated %s, create_new %s, details %s", updated, create_new, dict_test_case)
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

    def p4_changes_run(self, pattern_d, th_name, test_q, conn_q):
        """
        https://www.perforce.com/perforce/r15.1/manuals/cmdref/p4_fstat.html
        The older -C, -H, -W, -P, -l, and -s options are supported for compatibility purposes.

        Execute same as p4_changes_step but for single pattern

          "p4_changes": [
            {
              "status": "submitted",
              "changeType": "public",
              "desc": "use loadAllTplFiles\n",
              "user": "cblake",
              "time": "1475246768",
              "client": "Ozymandias",
              "change": "653762",
              "path": "//addm/tkn_main/tku_patterns/CORE/..."
            }
          ],
          "fstat_changes": [
            {
              "fileSize": "2023",
              "digest": "E5B191344E4341B6418F716F9C9802F9",
              "haveRev": "2",
              "headTime": "1316179219",
              "depotFile": "//addm/tkn_main/tku_patterns/CORE/ActuateeReports/ActuateProducts-research.txt",
              "headModTime": "1316176576",
              "headType": "text",
              "headRev": "2",
              "isMapped": "",
              "clientFile": "D:\\perforce\\addm\\tkn_main\\tku_patterns\\CORE\\ActuateeReports\\ActuateProducts-research.txt",
              "headChange": "246594",
              "headAction": "integrate"
            },
            {
              "fileSize": "21746",
              "digest": "8E0B3E9C18049F6E2695A687C2879818",
              "haveRev": "9",
              "headTime": "1469613615",
              "depotFile": "//addm/tkn_main/tku_patterns/CORE/ActuateeReports/ActuateeReports.tplpre",
              "headModTime": "1468511308",
              "headType": "text",
              "headRev": "9",
              "isMapped": "",
              "clientFile": "D:\\perforce\\addm\\tkn_main\\tku_patterns\\CORE\\ActuateeReports\\ActuateeReports.tplpre",
              "headChange": "638221",
              "headAction": "edit"
            }
          ]
        }

        :param conn_q: P4 Connected
        :param test_q: Thread Queue
        :param th_name: Thread Name
        :param pattern_d: set
        :return:
        """

        # msg = "Thread parse start: {}".format(th_name)
        # log.debug(msg)
        p4_conn = conn_q.get()  # Get active P4 Connection from threading queue

        changes_dict = PerforceOperations().p4_fstat_changes(
            p4_conn=p4_conn,
            p4_args='-l',
            p4_start_date='@2011/01/01',
            depot_path=pattern_d.get('pattern_folder_path_depot'))

        # Check
        if not isinstance(changes_dict, collections.OrderedDict):
            msg = "<=P4 Changes ERROR=> changes_dict is not a dict: {}".format(changes_dict)
            log.error(msg)

        # Parse result from previous step:
        changes_formatted_dict = self.parse_p4_changes(
            p4_conn=p4_conn,
            changes_arg=changes_dict,
            pattern_d=pattern_d)
        # Check
        if not isinstance(changes_formatted_dict, collections.OrderedDict):
            msg = "<=P4 Changes ERROR=> changes_formatted_dict is not a dict: \n{}".format(changes_formatted_dict)
            log.error(msg)

        # Return list of changes_formatted_dicts:
        if changes_formatted_dict.get('pattern_folder_change'):
            log.debug("Got change %s for pattern %s prev change:()",
                      changes_formatted_dict.get('pattern_folder_change'),
                      pattern_d.get('pattern_folder_name')), pattern_d.get('pattern_folder_change')
            self.insert_p4_fstat_patterns_db(changes=changes_formatted_dict, pattern_d=pattern_d)

        # else:
        #     log.debug("ELSE changes_formatted_dict.get('pattern_folder_change') = %s", changes_formatted_dict.get('pattern_folder_change'))
        #     msg = "Skipping change is recent: {} <- {}".format(pattern_d.get('pattern_folder_change'), pattern_d.get('pattern_folder_name'))
        #     log.debug(msg)

        msg = "Thread parse finish: {}".format(th_name)
        test_q.put(msg)  # Mark finished parsing
        conn_q.put(p4_conn)  # Put active P4 connection back

    # noinspection PyPep8
    def parse_p4_changes(self, changes_arg, pattern_d, p4_conn=False):
        """
        From p4 get changes - parse content and update table of patterns of selected mode.
        Or p4 dirs and then for each?

        Perforce server details: serverDate	2018/06/25 11:02:42 -0500 CDT, tzoffset	-18000

        Will convert p4 timestamps for changes to UTC, then convert p4 UTC zone to London time.
        https://stackoverflow.com/questions/4563272/convert-a-python-utc-datetime-to-a-local-datetime-using-only-python-standard-lib/13287083#13287083
        https://stackoverflow.com/questions/17733139/getting-the-correct-timezone-offset-in-python-using-local-timezone

            # try:
            #     log.debug("WIll try to sync this item separately. If fail - skip and warn.")
            #     PerforceOperations().sync_single(file_depot)
            #     change_skip = False
            # except:
            #     log.debug("Cannot sync this item. Skipping.")
            #     item_sort = json.dumps(change, indent=2, ensure_ascii=False, default=pformat)
            #     log.debug("Changes: %s", item_sort)
            #     change_skip = True


        :return:
        """
        lon_tz = pytz.timezone('Europe/London')
        ignore_actions = ["move/delete", "delete", "noaction"]
        change_skip = False

        pattern_folder_change = pattern_d.get('pattern_folder_change')
        pattern_folder_path_depot = pattern_d.get('pattern_folder_path_depot')

        changes_formatted_dict = collections.OrderedDict(
            # pattern_file_list='',
            # test_py_rev='',
            change_desc='',
            change_user='',
            change_review='',
            change_ticket='',
            pattern_folder_change='',
            pattern_folder_mod_time='',
        )

        if changes_arg.get('fstat_changes', False):
            fstat_changes = changes_arg.get('fstat_changes')
            p4_changes = changes_arg.get('p4_changes')
            change_desc_dict = self.parse_p4_change_text(change=p4_changes)

            # headTime 1529998851 06/26/2018 08:40 //addm/tkn_sandbox/o.danylchenko/projects/p4/...@739059
            folder_mod_date = p4_changes[0]['time']
            p4_utc_dt = pytz.utc.localize(datetime.utcfromtimestamp(int(folder_mod_date)))  # get UTC frm p4 time
            pattern_folder_mod_time = p4_utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=lon_tz)  # set London time

            # log.debug("PARSE_P4_CHANGES Patt folder: %s P4 + TZ pattern_folder_mod_time: %s",
            #           pattern_d['pattern_folder_name'], pattern_folder_mod_time)

            if pattern_folder_change:
                # Here check if pattern folder change is recent:
                if pattern_folder_change and change_desc_dict['change_num']:
                    if pattern_folder_change < change_desc_dict['change_num']:
                        log.debug("<=SYNC=> Pattern folder change is not the latest: %s < %s Sync force path: %s",
                                  pattern_folder_change, change_desc_dict['change_num'], pattern_folder_path_depot)
                        # If DB change num is less than p4 change number - force sync and update on next iter.
                        PerforceOperations().sync_force(p4_conn=p4_conn, depot_path=pattern_folder_path_depot)
                        # log.info("Perforce sync -f PLACEHOLDER!")
                    else:
                        changes_formatted_dict.update(pattern_folder_change=False)
                else:
                    # If DB change number is not available - force sync and then update DB change number from p4 change
                    log.debug("<=SYNC=> Pattern dir change is not present in DB. Sync this: %s",
                              pattern_folder_path_depot)
                    PerforceOperations().sync_force(p4_conn=p4_conn, depot_path=pattern_folder_path_depot)
            else:
                log.info("This pattern haven't a change number in database and should be updated by P4 commands: %s %s",
                         pattern_d.get('pattern_library'),
                         pattern_d.get('pattern_folder_name'))

            # If DB change is not equal p4 change number - insert changes to db.
            # If there is no change number available for this item from db - also update it.
            if not pattern_folder_change or pattern_folder_change != change_desc_dict['change_num']:
                for change in fstat_changes:
                    if change.get('headAction'):
                        action = change['headAction']
                    else:
                        action = "noaction"

                    if action not in ignore_actions:
                        # file_path = change['clientFile']
                        file_path = change.get('clientFile', 'clientFile: No key for change {}'.format(change))
                        # This may check if files are out of depot or were deleted. Better replace it with p4 clean
                        # if not change.get('haveRev'):
                        #     file_depot = change['depotFile']
                        #     if not change.get('clientFile'):
                        #         log.debug("This file is probably not mapped into workspace %s", file_depot)
                        #     else:
                        #         file_local = change['clientFile']
                        #         log.debug("WARNING Was deleted but still present in local file system! "
                        #                   "So it's better to delete it from local storage. "
                        #                   "\nFile: '%s' \nLocal: '%s'", file_depot, file_local)
                        #     # cmd = 'rm -r {}'.format(file_local)
                        #     # try:
                        #     #     subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        #     # except FileNotFoundError:
                        #     #     log.debug("File was absent, so nothing to delete.")
                        if not change_skip:
                            # Now check each file on FSTAT output and parse based on its extension:
                            if file_path.endswith(".tplpre"):
                                pass
                                """
                                Here we can extract any additional details about pattern: 
                                    change, modification time, type, action etc.
                                    Like:
                                    fileSize   = change['fileSize']
                                    fileSize   = change['fileSize']
                                    headChange = change['headChange']
                                    headType   = change['headType']
                                    headAction = change['headAction']
                                    haveRev    = change.get('haveRev', 'None')
                                    headRev    = change['headRev']
                                    digest     = change['digest']
                                    clientFile = change['clientFile']
                                    depotFile  = change['depotFile']
                                But this is not needed now, so I removed all code and just leave space with this note.
                                """
                            elif file_path.endswith("test.py"):
                                pass

                            # This is stub for case, if we want to get back details of pattern or test.py changes:
                            # changes_formatted_dict.update(pattern_file_list=pattern_file_list)
                            # changes_formatted_dict.update(test_py_rev=test_py_file_dict)

                            changes_formatted_dict.update(change_desc=change_desc_dict['description'])
                            changes_formatted_dict.update(change_user=change_desc_dict['change_user'])
                            changes_formatted_dict.update(change_review=change_desc_dict['review'])
                            changes_formatted_dict.update(change_ticket=change_desc_dict['ticket'])
                            changes_formatted_dict.update(pattern_folder_change=change_desc_dict['change_num'])
                            changes_formatted_dict.update(pattern_folder_mod_time=pattern_folder_mod_time)

                            return changes_formatted_dict
                        else:
                            log.debug("Skip this change %s due ignore action: %s", change, action)
                            changes_formatted_dict.update(pattern_folder_change=False)
                    else:
                        client_file = change.get('clientFile', 'clientFile: No key for change {}'.format(change))
                        log.debug("File change in ignore_actions - skipping. File: %s", client_file)
                        changes_formatted_dict.update(pattern_folder_change=False)
            # In case when DB has the same change as 'p4 change' - do nothing, and do not touch DB.
            else:
                changes_formatted_dict.update(pattern_folder_change=False)
        else:
            msg = "There is no change in p4_fstat_changes result. fstat_changes = False. Error {0}".format(
                changes_arg['p4_changes'])
            changes_formatted_dict.update(pattern_folder_change=False)
            changes_formatted_dict.update(message=msg)

        return changes_formatted_dict

    @staticmethod
    def parse_p4_change_text_old(change):
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
        # Regexes for parsing:
        ticket_r = re.compile(r"(?P<ticket>(?:DRDC|DRUD)\d+-\d+|(?i)Esc\s+\d+)")
        escalation_r = re.compile(r"(?P<ticket>(?i)Esc\s+\d+)")
        review_r = re.compile(r"(?i)(?:Review\s+#|@)(?P<review>\d+)")
        change_desc_dict = dict(description="None",
                                change_user="None",
                                change_num="None",
                                review="None",
                                ticket="None")
        # description = 'None'
        if isinstance(change, list):
            first_change = change[0]
            if first_change.get('desc'):
                description_raw = first_change['desc']
                change_user = first_change['user']
                change_num = first_change['change']
                review = re.search(review_r, description_raw)
                ticket = re.search(ticket_r, description_raw)
                escalation = re.match(escalation_r, description_raw)
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
            log.debug("There is no description for change %s", change)
        return change_desc_dict

    # noinspection PyUnusedLocal
    @staticmethod
    def insert_p4_fstat_patterns_db(pattern_d, changes, count=None):
        """
        Check key/values of parsed details in dicts "changes" and insert them in TKU_PATTERNS databases.
        Will add\\change any values on patterns only if change list number was changed in depot.

        changes: {'pattern_folder_change': '732231', 'change_ticket': 'DRDC1-10802', 'pattern_file_list': [],
            'change_review': '#754906', 'change_user': 'vturchin', 'pattern_folder_mod_time': '2018-04-11',
            'change_desc': 'CUSTOMER | RFE | DRDC1-10802 | UCS device enhancement request | Review #754906'}

        :param count:
        :param changes:
        :param pattern_d:
        :return:
        """

        pattern_d.update(changes)
        try:
            updated, create_new = TkuPatterns.objects.update_or_create(
                pattern_file_name=pattern_d.get('pattern_file_name'),
                pattern_library=pattern_d.get('pattern_library'),
                pattern_folder_name=pattern_d.get('pattern_folder_name'),
                pattern_file_path=pattern_d.get('pattern_file_path'),
                tkn_branch=pattern_d.get('tkn_branch'),
                defaults=dict(pattern_d),
            )
            if create_new:
                log.debug("New pattern created: create_new %s, details %s",
                          create_new,
                          pattern_d)
            elif updated:
                log.debug("Current pattern updated: updated %s, details %s",
                          updated,
                          (pattern_d['id'], pattern_d['pattern_folder_path_depot']))
            else:
                pass
        except Exception as e:
            msg = "<=LocalOper=> get_all_files: Error: {} Details {} ".format(e, pattern_d)
            log.error(msg)
            raise Exception(msg)

    """
    New method of test cases parse:
    """
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

        :param test_case:
        :param sync_force:
        :param th_name:
        :param test_q:
        :param conn_q:
        :return:
        """
        p4_conn = conn_q.get()
        assert isinstance(test_case, TestCases)
        latest_change = PerforceOperations().get_p4_changes(path=test_case.test_case_depot_path, p4_conn=p4_conn)[0]
        if int(latest_change.get('change', 0)) > int(test_case.change if test_case.change else 0):
            self.parse_and_save_changes(test_case, latest_change, sync_force, p4_conn=p4_conn)
            log.debug("%s Change update in db", th_name)
            msg = 'Updated: {} -> {} -> {}'.format(latest_change.get('change', 0), test_case.test_case_depot_path, test_case.change)
        else:
            # log.debug("%s Change is actual - skip", th_name)
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
        log.debug("Threads for parse patterns len: %s", len(threads))

        # Thread-cases pairs:
        for thread_i, cases_list in zip(threads, split_patt):
            cases_threads.update({'thread-{}'.format(str(thread_i)): dict(cases_list=collections.deque(cases_list), thread=thread_i)})

        log.debug("Filling threads with jobs...")
        for thread_i, cases in cases_threads.items():       # Iter each thread and cases in it:

            conn_q = Queue()                                      # Separate Queue for p4 connection store
            p4_conn = PerforceOperations().p4_initialize()        # Init p4 connection for single thread-worker
            conn_q.put(p4_conn)                                   # Put active connection in queue for all threads

            log.debug("Filling threads for thread: {}".format(thread_i))
            cases_list = cases.get('cases_list')                  # Choose cases list from dict of threads+cases

            while 0 < len(cases_list):                            # Each pattern generates own process
                test_case = cases_list.popleft()                  # When assigned to thread - delete item
                th_name = 'Parse thread: {} test case: {}'.format(thread_i, test_case.test_case_depot_path)  # type: str
                args_d = dict(test_case=test_case, th_name=th_name, test_q=test_q, conn_q=conn_q, sync_force=sync_force)
                parse_thread = Thread(target=LocalPatternsP4Parse().compare_change_thread, name=th_name, kwargs=args_d)
                thread_list.append(parse_thread)                  # Save list of threads for further execution

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
        log.debug(test_outputs)
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
        p4_time   = latest_change.get('time', None)
        p4_user   = latest_change.get('user', None)
        p4_desc   = latest_change.get('desc', None)
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
        test_case.change        = p4_change
        test_case.change_desc   = p4_desc
        test_case.change_user   = p4_user
        test_case.change_review = change_desc_dict.get('review', None)
        test_case.change_ticket = change_desc_dict.get('ticket', None)
        test_case.change_time   = change_time

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
        log.debug("Test cases changes compared and refreshed!")

    def last_changes_get(self):
        """
        Get only diff between MAX change from local DB and actual changes on p4 depot
        If no change found, use default change from 2015. This will be used as initial point to rebuild database.

        Run sync -f for all found changes.
        :return:
        """
        from django.db.models import Max

        p4_conn = PerforceOperations().p4_initialize(debug=True)

        change_max_q = TestCases.objects.all().aggregate(Max('change'))
        change_max = change_max_q.get('change__max', '312830')  # default change from 2015
        log.debug("change_max: %s", change_max)

        _files_synced_plan = []
        _files_synced_actually = []
        p4_filelog = self.get_latest_filelog(depot_path=None, change_max=change_max, p4_conn=p4_conn)
        if p4_filelog:

            for p4_file in p4_filelog:
                file_path = p4_file.get('depotFile', None)
                if not p4_file.get('action', None) == 'delete':
                    synced = PerforceOperations().p4_sync(path=file_path, force=True, p4_conn=p4_conn)
                    _files_synced_plan.append(file_path)
                    _files_synced_actually.append(synced[0].get('clientFile', None))
                    log.debug("This will be synced: %s - %s", file_path, p4_file.get('action', None))
                else:
                    log.debug("This should be deleted: %s", file_path)

        log.debug("Synced files_synced_plan: %s %s", len(_files_synced_plan), _files_synced_plan)
        log.debug("Synced files_synced_actually: %s %s", len(_files_synced_actually), _files_synced_actually)
        # Both should be equal:
        if len(_files_synced_plan) == len(_files_synced_actually):
            log.info("Change / synced files lists are equal")
        else:
            log.warning("Change / synced files lists are NOT equal!")

        self.parse_and_changes_routine(sync_force=False, full=True, p4_conn=p4_conn)


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
            'addm_main_nightly': 'ftp://buildhub.tideway.com/hub/addm_main-latest/publish/tkn/11.3/tku/',
            'addm_main_continuous': 'ftp://buildhub.tideway.com/hub/addm_main-continuous/publish/tkn/11.3/tku/'}

        download_paths_d: {
            'addm_released': '/home/user/TH_Octopus/UPLOAD/HUB/RELEASED',
            'released_tkn': '/home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN',
            'continuous': '/home/user/TH_Octopus/UPLOAD/HUB/addm_main-continuous',
            'nightly': '/home/user/TH_Octopus/UPLOAD/HUB/addm_main-nightly'}


        """
        # self.addm_dev_group = AddmDev.objects.exclude(disables__isnull=True, addm_group__in=['alpha', 'beta', 'charlie', 'delta', 'echo', 'foxtrot']).order_by('addm_full_version')

    @staticmethod
    def tku_local_paths():
        """
        Set paths to TKU packages on remote hub and local FS
        Use dev ADDM versions to compose paths for only current addm versions.

        BUILDHUB:
            addm_released_tkn:
             - /hub/RELEASED/11_2_0_1/publish/tkn/11.2
             - /hub/RELEASED/11_1_0_6/publish/tkn/11.1
             - /hub/RELEASED/11_0_0_4/publish/tkn/11.0
             - /hub/RELEASED/10_2_0_6/publish/tkn/10.2
             - /hub/RELEASED/11_3/publish/tkn/11.3

             addm_main_continuous:
             - /hub/addm_main-continuous/publish/tkn/ (11.3)

             addm_main_nightly:
             - /hub/addm_main-nightly-180409190810/publish/tkn/ (11.3)

             release_sprints:
             - /hub/RELEASED/TKN/ (TKN_release_2018-03-1-90)

        LOCAL:
             nightly:
             - /home/user/TH_Octopus/UPLOAD/HUB/addm_main-nightly/

              continuous:
             - /home/user/TH_Octopus/UPLOAD/HUB/addm_main-continuous/

             addm_released:
             - /home/user/TH_Octopus/UPLOAD/HUB/RELEASED/

             released_tkn:
             - /home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN/

        PARSE:
              2018 Jan 24 16:31  Directory   <a href="ftp://buildhub.tideway.com:21/hub/RELEASED/
                                        TKN/TKN_release_2018-01-1-76/">TKN_release_2018-01-1-76/</a>
              2018 Feb 22 17:02  Directory   <a href="ftp://buildhub.tideway.com:21/hub/RELEASED/
                                        TKN/TKN_release_2018-02-1-80/">TKN_release_2018-02-1-80/</a>
              2018 Mar 02 09:44  Directory   <a href="ftp://buildhub.tideway.com:21/hub/RELEASED/
                                        TKN/TKN_release_2018-02-2-82/">TKN_release_2018-02-2-82/</a>
              2018 Mar 13 16:41  Directory   <a href="ftp://buildhub.tideway.com:21/hub/RELEASED/
                                        TKN/TKN_release_2018-02-3-85/">TKN_release_2018-02-3-85/</a>
              2018 Mar 26 15:29  Directory   <a href="ftp://buildhub.tideway.com:21/hub/RELEASED/
                                        TKN/TKN_release_2018-03-1-90/">TKN_release_2018-03-1-90/</a>

        ftp://buildhub.tideway.com/hub/TKN_release_2018-04-1-91

        buildhub_paths:
        {
        'ga_candidate_path': 'ftp://buildhub.tideway.com/hub/',
        'addm_main_nightly': 'ftp://buildhub.tideway.com/hub/addm_main-latest/publish/tkn/11.3/',
        'addm_tkn_paths': [
            {'11_0_0_4': 'ftp://buildhub.tideway.com/hub/RELEASED/11_0_0_4/publish/tkn/11.0/'},
            {'11_1_0_6': 'ftp://buildhub.tideway.com/hub/RELEASED/11_1_0_6/publish/tkn/11.1/'},
            {'11_2_0_1': 'ftp://buildhub.tideway.com/hub/RELEASED/11_2_0_1/publish/tkn/11.2/'},
            {'11_2_0_2': 'ftp://buildhub.tideway.com/hub/RELEASED/11_2_0_2/publish/tkn/11.2/'},
            {'11_3': 'ftp://buildhub.tideway.com/hub/RELEASED/11_3/publish/tkn/11.3/'},
            {'11_3_0_2': 'ftp://buildhub.tideway.com/hub/RELEASED/11_3_0_2/publish/tkn/11.3/'}],
        'addm_main_continuous': 'ftp://buildhub.tideway.com/hub/addm_main-continuous/publish/tkn/11.3/',
        'tkn_main_cont_path': 'ftp://buildhub.tideway.com/hub/tkn_main-continuous/publish/tkn/',
        'release_sprints': 'ftp://buildhub.tideway.com/hub/RELEASED/TKN/'
        }


        :return:
        """
        log.debug("<=LocalDownloads=> Composing paths.")

        addm_sort = []
        addm_tkn_paths = []
        addm_versions = AddmDev.objects.filter(
            disables__isnull=True,
            addm_group__in=['alpha', 'beta', 'charlie', 'delta', 'echo', 'foxtrot']
        ).order_by('addm_full_version').values('addm_v_int', 'addm_full_version')

        # tkn_main_cont_paths = []
        place = '/home/user/TH_Octopus/UPLOAD/'
        hub_path = 'ftp://buildhub.tideway.com/'

        # Latest ADDM released
        # DEV: For addm dev code - it is not needed fot TKU.
        addm_main_continuous = '{}hub/addm_main-continuous/publish/tkn/11.3/tku/'.format(hub_path)
        # addm_main_continuous = '{}hub/addm_main-continuous/publish/tkn/11.3/'.format(hub_path)
        # ftp://buildhub.tideway.com/hub/addm_main-latest
        addm_main_nightly = '{}hub/addm_main-latest/publish/tkn/11.3/tku/'.format(hub_path)
        # addm_main_nightly    = '{}hub/addm_main-latest/publish/tkn/11.3/'.format(hub_path)

        # TKN Release:
        ga_candidate_path = '{}hub/'.format(hub_path)
        # TKN Daily builds:
        tkn_main_continuous_path = '{}hub/tkn_main-continuous/publish/tkn/'.format(hub_path)  # MAIN
        tkn_ship_continuous_path = '{}hub/tkn_ship-nightly-latest/publish/tkn/'.format(hub_path)  # SHIP

        # RELEASED TKU:
        released = '{}hub/RELEASED/'.format(hub_path)
        release_sprints = '{}TKN/'.format(released)
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
            tkn_main_cont_path=tkn_main_continuous_path,  # MAIN
            tkn_ship_cont_path=tkn_ship_continuous_path,  # SHIP
            # Other
            release_sprints=release_sprints,
            addm_tkn_paths=addm_tkn_paths,
            ga_candidate_path=ga_candidate_path,
            # DEV: For addm dev code - it is not needed fot TKU.
            # /hub/addm_main-continuous/publish/tkn/11.3/tku
            addm_main_continuous=addm_main_continuous,
            # /hub/addm_main-nightly-156/publish/tkn/11.3/tku
            addm_main_nightly=addm_main_nightly,
            # /hub/tkn_main-continuous/publish/tkn/11.3/tku
        )
        # log.debug("<=BUILDHUB_PATHS=> buildhub_paths: %s", buildhub_paths)

        download_paths = dict(
            # /hub/RELEASED/TKN/TKN_release_2018-02-2-82/publish/tkn/11.3/tku/
            released_tkn=released_tkn,
            addm_released="{}HUB/RELEASED".format(place),
            # /hub/tkn_main-continuous/publish/tkn/11.3/tku
            tkn_main_continuous="{}HUB/tkn_main_continuous".format(place),
            tkn_ship_continuous="{}HUB/tkn_ship-nightly-latest".format(place),
            # sftp://user@172.25.144.117/home/user/TH_Octopus/UPLOAD/HUB/GA_CANDIDATE
            ga_candidate="{}HUB/GA_CANDIDATE".format(place),
            # DEV: For addm dev code - it is not needed fot TKU.
            # /hub/addm_main-continuous/publish/tkn/11.3/tku
            continuous="{}HUB/addm_main-continuous".format(place),
            # /hub/addm_main-nightly-156/publish/tkn/11.3/tku
            nightly="{}HUB/addm_main-nightly".format(place),
        )
        # log.debug("<=DOWNLOAD_PATHS=> download_paths: %s", download_paths)

        return buildhub_paths, download_paths

    def tku_wget_cmd_compose(self):
        """
        Prepare list of commands to execute:

        addm_main_continuous:
            wget --no-verbose --continue --recursive --no-host-directories --read-timeout=120
                 --reject='*.log,*log,*com_tkn.log'
                 --exclude-directories='*/*/*/*/*/kickstarts/,*/*/*/*/kickstarts/,*/*/*/kickstarts/,*/*/kickstarts/'
                 --cut-dirs=5 ftp://buildhub.tideway.com/hub/addm_main-continuous/publish/tkn/11.3/tku/
                 --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/addm_main-continuous

        addm_main_nightly:
            wget --no-verbose --continue --recursive --no-host-directories --read-timeout=120
                 --reject='*.log,*log,*com_tkn.log'
                 --exclude-directories='*/*/*/*/*/kickstarts/,*/*/*/*/kickstarts/,*/*/*/kickstarts/,*/*/kickstarts/'
                 --cut-dirs=5 ftp://buildhub.tideway.com/hub/addm_main-latest/publish/tkn/11.3/tku/
                 --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/addm_main-nightly

        tkn_main_continuous:
            wget --no-verbose --continue --recursive --no-host-directories --read-timeout=120
                 --reject='*.log,*log,*com_tkn.log'
                 --exclude-directories='*/*/*/*/*/kickstarts/,*/*/*/*/kickstarts/,*/*/*/kickstarts/,*/*/kickstarts/'
                 --cut-dirs=4 ftp://buildhub.tideway.com/hub/tkn_main-continuous/publish/tkn/
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
        # Get all parsed paths to release_sprints:
        release_sprints = self.parse_released_tkn_html(buildhub_paths_d['release_sprints'],
                                                       download_paths_d['released_tkn'])

        # Get all parsed paths to ga_candidate:
        ga_candidates = self.parse_released_tkn_html(buildhub_paths_d['ga_candidate_path'],
                                                     download_paths_d['ga_candidate'])

        # WGET options need to be filled with args:
        #            "--timestamping;" \
        wget_rec = "wget;" \
                   "--no-verbose;" \
                   "--timestamping;" \
                   "--recursive;" \
                   "--no-host-directories;" \
                   "--read-timeout=120;" \
                   "--reject='*.log,*log,*com_tkn.log';" \
                   "--exclude-directories='*/*/*/*/*/kickstarts/,*/*/*/*/kickstarts/,*/*/*/kickstarts/,*/*/kickstarts/,*/kickstarts/';" \
                   "--cut-dirs={cut};{ftp};" \
                   "--directory-prefix={dir}"

        # DEV: For addm dev code - it is not needed fot TKU.
        # Compose download wget cmd for CONTINUOUS:
        # wget_continuous = wget_rec.format(cut=5, ftp=buildhub_paths_d['addm_main_continuous'],
        #                                   dir=download_paths_d['continuous'])
        # wget_cmd_d.update(addm_main_continuous=wget_continuous)

        # DEV: For addm dev code - it is not needed fot TKU.
        # Compose download wget cmd for NIGHTLY
        # wget_nightly = wget_rec.format(cut=5, ftp=buildhub_paths_d['addm_main_nightly'],
        #                                dir=download_paths_d['nightly'])
        # wget_cmd_d.update(addm_main_nightly=wget_nightly)

        # Compose download wget cmd for tkn_main-continuous
        # 4 - do not cut addm version folders
        tkn_main_cont_wget = wget_rec.format(cut=4, ftp=buildhub_paths_d['tkn_main_cont_path'],
                                             dir=download_paths_d['tkn_main_continuous'])
        # For TKN_SHIP:
        tkn_ship_cont_wget = wget_rec.format(cut=4, ftp=buildhub_paths_d['tkn_ship_cont_path'],
                                             dir=download_paths_d['tkn_ship_continuous'])

        wget_cmd_d.update(
            tkn_main_continuous=tkn_main_cont_wget,
            tkn_ship_continuous=tkn_ship_cont_wget,
        )

        # Compose download wget cmd for each sprint TKN
        for sprint in release_sprints:
            wget_sprints_html = wget_rec.format(cut=3, ftp=sprint, dir=download_paths_d['released_tkn'])
            if wget_sprints_html not in wget_cmd_d:
                wget_cmd_d.update(released_tkn=wget_sprints_html)

        # GA Candidate -  Compose download wget cmd for each sprint TKN
        for ga_candidate in ga_candidates:
            ga_candidate_html = wget_rec.format(cut=1, ftp=ga_candidate, dir=download_paths_d['ga_candidate'])
            if ga_candidate_html not in wget_cmd_d:
                wget_cmd_d.update(ga_candidate=ga_candidate_html)

        # Compose paths to download separately released packages for ADDM VA:
        for addm_va_d_item in buildhub_paths_d['addm_tkn_paths']:
            for va_k, va_v in addm_va_d_item.items():
                # local_path_to_zip = download_paths_d['addm_released']+va_k
                wget_addm_va = wget_rec.format(cut=2, ftp=va_v, dir=download_paths_d['addm_released'])
                if wget_addm_va not in wget_cmd_d:
                    # log.debug("<=LocalDownloads=> Download ADDM VA: %s %s", va_k, wget_addm_va)
                    wget_cmd_d.update(addm_released=wget_addm_va)

        log.debug("<=LocalDownloads=> Compose commands! %s", wget_cmd_d)
        return wget_cmd_d

    def wget_tku_build_hub_option(self, **kwargs):
        """
        Download and parse only selected package:
        available options:
            addm_main_continuous
            addm_main_nightly
            tkn_main_continuous
            released_tkn
            addm_released

        :return:
        """
        import subprocess
        tku_key = kwargs.get('tku_type', None)
        outputs_l = []
        command_list = []
        wget_cmd_d = self.tku_wget_cmd_compose()
        if tku_key:
            command_list = [wget_cmd_d[tku_key]]  # tkn_main_continuous
        else:
            for k, v in wget_cmd_d.items():
                command_list.append(v)

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
        self.tku_packages_parse(download_paths_d)

        # Do not return outputs, because we don't care of saving them to database instead of read logs!
        # return outputs_l
        return True

    @staticmethod
    def parse_released_tkn_html(release_sprints, released_tkn):
        """
        Parse HTML in RELEASED/TKN/index.html to get all located sprint builds in there.
        Pompose links ready to download.

        :return:
        """
        import subprocess
        run_cmd = []
        all_last_sprints = []
        last_tkn_r = re.compile(r"(TKN_release_\d+-\d+-\d+-\d+)")

        log.debug("<=LocalDownloads=> Parsing index.html for %s to get sprint builds.", released_tkn)
        try:
            # sftp://user@172.25.144.117/home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN/index.html
            run_cmd = subprocess.Popen(['wget', '--timestamping', release_sprints, '--directory-prefix', released_tkn],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            run_cmd.communicate()
            run_cmd.wait()
        except Exception as e:
            log.error("<=LocalDownloads=> Error during operation for: %s %s", run_cmd, e)

        index_file = released_tkn + "/index.html"
        if os.path.isfile(index_file):
            open_file = open(index_file, "r")
            read_file = open_file.read()
            latest_tkn = last_tkn_r.findall(read_file)
            open_file.close()
            for found in latest_tkn:
                tkn_release_link = release_sprints + found + '/'
                if tkn_release_link not in all_last_sprints:
                    all_last_sprints.append(tkn_release_link)

        return all_last_sprints

    def tku_packages_parse(self, download_paths_d):
        """
        Parse local packages of TKU and save versions and file info to DB

        Nightly path: '/home/user/TH_Octopus/UPLOAD/HUB/addm_main-nightly'
            dir: 'nightly'
                items: '['tku']'

        Released TKN path: '/home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN'
            dir: 'released_tkn'
                items: '['index.html', 'TKN_release_2018-01-1-76', 'TKN_release_2018-02-1-80',
                'TKN_release_2018-02-2-82', 'TKN_release_2018-02-3-85', 'TKN_release_2018-03-1-90']'

        Continuous path: '/home/user/TH_Octopus/UPLOAD/HUB/addm_main-continuous'
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
            if key == 'nightly':
                pass
                # /home/user/TH_Octopus/UPLOAD/HUB/addm_main-nightly/tku/
                #   Technology-Knowledge-Update-2068-04-1-ADDM-11.3+.zip
                # tku_zips = os.path.join(path_v, "tku")
                # tku_content = os.listdir(tku_zips)
                # tkn_nightly_zip_list = self.compose_tku_args(dir_content=tku_content, tku_zips=tku_zips,
                #                                              dir_key=key, package_type='nightly', zip_type='tku')
                # # log.debug("<=LocalDownloads=> Insert TKU nightly package details in db.")
                # self.insert_tku_package(tkn_nightly_zip_list)
                #
                # edp_zips = os.path.join(path_v, "edp")
                # edp_content = os.listdir(edp_zips)
                # nightly_edp_zip_list = self.compose_tku_args(dir_content=edp_content, tku_zips=edp_zips,
                #                                              dir_key=key, package_type='nightly', zip_type='edp')
                # # log.debug("<=LocalDownloads=> Insert TKU nightly package details in db.")
                # self.insert_tku_package(nightly_edp_zip_list)

            # DEV: For addm dev code - it is not needed fot TKU.
            elif key == 'continuous':
                pass
                # # /home/user/TH_Octopus/UPLOAD/HUB/addm_main-continuous/tku/
                # #   Technology-Knowledge-Update-2068-04-1-ADDM-11.3+.zip
                # tku_zips = os.path.join(path_v, "tku")
                # tku_content = os.listdir(tku_zips)
                # tkn_nightly_zip_list = self.compose_tku_args(dir_content=tku_content, tku_zips=tku_zips,
                #                                              dir_key=key, package_type='continuous', zip_type='tku')
                # # log.debug("<=LocalDownloads=> Insert TKU continuous package details in db.")
                # self.insert_tku_package(tkn_nightly_zip_list)
                #
                # edp_zips = os.path.join(path_v, "edp")
                # edp_content = os.listdir(edp_zips)
                # nightly_edp_zip_list = self.compose_tku_args(dir_content=edp_content, tku_zips=edp_zips,
                #                                              dir_key=key, package_type='continuous', zip_type='edp')
                # # log.debug("<=LocalDownloads=> Insert TKU continuous package details in db.")
                # self.insert_tku_package(nightly_edp_zip_list)

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
                # When md5sum is different - update current record:
                if not get_if_exist.zip_file_md5_digest == package['zip_file_md5_digest']:
                    log.debug("<=UPDATE=> (%s) != (%s)", get_if_exist.zip_file_md5_digest,
                              package['zip_file_md5_digest'])
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

    # For debugging and other purposes:
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

    def _wget_tku_build_hub(self):
        """
        WGET TKU zips for upload tests

        CMD EXAMPLES:

        wget,--no-verbose,--timestamping,--recursive,--continue,--no-host-directories,--reject,'*.log',
            --cut-dirs=5,ftp://buildhub.tideway.com/hub/addm_main-continuous/publish/tkn/11.3/tku/,
                --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/addm_main-continuous

        wget,--no-verbose,--timestamping,--recursive,--continue,--no-host-directories,--reject,'*.log',
            --cut-dirs=5,ftp://buildhub.tideway.com/hub/addm_main-latest/publish/tkn/11.3/tku/,
                --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/addm_main-nightly

        wget,--no-verbose,--timestamping,--recursive,--continue,--no-host-directories,--reject,'*.log',
            --cut-dirs=3,ftp://buildhub.tideway.com/hub/RELEASED/TKN/TKN_release_2018-01-1-76/,
                --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN

        wget,--no-verbose,--timestamping,--recursive,--continue,--no-host-directories,--reject,'*.log',
            --cut-dirs=5,{'11_2_0_2': 'ftp://buildhub.tideway.com/hub/RELEASED/11_2_0_2/publish/tkn/11.2/tku/'},
                --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN

        wget,--no-verbose,--timestamping,--recursive,--continue,--no-host-directories,--reject,'*.log',
            --cut-dirs=5,{'11_3': 'ftp://buildhub.tideway.com/hub/RELEASED/11_3/publish/tkn/11.3/tku/'},
                --directory-prefix=/home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN

        ftp://buildhub.tideway.com/hub/TKN_release_2018-04-1-91


        :return:
        """
        import subprocess
        wget_cmd_list = []
        outputs_l = []

        # Get usual paths to all TKNs AND:
        buildhub_paths_d, download_paths_d = self.tku_local_paths()
        # Get all parsed paths to release_sprints:
        release_sprints = self.parse_released_tkn_html(buildhub_paths_d['release_sprints'],
                                                       download_paths_d['released_tkn'])

        # Get all parsed paths to ga_candidate:
        ga_candidates = self.parse_released_tkn_html(buildhub_paths_d['ga_candidate_path'],
                                                     download_paths_d['ga_candidate'])

        # WGET options need to be filled with args:
        #            "--timestamping;" \
        wget_rec = "wget;" \
                   "--no-verbose;" \
                   "--timestamping;" \
                   "--recursive;" \
                   "--no-host-directories;" \
                   "--read-timeout=120;" \
                   "--reject='*.log,*log,*com_tkn.log';" \
                   "--exclude-directories='*/*/*/*/*/kickstarts/,*/*/*/*/kickstarts/,*/*/*/kickstarts/,*/*/kickstarts/,*/kickstarts/';" \
                   "--cut-dirs={cut};{ftp};" \
                   "--directory-prefix={dir}"

        # DEV: For addm dev code - it is not needed fot TKU.
        # Compose download wget cmd for CONTINUOUS:
        # wget_continuous = wget_rec.format(5, buildhub_paths_d['addm_main_continuous'], download_paths_d['continuous'])
        # wget_cmd_list.append(wget_continuous)

        # DEV: For addm dev code - it is not needed fot TKU.
        # Compose download wget cmd for NIGHTLY
        # wget_nightly = wget_rec.format(5, buildhub_paths_d['addm_main_nightly'], download_paths_d['nightly'])
        # wget_cmd_list.append(wget_nightly)

        # Compose download wget cmd for tkn_main-continuous
        # 4 - do not cut addm version folders
        tkn_main_cont_wget = wget_rec.format(cut=4, ftp=buildhub_paths_d['tkn_main_cont_path'],
                                             dir=download_paths_d['tkn_main_continuous'])
        wget_cmd_list.append(tkn_main_cont_wget)

        # Compose download wget cmd for each sprint TKN
        for sprint in release_sprints:
            wget_sprints_html = wget_rec.format(cut=3, ftp=sprint, dir=download_paths_d['released_tkn'])

            if wget_sprints_html not in wget_cmd_list:
                wget_cmd_list.append(wget_sprints_html)

        # GA Candidate -  Compose download wget cmd for each sprint TKN
        for ga_candidate in ga_candidates:
            ga_candidate_html = wget_rec.format(cut=1, ftp=ga_candidate, dir=download_paths_d['ga_candidate'])

            if ga_candidate_html not in wget_cmd_list:
                wget_cmd_list.append(ga_candidate_html)

        # Compose paths to download separately released packages for ADDM VA:
        for addm_va_d_item in buildhub_paths_d['addm_tkn_paths']:
            for va_k, va_v in addm_va_d_item.items():
                # local_path_to_zip = download_paths_d['addm_released']+va_k

                wget_addm_va = wget_rec.format(cut=2, ftp=va_v, dir=download_paths_d['addm_released'])

                if wget_addm_va not in wget_cmd_list:
                    # log.debug("<=LocalDownloads=> Download ADDM VA: %s %s", va_k, wget_addm_va)
                    wget_cmd_list.append(wget_addm_va)

        log.debug("<=LocalDownloads=> START WGET commands exec!")
        # noinspection PyBroadException
        for cmd_item in wget_cmd_list:
            try:
                log.debug("<=LocalDownloads=> RUN cmd_item: '%s'", cmd_item.replace(';', ' '))
                run_cmd = subprocess.Popen(cmd_item.split(';'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = run_cmd.communicate()
                stdout, stderr = stdout.decode('utf-8'), stderr.decode('utf-8')
                run_cmd.wait()  # wait until command finished
                outputs_l.append([stdout, stderr])
                log.debug("<=LocalDownloads=>  WGET stdout/stderr: \n\tstdout: %s \n\tstderr %s", stdout, stderr)
            except Exception as e:
                log.error("<=LocalDownloads=> Error during operation for: %s %s", cmd_item, e)
        log.debug("<=LocalDownloads=> FINISH WGET commands exec!")

        self.tku_packages_parse(download_paths_d)

        # Do not return outputs, because we don't care of saving them to database instead of read logs!
        # return outputs_l
        return True


class LocalDB:
    """
    Local operations with database - update, insert, index etc
    """

    @staticmethod
    def history_weight(last_days=30):
        """
        Get historical test records for n days,
        group by test.py path and date, summarize all weights for each

        :return:
        """
        patterns_weight = collections.OrderedDict()
        all_history_weight = PatternsDjangoModelRaw().sel_history_by_latest_all(query_args=dict(last_days=last_days))

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
