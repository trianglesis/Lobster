# Python logger
import logging
from hashlib import blake2b
from hmac import compare_digest
import datetime

from django.conf import settings
from django.core.cache import cache
from django.db.models.query import EmptyResultSet
from django.db.models.signals import post_save, pre_delete, post_delete
from django.db.utils import IntegrityError
from django.dispatch import receiver

from octo.helpers.tasks_run import Runner
from octo.models import OctoCacheStore
from octo_tku_patterns.models import TestLast, TestCases
from octo_tku_patterns.tasks import TPatternRoutine
from octo_tku_upload.models import UploadTestsNew

log = logging.getLogger("octo.octologger")

SECRET_KEY = 'DefaultKeyResetEverything'


def working_hours():
    now = datetime.datetime.now().replace(second=0, microsecond=0)
    morning = now.replace(hour=7, minute=0)
    evening = now.replace(hour=19, minute=0)
    if now > morning and now < evening:
        return True
    log.info(f"No re-caching during non-working hours! {morning} - {now} - {evening}")
    return False


class OctoCache:

    def __init__(self):
        """Init something useful on import"""
        self.cache = cache

    def cache_query(self, caching, **kwargs):
        """
        Make a cache of most callable queries, save everything in cache for 5 hrs or more.
        Cache will be deleted for related models with signals.
        :param caching: django model queryset.query or other cache-able- will be used to generate hash
        https://docs.python.org/3/library/hashlib.html
        :return:
        """
        ttl = kwargs.get('ttl', 60 * 60 * 5)  # Save for 5 hours.
        assert hasattr(caching, 'query'), "Can only make cache from django model query!"
        try:
            h = blake2b(digest_size=50)
            # h.update(caching.query.encode('utf-8'))
            # NOTE: Consider to add length attribute to hash? Or another anchor?
            h.update(str(caching.query).encode('utf-8'))
        except TypeError as e:
            log.error(f"Cannot hash this: {caching} | Error: {e}")
            raise Exception(e)
        hashed = h.hexdigest()
        return self._get_or_set(hashed, caching, ttl, caching.model.__name__)

    def cache_item(self, caching, hkey, **kwargs):
        """
        Cache something other than query:

        :param caching:
        :param hkey:
        :param kwargs:
        :return:
        """
        ttl = kwargs.get('ttl', 60 * 60 * 5)
        key = kwargs.get('key', SECRET_KEY)
        # log.debug(f"Caching this: {caching}")
        try:
            h = blake2b(digest_size=50)
            h.update(hkey.encode('utf-8'))
        except TypeError as e:
            log.error(f"Cannot hash this: {caching} | Error: {e}")
            raise Exception(e)
        hashed = h.hexdigest()
        return self._get_or_set(hashed, caching, ttl, key)

    def _get_or_set(self, hashed, caching, ttl, hkey):
        """
        Get cache, of set new is get returns None
        :param hashed: hashed key or sql query itself.
        :param caching: object to be saved in cache
        :param ttl: time to live for cached
        :param hkey: key to save in table, will be used to select all related to one model caches and delete on signal
        :return:
        """
        cached = self.cache.get(hashed)
        if cached is None:
            self.cache.set(hashed, caching, ttl)
            got = self.cache.get(hashed)
            self.save_cache_hash_db(hashed=hashed, caching=caching, key=hkey, ttl=ttl)
            return got
        else:
            return cached

    @staticmethod
    def save_cache_hash_db(**kwargs):
        caching = kwargs.pop('caching')
        if hasattr(caching, 'query'):
            sql_query = caching.query
            kwargs.update(query=str(sql_query).encode('utf-8'))
        try:
            updated, created = OctoCacheStore.objects.update_or_create(
                hashed=kwargs.get('hashed'),
                defaults=dict(**kwargs),
            )
            updated.counter += 1
            updated.save()
        except IntegrityError as e:
            log.warning(f'IntegrityError output: {type(e)} {e}')
        except EmptyResultSet as e:
            log.info(f"Probably an empty query to cache: {e}")
            pass
        except Exception as e:
            msg = f"<=save_cache_hash_db=> Error: {e}"
            print(msg)
            raise Exception(msg)

    def delete_cache_on_signal(self, keys=None, models=None):
        """
        Just delete all cache by keys, no regret,
        :param keys:
        :return:
        """
        cached_items = OctoCacheStore.objects.all()
        cached_items = cached_items.filter(key__in=keys)
        cached_values = cached_items.values_list('hashed', flat=True)
        cache.delete_many(cached_values)
        # NOTE: Delete cache ROW only in case, when we do not want to re-execute RAW SQL,
        #  Now RAW SQL exec is impossible to do, so it's disabled until I find a way.
        # self.delete_cache_item_row(cached_items)
        # NOTE: We have fine method to recreate cache automatically right now, but this is fine.
        # self.create_new_cache(cached_items, models)

    def task_re_cache(self, test_methods):
        """
        Task to run view tests, this will automatically re-cache most common views on model signals.
        :param test_methods:
        :return:
        """
        for test in test_methods:
            kwargs = {
                "test_method": test,
                "test_class": "AdvancedViews",
                "test_module": "octotests.tests.test_views_requests"
            }
            tag = f'AdvancedViews.{test}'
            Runner.fire_t(
                TPatternRoutine.t_patt_routines,
                t_args=[tag],
                t_kwargs=kwargs,
                t_routing_key=tag)

    def cache_operation(self, keys, methods):
        """
        Delete outdated cache - all at once, and then - run simple task as view test to generate some common caches.
        :param keys:
        :param methods:
        :return:
        """
        self.delete_cache_on_signal(keys=keys)
        # NOTE: Do not run at non-working hours
        if working_hours():
            self.task_re_cache(test_methods=methods)

    def delete_cache_item_row(self, cached_items):
        """
        Clean cached table from rare queries to keep only most commonly used.
        This should be executed when we have a RAW SQL execution mechanism. It should left only most common queries.
        Later those queries may be executed as RAW SQL on selected model, but currently it's impossible to do.
        Method wil be here as a reminder,
        :param cached_items:
        :return:
        """
        lte_one = cached_items.filter(counter__lte=2)
        lte_one.delete()

    def _create_new_cache(self, cached_items, models):
        """
        Making a RAW query cache. Need consider about escaping anything such as params
        Now we can't ru RAW SQL on models. because SQL code is not escaped properly,
        Escaping it in manual manner will break the initial way of caching.
        :param cached_items:
        :return:
        """
        gt_one = cached_items.filter(counter__gt=3)
        cached_queries = gt_one.values('query', 'key')
        # for _model in models:
        #     log.debug(f'Model name {_model.__name__}')
        # Make threading or something like that?
        for _query in cached_queries:
            if _query['query']:
                q = eval(_query['query'])
                query = q.decode('utf-8')
                for _model in models:
                    if _model.__name__ == _query['key']:
                        # log.debug(f'Recaching model {_model.__name__} == {_query["key"]}')
                        OctoCache().cache_query(_model.objects.raw(query))


