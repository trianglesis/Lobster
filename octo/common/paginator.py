from django.core.paginator import Paginator
from django.utils.functional import cached_property
from django.db import connection, transaction, OperationalError


class TimeLimitedPaginator(Paginator):
    """
    Paginator that enforces a timeout on the count operation.
    If the operations times out, a fake bogus value is
    returned instead.
    """

    @cached_property
    def count(self):
        # We set the timeout in a db transaction to prevent it from
        # affecting other transactions.
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('SET session wait_timeout=30;')
            try:
                return super().count
            except OperationalError:
                return 9999999999
