"""
Generates human-readable, sortable internal references for wallet
transactions, e.g. ``VH-TRX-20260711-000001``.

The daily counter is derived atomically from the database (a row-count
under the same ``transaction.atomic()`` block the caller already holds)
so no separate sequence table or cache is required. A short random
suffix is appended as a defense-in-depth measure against a race
between the count read and the insert under high concurrency; the
``internal_reference`` column is still uniquely constrained at the DB
level, so a collision simply raises ``IntegrityError`` and the caller
can retry.
"""

import secrets

from django.utils import timezone

PREFIX = "VH-TRX"


def generate_internal_reference(model_cls):
    """
    Build a new unique internal reference.

    Must be called from within the same ``transaction.atomic()`` block
    (ideally after a ``select_for_update()`` on the wallet) that will
    persist the transaction, so the sequence stays monotonic per day
    under concurrent load.
    """

    today = timezone.localdate()
    date_part = today.strftime("%Y%m%d")

    count_today = model_cls.objects.filter(
        created_at__date=today,
    ).count()

    sequence = count_today + 1
    suffix = secrets.token_hex(2).upper()

    return f"{PREFIX}-{date_part}-{sequence:06d}-{suffix}"
