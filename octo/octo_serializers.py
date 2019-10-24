from django.contrib.auth.models import User
from run_core.models import AddmDev
from octo_tku_patterns.models import TkuPatterns, TestLast, TestHistory
from octo_tku_upload.models import TkuPackagesNew as TkuPackages
from octo_tku_upload.models import UploadTestsNew as UploadTests
from rest_framework import routers, serializers, viewsets

DUMMY = ''


# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'is_staff')


class TkuPatternsSerializer(serializers.ModelSerializer):
    class Meta:
        id = serializers.IntegerField(read_only=True)

        model = TkuPatterns
        fields = (
            'tkn_branch',
            'pattern_library',
            'pattern_folder_name',
            'pattern_file_name',
            'pattern_folder_change',
            'pattern_folder_mod_time',
            'change_desc',
            'change_user',
            'change_review',
            'change_ticket',
            'pattern_file_path',
            'pattern_file_path_depot',
            'pattern_folder_path_depot',
            'test_py_path',
            'test_py_path_template',
            'test_folder_path',
            'test_folder_path_template',
            'is_key_pattern',
            'date_time_auto_now',
        )


class TkuPatternsSerializerUsual(serializers.Serializer):
    class Meta:
        id                        = serializers.IntegerField(read_only    = True)
        tkn_branch                = serializers.CharField(max_length      = 10, required     = False)
        pattern_library           = serializers.CharField(max_length      = 120, required    = False)
        pattern_folder_name       = serializers.CharField(max_length      = 120, required    = False)
        pattern_file_name         = serializers.CharField(max_length      = 120, required    = False)
        pattern_folder_change     = serializers.CharField(allow_blank     = True, allow_null = True, max_length = 20, required  = False)
        pattern_folder_mod_time   = serializers.DateTimeField(read_only   = True)
        change_desc               = serializers.CharField(allow_blank     = True, allow_null = True, required   = False, style  = {'base_template': 'textarea.html'})
        change_user               = serializers.CharField(allow_blank     = True, allow_null = True, max_length = 20, required  = False)
        change_review             = serializers.CharField(allow_blank     = True, allow_null = True, max_length = 20, required  = False)
        change_ticket             = serializers.CharField(allow_blank     = True, allow_null = True, max_length = 20, required  = False)
        pattern_file_path         = serializers.CharField(max_length      = 255, required    = False)
        pattern_file_path_depot   = serializers.CharField(max_length      = 255)
        pattern_folder_path_depot = serializers.CharField(max_length      = 255)
        test_py_path              = serializers.CharField(allow_blank     = True, allow_null = True, max_length = 255, required = False)
        test_py_path_template     = serializers.CharField(allow_blank     = True, allow_null = True, max_length = 255, required = False)
        test_folder_path          = serializers.CharField(allow_blank     = True, allow_null = True, max_length = 255, required = False)
        test_folder_path_template = serializers.CharField(allow_blank     = True, allow_null = True, max_length = 255, required = False)
        is_key_pattern            = serializers.NullBooleanField(required = False)
        date_time_auto_now        = serializers.DateTimeField(read_only   = True)

    def create(self, validated_data):
        """
        Create and return a new `Snippet` instance, given the validated data.
        """
        return TkuPatterns.objects.create(**validated_data)
        # pass

    def update(self, instance, validated_data):
        """
        Update and return an existing `Snippet` instance, given the validated data.
        """
        instance.tkn_branch                = validated_data.get('tkn_branch', instance.tkn_branch)
        instance.pattern_library           = validated_data.get('pattern_library', instance.pattern_library)
        instance.pattern_folder_name       = validated_data.get('pattern_folder_name', instance.pattern_folder_name)
        instance.pattern_file_name         = validated_data.get('pattern_file_name', instance.pattern_file_name)
        instance.pattern_folder_change     = validated_data.get('pattern_folder_change', instance.pattern_folder_change)
        instance.pattern_folder_mod_time   = validated_data.get('pattern_folder_mod_time', instance.pattern_folder_mod_time)
        instance.change_desc               = validated_data.get('change_desc', instance.change_desc)
        instance.change_user               = validated_data.get('change_user', instance.change_user)
        instance.change_review             = validated_data.get('change_review', instance.change_review)
        instance.change_ticket             = validated_data.get('change_ticket', instance.change_ticket)
        instance.pattern_file_path         = validated_data.get('pattern_file_path', instance.pattern_file_path)
        instance.pattern_file_path_depot   = validated_data.get('pattern_file_path_depot', instance.pattern_file_path_depot)
        instance.pattern_folder_path_depot = validated_data.get('pattern_folder_path_depot', instance.pattern_folder_path_depot)
        instance.test_py_path              = validated_data.get('test_py_path', instance.test_py_path)
        instance.test_py_path_template     = validated_data.get('test_py_path_template', instance.test_py_path_template)
        instance.test_folder_path          = validated_data.get('test_folder_path', instance.test_folder_path)
        instance.test_folder_path_template = validated_data.get('test_folder_path_template', instance.test_folder_path_template)
        instance.is_key_pattern            = validated_data.get('is_key_pattern', instance.is_key_pattern)
        instance.date_time_auto_now        = validated_data.get('date_time_auto_now', instance.date_time_auto_now)
        # instance.title = validated_data.get('title', instance.title)
        # instance.code = validated_data.get('code', instance.code)
        # instance.linenos = validated_data.get('linenos', instance.linenos)
        # instance.language = validated_data.get('language', instance.language)
        # instance.style = validated_data.get('style', instance.style)
        instance.save()
        return instance
        # pass


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


class TkuPatternsViewSet(viewsets.ModelViewSet):
    queryset = TkuPatterns.objects.all()


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

# router.register(r'tku_patterns', TkuPatternsViewSet)
router.register(r'tku_packages', TkuPackagesViewSet)

router.register(r'tests_last', TestLastViewSet)
router.register(r'tests_history', TestHistoryViewSet)
router.register(r'upload_tests', UploadTestsViewSet)

router.register(r'addm_dev', AddmDevViewSet)
