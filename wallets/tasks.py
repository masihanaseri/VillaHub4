"""
Thin task wrappers around the service layer, kept framework-agnostic
so they can be called directly, from a management command, or wired
up as Celery tasks (``@shared_task`` can be added by the task runner
integration without touching the business logic below).
"""

import logging

from .services import CleanupService

logger = logging.getLogger("wallets.tasks")


def expire_pending_transactions():
    """Transition stale PENDING transactions to EXPIRED. Returns the count."""

    count = CleanupService.expire_stale_pending_transactions()

    logger.info("tasks.expire_pending_transactions.done", extra={"count": count})

    return count


def retry_failed_gateway_transactions():
    """
    Placeholder hook for re-querying the gateway on transactions that
    errored out before a definitive verify response was received.
    Currently a no-op; wire up when a gateway that needs this is added.
    """

    logger.info("tasks.retry_failed_gateway_transactions.noop")

    return 0


def auto_settle_wallets():
    """
    Placeholder hook for scheduled automatic settlement runs (e.g.
    nightly payout of township wallets above a threshold). Currently a
    no-op; implement against SettlementService when the business rule
    for automatic settlement triggers is defined.
    """

    logger.info("tasks.auto_settle_wallets.noop")

    return 0
