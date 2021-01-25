from django.db import models


# for VIEWs https://www.tutorialspoint.com/What-do-you-mean-by-database-view-and-how-do-MySQL-views-work
class AddmDigest(models.Model):
    tkn_branch = models.CharField(max_length=100)
    addm_host = models.CharField(max_length=100)
    addm_name = models.CharField(max_length=100)
    addm_v_int = models.CharField(max_length=100)
    tests_count = models.CharField(max_length=100)
    patterns_count = models.CharField(max_length=100)
    fails = models.CharField(max_length=100)
    error = models.CharField(max_length=100)
    passed = models.CharField(max_length=100)
    skipped = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "addm_test_digest"


class TestLatestDigestAll(models.Model):
    test_type = models.CharField(max_length=255)
    tkn_branch = models.CharField(max_length=255)
    addm_name = models.CharField(max_length=255)
    pattern_library = models.CharField(max_length=255)
    pattern_folder_name = models.CharField(max_length=255)
    time_spent_test = models.FloatField()
    test_date_time = models.DateTimeField()
    addm_v_int = models.CharField(max_length=255)
    change = models.CharField(max_length=255)
    change_user = models.CharField(max_length=255)
    change_review = models.CharField(max_length=255)
    change_ticket = models.CharField(max_length=255)
    change_desc = models.TextField()
    change_time = models.DateTimeField()
    test_case_depot_path = models.CharField(max_length=255)
    test_time_weight = models.CharField(max_length=255)
    test_py_path = models.CharField(max_length=255)
    test_id = models.CharField(max_length=255)
    case_id = models.CharField(max_length=255)
    test_items_prepared = models.IntegerField()
    fails = models.IntegerField()
    error = models.IntegerField()
    passed = models.IntegerField()
    skipped = models.IntegerField()

    class Meta:
        managed = False
        db_table = "test_latest_digest_all"

    def __str__(self):
        return '{0} - {1}: t{2}'.format(self.tkn_branch, self.test_py_path, self.time_spent_test)


class TestLatestDigestLibShort(models.Model):
    tkn_branch = models.CharField(max_length=255)
    pattern_library = models.CharField(max_length=255)
    test_date_time = models.DateTimeField()
    tests_count = models.IntegerField()
    patterns_count = models.IntegerField()
    fails = models.IntegerField()
    error = models.IntegerField()
    passed = models.IntegerField()
    skipped = models.IntegerField()

    class Meta:
        managed = False
        db_table = "test_latest_digest_lib_short"

    def __str__(self):
        return '{0} - {1}'.format(self.tkn_branch, self.pattern_library)


class TestHistoryDigestDaily(models.Model):
    test_type = models.CharField(max_length=255)
    tkn_branch = models.CharField(max_length=255)
    addm_name = models.CharField(max_length=255)
    pattern_library = models.CharField(max_length=255)
    pattern_folder_name = models.CharField(max_length=255)
    time_spent_test = models.FloatField()
    test_date_time = models.DateTimeField()
    addm_v_int = models.CharField(max_length=255)
    change = models.CharField(max_length=255)
    change_user = models.CharField(max_length=255)
    change_review = models.CharField(max_length=255)
    change_ticket = models.CharField(max_length=255)
    change_desc = models.TextField()
    change_time = models.DateTimeField()
    test_case_depot_path = models.CharField(max_length=255)
    test_time_weight = models.CharField(max_length=255)
    test_py_path = models.CharField(max_length=255)
    test_id = models.CharField(max_length=255)
    case_id = models.CharField(max_length=255)
    test_items_prepared = models.IntegerField()
    fails = models.IntegerField()
    error = models.IntegerField()
    passed = models.IntegerField()
    skipped = models.IntegerField()

    class Meta:
        managed = False
        db_table = "test_history_digest_daily"

    def __str__(self):
        return '{0} - {1}: t{2}'.format(self.tkn_branch, self.test_py_path, self.time_spent_test)


