from decimal import Decimal

from django.contrib.auth import get_user_model

from wallets.models import Wallet, WalletType

User = get_user_model()


def make_user(username="resident", **kwargs):

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
