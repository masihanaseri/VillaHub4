import re
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from wallets.models import WalletTransaction
from wallets.utils.reference import generate_internal_reference

from .factories import make_resident_wallet

REFERENCE_RE = re.compile(r"^VH-TRX-\d{8}-\d{6}-[0-9A-F]{4}$")


class InternalReferenceGeneratorTests(TestCase):

    def setUp(self):

        self.wallet = make_resident_wallet(balance=Decimal("0"))

    def _create_transaction(self, created_at=None):

        reference = generate_internal_reference(WalletTransaction)

        transaction_ = WalletTransaction.objects.create(
            wallet=self.wallet,
            transaction_type="DEPOSIT",
            amount=Decimal("10"),
            balance_before=Decimal("0"),
            balance_after=Decimal("0"),
            status=WalletTransaction.TransactionStatus.PENDING,
            internal_reference=reference,
        )

        if created_at is not None:
            WalletTransaction.objects.filter(pk=transaction_.pk).update(created_at=created_at)

        return transaction_

    def test_format_matches_expected_pattern(self):

        reference = generate_internal_reference(WalletTransaction)

        self.assertRegex(reference, REFERENCE_RE)

    def test_references_are_unique_across_calls(self):

        references = {generate_internal_reference(WalletTransaction) for _ in range(20)}

        self.assertEqual(len(references), 20)

    def test_uniqueness_enforced_at_db_level(self):

        reference = generate_internal_reference(WalletTransaction)

        WalletTransaction.objects.create(
            wallet=self.wallet,
            transaction_type="DEPOSIT",
            amount=Decimal("10"),
            balance_before=Decimal("0"),
            balance_after=Decimal("10"),
            status=WalletTransaction.TransactionStatus.SUCCESS,
            paid_at=timezone.now(),
            verified_at=timezone.now(),
            internal_reference=reference,
        )

        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WalletTransaction.objects.create(
                    wallet=self.wallet,
                    transaction_type="DEPOSIT",
                    amount=Decimal("10"),
                    balance_before=Decimal("10"),
                    balance_after=Decimal("20"),
                    status=WalletTransaction.TransactionStatus.SUCCESS,
                    paid_at=timezone.now(),
                    verified_at=timezone.now(),
                    internal_reference=reference,
                )

    def test_daily_sequence_increments_for_transactions_created_today(self):

        first = self._create_transaction()
        second = self._create_transaction()

        first_seq = int(first.internal_reference.split("-")[3])
        second_seq = int(second.internal_reference.split("-")[3])

        self.assertEqual(second_seq, first_seq + 1)

    def test_sequence_only_counts_todays_rows(self):

        yesterday = timezone.now() - timedelta(days=1)
        self._create_transaction(created_at=yesterday)

        today_reference = generate_internal_reference(WalletTransaction)
        today_date_part = timezone.localdate().strftime("%Y%m%d")

        # A row from yesterday must not inflate today's sequence.
        self.assertIn(f"-{today_date_part}-000001-", today_reference)
