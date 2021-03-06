from rest_framework import serializers
from octo_tku_patterns.models import *
from octo_tku_patterns.model_views import TestLatestDigestAll, TestHistoryDigestDaily, AddmDigest

from django.contrib.auth import get_user_model

import logging

log = logging.getLogger("octo.octologger")

User = get_user_model()


class TestCasesSerializer(serializers.ModelSerializer):
    # TOO MANY SQL operations, give this job to JS+JSON
    # case_group = serializers.SerializerMethodField()

    class Meta:
        model = TestCases
        fields = (
            'id',
            'test_type',
            'tkn_branch',
            'pattern_library',
            'pattern_folder_name',
            'pattern_folder_path',
            'pattern_library_path',
            'test_case_dir',
            'change',
            'change_desc',
            'change_user',
            'change_review',
            'change_ticket',
            'change_time',
            'test_case_depot_path',
            'test_py_path',
            'test_py_path_template',
            'test_dir_path',
            'test_dir_path_template',
            'test_time_weight',
            'created_time',
            # Methods
            # TOO MANY SQL operations, give this job to JS+JSON
            # 'case_group',
        )

    # TOO MANY SQL operations, give this job to JS+JSON
    # @staticmethod
    # def get_case_group(obj):
    #     serializer = TestCasesDetailsSerializer(obj.related_test_cases, many=True)
    #     return serializer.data


class TestCasesDetailsSerializer(serializers.ModelSerializer):
    # TODO: Show test cases IDs so later we can use those as reference for JSON comparison
    # author_username = serializers.SerializerMethodField()
    # test_cases_names = serializers.SerializerMethodField()

    class Meta:
        # Get author name
        # Get test_cases short names
        model = TestCasesDetails
        fields = (
            'id',
            'title',
            'author',
            'test_cases',
            'description',
            'pub_date',
            'changed_date',
            # 'author_username',
            # 'test_cases_names',
        )

    # @staticmethod
    # def get_author_username(obj):
    #     return obj.author.username
    #
    # @staticmethod
    # def get_test_cases_names(obj):
    #     cases_names_list = []
    #     for test_case in obj.test_cases.all():
    #         cases_names_list.append(f"{test_case.tkn_branch}-{test_case.pattern_folder_name}")
    #     return cases_names_list


class TestLastSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestLast
        fields = (
            'id',
            'tkn_branch',
            'pattern_library',
            'pattern_folder_name',
            'test_py_path',
            'tst_name',
            'tst_module',
            'tst_class',
            'tst_message',
            'tst_status',
            'fail_message',
            'addm_name',
            'addm_group',
            'addm_v_int',
            'addm_host',
            'addm_ip',
            'time_spent_test',
            'test_date_time',
        )


class TestHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TestHistory
        fields = (
            'id',
            'tkn_branch',
            'pattern_library',
            'pattern_folder_name',
            'test_py_path',
            'tst_name',
            'tst_module',
            'tst_class',
            'tst_message',
            'tst_status',
            'fail_message',
            'addm_name',
            'addm_group',
            'addm_v_int',
            'addm_host',
            'addm_ip',
            'time_spent_test',
            'test_date_time',
        )


# Model views (pre-saved) model
class TestLatestDigestAllSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestLatestDigestAll
        fields = (
            'id',
            'test_type',
            'tkn_branch',
            'addm_name',
            'pattern_library',
            'pattern_folder_name',
            'time_spent_test',
            'test_date_time',
            'addm_v_int',
            'change',
            'change_user',
            'change_review',
            'change_ticket',
            'change_desc',
            'change_time',
            'test_case_depot_path',
            'test_time_weight',
            'test_py_path',
            'test_id',
            'case_id',
            'test_items_prepared',
            'fails',
            'error',
            'passed',
            'skipped',
        )

class AddmDigestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddmDigest
        fields = (
            # 'id',
            'tkn_branch',
            # 'addm_host',
            'addm_name',
            'addm_v_int',
            'tests_count',
            'patterns_count',
            'fails',
            'error',
            'passed',
            'skipped',
        )


# Model views (pre-saved) model
class TestHistoryDigestDailySerializer(serializers.ModelSerializer):
    class Meta:
        model = TestHistoryDigestDaily
        fields = (
            'id',
            'test_type',
            'tkn_branch',
            'addm_name',
            'pattern_library',
            'pattern_folder_name',
            'time_spent_test',
            'test_date_time',
            'addm_v_int',
            'change',
            'change_user',
            'change_review',
            'change_ticket',
            'change_desc',
            'change_time',
            'test_case_depot_path',
            'test_time_weight',
            'test_py_path',
            'test_id',
            'case_id',
            'test_items_prepared',
            'fails',
            'error',
            'passed',
            'skipped',
        )
