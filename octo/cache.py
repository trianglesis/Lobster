from hashlib import blake2b
from hmac import compare_digest

from django.conf import settings
from django.db.models.query import EmptyResultSet
from django.db.utils import IntegrityError
from django.db.models import F

from django.core.cache import caches, cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from octo_tku_patterns.models import TestLast, TestHistory, TestCases
from octo_tku_upload.models import UploadTestsNew, TkuPackagesNew

from octo.models import OctoCacheStore

# Python logger
import logging

log = logging.getLogger("octo.octologger")

SECRET_KEY = 'DefaultKeyResetEverything'


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
            h.update(str(caching.query).encode())
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
        cached = self.cache.get(hashed)
        if cached is None:
            self.cache.set(hashed, caching, ttl)
            log.debug(f"Set: {hashed}")
            if settings.DEV:
                log.debug(f"And get: {hashed}")
            got = self.cache.get(hashed)
            self.save_cache_hash_db(hashed=hashed, caching=caching, key=hkey, ttl=ttl)
            return got
        else:
            log.debug(f"Get: {hashed}")
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
            log.debug(f"Counter {updated.counter}")
            # updated.counter = F('counter') + updated.counter + 1
            updated.counter += 1
            log.debug(f"Updated {updated.counter}")
            updated.save()
            # if settings.DEV:
            #     if updated:
            #         log.info(f'Updating cache-hash {kwargs}')
            #     if created:
            #         log.info(f'Saving new cache-hash {kwargs}')
        except IntegrityError as e:
            log.warning(f'IntegrityError output: {type(e)} {e}')
        except EmptyResultSet as e:
            log.info(f"Probably an empty query to cache: {e}")
            pass
        except Exception as e:
            msg = f"<=save_cache_hash_db=> Error: {e}"
            print(msg)
            raise Exception(msg)

    def verify(self, comparing, hashed):
        """Only for check!"""
        h = blake2b(digest_size=50)
        h.update(f'{comparing}'.encode("utf-8"))
        hash = h.hexdigest()
        # log.debug(f"Hashed comparison: {hashed} with {hashed}")
        return compare_digest(hash, hashed)

    def delete_cache_on_signal(self, keys=None):
        """
        Just delete all cache by keys, no regret,
        :param keys:
        :return:
        """
        cached_items = OctoCacheStore.objects.all()
        cached_items = cached_items.filter(key__in=keys)
        cached_values = cached_items.values_list('hashed', flat=True)
        log.debug(f"About to delete cache for keys: {cached_values}")
        cache.delete_many(cached_values)
        self.delete_cache_item_row(cached_items)

    def delete_cache_item_row(self, cached_items):
        """
        Clean cached table from rare queries to keep only most commonly used.
        :param cached_items:
        :return:
        """
        gt_one = cached_items.filter(counter__gt=1)
        log.debug(f"Common cache queries save: {gt_one.values_list('key', 'counter')}")
        lte_one = cached_items.filter(counter__lte=1)
        log.debug(f"Rare cache queries save: {lte_one.values_list('key', 'counter')}")
        lte_one.delete()

    def select_and_verify(self, model, keys=None):
        """
        Select all related to model cached items and delete their caches.
        Later re-made caches for most used ones by counter
        :param model:
        :param keys:
        :return:
        """
        if keys is None:
            keys = []
        cached_items = OctoCacheStore.objects.all()
        cached_items = cached_items.filter(key__in=keys)
        for cached_item in cached_items:
            # IMPORTANT:
            # When checking we anyway delete all caches from related model to avoid any old cache remains
            cache.delete(cached_item.hashed)
            # Now we able to renew cached query if it's item has a raw query in it!
            if cached_item.query:
                # Convert b'SELECT' back to actual python b'' string
                # q = eval(cached_item.query)
                # For all queries with hit more than once (or more?)
                if cached_item.counter > 1:
                    pass
                    # query = q.decode('utf-8')
                    # Check query hash from DB and hashed again, to be sure we use the same item for renew
                    # verifying = OctoCache().verify(query, cached_item.hashed)
                    # if verifying:
                    #     log.info(f"Cache sig OK: {verifying}")
                        # RE-EXECUTE query and put it into the cache again!
                        # NOTE: Cannot replace the cached query, because here it's a RawQuerySet, while we need QuerySet
                        # IDEA: Refer to related test item and just execute local test task?
                        # OctoCache().cache_query(model.objects.raw(query))
                        # qs = model.objects.all()
                        # OctoCache().cache_query(qs.extra(query))
                    # else:
                    #     log.error(f"Query hash is diff for this query: '{query}' != hash '{cached_item.hashed}'")
                # For any query which hit count is less then 1, means it was requested only once, this is not common.
                elif cached_item.counter <= 1:
                    # log.debug(f'Single {cached_item.counter} query can be deleted! QUERY {q}')
                    cached_item.delete()
                # Something...
                else:
                    # log.debug(f'Zero {cached_item.counter} query will be deleted! QUERY {q}')
                    cached_item.delete()
                # HERE: Run cache delete for the following key ot all keys, and then
                # we need to re-execute most used queries and save is to cache
            else:
                # IDEA: Need to delete detailed queries where users are asking for single tests
                # - those queries should not be automatically rebuild!
                cached_item.delete()
                log.info("This cache item have no query - just deleted!")

