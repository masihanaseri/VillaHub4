from django.db import models


class WalletQuerySet(models.QuerySet):

    def active(self):

        return self.filter(is_active=True)

    def for_user(self, user):

        return self.filter(user=user)


class WalletTransactionQuerySet(models.QuerySet):

    def successful(self):

        return self.filter(status="SUCCESS")

    def pending(self):

        return self.filter(status="PENDING")

    def for_wallet_owner(self, user):

        return self.filter(wallet__user=user)
