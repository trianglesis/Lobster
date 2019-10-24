
from rest_framework import serializers
from octo_tku_patterns.models import *
from octo.models import CeleryTaskmeta

from django.contrib.auth import get_user_model

import logging
log = logging.getLogger("octo.octologger")

User = get_user_model()


class TestCasesSerializer(serializers.ModelSerializer):
    case_group = serializers.SerializerMethodField()

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
            'case_group',
        )

    @staticmethod
    def get_case_group(obj):
        serializer = TestCasesDetailsSerializer(obj.related_test_cases, many=True)
        return serializer.data


class TestCasesDetailsSerializer(serializers.ModelSerializer):
    author_username = serializers.SerializerMethodField()
    test_cases_names = serializers.SerializerMethodField()

    class Meta:
        # Get author name
        # Get test_cases short names
        model = TestCasesDetails
        fields = (
            'id',
            'title',
            'author',
            'author_username',
            'test_cases',
            'test_cases_names',
            'description',
            'pub_date',
            'changed_date',
        )

    @staticmethod
    def get_author_username(obj):
        return obj.author.username

    @staticmethod
    def get_test_cases_names(obj):
        cases_names_list = []
        for test_case in obj.test_cases.all():
            cases_names_list.append(f"{test_case.tkn_branch}-{test_case.pattern_folder_name}")
        return cases_names_list


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
            'fail_status',
            'fail_name',
            'fail_module',
            'fail_class',
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
            'pattern_file_name',
            'pattern_folder_name',
            'pattern_file_path',
            'test_py_path',
            'pattern_folder_path_depot',
            'pattern_file_path_depot',
            'is_key_pattern',
            'tst_message',
            'tst_name',
            'tst_module',
            'tst_class',
            'tst_status',
            'fail_status',
            'fail_name',
            'fail_module',
            'fail_class',
            'fail_message',
            'addm_name',
            'addm_group',
            'addm_v_int',
            'addm_host',
            'addm_ip',
            'time_spent_test',
            'test_date_time',
        )
