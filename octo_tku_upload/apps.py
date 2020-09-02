from django.apps import AppConfig
from django.db.models.signals import post_save, post_delete, pre_delete
import logging

log = logging.getLogger("octo.octologger")


class TkuUploadConfig(AppConfig):
    name = 'octo_tku_upload'
    verbose_name = "TKU Upload Tests"

    def ready(self):
        print(f"Loaded {self.verbose_name}")
        from octo_tku_upload.models import TkuPackagesNew
        post_save.connect(self.tku_package_save, sender=TkuPackagesNew)
        post_delete.connect(self.tku_package_delete, sender=TkuPackagesNew)
        pre_delete.connect(self.tku_package_pre_delete, sender=TkuPackagesNew)

    @staticmethod
    def tku_package_pre_delete(sender, instance, **kwargs):
        log.info(f"<=Signal=> TKU Pre-Delete: {sender} {instance} {kwargs}")

    @staticmethod
    def tku_package_delete(sender, instance, **kwargs):
        log.info(f"<=Signal=> TKU Delete: {sender} {instance} {kwargs}")

    @staticmethod
    def tku_package_save(sender, instance, created, **kwargs):
        from octo_tku_upload.tasks import TKUSignalExecCases
        log.info(f"<=Signal=> TKU Save: {sender} {instance} {created} {kwargs}")
        TKUSignalExecCases.test_exec_on_change(sender, instance, created, **kwargs)