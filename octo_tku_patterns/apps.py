from django.apps import AppConfig
from django.db.models.signals import post_save, post_delete, pre_delete
from django.conf import settings

import logging

log = logging.getLogger("octo.octologger")
curr_hostname = getattr(settings, 'CURR_HOSTNAME', None)


class TkuPatternsConfig(AppConfig):
    name = 'octo_tku_patterns'
    verbose_name = "TKU Test Cases"

    def ready(self):
        print(f"Loaded {self.verbose_name}")
        from octo_tku_patterns.models import TestCases
        post_save.connect(self.test_cases_save, sender=TestCases)
        post_delete.connect(self.test_cases_delete, sender=TestCases)

    @staticmethod
    def test_cases_delete(sender, instance, **kwargs):
        # from run_core.models import UserAdprod
        log.info(f"<=Signal=> TestCases Delete => sender: {sender}; instance: {instance}; kwargs: {kwargs};")
        # user = UserAdprod.objects.get(adprod_username__exact=instance.change_user)
        # user_email = user.user.email
        # log.info(f"TestCas => User: {instance.change_user} - {user_email}; branch: {instance.tkn_branch}; test_py: {instance.test_py_path}")

    @staticmethod
    def test_cases_save(sender, instance, created, **kwargs):
        from octo_tku_patterns.tasks import PatternTestExecCases
        if settings.DEV or settings.DEBUG:
            log.info("This is a dev or debug server - do not run signal actions!")
            pass
        else:
            PatternTestExecCases.test_exec_on_change(sender, instance, created, **kwargs)
