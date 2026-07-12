import threading
from decimal import Decimal

from django.db import connections
from django.test import TransactionTestCase

from wallets.services import InsufficientBalanceError, TransferService

from .factories import make_resident_wallet


class TransferServiceTests(TransactionTestCase):

    def test_transfer_moves_funds_and_creates_two_transactions(self):

        source = make_resident_wallet(balance=Decimal("1000"))
        destination = make_resident_wallet(balance=Decimal("0"))

        outgoing, incoming = TransferService.transfer(source, destination, Decimal("300"))

        source.refresh_from_db()
        destination.refresh_from_db()

        self.assertEqual(source.balance, Decimal("700"))
        self.assertEqual(destination.balance, Decimal("300"))
        self.assertEqual(outgoing.amount, Decimal("300"))
        self.assertEqual(incoming.amount, Decimal("300"))
        self.assertEqual(outgoing.reference, incoming.internal_reference)

    def test_transfer_insufficient_balance_rolls_back(self):

        source = make_resident_wallet(balance=Decimal("50"))
        destination = make_resident_wallet(balance=Decimal("0"))

        with self.assertRaises(InsufficientBalanceError):
            TransferService.transfer(source, destination, Decimal("100"))

        source.refresh_from_db()
        destination.refresh_from_db()

        self.assertEqual(source.balance, Decimal("50"))
        self.assertEqual(destination.balance, Decimal("0"))

    def test_transfer_to_self_rejected(self):

        wallet = make_resident_wallet(balance=Decimal("100"))

        with self.assertRaises(ValueError):
            TransferService.transfer(wallet, wallet, Decimal("10"))

    def test_concurrent_opposite_direction_transfers_do_not_deadlock(self):
        """
        A transfers to B while B simultaneously transfers to A. Locking
        both wallets in a fixed (ascending pk) order regardless of
        sender/receiver role prevents the classic deadlock this would
        otherwise cause.
        """

        wallet_a = make_resident_wallet(balance=Decimal("500"))
        wallet_b = make_resident_wallet(balance=Decimal("500"))

        errors = []

        def run(source, destination, amount):
            try:
                TransferService.transfer(source, destination, amount)
            except Exception as exc:  # pragma: no cover - diagnostic only
                errors.append(exc)
            finally:
                connections.close_all()

        threads = [
            threading.Thread(target=run, args=(wallet_a, wallet_b, Decimal("50"))),
            threading.Thread(target=run, args=(wallet_b, wallet_a, Decimal("30"))),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual(errors, [])

        wallet_a.refresh_from_db()
        wallet_b.refresh_from_db()

        self.assertEqual(wallet_a.balance + wallet_b.balance, Decimal("1000"))
