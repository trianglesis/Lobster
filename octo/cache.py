
from hashlib import blake2b
from hmac import compare_digest

from django.core.cache import cache, caches

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
        ttl = kwargs.get('ttl', 60 * 15)  # Save for 15 minutes. Later change to 1 min?
        hkey = kwargs.get('hkey', SECRET_KEY)
        # TODO: Sep this to different methods for different cases
        try:
            if hasattr(caching, 'query'):
                hkey = caching.model.__name__
                # Change hash base and add model name as secret key to hash
                h = blake2b(digest_size=50, key=hkey.encode('utf-8'))
                h.update(f'{caching.query}'.encode('utf-8'))
                # log.debug(f'Hashed model query with key: {hkey}')
            elif hasattr(caching, 'encode'):
                h = blake2b(digest_size=50, key=hkey.encode('utf-8'))
                h.update(f'{caching}'.encode('utf-8'))
            else:
                h = blake2b(digest_size=50, key=hkey.encode('utf-8'))
                h.update(caching)
        # Here we cannot hash
        except TypeError as e:
            log.error(f"Cannot hash this: {caching} | Error: {e}")
            raise Exception(e)

        hashed = h.hexdigest()
        return self.get_or_set(hashed, caching, ttl, hkey)

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

    def get_or_set(self, hashed, caching, ttl, hkey):
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
            updated, created = OctoCacheStore.objects.update_or_create(
                hashed=kwargs.get('hashed'),
                defaults=dict(**kwargs),
            )
            if created:
                log.info('Saving new cache-hash')
            if updated:
                log.info('We have this already.')
        except Exception as e:
            msg = f"<=save_cache_hash_db=> get_all_files: Error: {e}"
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