import threading
from decimal import Decimal
from unittest import mock

from django.db import connections
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient

from wallets.models import (
    GatewayTransaction,
    TransactionType,
    WalletTransaction,
)
from wallets.services import WalletService
from wallets.services.refund_service import RefundService
from wallets.services.transfer_service import TransferService

from .factories import make_gateway, make_resident_wallet, make_user


def _run_concurrently(callables):

    errors = []
    threads = []

    def wrap(fn):
        def runner():
            try:
                fn()
            except Exception as exc:  # noqa: BLE001 - captured for assertions
                errors.append(exc)
            finally:
                connections.close_all()

        return runner

    for fn in callables:
        thread = threading.Thread(target=wrap(fn))
        threads.append(thread)

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    return errors


class DepositAndWithdrawConcurrencyTests(TransactionTestCase):

    def test_simultaneous_deposit_and_withdraw_leave_consistent_balance(self):

        wallet = make_resident_wallet(balance=Decimal("1000"))

        errors = _run_concurrently([
            lambda: WalletService.deposit(wallet, Decimal("500")),
            lambda: WalletService.withdraw(wallet, Decimal("300")),
        ])

        wallet.refresh_from_db()

        self.assertEqual(errors, [])
        self.assertEqual(wallet.balance, Decimal("1200"))  # 1000 + 500 - 300
        self.assertEqual(
            WalletTransaction.objects.filter(wallet=wallet).count(), 2,
        )


class TransferAndWithdrawConcurrencyTests(TransactionTestCase):

    def test_simultaneous_transfer_and_withdraw_never_overdraw_source_wallet(self):

        source = make_resident_wallet(balance=Decimal("1000"))
        destination = make_resident_wallet(balance=Decimal("0"))

        successes = []
        errors = []

        def do_transfer():
            try:
                TransferService.transfer(source, destination, Decimal("700"))
                successes.append("transfer")
            except Exception:
                pass

        def do_withdraw():
            try:
                WalletService.withdraw(source, Decimal("700"))
                successes.append("withdraw")
            except Exception:
                pass

        threads = [threading.Thread(target=t) for t in (do_transfer, do_withdraw)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            connections.close_all()

        source.refresh_from_db()
        destination.refresh_from_db()

        # Only one of the two 700-unit debits can succeed against a
        # 1000 balance; the source wallet must never go negative.
        self.assertGreaterEqual(source.balance, Decimal("0"))
        self.assertEqual(len(successes), 1)
        self.assertEqual(source.balance, Decimal("1000") - Decimal("700") * len(successes))


class TransferAndPaymentConcurrencyTests(TransactionTestCase):

    def test_simultaneous_transfer_and_online_payment_settlement_are_both_reflected(self):
        """
        A transfer debiting/crediting wallets and an independent
        online-payment settlement (deposit) landing on the source
        wallet at the same moment must not clobber each other —
        both amounts must be reflected in the final balance.
        """

        source = make_resident_wallet(balance=Decimal("1000"))
        destination = make_resident_wallet(balance=Decimal("0"))

        gateway = make_gateway()
        wallet_transaction = WalletService.create_pending_transaction(
            wallet=source, amount=Decimal("400"), transaction_type=TransactionType.DEPOSIT,
        )
        GatewayTransaction.objects.create(
            wallet=source, gateway=gateway, wallet_transaction=wallet_transaction,
            amount=Decimal("400"), authority="A-CONC-1",
        )

        def do_transfer():
            TransferService.transfer(source, destination, Decimal("300"))

        def do_settle_payment():
            WalletService.settle_pending_transaction(wallet_transaction)

        errors = _run_concurrently([do_transfer, do_settle_payment])

        source.refresh_from_db()
        destination.refresh_from_db()
        wallet_transaction.refresh_from_db()

        self.assertEqual(errors, [])
        self.assertEqual(destination.balance, Decimal("300"))
        self.assertEqual(
            wallet_transaction.status, WalletTransaction.TransactionStatus.SUCCESS,
        )
        # 1000 - 300 (transfer out) + 400 (settled payment)
        self.assertEqual(source.balance, Decimal("1100"))


class ConcurrentCallbackTests(TransactionTestCase):

    def test_two_simultaneous_callbacks_for_the_same_authority_credit_once(self):

        wallet = make_resident_wallet(balance=Decimal("0"))
        gateway = make_gateway()

        wallet_transaction = WalletService.create_pending_transaction(
            wallet=wallet, amount=Decimal("1000"), transaction_type=TransactionType.DEPOSIT,
        )
        GatewayTransaction.objects.create(
            wallet=wallet, gateway=gateway, wallet_transaction=wallet_transaction,
            amount=Decimal("1000"), authority="A-RACE-1",
        )
        wallet_transaction.authority = "A-RACE-1"
        wallet_transaction.gateway = gateway
        wallet_transaction.save()

        url = reverse("wallet-payment-callback")

        class FakeAdapter:
            def verify_payment(self, **kwargs):
                return {"data": {"code": 100, "ref_id": "REF-RACE-1"}}

        def hit_callback():
            client = APIClient()
            client.get(url, {"Authority": "A-RACE-1", "Status": "OK"})

        with mock.patch(
            "wallets.services.payment_service.GatewayFactory.get",
            return_value=FakeAdapter(),
        ):
            errors = _run_concurrently([hit_callback, hit_callback])

        wallet.refresh_from_db()

        self.assertEqual(errors, [])
        self.assertEqual(wallet.balance, Decimal("1000"))
        self.assertEqual(
            WalletTransaction.objects.filter(wallet=wallet).count(), 1,
        )


class SimultaneousRefundConcurrencyTests(TransactionTestCase):

    def test_simultaneous_manual_refunds_both_apply_exactly_once(self):

        wallet = make_resident_wallet(balance=Decimal("0"))

        errors = _run_concurrently([
            lambda: RefundService.refund_manual(wallet, Decimal("150"), reason="dup-1"),
            lambda: RefundService.refund_manual(wallet, Decimal("150"), reason="dup-2"),
        ])

        wallet.refresh_from_db()

        self.assertEqual(errors, [])
        self.assertEqual(wallet.balance, Decimal("300"))
        self.assertEqual(
            WalletTransaction.objects.filter(
                wallet=wallet, transaction_type=TransactionType.REFUND,
            ).count(),
            2,
        )
