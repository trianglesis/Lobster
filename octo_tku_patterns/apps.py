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
        pre_delete.connect(self.test_cases_pre_delete, sender=TestCases)

    @staticmethod
    def test_cases_pre_delete(sender, instance, **kwargs):
        log.info(f"<=Signal=> TestCases Pre-Delete: {sender} {instance} {kwargs}")

    @staticmethod
    def test_cases_delete(sender, instance, **kwargs):
        log.info(f"<=Signal=> TestCases Delete: {sender} {instance} {kwargs}")

    @staticmethod
    def test_cases_save(sender, instance, created, **kwargs):
        log.info(f"<=Signal=> TestCases Save: {sender} {instance} {created} {kwargs}")