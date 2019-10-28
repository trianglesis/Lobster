
if __name__ == "__main__":

    import re
    import logging
    import django


    django.setup()
    from run_core.models import ServiceLog

    log = logging.getLogger("octo.octologger")
    log.info("RUNNING LOCAL TO REMOTE EXECUTION!")

    out_clear_re = re.compile(r';#.*;\n')


    def select_log(log_type=None, table_key=None, date_str=None):

        # UploadTest_update-candidate_tku_install_custard_cream-vl-aus-btk-qa06_2019-01-11 10:11:21.563923

        kind = dict(fresh='UploadTest_fresh-fresh_tku_install',
                    prev='UploadTest_update-candidate_tku_install',
                    candidate='UploadTest_update-previous_tku_install')

        if kind.get(log_type):
            log.info("Kind is present! %s", log_type)
            upload_log = ServiceLog.objects.filter(log_key__iregex=kind[log_type]).values()
        else:
            if table_key:
                # log.info("Kind is NOT present use table_key! %s - %s", type, table_key)
                upload_log = ServiceLog.objects.filter(log_key=table_key).values()
            elif date_str:
                # log.info("Kind is NOT present use date_str! %s - %s", type, table_key)
                upload_log = ServiceLog.objects.filter(created_at__gte=date_str).values()
            else:
                # log.info("Kind is NOT present select ALL! %s - %s", type, table_key)
                upload_log = ServiceLog.objects.all().values()

        return upload_log


    # logs = select_log(None, 'UploadTest_fresh-fresh_tku_install_bobblehat-vl-aus-btk-qa07_2019-01-11 15:11:21.205135')
    # logs = select_log(date_str='2019-01-11 16:00')
    # logs = select_log()

    #
    # for log_item in logs:
    #     logs_step = log_item['log_out'].replace(chr(27), ';').replace('\x1b', ';').replace('[0G', '#').replace('[K', '\n')  # .replace('\n\n', '\n')
    #     logs_important = out_clear_re.sub('', logs_step)
    #     # log.info("CLEAR OUTPUT: \n%s", logs_step)
    #     # log.info("IMPORTANT: log_kwargs: %s ", log_item['log_kwargs'])
    #     log.info("IMPORTANT: \n+====%s\n%s", log_item['log_key'], logs_important)
        # break

    # count = 0
    # for ch in logs[0]['log_out']:
    #     log.info('%s CHAR: %s %s', count, ch, ord(ch))
    #     count += 1
    #     if count == 100:
    #         break


    # log.info('Ch ord; %s', ord(''))
    # log.info('Ch 27: %s', chr(27))
    # log.info('Ch 7: %s', chr(7))