class TestLatestDigestFailed(models.Model):
    test_type = models.CharField(max_length=255)
    tkn_branch = models.CharField(max_length=255)
    addm_name = models.CharField(max_length=255)
    pattern_library = models.CharField(max_length=255)
    pattern_folder_name = models.CharField(max_length=255)
    time_spent_test = models.FloatField()
    test_date_time = models.DateTimeField()
    addm_v_int = models.CharField(max_length=255)
    change = models.CharField(max_length=255)
    change_user = models.CharField(max_length=255)
    change_review = models.CharField(max_length=255)
    change_ticket = models.CharField(max_length=255)
    change_desc = models.TextField()
    change_time = models.DateTimeField()
    test_case_depot_path = models.CharField(max_length=255)
    test_time_weight = models.CharField(max_length=255)
    test_py_path = models.CharField(max_length=255)
    test_id = models.CharField(max_length=255)
    case_id = models.CharField(max_length=255)
    # test_items_prepared  = models.IntegerField()
    fails = models.IntegerField()

    class Meta:
        managed = False
        db_table = "test_latest_digest_failed"


class TestLatestDigestPassed(models.Model):
    test_type = models.CharField(max_length=255)
    tkn_branch = models.CharField(max_length=255)
    addm_name = models.CharField(max_length=255)
    pattern_library = models.CharField(max_length=255)
    pattern_folder_name = models.CharField(max_length=255)
    time_spent_test = models.FloatField()
    test_date_time = models.DateTimeField()
    addm_v_int = models.CharField(max_length=255)
    change = models.CharField(max_length=255)
    change_user = models.CharField(max_length=255)
    change_review = models.CharField(max_length=255)
    change_ticket = models.CharField(max_length=255)
    change_desc = models.TextField()
    change_time = models.DateTimeField()
    test_case_depot_path = models.CharField(max_length=255)
    test_time_weight = models.CharField(max_length=255)
    test_py_path = models.CharField(max_length=255)
    test_id = models.CharField(max_length=255)
    case_id = models.CharField(max_length=255)
    test_items_prepared = models.IntegerField()
    passed = models.IntegerField()

    class Meta:
        managed = False
        db_table = "test_latest_digest_passed"


class TestLatestDigestSkipped(models.Model):
    test_type = models.CharField(max_length=255)
    tkn_branch = models.CharField(max_length=255)
    addm_name = models.CharField(max_length=255)
    pattern_library = models.CharField(max_length=255)
    pattern_folder_name = models.CharField(max_length=255)
    time_spent_test = models.FloatField()
    test_date_time = models.DateTimeField()
    addm_v_int = models.CharField(max_length=255)
    change = models.CharField(max_length=255)
    change_user = models.CharField(max_length=255)
    change_review = models.CharField(max_length=255)
    change_ticket = models.CharField(max_length=255)
    change_desc = models.TextField()
    change_time = models.DateTimeField()
    test_case_depot_path = models.CharField(max_length=255)
    test_time_weight = models.CharField(max_length=255)
    test_py_path = models.CharField(max_length=255)
    test_id = models.CharField(max_length=255)
    case_id = models.CharField(max_length=255)
    test_items_prepared = models.IntegerField()
    skipped = models.IntegerField()

    class Meta:
        managed = False
        db_table = "test_latest_digest_skipped"


class TestReportsView(models.Model):
    test_type = models.CharField(max_length=255)
    tkn_branch = models.CharField(max_length=100)
    pattern_library = models.CharField(max_length=100)
    addm_host = models.CharField(max_length=100)
    addm_name = models.CharField(max_length=100)
    addm_v_int = models.CharField(max_length=100)
    tests_count = models.CharField(max_length=100)
    patterns_count = models.CharField(max_length=100)
    fails = models.CharField(max_length=100)
    error = models.CharField(max_length=100)
    passed = models.CharField(max_length=100)
    skipped = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "octo_test_report_view"
