from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase

from wallets.admin import (
    CommissionRuleAdmin,
    CommissionTransactionAdmin,
    GatewayCallbackAdmin,
    GatewayTransactionAdmin,
    PaymentGatewayAdmin,
    SettlementAdmin,
    WalletAdmin,
    WalletTransactionAdmin,
    WithdrawalRequestAdmin,
)
from wallets.models import (
    CommissionRule,
    CommissionTransaction,
    GatewayCallback,
    GatewayTransaction,
    PaymentGateway,
    Settlement,
    Wallet,
    WalletTransaction,
    WithdrawalRequest,
)
from wallets.services import WalletService
from wallets.services.settlement_service import SettlementService

from .factories import (
    make_commission_rule,
    make_gateway,
    make_resident_wallet,
    make_township,
    make_township_wallet,
    make_user,
)


class AdminChangelistSmokeTests(TestCase):
    """
    Confirms every registered ModelAdmin can render its changelist
    (i.e. `list_display`/`list_select_related`/`list_filter` are all
    internally consistent) against at least one real row.
    """

    def setUp(self):

        self.site = AdminSite()
        self.factory = RequestFactory()
        self.superuser = make_user("admin-superuser", is_staff=True, is_superuser=True)

    def _get_changelist_response(self, model_admin_cls, model):

        request = self.factory.get("/admin/wallets/x/")
        request.user = self.superuser

        model_admin = model_admin_cls(model, self.site)
        response = model_admin.changelist_view(request)
        response.render()

        return response

    def test_wallet_admin_changelist(self):

        make_resident_wallet(balance=Decimal("100"))

        response = self._get_changelist_response(WalletAdmin, Wallet)

        self.assertEqual(response.status_code, 200)

    def test_wallet_transaction_admin_changelist(self):

        wallet = make_resident_wallet(balance=Decimal("0"))
        WalletService.deposit(wallet, Decimal("100"))

        response = self._get_changelist_response(WalletTransactionAdmin, WalletTransaction)

        self.assertEqual(response.status_code, 200)

    def test_settlement_admin_changelist(self):

        wallet = make_township_wallet(balance=Decimal("1000"))
        SettlementService.request(wallet, Decimal("100"))

        response = self._get_changelist_response(SettlementAdmin, Settlement)

        self.assertEqual(response.status_code, 200)

    def test_commission_rule_admin_changelist(self):

        make_commission_rule()

        response = self._get_changelist_response(CommissionRuleAdmin, CommissionRule)

        self.assertEqual(response.status_code, 200)

    def test_commission_transaction_admin_changelist(self):

        rule = make_commission_rule()
        wallet = make_resident_wallet(balance=Decimal("0"))
        wallet_transaction = WalletService.deposit(wallet, Decimal("100"))
        CommissionTransaction.objects.create(
            wallet_transaction=wallet_transaction, township=rule.township,
            amount=Decimal("2"), percent=rule.transaction_percent,
        )

        response = self._get_changelist_response(
            CommissionTransactionAdmin, CommissionTransaction,
        )

        self.assertEqual(response.status_code, 200)

    def test_payment_gateway_admin_changelist(self):

        make_gateway()

        response = self._get_changelist_response(PaymentGatewayAdmin, PaymentGateway)

        self.assertEqual(response.status_code, 200)

    def test_gateway_transaction_admin_changelist(self):

        wallet = make_resident_wallet(balance=Decimal("0"))
        gateway = make_gateway()
        GatewayTransaction.objects.create(
            wallet=wallet, gateway=gateway, amount=Decimal("10"), authority="A-ADM",
        )

        response = self._get_changelist_response(GatewayTransactionAdmin, GatewayTransaction)

        self.assertEqual(response.status_code, 200)

    def test_gateway_callback_admin_changelist(self):

        wallet = make_resident_wallet(balance=Decimal("0"))
        gateway = make_gateway()
        gateway_transaction = GatewayTransaction.objects.create(
            wallet=wallet, gateway=gateway, amount=Decimal("10"), authority="A-ADM-CB",
        )
        GatewayCallback.objects.create(
            gateway_transaction=gateway_transaction, raw_data={"a": 1},
        )

        response = self._get_changelist_response(GatewayCallbackAdmin, GatewayCallback)

        self.assertEqual(response.status_code, 200)

    def test_withdrawal_request_admin_changelist(self):

        from wallets.services.withdrawal_service import WithdrawalService

        user = make_user("admin-withdrawal-user")
        make_resident_wallet(user=user, balance=Decimal("1000"))
        WithdrawalService.create_request(user, amount=Decimal("100"))

        response = self._get_changelist_response(WithdrawalRequestAdmin, WithdrawalRequest)

        self.assertEqual(response.status_code, 200)
