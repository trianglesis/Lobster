from django.apps import AppConfig
from django.db.models.signals import post_save, post_delete, pre_delete

import logging
log = logging.getLogger("octo.octologger")

class TkuPatternsConfig(AppConfig):
    name = 'octo_tku_patterns'
    verbose_name = "TKU Test Cases"

    def ready(self):
        print(f"Loaded {self.verbose_name}")
        from octo_tku_patterns.models import TestCases
        post_save.connect(self.test_cases_save, sender=TestCases)
        post_delete.connect(self.test_cases_delete, sender=TestCases)
        # pre_delete.connect(self.test_cases_pre_delete, sender=TestCases)

    @staticmethod
    def test_cases_pre_delete(sender, instance, **kwargs):
        log.info(f"<=Signal=> TestCases Pre-Delete => sender: {sender}; instance: {instance}; kwargs: {kwargs};")
        log.info(f"TestCas => User: {instance.change_user}; branch: {instance.tkn_branch}; test_py: {instance.test_py_path}")

    @staticmethod
    def test_cases_delete(sender, instance, **kwargs):
        from run_core.models import UserAdprod
        log.info(f"<=Signal=> TestCases Delete => sender: {sender}; instance: {instance}; kwargs: {kwargs};")
        user = UserAdprod.objects.get(adprod_username__exact=instance.change_user)
        user_email = user.user.email
        log.info(f"TestCas => User: {instance.change_user} - {user_email}; branch: {instance.tkn_branch}; test_py: {instance.test_py_path}")

    @staticmethod
    def test_cases_save(sender, instance, created, **kwargs):
        if kwargs.get('update_fields'):
            log.info(f"<=Signal=> TestCases Save => sender: {sender}; instance: {instance}; created: {created}; kwargs: {kwargs}")
            update_fields = kwargs.get('update_fields')
            if 'change_ticket' in update_fields:
                log.info(f"<=Signal=> TestCases => Change updated ===> "
                         f"User: {instance.change_user}; branch: {instance.tkn_branch}; test_py: {instance.test_py_path}")