test_last = ['AddmDigest', 'TestLast', 'TestLatestDigestAll']

test_cases = ['TestCases']
test_cases_t = ['test002_test_cases']

upload_tests = ['UploadTestsNew', 'TkuPackagesNew']
upload_tests_t = ['test001_main_page', 'test001_tku_workbench', 'test001_upload_today']


class OctoSignals:
    """
    https://docs.djangoproject.com/en/3.0/ref/signals/
    """

    # SAVE:
    @staticmethod
    @receiver(post_save, sender=TestLast)
    def test_last_save(sender, instance, created, **kwargs):
        test_last_t = ['test001_main_page', 'test001_addm_digest']
        if hasattr(instance, 'tkn_branch'):
            if instance.tkn_branch == 'tkn_main':
                test_last_t.extend(('test002_tests_last_tkn_main', 'test003_test_details_tkn_main'))
            elif instance.tkn_branch == 'tkn_ship':
                test_last_t.extend(('test002_tests_last_tkn_ship', 'test003_test_details_tkn_ship'))
            else:
                log.error('No branch in deleted item?! OctoSignals')
        OctoCache().cache_operation(keys=test_last, methods=test_last_t)

    @staticmethod
    @receiver(post_save, sender=TestCases)
    def test_cases_save(sender, instance, created, **kwargs):
        OctoCache().cache_operation(keys=test_cases, methods=test_cases_t)

    @staticmethod
    @receiver(post_save, sender=UploadTestsNew)
    def tku_upload_test_save(sender, instance, created, **kwargs):
        OctoCache().cache_operation(keys=upload_tests, methods=upload_tests_t)

    # DELETE
    @staticmethod
    @receiver(post_delete, sender=TestLast)
    def test_last_delete(sender, instance, **kwargs):
        log.debug(f'Args: {sender} {instance}  kwargs: {kwargs}')
        test_last_t = ['test001_main_page', 'test001_addm_digest',]
        if hasattr(instance, 'tkn_branch'):
            if instance.tkn_branch == 'tkn_main':
                test_last_t.extend(('test002_tests_last_tkn_main', 'test003_test_details_tkn_main'))
            elif instance.tkn_branch == 'tkn_ship':
                test_last_t.extend(('test002_tests_last_tkn_ship', 'test003_test_details_tkn_ship'))
            else:
                log.error('No branch in deleted item?! OctoSignals')
        OctoCache().cache_operation(keys=test_last, methods=test_last_t)

    @staticmethod
    @receiver(post_delete, sender=TestCases)
    def test_cases_delete(sender, instance, **kwargs):
        OctoCache().cache_operation(keys=test_cases, methods=test_cases_t)

    @staticmethod
    @receiver(post_delete, sender=UploadTestsNew)
    def tku_upload_test_delete(sender, instance, **kwargs):
        OctoCache().cache_operation(keys=upload_tests, methods=upload_tests_t)
