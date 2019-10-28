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
