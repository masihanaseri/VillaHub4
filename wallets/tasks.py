import logging

logger = logging.getLogger("wallets.tasks")


def retry_failed_gateway_transactions():

    logger.info(
        "Retry failed gateway transactions..."
    )

    return 0


def auto_settle_wallets():

    logger.info(
        "Auto settlement task executed."
    )

    return 0