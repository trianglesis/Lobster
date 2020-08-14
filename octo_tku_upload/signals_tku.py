# Python logger
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from octo.helpers.tasks_run import Runner
from octo_tku_upload.models import TkuPackagesNew
from octo_tku_upload.tasks import TUploadExec

log = logging.getLogger("octo.octologger")


@receiver(post_save, sender=TkuPackagesNew)
def tku_package_save(sender, instance, **kwargs):
    log.info(f"<=Signal=> TkuPackagesNew Save: {sender} {instance} {kwargs}")
    # TODO: Run user test and send email results after:
    run = False
    if run:
        kw_options = dict(
            test_method='self.test_method',
            test_class='self.test_class',
            test_module='self.test_module',
            user_name='self.request.user.username',
            user_email='self.request.user.email',
        )
        t_tag = f'tag=t_upload_test;user_name={kw_options["user_name"]};test_method={kw_options["test_method"]}'
        t_queue = 'w_routines@tentacle.dq2'
        t_routing_key = 'TKUOperationsREST.tku_install_test.TUploadExec.t_upload_routines'
        task = Runner.fire_t(TUploadExec.t_upload_routines,
                             fake_run=run,
                             args=[t_tag],
                             t_kwargs=kw_options,
                             t_queue=t_queue,
                             t_routing_key=t_routing_key)