
from rest_framework import serializers
from run_core.models import AddmDev

from django.contrib.auth import get_user_model

import logging
log = logging.getLogger("octo.octologger")

User = get_user_model()


class AddmDevSerializer(serializers.ModelSerializer):
    tideway_user = serializers.SerializerMethodField()
    tideway_pdw = serializers.SerializerMethodField()
    root_user = serializers.SerializerMethodField()
    root_pwd = serializers.SerializerMethodField()

    class Meta:
        model = AddmDev
        fields = (
            'addm_host',
            'addm_name',
            #
            'tideway_user',
            'tideway_pdw',
            'root_user',
            'root_pwd',
            #
            'addm_ip',
            'addm_v_code',
            'addm_v_int',
            'addm_full_version',
            'addm_branch',
            'addm_owner',
            'addm_group',
            'disables',
            'branch_lock',
            'description',
            'vm_cluster',
            'vm_id',
        )

    def get_tideway_user(self, obj):
        request = self.context.get('request')
        # authenticated = request.user.is_authenticated
        # username = request.user.get_username()
        # user_email = request.user.email
        if request and request.user:
            admin_users = request.user.groups.filter(name='admin_users').exists()
            # power_users = request.user.groups.filter(name='power_users').exists()
            # msg = f'authenticated:{authenticated} username:{username} user_email{user_email} admin_users{admin_users} power_users:{power_users}'
            # log.debug("request: %s", msg)
            if admin_users:
                return obj.tideway_user

    def get_tideway_pdw(self, obj):
        request = self.context.get('request')
        if request and request.user:
            admin_users = request.user.groups.filter(name='admin_users').exists()
            if admin_users:
                return obj.tideway_pdw

    def get_root_user(self, obj):
        request = self.context.get('request')
        if request and request.user:
            admin_users = request.user.groups.filter(name='admin_users').exists()
            if admin_users:
                return obj.root_user

    def get_root_pwd(self, obj):
        request = self.context.get('request')
        if request and request.user:
            admin_users = request.user.groups.filter(name='admin_users').exists()
            if admin_users:
                return obj.root_pwd
