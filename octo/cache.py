
from hashlib import blake2b
from hmac import compare_digest

# from MySQLdb._exceptions import IntegrityError
from django.db.utils import IntegrityError

from django.core.cache import cache, caches
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
        self.cached = []

    def cache_query(self, caching, **kwargs):
        """
        :param caching: django model queryset.query or other cache-able- will be used to generate hash
        https://docs.python.org/3/library/hashlib.html
        :return:
        """
        ttl = kwargs.get('ttl', 60 * 5)  # Save for 15 minutes. Later change to 1 min?
        assert hasattr(caching, 'query')
        # TODO: Sep this to different methods for different cases
        try:
            hkey = caching.model.__name__
            h = blake2b(digest_size=50, key=hkey.encode('utf-8'))
            h.update(f'{caching.query}'.encode('utf-8'))
            # log.debug(f'Hashed model query with key: {hkey}')
        # Here we cannot hash
        except TypeError as e:
            log.error(f"Cannot hash this: {caching} | Error: {e}")
            raise Exception(e)

        hashed = h.hexdigest()
        return self._get_or_set(hashed, caching, ttl, hkey)

    def cache_context(self, caching, hkey, **kwargs):
        ttl = kwargs.get('ttl', 60 * 3)
        try:
            h = blake2b(digest_size=50)
            h.update(hkey.encode('utf-8'))
        # Here we cannot hash
        except TypeError as e:
            log.error(f"Cannot hash this: {caching} | Error: {e}")
            raise Exception(e)
        hashed = h.hexdigest()
        return self._get_or_set(hashed, caching, ttl, hkey)

    def cache_iterable(self, caching, **kwargs):
        ttl = kwargs.get('ttl', 60 * 15)  # Save for 15 minutes. Later change to 1 min?
        hkey = kwargs.get('hkey', SECRET_KEY)
        try:
            if hasattr(caching, 'encode'):
                h = blake2b(digest_size=50, key=hkey.encode('utf-8'))
                h.update(f'{caching}'.encode('utf-8'))
        # Here we cannot hash
        except TypeError as e:
            log.error(f"Cannot hash this: {caching} | Error: {e}")
            raise Exception(e)
        hashed = h.hexdigest()
        return self._get_or_set(hashed, caching, ttl, hkey)

    def cache_other(self, caching, **kwargs):
        ttl = kwargs.get('ttl', 60 * 15)  # Save for 15 minutes. Later change to 1 min?
        hkey = kwargs.get('hkey', SECRET_KEY)
        try:
            h = blake2b(digest_size=50, key=hkey.encode('utf-8'))
            h.update(caching)
        # Here we cannot hash
        except TypeError as e:
            log.error(f"Cannot hash this: {caching} | Error: {e}")
            raise Exception(e)
        hashed = h.hexdigest()
        return self._get_or_set(hashed, caching, ttl, hkey)

    def _get_or_set(self, hashed, caching, ttl, hkey):
        cached = cache.get(hashed)
        if cached is None:
            cache.set(hashed, caching, ttl)
            self.save_cache_hash_db(hashed=hashed, caching=caching, key=hkey, ttl=ttl)
            return caching
        else:
            return cached

    def save_cache_hash_db(self, **kwargs):
        caching = kwargs.pop('caching')
        if hasattr(caching, 'query'):
            sql_query = caching.query
            kwargs.update(query=str(sql_query).encode('utf-8'))
        try:
            # TODO: Do not update if exist anyway?
            _, created = OctoCacheStore.objects.update_or_create(
                hashed=kwargs.get('hashed'),
                defaults=dict(**kwargs),
            )
            if created:
                log.debug(f"Cache table updated: {kwargs}")
            # log.debug(f'Query kw: {kwargs}')
            # cache_save = OctoCacheStore(**kwargs)
            # cache_save.save()
            # if cache_save:
            #     log.info(f'Saving new cache-hash {kwargs}')
        except IntegrityError as e:
            log.warning(f'IntegrityError output: {type(e)} {e}')
        except Exception as e:
            msg = f"<=save_cache_hash_db=> Error: {e}"
            print(msg)
            raise Exception(msg)

    def delete_cahe(self, **kwargs):
        hashed=kwargs.get('hashed')
        key=kwargs.get('key')
        name=kwargs.get('name')

        if hashed:
            log.info("Deleting cache by hash only.")
            cache.delete(hashed)

        if key:
            log.info("Deleting cache by key and all related!")
            tb_keys = OctoCacheStore.objects.filter(key__exact=key).values('hashed')
            # TODO: Or https://docs.djangoproject.com/en/3.0/topics/cache/#django.core.caches.cache.delete_many
            # cache.delete_many(['a', 'b', 'c'])
            for tb_hash in tb_keys:
                cache.delete(tb_hash)

        if name:
            log.info("Deleting cache by key and all related!")
            tb_keys = OctoCacheStore.objects.filter(name__exact=name).values('hashed')
            # TODO: Or https://docs.djangoproject.com/en/3.0/topics/cache/#django.core.caches.cache.delete_many
            # cache.delete_many(['a', 'b', 'c'])
            for tb_hash in tb_keys:
                cache.delete(tb_hash)

        # TODO: Should we also delete row with this cache, or use?


    # def verify(self, cache_name, sig):
    #     """Only for check!"""
    #     h = blake2b(digest_size=20, key=SECRET_KEY.encode('utf-8'))
    #     h.update(f'{cache_name}'.encode("utf-8"))
    #     hashed = h.hexdigest()
    #     return compare_digest(hashed, sig)
    #
    # def get_cached(self, hash_key):
    #     all_cache = CACHED
    #     # hash_key = f'{hash_key.encode("utf-8")}'
    #     for key in all_cache:
    #         self.verify(hash_key, key)
    #         # log.debug(f'Yes, this is: {hash_key}:{key} -> {cache.get(key)}')
    #         log.debug(f'Yes, this is: {hash_key}:{key}')
    #         break


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