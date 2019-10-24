"""
Manage p4 actions:
Now:
- Force sync everything with predefined workspace mapping excludes all garbage files.
Plan:
- Track changes and sync only changed files.
- Track revisions and file versions - save them to kind of DB
- Execute checking mechanism each <period of time>
- Backward API - listen to P4 server events. (UNSUPPORTED by p4)
"""

from __future__ import absolute_import, unicode_literals
import socket
import P4
import collections
from time import time
from octo_tku_patterns.models import TkuPatterns
from octo.config_cred import p4_cred, cred

# Python logger
import logging

log = logging.getLogger("octo.octologger")


class PerforceOperations:

    # noinspection SpellCheckingInspection
    def __init__(self):
        """

        CMD/TH_Octopus_mappings

        """
        # This variables can be shared to another functions.
        self.dep_path = p4_cred['dep_path']

        if cred['LOBSTER_HOST'] in socket.gethostname():
            self.p4_user = p4_cred['lobster_p4_user']
            self.p4_password = p4_cred['lobster_p4_password']
            self.p4_port = p4_cred['lobster_p4_port']
            self.p4_path = p4_cred['lobster_p4_path']
            self.p4_client = p4_cred['lobster_p4_client']
        else:
            self.p4_user = p4_cred['octopus_p4_user']
            self.p4_password = p4_cred['octopus_p4_password']
            self.p4_port = p4_cred['octopus_p4_port']
            self.p4_path = p4_cred['octopus_p4_path']
            self.p4_client = p4_cred['octopus_p4_client']

    def open_p4(self):
        log.info("<PerforceOperations> Making connection...")
        p4 = P4.P4()
        p4.user = self.p4_user
        p4.password = self.p4_password
        p4.port = self.p4_port
        p4.client = self.p4_client
        p4.ticket_file = '/var/www/octopus/p4_tickets'
        try:
            p4.connect()
            p4.run_login()
        except P4.P4Exception:
            for err in p4.errors:  # Display errors
                log.error("P4.P4Exception -> (%s)", err)
            for warn in p4.warnings:  # Display errors
                log.warning("P4.P4Exception -> (%s)", warn)
            # msg = '<=P4 CONNECTION=> P4Exception: {}'.format(e)
            # log.error(msg)
            # self.close_p4(p4)
            # raise P4.P4Exception(msg)
        except Exception as e:
            msg = "<=P4 CONNECTION ERROR=> {0}".format(e)
            log.error(msg)
            # self.close_p4(p4)
            raise Exception(msg)
        log.debug("<=P4 CONNECTION=> Connection made and saved: %s", p4)
        return p4

    def p4_initialize(self, debug=False):
        if debug:
            log.debug("<p4_initialize> Making connection...")
        p4 = P4.P4()
        p4.user = self.p4_user
        p4.password = self.p4_password
        p4.port = self.p4_port
        p4.client = self.p4_client
        try:
            p4.connect()
            p4.run_login()
        except P4.P4Exception:
            for err in p4.errors:  # Display errors
                log.error("P4.P4Exception -> (%s)", err)
            for warn in p4.warnings:  # Display errors
                log.warning("P4.P4Exception -> (%s)", warn)
            # msg = '<=P4 CONNECTION=> P4Exception: {}'.format(e)
            # log.error(msg)
            # self.close_p4(p4)
            # raise P4.P4Exception(msg)
        except Exception as e:
            msg = "<=P4 CONNECTION ERROR=> {0}".format(e)
            log.error(msg)
            # self.close_p4(p4)
            raise Exception(msg)
        return p4

    @staticmethod
    def close_p4(p4_conn, debug=False):
        if debug:
            log.debug("<close_p4> Close connection...")
        try:
            p4_conn.disconnect()
        except P4.P4Exception:
            for err in p4_conn.errors:  # Display errors
                log.error("P4.P4Exception -> (%s)", err)
                pass
            for warn in p4_conn.warnings:  # Display errors
                log.warning("P4.P4Exception -> (%s)", warn)
                pass
            # msg = '<=P4 CLOSE CONNECTION=> P4Exception: {}'.format(e)
            # log.error(msg)
            # return msg

    def p4_info(self):
        p4_info_str = []
        p4 = PerforceOperations().open_p4()
        log.debug("p4 instance: %s", p4)
        if p4:
            try:
                info = p4.run("info")
                for key in info[0]:
                    string = key, "=", info[0][key]
                    p4_info_str.append(string)
                # self.close_p4(p4)
                return p4_info_str
            except P4.P4Exception:
                for err in p4.errors:  # Display errors
                    log.error("P4.P4Exception -> (%s)", err)
                for warn in p4.warnings:  # Display errors
                    log.warning("P4.P4Exception -> (%s)", warn)
                # msg = '<=P4 CONNECTION=> P4Exception: {}'.format(e)
                # log.error(msg)
                # self.close_p4(p4)
                # raise P4.P4Exception(msg)
            except Exception as e:
                p4_info_str.append(('P4 Traceback', '=', e), )
                self.close_p4(p4)
                return p4_info_str

        else:
            p4_info_str.append(('P4 Traceback', '=',
                                "Perforce connection cannot be established. "
                                "All P4 operations are skipped for now."), )
            self.close_p4(p4)
            return p4_info_str

    def sync_force(self, depot_path, p4_conn=None):
        """
        Sync all data for testing.

        :return:
        """
        ts = time()
        # log.debug("<=P4 SYNCING=> sync_force Syncing path: %s", depot_path)
        if not p4_conn:
            p4_conn = self.p4_initialize(debug=True)

        try:
            p4_conn.run("sync", "-f", depot_path)
        except P4.P4Exception:
            for err in p4_conn.errors:  # Display errors
                log.error("P4.P4Exception -> (%s)", err)
            for warn in p4_conn.warnings:  # Display errors
                log.warning("P4.P4Exception -> (%s)", warn)
            # msg = '<=P4 CONNECTION=> P4Exception: {}'.format(e)
            # log.warning(msg)
            # return msg
        except Exception as e:
            log.debug("<=P4 CONNECTION ERROR=> sync_force P4 connection Fail!")
            # self.close_p4(p4_conn)
            raise Exception(e)
        # log.debug("<=P4 SYNCING=> sync_force Time spent: %s ", time() - ts)
        # self.close_p4(p4_conn)
        return dict(py_sync_force=True, time_stamp=time() - ts)

    def sync_last(self, branch):
        # noinspection SpellCheckingInspection
        """
        Sync only from latest changelist in DB till 999999999 change.
        So this only sync latest.

        https://stackoverflow.com/questions/4843158/check-if-a-python-list-item-contains-a-string-inside-another-string
        Example of p4_filelog z_DEV/outputs_examples/p4_filelog.txt

        Use Min>Max change to sync only difference.
        If Max is None - use one default and old change number from 2015. 312830
        In this case it will sync and parse everything that old.

        :param branch:
        :return:
        """
        from django.db.models import Max
        p4_conn = self.p4_initialize(debug=True)
        sync_depot = []

        change_max_q = TkuPatterns.objects.filter(tkn_branch__exact=branch).aggregate(Max('pattern_folder_change'))
        if not change_max_q.get('pattern_folder_change__max'):
            change_max = '312830'  # default change from 2015
        else:
            change_max = change_max_q.get('pattern_folder_change__max')

        log.debug("Select CHANGE MAX: %s", change_max)

        change_from = '@{}'.format(change_max)
        path = '//addm/{}/...'.format(branch)
        args = ['-t', '-l', '-m1']
        place_arg = path + change_from + ",@999999999"

        # P4 Run command:
        # noinspection SpellCheckingInspection,SpellCheckingInspection
        p4_filelog = p4_conn.run("filelog", args, place_arg)

        """ Excluded paths should not be synced, some of them are not needed for tests,
            another ones use local modified files, like tpl_tests.py 
            - locally modified Universal_dml_test_utils.py as main dml_test_utils.py
        """
        # noinspection SpellCheckingInspection,SpellCheckingInspection
        excluded = [
            # There are too much of updates we really don't use:
            'devices', 'docs', 'tkuwebapps',
            # Excluded from real testings:
            'HarnessFiles', 'SUPPORTDETAILS',
            # Do not sync to allow usage of my custom test utils:
            'python', 'tpl_tests', 'dml_test_utils',
        ]
        file_actions = ['delete']
        if 'python' in excluded:
            # noinspection SpellCheckingInspection
            log.warning("Attention, path '//addm/tkn_main/python/' is excluded!")

        log.debug("<=P4 LAST SYNCING=> Some folders and files were excluded from sync: %s", excluded)
        log.debug("<=P4 LAST SYNCING=> Syncing path: {0} Syncing from change: {1}".format(path, change_max))

        for change in p4_filelog:
            file_action = change['action'][0]
            depot_file_path = change['depotFile']
            if any(file_action in s for s in file_actions):
                pass
                # log.debug("This file was deleted: %s", depot_file_path)
            else:
                if [exclude for exclude in excluded if exclude in depot_file_path]:
                    pass
                    # log.debug("This path excluded: %s", depot_file_path)
                else:
                    try:
                        log.debug("<=P4 LAST SYNCING=> Syncing file: %s", depot_file_path)
                        sync_depot = p4_conn.run("sync", "-f", depot_file_path)
                        log.debug("<=P4 LAST SYNCING=> sync_depot out: Action %s change #%s", sync_depot[0]['action'],
                                  sync_depot[0]['change'])
                    except Exception as e:
                        log.error("<=P4 LAST SYNCING=> Errors: %s", e)
                        # pass
        # self.close_p4(p4)
        if sync_depot:
            if sync_depot[0].get('clientFile', False):
                return "Local sync_last OK!"  # This is only for task output.
        self.close_p4(p4_conn, debug=True)
        return "Local sync_last P4 not OK!"

    def p4_fstat_changes(self, p4_args, depot_path, p4_start_date='@2011/01/01', p4_end_date=None, p4_conn=None):
        # noinspection SpellCheckingInspection
        """
        The p4 fstat command dumps information about each file, with each item of information on a separate line.
        The output is best used within a Perforce API application where the items can be
        accessed as variables, but is also suitable for parsing by scripts from the client command output.
        https://www.perforce.com/perforce/doc.031/manuals/cmdref/fstat.html#1040665
        Will use:
        p4 fstat -C -l -H -s //addm/tkn_main/tku_patterns/...@2017/10/01,@2017/10/31
            >> /home/user/TH_Octopus/p4_fstat_date_C_l_H_s_2017
        For example - to get all changed files for last month. Just 70 Kb of data.

        -C Limits output to files mapped into the current workspace.
        -H Limits output to files on your have list; that is, files synced in the current workspace.
        -P Display the clientFile in Perforce syntax, as opposed to local syntax.
        -s Shortens output by excluding client-related data (for instance, the clientFile field).
        https://www.perforce.com/perforce/doc.031/manuals/cmdref/fstat.html#1040665

        p4_changes: [{'user': 'USER', 'path': '//addm/tkn_main/tku_patterns/CORE/IIS/tests/dml/*',
        'desc': 'IIS Test dml data update|No review\n', 'client': 'TH_Octopus_LP', 'change': '739024',
        'changeType': 'public', 'time': '1529929975', 'status': 'submitted'}]
            [{'change': '653772', 'time': '1475249848', 'user': 'cblake', 'client': 'Ozymandias', 'status': 'submitted',
            'changeType': 'public', 'path': '//addm/tkn_main/tku_patterns/CORE/B...',
            'desc': 'Update test.py to use loadAllTplFiles\n'}]



        :param p4_conn:
        :param p4_args:
        :param depot_path:
        :param p4_start_date:
        :param p4_end_date:
        :return:
        """
        fstat_changes = False
        changes_dict = collections.OrderedDict(fstat_changes='', p4_changes='')

        if not p4_conn:
            p4_conn = self.p4_initialize(debug=True)

        if p4_args:
            args = p4_args.split(" ")
        else:
            args = "-l".split(" ")

        if not p4_end_date:
            p4_end_date = "@now"

        p4_conn.cwd = self.p4_path
        if depot_path:
            depot_and_date = "{}{},{}".format(depot_path, p4_start_date, p4_end_date)
            # log.debug("RUN depot_and_date: %s", depot_and_date)
            try:
                fstat_changes = p4_conn.run_fstat(args, depot_and_date)
            except P4.P4Exception:
                for err in p4_conn.errors:  # Display errors
                    log.error("P4.P4Exception -> (%s)", err)
                for warn in p4_conn.warnings:  # Display errors
                    log.warning("P4.P4Exception -> (%s)", warn)
                    if 'no revision(s) after that date' in warn:
                        depot_and_date = "{}@2012/01/01,{}".format(depot_path, p4_start_date, p4_end_date)
                        log.debug("No revisions since (%s) use (%s) instead!", p4_start_date, depot_and_date)
                        try:
                            fstat_changes = p4_conn.run_fstat(args, depot_and_date)
                        except Exception as e:
                            msg = '<=P4 p4_fstat_changes=> Get older revisions - P4Exception: {}'.format(e)
                            log.warning(msg)
            except Exception as e:
                log.debug("<=P4 CONNECTION ERROR=> p4_fstat_changes P4 connection Fail! %s", e)
                raise Exception(e)
        else:
            msg = "<=P4 FSTAT ERROR=> depot_path is not set {}".format(depot_path)
            log.error(msg)
            return msg

        if fstat_changes:
            changes_dict.update(fstat_changes=fstat_changes)
            p4_changes = p4_conn.run("changes", "-t", "-m1", "-L", depot_path)
            changes_dict.update(p4_changes=p4_changes)

        # self.close_p4(p4_conn, debug=True)
        return changes_dict

    """
    New perforce operations class and methods
    """
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
            path = self.dep_path

        clean_ = self.p4_cmd_run(p4_cmd='clean', args=args, p4_conn=p4_conn, path=path)
        return clean_

    def p4_sync(self, path, force=False, p4_conn=None):
        """
        P4 synced: [
            {
        'depotFile': '//addm/tkn_ship/tku_patterns/CORE/BBB/AAA.tplpre',
        'clientFile': '/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE/BBB/AAA.tplpre',
        'rev': '4',
        'action': 'refreshed',
        'fileSize': '7794',
        'totalFileSize': '7794',
        'totalFileCount': '1',
        'change': '778849'
            }
        ]

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
            print("<=P4 LAST SYNCING=> sync_depot out: Action {} change #{}".format(sync_depot[0]['action'], sync_depot[0]['change']))
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
