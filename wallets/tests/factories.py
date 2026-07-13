import itertools
from decimal import Decimal

from django.contrib.auth import get_user_model

from wallets.models import (
    CommissionRule,
    PaymentGateway,
    Wallet,
    WalletType,
)

User = get_user_model()

_slug_counter = itertools.count(1)


def make_user(username=None, **kwargs):

    username = username or f"resident-{next(_slug_counter)}"

    kwargs.setdefault("mobile", f"0900{next(_slug_counter):07d}")

    return User.objects.create_user(username=username, password="pass1234", **kwargs)


def make_resident_wallet(user=None, balance=Decimal("0"), **kwargs):

    user = user or make_user()

    return Wallet.objects.create(
        wallet_type=WalletType.RESIDENT,
        user=user,
        balance=balance,
        **kwargs,
    )


def make_system_wallet(balance=Decimal("0")):

    return Wallet.objects.create(wallet_type=WalletType.SYSTEM, balance=balance)


def make_township(name=None, **kwargs):
    """
    Minimal Township factory. The `townships` app isn't part of this
    module, so only the field guaranteed to exist by `Wallet.__str__`
    / `CommissionRule.__str__` (``name``) is set explicitly; anything
    else required by that app's model must already have a default.
    """

    from townships.models import Township

    name = name or f"Test Township {next(_slug_counter)}"

    return Township.objects.create(name=name, **kwargs)


def make_township_wallet(township=None, balance=Decimal("0"), **kwargs):

    township = township or make_township()

    return Wallet.objects.create(
        wallet_type=WalletType.TOWNSHIP,
        township=township,
        balance=balance,
        **kwargs,
    )


def make_commission_rule(township=None, transaction_percent=Decimal("2"),
                          monthly_subscription=Decimal("0"), is_active=True, **kwargs):

    township = township or make_township()

    return CommissionRule.objects.create(
        township=township,
        transaction_percent=transaction_percent,
        monthly_subscription=monthly_subscription,
        is_active=is_active,
        **kwargs,
    )


def make_gateway(slug=None, name="ZarinPal", is_active=True, priority=1,
                  sandbox=True, **kwargs):

    slug = slug or f"zarinpal-{next(_slug_counter)}"

    return PaymentGateway.objects.create(
        name=name,
        slug=slug,
        merchant_id="merchant-x",
        sandbox=sandbox,
        sandbox_merchant_id="sandbox-merchant-x",
        production_merchant_id="prod-merchant-x",
        is_active=is_active,
        priority=priority,
        **kwargs,
    )
