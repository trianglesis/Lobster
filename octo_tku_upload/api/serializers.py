from rest_framework import serializers

from octo_tku_upload.models import *

from django.contrib.auth import get_user_model

import logging
log = logging.getLogger("octo.octologger")

User = get_user_model()


class TkuPackagesNewSerializer(serializers.ModelSerializer):
    class Meta:
        model = TkuPackagesNew
        fields = (
            'id',
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
            'zip_file_md5_digest',
            'updated_at',
            'updated_at',
            'created_at',
        )


class UploadTestsNewSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadTestsNew
        fields = (
            'id',
            'test_mode',
            'mode_key',
            'package_type',
            'tku_type',
            'upload_test_status',
            'upload_test_str_stdout',
            'upload_test_str_stderr',
            'important_out',
            'all_errors',
            'all_warnings',
            'upload_warnings',
            'upload_errors',
            'tku_statuses',
            'addm_name',
            'addm_v_int',
            'addm_host',
            'addm_ip',
            'addm_version',
            'time_spent_test',
            'test_date_time',
        )
