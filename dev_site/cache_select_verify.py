
if __name__ == "__main__":
    import logging
    import django

    django.setup()

    from octo_tku_patterns.models import TestLast
    from octo.models import OctoCacheStore
    from octo.cache import OctoCache

    log = logging.getLogger("octo.octologger")
    log.info("\n\n\n\n\nRun DevTasksOper")

    test_last_q_cache = OctoCacheStore.objects.all()
    test_last_q_cache = test_last_q_cache.filter(key__in=['TestLast', 'TestLatestDigestAll'])
    log.debug(f"This is queryset {test_last_q_cache}")
    log.debug(f"This is query {test_last_q_cache.query}")
    log.debug(f"This is model {test_last_q_cache.model}")
    log.debug(f"This is raw {test_last_q_cache.raw}")
    log.debug(f"This is resolve_expression {test_last_q_cache.resolve_expression}")
    log.debug(f"This is query attrs {dir(test_last_q_cache)}")

    # for cached_q in test_last_q_cache:
    #     if cached_q.query:
    #         if cached_q.counter > 1:
    #             log.debug(f"Counter: {cached_q.counter}")
    #             q = eval(cached_q.query)
    #             query = q.decode('utf-8')
    #             verifying = OctoCache().verify(query, cached_q.hashed)
    #             if verifying:
    #                 log.info(f"Cache sig OK: {verifying}")
    #         elif cached_q.counter <= 1:
    #             q = eval(cached_q.query)
    #             log.debug(f'Single {cached_q.counter} query can be deleted! QUERY {q}')
    #         else:
    #             q = eval(cached_q.query)
    #             log.debug(f'Zero {cached_q.counter} query will be deleted! QUERY {q}')
    #         # HERE: Run cache delete for the following key ot all keys, and then
    #         # we need to re-execute most used queries and save is to cache
    #     else:
    #         # IDEA: Need to delete detailed queries where users are asking for single tests
    #         # - those queries should not be automatically rebuild!
    #         log.info("This cache item have no query - just delete!")