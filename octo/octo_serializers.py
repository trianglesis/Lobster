from django.contrib.auth.models import User
from run_core.models import AddmDev
from octo_tku_patterns.models import TestLast, TestHistory
from octo_tku_upload.models import TkuPackagesNew as TkuPackages
from octo_tku_upload.models import UploadTestsNew as UploadTests
from rest_framework import routers, serializers, viewsets


# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'is_staff')


class TestLastSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = TestLast
        fields = (
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


class TestHistorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = TestHistory
        fields = (
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


class TkuPackagesSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = TkuPackages
        fields = (
            'zip_file_path',
            'zip_file_name',
            'package_type',
            'tku_type',
            'zip_type',
            'addm_version',
            'tku_name',
            'tku_addm_version',
            'tku_build',
            'tku_date',
            'tku_month',
            'tku_pack',
        )


class UploadTestsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = UploadTests
        fields = (
            'test_case_key',
            'test_mode',
            'mode_key',
            'test_date',
            'test_time',
            'upload_test_status',
            'upload_test_str_stdout',
            'upload_test_str_stderr',
            'important_out',
            'all_errors',
            'all_warnings',
            'upload_warnings',
            'upload_errors',
            'tku_statuses',
            'time_spent_test',
            'tested_zips',
            'addm_name',
            'addm_v_int',
            'addm_host',
            'addm_ip',
            'addm_version',
            'tku_type',
            'package_type',
            'tku_build',
            'tku_date',
            'tku_month',
        )


class AddmDevSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = AddmDev
        fields = (
            'addm_host',
            'addm_name',
            'tideway_user',
            'tideway_pdw',
            'root_user',
            'root_pwd',
            'addm_ip',
            'addm_v_code',
            'addm_v_int',
            'addm_full_version',
            'addm_branch',
            'addm_owner',
            'addm_group',
            'disables',
        )


# ViewSets define the view behavior.
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class TestLastViewSet(viewsets.ModelViewSet):
    queryset = TestLast.objects.all()
    serializer_class = TestLastSerializer


class TestHistoryViewSet(viewsets.ModelViewSet):
    queryset = TestHistory.objects.all()
    serializer_class = TestHistorySerializer


class TkuPackagesViewSet(viewsets.ModelViewSet):
    queryset = TkuPackages.objects.all()
    serializer_class = TkuPackagesSerializer


class UploadTestsViewSet(viewsets.ModelViewSet):
    queryset = UploadTests.objects.all()
    serializer_class = UploadTestsSerializer


class AddmDevViewSet(viewsets.ModelViewSet):
    queryset = AddmDev.objects.all()
    serializer_class = AddmDevSerializer


# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'users', UserViewSet)

router.register(r'tku_packages', TkuPackagesViewSet)

router.register(r'tests_last', TestLastViewSet)
router.register(r'tests_history', TestHistoryViewSet)
router.register(r'upload_tests', UploadTestsViewSet)

router.register(r'addm_dev', AddmDevViewSet)