class OctoSignals:

    def __init__(self):
        self.test_last = ['AddmDigest', 'TestLast', 'TestLatestDigestAll']
        self.test_history = ['TestHistory', 'TestHistoryDigestDaily']
        self.test_cases = ['TestCases']
        self.upload_tests = ['UploadTestsNew', 'TkuPackagesNew']

    # SAVE:
    @staticmethod
    @receiver(post_save, sender=TestLast)  # the sender is your fix
    def test_last_save(sender, instance, created, **kwargs):
        log.info("post_save in TestLast table!")
        log.debug(f'Args: {sender} {instance} {created} kwargs: {kwargs}')
        # OctoCache().select_and_verify(model=TestLast, keys=OctoSignals().test_last)
        OctoCache().delete_cache_on_signal(keys=OctoSignals().test_last)

    @staticmethod
    @receiver(post_save, sender=TestHistory)  # the sender is your fix
    def test_history_save(sender, instance, created, **kwargs):
        log.info("post_save in TestHistory table!")
        log.debug(f'Args: {sender} {instance} {created} kwargs: {kwargs}')
        # OctoCache().select_and_verify(model=TestHistory, keys=OctoSignals().test_history)
        OctoCache().delete_cache_on_signal(keys=OctoSignals().test_history)

    @staticmethod
    @receiver(post_save, sender=TestCases)  # the sender is your fix
    def test_cases_save(sender, instance, created, **kwargs):
        log.info("post_save in TestCases table!")
        log.debug(f'Args: {sender} {instance} {created} kwargs: {kwargs}')
        # OctoCache().select_and_verify(model=TestCases, keys=OctoSignals().test_cases)
        OctoCache().delete_cache_on_signal(keys=OctoSignals().test_cases)

    @staticmethod
    @receiver(post_save, sender=UploadTestsNew)  # the sender is your fix
    def tku_upload_test_save(sender, instance, created, **kwargs):
        log.info("post_save in TestCases table!")
        log.debug(f'Args: {sender} {instance} {created} kwargs: {kwargs}')
        # OctoCache().select_and_verify(model=UploadTestsNew, keys=OctoSignals().upload_tests)
        OctoCache().delete_cache_on_signal(keys=OctoSignals().upload_tests)

    # DELETE
    @staticmethod
    @receiver(post_delete, sender=TestLast)  # the sender is your fix
    def test_last_delete(sender, instance, **kwargs):
        log.info("post_delete in TestLast table!")
        log.debug(f'Args: {sender} {instance}  kwargs: {kwargs}')
        # OctoCache().select_and_verify(model=TestLast, keys=OctoSignals().test_last)
        OctoCache().delete_cache_on_signal(keys=OctoSignals().test_last)

    @staticmethod
    @receiver(post_delete, sender=TestHistory)  # the sender is your fix
    def test_history_delete(sender, instance, **kwargs):
        log.info("post_delete in TestHistory table!")
        log.debug(f'Args: {sender} {instance}  kwargs: {kwargs}')
        # OctoCache().select_and_verify(model=TestHistory, keys=OctoSignals().test_history)
        OctoCache().delete_cache_on_signal(keys=OctoSignals().test_history)

    @staticmethod
    @receiver(post_delete, sender=TestCases)  # the sender is your fix
    def test_cases_delete(sender, instance, **kwargs):
        log.info("post_delete in TestCases table!")
        log.debug(f'Args: {sender} {instance}  kwargs: {kwargs}')
        # OctoCache().select_and_verify(model=TestCases, keys=OctoSignals().test_cases)
        OctoCache().delete_cache_on_signal(keys=OctoSignals().test_cases)

    @staticmethod
    @receiver(post_delete, sender=UploadTestsNew)  # the sender is your fix
    def tku_upload_test_delete(sender, instance, **kwargs):
        log.info("post_delete in TestCases table!")
        log.debug(f'Args: {sender} {instance}  kwargs: {kwargs}')
        # OctoCache().select_and_verify(model=UploadTestsNew, keys=OctoSignals().upload_tests)
        OctoCache().delete_cache_on_signal(keys=OctoSignals().upload_tests)
