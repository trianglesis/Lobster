if __name__ == "__main__":

    import django
    import logging

    log = logging.getLogger("octo.octologger")
    django.setup()

    from django.db import connection
    from django.db.models import Q
    from octo_tku_patterns.models import TestHistory, TestLast

    def select_unwanted_results():
        unwanted_query = TestHistory.objects.filter(
            Q(tst_status__exact='ERROR:') |
            Q(tst_status__exact='ERROR') |
            Q(tst_status__exact='WARNING') |
            Q(tst_status__exact='unexpected success') |
            Q(tst_status__regex=r"skipped \'Version is") |
            Q(tst_status__regex=r"testutils\.MY_dml_test_utils")
        ).defer()
        log.debug("Count unwanted_query: %s", unwanted_query.count())
        log.debug("unwanted_query.query %s", unwanted_query.query)
        return unwanted_query

    def select_unwanted_results_raw():
        unwanted_query = """
            SELECT `octo_test_history`.`id`,
                   `octo_test_history`.`tkn_branch`,
                   `octo_test_history`.`pattern_library`,
                   `octo_test_history`.`pattern_file_name`,
                   `octo_test_history`.`pattern_folder_name`,
                   `octo_test_history`.`tst_name`,
                   `octo_test_history`.`tst_status`,
                   `octo_test_history`.`addm_name`,
                   `octo_test_history`.`addm_group`
            FROM `octopus_dev_copy`.`octo_test_history`
            WHERE octo_test_history.tst_status REGEXP "testutils.MY_dml_test_utils" OR
                  octo_test_history.tst_status REGEXP "skipped 'Version is" OR
                  octo_test_history.tst_status = "ERROR:" OR
                  octo_test_history.tst_status = "ERROR" OR
                  octo_test_history.tst_status = "WARNING" OR
                  octo_test_history.tst_status = "unexpected success" OR
                  octo_test_history.addm_name = "zythum"
        """
        unwanted_results = TestHistory.objects.raw(unwanted_query)

        log.debug("Count unwanted_query: %s", unwanted_results.count())
        log.debug("unwanted_query.query %s", unwanted_results.query)
        return unwanted_results

    def delete_unwanted_results_raw():
        delete_unw_query = """
            DELETE FROM `octopus_dev_copy`.`octo_test_history`
            WHERE octo_test_history.tst_status REGEXP "testutils.MY_dml_test_utils" OR
                  octo_test_history.tst_status REGEXP "skipped" OR
                  octo_test_history.tst_status REGEXP "ERROR" OR
                  octo_test_history.tst_status REGEXP "WARNING" OR
                  octo_test_history.tst_status REGEXP "unexpected success" OR
                  octo_test_history.tst_status REGEXP "expected failure" OR
                  octo_test_history.addm_name = "zythum"
        """
        deleted_items = TestHistory.objects.raw(delete_unw_query)
        # log.debug("unwanted_query.query %s", deleted_items.query)
        return deleted_items

    def select_addm_all(addm_name):
        addm_name_query = TestHistory.objects.filter(addm_name__exact=addm_name)
        log.debug("Count addm_name_query: %s", addm_name_query.count())
        log.debug("unwanted_query.query %s", addm_name_query.query)
        return addm_name_query

    def select_errors_all():
        errors_query = TestHistory.objects.filter(tst_status__exact='ERROR:')
        log.debug("Count errors_query: %s", errors_query.count())
        log.debug("unwanted_query.query %s", errors_query.query)
        return errors_query

    def select_skips_all():
        skipped_query = TestHistory.objects.filter(tst_status__contains="skipped 'Version is")
        log.debug("Count select_skips_all: %s", skipped_query.count())
        log.debug("unwanted_query.query %s", skipped_query.query)
        return skipped_query

    def delete_selected(query_sel):
        log.warning("About to delete all selected items %s", query_sel.count())
        deleted = query_sel.delete()
        log.debug("deleted: %s", deleted)
        return deleted

    def _optimize_table(model_sel=None, table_name=None):
        """
        :type model_sel: model
        """
        if not table_name:
            table_name = model_sel.model._meta.db_table

        log.info("Run Optimize, check, analyze for: %s'", table_name)

        OPTIMIZE = """OPTIMIZE TABLE {}""".format(table_name)
        optimize = model_sel.raw(OPTIMIZE)
        log.debug("Table %s optimize: %s", table_name, optimize)
        for item in optimize:
            for keys, values in item.items():
                log.debug('optimize item: %s: %s', keys, values)

        CHECK = """CHECK TABLE {}""".format(table_name)
        check = model_sel.raw(CHECK)
        log.debug("Table %s check: %s", table_name, check)
        for keys, values in check.items():
            log.debug('check item: %s: %s', keys, values)

        ANALYZE = """ANALYZE TABLE {}""".format(table_name)
        analyze = model_sel.raw(ANALYZE)
        log.debug("Table %s analyze: %s", table_name, analyze)
        for keys, values in analyze.items():
            log.debug('analyze item: %s: %s', keys, values)

        return optimize, check, analyze

    def optimize_table(model_sel=None, table_name=None):
        """
        :type model_sel: model
        """
        if not table_name:
            table_name = model_sel.model._meta.db_table

        log.info("Run Optimize, check, analyze for: %s'", table_name)

        # optimize = 'Skip this time'
        # Run same as #ALTER TABLE octo_test_history ENGINE='InnoDB';
        with connection.cursor() as cursor:
            OPTIMIZE = """OPTIMIZE TABLE {}""".format(table_name)
            cursor.execute(OPTIMIZE)
            optimize = cursor.fetchone()
            log.debug("Table %s optimize: %s", table_name, optimize)

        # with connection.cursor() as cursor:
        #     CHECK = """CHECK TABLE {}""".format(table_name)
        #     cursor.execute(CHECK)
        #     check = cursor.fetchone()
        #     log.debug("Table %s check: %s", table_name, check)

        with connection.cursor() as cursor:
            ANALYZE = """ANALYZE TABLE {}""".format(table_name)
            cursor.execute(ANALYZE)
            analyze = cursor.fetchone()
            log.debug("Table %s analyze: %s", table_name, analyze)

        return optimize, analyze

    # unwanted = select_unwanted_results()
    # if len(unwanted) > 0:
    #     print("Len unwanted {}".format(len(unwanted)))
    #     # delete_selected(unwanted)
    #     # optimize_table(old_addm)    unwanted = select_unwanted_results()

    # old_addm = select_addm_all('zythum')
    # if len(old_addm) > 0:
    #     print("Len old_addm {}".format(len(old_addm)))
    # #     # delete_selected(old_addm)
    # #     # optimize_table(old_addm)
    #
    # strict_err = select_errors_all()
    # if len(strict_err) > 0:
    #     print("Len strict_err {}".format(len(strict_err)))
    #     # delete_selected(strict_err)
    #     # optimize_table(strict_err)
    #
    # skipped_items = select_skips_all()
    # if len(skipped_items) > 0:
    #     print("Len skipped_items {}".format(len(skipped_items)))
    #     # delete_selected(skipped_items)
    #     # optimize_table(skipped_items)


    # unwanted_raw = select_unwanted_results_raw()
    # if len(unwanted_raw) > 0:
    #     print("Len unwanted_raw {}".format(len(unwanted_raw)))
    #     delete_selected(unwanted_raw)

    delete_unwanted_results_raw()
    optimize_table(model_sel=TestHistory.objects, table_name='octo_test_history')