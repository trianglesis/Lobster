
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
        ttl = kwargs.get('ttl', 60)
        hkey = kwargs.get('hkey', SECRET_KEY)

        try:
            if hasattr(caching, 'query'):
                hkey = caching.model.__name__
                # Change hash base and add model name as secret key to hash
                h = blake2b(digest_size=20, key=hkey.encode('utf-8'))
                h.update(f'{caching.query}'.encode('utf-8'))
                log.debug(f'Hashed model query with key: {hkey}')

            elif hasattr(caching, 'encode'):
                h = blake2b(digest_size=20, key=hkey.encode('utf-8'))
                h.update(f'{caching}'.encode('utf-8'))

            else:
                h = blake2b(digest_size=20, key=hkey.encode('utf-8'))
                h.update(caching)

        except TypeError as e:
            log.error(f"Cannot hash this: {caching} | Error: {e}")

        hashed = h.hexdigest()

        cached = cache.get(hashed)
        if cached is None:
            cache.set(hashed, caching, ttl)
            self.save_cache_hash_db(hashed=hashed, caching=caching, key=hkey, ttl=ttl)
            # log.debug(f'Caching {hashed} cached: {CACHED}')
            return caching
        else:
            # log.debug(f'Get from cache {hashed}, cached: {CACHED}')
            # self.get_cached(hash_key='TestLatestDigestAll')
            return cached

    def save_cache_hash_db(self, **kwargs):
        caching = kwargs.pop('caching')
        if hasattr(caching, 'query'):
            sql_query = caching.query
            kwargs.update(query=str(sql_query).encode('utf-8'))
        try:
            OctoCacheStore.objects.update_or_create(
                hashed=kwargs.get('hashed'),
                defaults=dict(**kwargs),
            )
        except Exception as e:
            msg = f"<=save_cache_hash_db=> get_all_files: Error: {e}"
            print(msg)
            raise Exception(msg)

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