
from hashlib import blake2b
from hmac import compare_digest

from django.conf import settings
from django.db.models.query import EmptyResultSet
from django.db.utils import IntegrityError

from django.core.cache import caches, cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from octo_tku_patterns.models import TestLast, TestHistory, TestCases


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
        :param caching: django model queryset.query or other cache-able- will be used to generate hash
        https://docs.python.org/3/library/hashlib.html
        :return:
        """
        ttl = kwargs.get('ttl', 60 * 5)  # Save for 15 minutes. Later change to 1 min?
        assert hasattr(caching, 'query'), "Can only make cache from django model query!"
        try:
            h = blake2b(digest_size=50)
            h.update(f'{caching.query}'.encode('utf-8'))
        except TypeError as e:
            log.error(f"Cannot hash this: {caching} | Error: {e}")
            raise Exception(e)
        hashed = h.hexdigest()
        return self._get_or_set(hashed, caching, ttl, caching.model.__name__)

    def cache_item(self, caching, hkey, **kwargs):
        ttl = kwargs.get('ttl', 60 * 3)
        try:
            h = blake2b(digest_size=50)
            h.update(hkey.encode('utf-8'))
        except TypeError as e:
            log.error(f"Cannot hash this: {caching} | Error: {e}")
            raise Exception(e)
        hashed = h.hexdigest()
        return self._get_or_set(hashed, caching, ttl, hkey)

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

    def delete_cahe(self, **kwargs):
        hashed=kwargs.get('hashed')

class OctoSignals:

    def __init__(self):
        pass

    @staticmethod
    @receiver(post_save, sender=TestLast) # the sender is your fix
    def test_last(sender, instance, created, **kwargs):
        log.info("Something have post_save in TestLast table!")
        log.debug(f'Args: {sender} {instance} {created} kwargs: {kwargs}')

    @staticmethod
    @receiver(post_save, sender=TestHistory) # the sender is your fix
    def test_history(sender, instance, created, **kwargs):
        log.info("Something have post_save in TestHistory table!")
        log.debug(f'Args: {sender} {instance} {created} kwargs: {kwargs}')

    @staticmethod
    @receiver(post_save, sender=TestCases) # the sender is your fix
    def test_cases(sender, instance, created, **kwargs):
        log.info("Something have post_save in TestCases table!")
        log.debug(f'Args: {sender} {instance} {created} kwargs: {kwargs}')

    @staticmethod
    @receiver(post_delete, sender=TestLast) # the sender is your fix
    def test_last(sender, instance, **kwargs):
        log.info("Something have post_delete in TestLast table!")
        log.debug(f'Args: {sender} {instance}  kwargs: {kwargs}')

    @staticmethod
    @receiver(post_delete, sender=TestHistory) # the sender is your fix
    def test_history(sender, instance, **kwargs):
        log.info("Something have post_delete in TestHistory table!")
        log.debug(f'Args: {sender} {instance}  kwargs: {kwargs}')

    @staticmethod
    @receiver(post_delete, sender=TestCases) # the sender is your fix
    def test_cases(sender, instance, **kwargs):
        log.info("Something have post_delete in TestCases table!")
        log.debug(f'Args: {sender} {instance}  kwargs: {kwargs}')