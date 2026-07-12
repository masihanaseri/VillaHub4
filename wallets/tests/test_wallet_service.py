import threading
from decimal import Decimal

from django.db import connections
from django.test import TransactionTestCase

from wallets.models import TransactionType, WalletTransaction
from wallets.services import InsufficientBalanceError, WalletService

from .factories import make_resident_wallet


class WalletServiceDepositWithdrawTests(TransactionTestCase):

    def test_deposit_increases_balance_and_logs_transaction(self):

        wallet = make_resident_wallet(balance=Decimal("0"))

        wallet_transaction = WalletService.deposit(wallet, Decimal("500"))

        wallet.refresh_from_db()

        self.assertEqual(wallet.balance, Decimal("500"))
        self.assertEqual(wallet_transaction.balance_before, Decimal("0"))
        self.assertEqual(wallet_transaction.balance_after, Decimal("500"))
        self.assertEqual(
            wallet_transaction.status, WalletTransaction.TransactionStatus.SUCCESS,
        )

    def test_withdraw_decreases_balance(self):

        wallet = make_resident_wallet(balance=Decimal("500"))

        WalletService.withdraw(wallet, Decimal("200"))

        wallet.refresh_from_db()

        self.assertEqual(wallet.balance, Decimal("300"))

    def test_withdraw_more_than_balance_raises(self):

        wallet = make_resident_wallet(balance=Decimal("100"))

        with self.assertRaises(InsufficientBalanceError):
            WalletService.withdraw(wallet, Decimal("200"))

        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal("100"))

    def test_zero_or_negative_amount_rejected(self):

        wallet = make_resident_wallet(balance=Decimal("100"))

        with self.assertRaises(Exception):
            WalletService.deposit(wallet, Decimal("0"))

        with self.assertRaises(Exception):
            WalletService.deposit(wallet, Decimal("-10"))


class WalletServiceConcurrencyTests(TransactionTestCase):
    """
    Exercises select_for_update() under real concurrent DB connections.
    Requires a DB backend that supports row locking (sqlite in the
    default Django test runner uses a single connection per thread
    against the same file, which still serializes writes and is
    sufficient to prove no lost updates occur; Postgres/MySQL in CI
    exercise true row-level locking).
    """

    def test_concurrent_deposits_do_not_lose_updates(self):

        wallet = make_resident_wallet(balance=Decimal("0"))

        thread_count = 10
        amount_each = Decimal("100")
        errors = []

        def deposit_once():
            try:
                WalletService.deposit(wallet, amount_each)
            except Exception as exc:  # pragma: no cover - diagnostic only
                errors.append(exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=deposit_once) for _ in range(thread_count)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        wallet.refresh_from_db()

        self.assertEqual(errors, [])
        self.assertEqual(wallet.balance, amount_each * thread_count)
        self.assertEqual(
            WalletTransaction.objects.filter(
                wallet=wallet, transaction_type=TransactionType.DEPOSIT,
            ).count(),
            thread_count,
        )

    def test_concurrent_withdrawals_never_take_balance_negative(self):

        wallet = make_resident_wallet(balance=Decimal("500"))

        thread_count = 10
        amount_each = Decimal("100")  # only 5 of 10 can succeed
        errors = []

        def withdraw_once():
            try:
                WalletService.withdraw(wallet, amount_each)
            except InsufficientBalanceError:
                pass
            except Exception as exc:  # pragma: no cover - diagnostic only
                errors.append(exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=withdraw_once) for _ in range(thread_count)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        wallet.refresh_from_db()

        self.assertEqual(errors, [])
        self.assertGreaterEqual(wallet.balance, Decimal("0"))
        self.assertEqual(wallet.balance % amount_each, Decimal("0"))
