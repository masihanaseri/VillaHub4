import threading
from decimal import Decimal

from django.db import connections
from django.test import TestCase, TransactionTestCase

from wallets.models import Settlement, SettlementStatus, TransactionType, WalletTransaction
from wallets.services import InsufficientBalanceError
from wallets.services.settlement_service import SettlementError, SettlementService

from .factories import make_township_wallet


class SettlementServiceRequestTests(TestCase):

    def test_request_creates_pending_settlement(self):

        wallet = make_township_wallet(balance=Decimal("5000"))

        settlement = SettlementService.request(wallet, Decimal("1000"))

        self.assertEqual(settlement.status, SettlementStatus.PENDING)
        self.assertEqual(settlement.amount, Decimal("1000"))
        self.assertEqual(settlement.wallet_id, wallet.id)
        # Requesting a settlement never touches the balance by itself.
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal("5000"))


class SettlementServiceApproveTests(TestCase):

    def setUp(self):

        self.wallet = make_township_wallet(balance=Decimal("5000"))
        self.settlement = SettlementService.request(self.wallet, Decimal("1000"))

    def test_approve_pending_settlement(self):

        approved = SettlementService.approve(self.settlement)

        self.assertEqual(approved.status, SettlementStatus.APPROVED)

    def test_cannot_approve_twice(self):

        SettlementService.approve(self.settlement)
        self.settlement.refresh_from_db()

        with self.assertRaises(SettlementError):
            SettlementService.approve(self.settlement)

    def test_cannot_approve_already_paid_settlement(self):

        SettlementService.approve(self.settlement)
        self.settlement.refresh_from_db()
        SettlementService.pay(self.settlement, tracking_code="TRK-1")
        self.settlement.refresh_from_db()

        with self.assertRaises(SettlementError):
            SettlementService.approve(self.settlement)


class SettlementServicePayTests(TestCase):

    def setUp(self):

        self.wallet = make_township_wallet(balance=Decimal("5000"))
        self.settlement = SettlementService.request(self.wallet, Decimal("1000"))

    def test_cannot_pay_before_approval(self):

        with self.assertRaises(SettlementError):
            SettlementService.pay(self.settlement, tracking_code="TRK-1")

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("5000"))

    def test_pay_debits_wallet_and_creates_transaction(self):

        SettlementService.approve(self.settlement)
        self.settlement.refresh_from_db()

        paid = SettlementService.pay(self.settlement, tracking_code="TRK-1")

        self.wallet.refresh_from_db()

        self.assertEqual(paid.status, SettlementStatus.PAID)
        self.assertEqual(paid.tracking_code, "TRK-1")
        self.assertIsNotNone(paid.paid_at)
        self.assertEqual(self.wallet.balance, Decimal("4000"))

        transaction_ = WalletTransaction.objects.get(
            wallet=self.wallet, transaction_type=TransactionType.SETTLEMENT,
        )
        self.assertEqual(transaction_.amount, Decimal("1000"))
        self.assertEqual(transaction_.status, WalletTransaction.TransactionStatus.SUCCESS)
        self.assertEqual(transaction_.reference, "TRK-1")

    def test_pay_with_insufficient_balance_raises_and_leaves_settlement_untouched(self):

        SettlementService.approve(self.settlement)
        self.settlement.refresh_from_db()

        # Drain the wallet after approval but before payout.
        self.wallet.balance = Decimal("100")
        self.wallet.save(update_fields=["balance"])

        with self.assertRaises(InsufficientBalanceError):
            SettlementService.pay(self.settlement, tracking_code="TRK-1")

        self.settlement.refresh_from_db()
        self.wallet.refresh_from_db()

        self.assertEqual(self.settlement.status, SettlementStatus.APPROVED)
        self.assertEqual(self.wallet.balance, Decimal("100"))
        self.assertFalse(
            WalletTransaction.objects.filter(
                wallet=self.wallet, transaction_type=TransactionType.SETTLEMENT,
            ).exists()
        )

    def test_duplicate_pay_rejected(self):

        SettlementService.approve(self.settlement)
        self.settlement.refresh_from_db()
        SettlementService.pay(self.settlement, tracking_code="TRK-1")
        self.settlement.refresh_from_db()

        with self.assertRaises(SettlementError):
            SettlementService.pay(self.settlement, tracking_code="TRK-2")

        self.wallet.refresh_from_db()
        # Balance was only debited once.
        self.assertEqual(self.wallet.balance, Decimal("4000"))
        self.assertEqual(
            WalletTransaction.objects.filter(
                wallet=self.wallet, transaction_type=TransactionType.SETTLEMENT,
            ).count(),
            1,
        )

    def test_invalid_transition_request_status_rejected_when_paid(self):

        SettlementService.approve(self.settlement)
        self.settlement.refresh_from_db()
        SettlementService.pay(self.settlement, tracking_code="TRK-1")
        self.settlement.refresh_from_db()

        with self.assertRaises(SettlementError):
            SettlementService.pay(self.settlement, tracking_code="TRK-1")


class SettlementServiceConcurrencyTests(TransactionTestCase):

    def test_simultaneous_pay_only_debits_wallet_once(self):
        """
        Two concurrent `pay()` calls against the same approved
        settlement must not double-debit the wallet: the DB row lock
        on the settlement in `SettlementService.pay` serializes the
        two attempts, and the second sees status=PAID and raises.
        """

        wallet = make_township_wallet(balance=Decimal("5000"))
        settlement = SettlementService.request(wallet, Decimal("1000"))
        SettlementService.approve(settlement)
        settlement.refresh_from_db()

        errors = []
        successes = []

        def pay_once(tracking_code):
            try:
                SettlementService.pay(settlement, tracking_code=tracking_code)
                successes.append(tracking_code)
            except SettlementError:
                pass
            except Exception as exc:  # pragma: no cover - diagnostic only
                errors.append(exc)
            finally:
                connections.close_all()

        threads = [
            threading.Thread(target=pay_once, args=(f"TRK-{i}",))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        wallet.refresh_from_db()
        settlement.refresh_from_db()

        self.assertEqual(errors, [])
        self.assertEqual(len(successes), 1)
        self.assertEqual(settlement.status, SettlementStatus.PAID)
        self.assertEqual(wallet.balance, Decimal("4000"))
        self.assertEqual(
            WalletTransaction.objects.filter(
                wallet=wallet, transaction_type=TransactionType.SETTLEMENT,
            ).count(),
            1,
        )
