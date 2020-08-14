# Python logger
import logging

from octo_tku_patterns.models import TestCases

from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver

from octo.helpers.tasks_run import Runner
from octo_tku_patterns.tasks import TPatternRoutine

log = logging.getLogger("octo.octologger")


class CasesSignals:

    @staticmethod
    @receiver(post_delete, sender=TestCases)
    def test_cases_delete(sender, instance, **kwargs):
        log.info(f"<=Signal=> TestCases Delete: {sender} {instance} {kwargs}")

    @staticmethod
    @receiver(pre_delete, sender=TestCases)
    def test_cases_delete(sender, instance, **kwargs):
        log.info(f"<=Signal=> TestCases Pre-Delete: {sender} {instance} {kwargs}")

    @staticmethod
    @receiver(post_save, sender=TestCases)
    def test_cases_save(sender, instance, created, **kwargs):
        log.info(f"<=Signal=> TestCases Save: {sender} {instance} {created} {kwargs}")
        # TODO: Run user test and send email results after:
        # Get case ID
        # Get case change user
        # Get user adprod and email

        run = False
        if run:

            cases_ids = 'case,case1'
            user_name = ''
            obj = dict(
                context=dict(selector=dict(cases_ids=cases_ids)),
                request=None,
                user_name='',
                user_email='',
            )
            # TaskPrepare(obj).run_tku_patterns()
            t_tag = f'tag=t_test_prep;user_name={user_name};'
            t_queue = 'w_routines@tentacle.dq2'
            t_routing_key = 'routines.TRoutine.t_test_prep'
            Runner.fire_t(TPatternRoutine.t_test_prep,
                t_args=[t_tag],
                t_kwargs=dict(obj=obj),
                t_queue=t_queue,
                t_routing_key=t_routing_key,
            )