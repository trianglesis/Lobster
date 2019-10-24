if __name__ == "__main__":

    import django
    import logging
    import P4

    log = logging.getLogger("octo.octologger")

    django.setup()

    from octo_tku_patterns.tasks import PatternTestExecCases
    from octo_tku_patterns.tasks import TPatternParse

    from run_core.p4_operations import PerforceOperations
    from octo_tku_patterns.tasks import TPatternParse

    from octo.config_cred import p4_cred


    def dev_p4_fstat_file_change(file_path, change_num):
        """
        Use path to file and change number with p4 fstat to get info in change description.

        :param file_path:
        :param change_num:
        :return:
        """
        p4 = PerforceOperations().open_p4()
        changes_d = dict(changes='', errors='')
        p4_path = "/home/user/TH_Octopus/perforce"

        # START only when dates were chosen:
        if file_path and not change_num == "None":
            # try:
            p4.cwd = p4_path
            # changes = p4.run_fstat(args)
            # changes = p4.run_fstat(branch_date)
            # changes = p4.run("fstat", "-e", change_num, file_path)
            # noinspection SpellCheckingInspection
            changes = p4.run("filelog", "-t", "-l", "-m1", "-c", change_num, file_path)
            changes_d['changes'] = changes
            changes_d['errors'] = "OK"
            # except p4OperException as e:
            # except p4OperException:
            #     for e in P4.errors:
            #         changes_d['changes'] = e
            #         changes_d['errors'] = "p4OperException"
            # except:
            #     changes_d['changes'] = "Unexpected exception in p4_fstat_file_change_web"
            #     changes_d['errors'] = "p4OperException"
        else:
            # noinspection SpellCheckingInspection
            changes_d['changes'] = "<=P4 FILELOG ERROR=> No change list or file path."
            changes_d['errors'] = "p4OperException"

        # PerforceOperations().close_p4(p4)
        return changes_d


    class DevPerforceOperations:

        @staticmethod
        def open_p4():
            p4 = P4.P4()
            p4.user = p4_cred['user']
            p4.password = p4_cred['password']
            p4.port = p4_cred['port']
            p4.client = p4_cred['client']
            p4.ticket_file = p4_cred['ticket_file']
            try:
                p4.connect()
                p4.run_login()
                opened = p4.run_opened()
                log.debug("<=P4 CONNECTION=> p4 opened %s", opened)
            except P4.P4Exception:
                for err in p4.errors:  # Display errors
                    log.error("P4.P4Exception -> (%s)", err)
                for warn in p4.warnings:  # Display errors
                    log.warning("P4.P4Exception -> (%s)", warn)
                # msg = '<=P4 CONNECTION=> P4Exception: {}'.format(e)
                # log.error(msg)
                # DevPerforceOperations.close_p4(p4)
                # raise P4.P4Exception(msg)
            except Exception as e:
                msg = "<=P4 CONNECTION ERROR=> {0}".format(e)
                log.error(msg)
                DevPerforceOperations.close_p4(p4)
                raise Exception(msg)
            log.debug("<=P4 CONNECTION=> Connection made and saved: %s", p4)
            return p4

        @staticmethod
        def close_p4(p4):
            try:
                p4.disconnect()
            except P4.P4Exception:
                for err in p4.errors:  # Display errors
                    log.error("P4.P4Exception -> (%s)", err)
                for warn in p4.warnings:  # Display errors
                    log.warning("P4.P4Exception -> (%s)", warn)
                # msg = '<=P4 CLOSE CONNECTION=> P4Exception: {}'.format(e)
                # log.error(msg)
                # return msg

        @staticmethod
        def p4_info():
            p4_info_str = []
            p4 = DevPerforceOperations().open_p4()
            log.debug("p4 instance: %s", p4)
            if p4:
                try:
                    info = p4.run("info")
                    for key in info[0]:
                        string = key, "=", info[0][key]
                        p4_info_str.append(string)
                    DevPerforceOperations.close_p4(p4)
                    return p4_info_str
                except P4.P4Exception:
                    for err in p4.errors:  # Display errors
                        log.error("P4.P4Exception -> (%s)", err)
                    for warn in p4.warnings:  # Display errors
                        log.warning("P4.P4Exception -> (%s)", warn)
                    # msg = '<=P4 CONNECTION=> P4Exception: {}'.format(e)
                    # log.error(msg)
                    # DevPerforceOperations.close_p4(p4)
                    # raise P4.P4Exception(msg)
                except Exception as e:
                    p4_info_str.append(('P4 Traceback', '=', e), )
                    DevPerforceOperations.close_p4(p4)
                    return p4_info_str

            else:
                p4_info_str.append(('P4 Traceback', '=',
                                    "Perforce connection cannot be established. "
                                    "All P4 operations are skipped for now."), )
                DevPerforceOperations.close_p4(p4)
                return p4_info_str

        @staticmethod
        def p4_sync_path(p4, depot_path):
            if not p4:
                p4 = DevPerforceOperations.open_p4()
            try:
                p4.run("sync", "-f", depot_path)
            except P4.P4Exception:
                for err in p4.errors:  # Display errors
                    log.error("P4.P4Exception -> (%s)", err)
                for warn in p4.warnings:  # Display errors
                    log.warning("P4.P4Exception -> (%s)", warn)
                # msg = '<=P4 CONNECTION=> P4Exception: {}'.format(e)
                # log.warning(msg)
                # return msg
            except Exception as e:
                log.debug("<=P4 CONNECTION ERROR=> sync_force P4 connection Fail!")
                DevPerforceOperations.close_p4(p4)
                raise Exception(e)

        @staticmethod
        def __p4_create_client__():
            """
            Run this ONCE, not for usage.
            This creates client and views for paths.
            After run it will WIPE all mappings for current client!

            Current mappings in CMD/TH_Octopus_mappings

            """
            p4 = PerforceOperations().open_p4()
            log.debug("Trying to create\\wipe client for sync. Be careful!")
            try:
                client = p4.fetch_client()
                client["Description"] = "TH_Octopus client for testing"
                client["Root"] = "/home/user/TH_Octopus/perforce"
                client["View"] = ["//addm/rel/branches/custard_cream/r11_2_0_x/code/utils/...  "
                                  "//%s/addm/rel/branches/custard_cream/r11_2_0_x/code/utils/... " % p4.client, ]
                p4.save_client(client)
            except Exception as e:
                log.debug("__p4_create_client__ err: %s", e)
            # PerforceOperations().close_p4(p4)


    # p4_info = DevPerforceOperations.p4_info()
    # log.debug('p4_info: %s', p4_info)

    # open_p4 = DevPerforceOperations.open_p4()
    # sync_path = DevPerforceOperations.p4_sync_path(p4=open_p4, depot_path='//addm/tkn_ship/tku_patterns/CORE/MicrosoftAzureServiceFabric/tests/TEST')

    PatternTestExecCases().p4_changes_multi(branch='tkn_main')

    # Run Task:
    # kwargs = {"branch": "tkn_main", "user_name": "local_dev"}
    # TestExecCases().auto_p4_parse_sync(**kwargs)

    TPatternParse().t_p4_changes_threads.apply_async(queue='w_parsing@tentacle.dq2', args=['local_dev'],
                                                     kwargs={"branch": "tkn_main"})
