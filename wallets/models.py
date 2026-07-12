"""
Wallet domain models.

Design notes
------------
* ``Wallet.balance`` is only ever mutated through ``wallets.services``
  under ``transaction.atomic()`` + ``select_for_update()``. A DB level
  ``CheckConstraint`` additionally guarantees the balance can never go
  negative, even if a bug bypasses the service layer.
* ``WalletTransaction`` is the single source of truth for every balance
  change. Rows are created once (in ``PENDING`` for online payments, or
  directly in a terminal state for instant operations) and are updated
  in place — a new transaction is never created to "finish" an existing
  payment. See ``wallets.services.payment_service``.
* ``TransactionStatus`` is a strict state machine. Impossible
  combinations (e.g. SUCCESS while still un-paid) are prevented by
  ``WalletTransaction.clean()`` and by the service layer, which is the
  only writer.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import BaseModel

from .managers import WalletQuerySet, WalletTransactionQuerySet


# ----------------------------------------
# Wallet Types
# ----------------------------------------

class WalletType(models.TextChoices):
    SYSTEM = "SYSTEM", "System"
    TOWNSHIP = "TOWNSHIP", "Township"
    RESIDENT = "RESIDENT", "Resident"


# ----------------------------------------
# Wallet
# ----------------------------------------

class Wallet(BaseModel):

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )

    wallet_type = models.CharField(
        max_length=20,
        choices=WalletType.choices,
        db_index=True,
    )

    township = models.ForeignKey(
        "townships.Township",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="wallets",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="wallets",
    )

    balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        help_text="Never edit directly. Use wallets.services.WalletService.",
    )

    is_active = models.BooleanField(
        default=True,
    )

    objects = WalletQuerySet.as_manager()

    class Meta:

        db_table = "wallets"

        constraints = [
            models.CheckConstraint(
                check=models.Q(balance__gte=0),
                name="wallet_balance_non_negative",
            ),
            # A resident/township wallet is scoped to exactly one owner;
            # the system wallet has neither.
            models.CheckConstraint(
                check=(
                    models.Q(wallet_type="SYSTEM")
                    | models.Q(wallet_type="TOWNSHIP", township__isnull=False)
                    | models.Q(wallet_type="RESIDENT", user__isnull=False)
                ),
                name="wallet_owner_matches_type",
            ),
        ]

        indexes = [
            models.Index(fields=["wallet_type", "is_active"]),
            models.Index(fields=["user", "wallet_type"]),
            models.Index(fields=["township", "wallet_type"]),
        ]

    def __str__(self):

        if self.wallet_type == WalletType.SYSTEM:
            return "VillaHub"

        if self.wallet_type == WalletType.TOWNSHIP:
            return self.township.name if self.township_id else "Township Wallet"

        return self.user.username if self.user_id else "Resident Wallet"


# ----------------------------------------
# Transaction Types
# ----------------------------------------

class TransactionType(models.TextChoices):

    DEPOSIT = "DEPOSIT", "Deposit"
    WITHDRAW = "WITHDRAW", "Withdraw"
    TRANSFER_IN = "TRANSFER_IN", "Transfer In"
    TRANSFER_OUT = "TRANSFER_OUT", "Transfer Out"
    COMMISSION = "COMMISSION", "Commission"
    PAYMENT = "PAYMENT", "Payment"
    REFUND = "REFUND", "Refund"
    SETTLEMENT = "SETTLEMENT", "Settlement"


# ----------------------------------------
# Wallet Transaction
# ----------------------------------------

class WalletTransaction(BaseModel):

    class TransactionStatus(models.TextChoices):
        """
        Strict transaction state machine.

        Allowed transitions::

            PENDING -> SUCCESS
            PENDING -> FAILED
            PENDING -> CANCELLED
            PENDING -> EXPIRED
            SUCCESS -> REFUNDED

        Any other transition is rejected by ``WalletService`` /
        ``PaymentService``.
        """

        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"
        REFUNDED = "REFUNDED", "Refunded"

    TERMINAL_STATUSES = (
        TransactionStatus.SUCCESS,
        TransactionStatus.FAILED,
        TransactionStatus.CANCELLED,
        TransactionStatus.EXPIRED,
        TransactionStatus.REFUNDED,
    )

    # Valid status -> {allowed next statuses}
    ALLOWED_TRANSITIONS = {
        TransactionStatus.PENDING: {
            TransactionStatus.SUCCESS,
            TransactionStatus.FAILED,
            TransactionStatus.CANCELLED,
            TransactionStatus.EXPIRED,
        },
        TransactionStatus.SUCCESS: {
            TransactionStatus.REFUNDED,
        },
        TransactionStatus.FAILED: set(),
        TransactionStatus.CANCELLED: set(),
        TransactionStatus.EXPIRED: set(),
        TransactionStatus.REFUNDED: set(),
    }

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    invoice = models.ForeignKey(
        "billing.Invoice",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="wallet_transactions",
    )

    gateway = models.ForeignKey(
        "wallets.PaymentGateway",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="wallet_transactions",
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        db_index=True,
    )

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )

    balance_before = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )

    balance_after = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING,
        db_index=True,
    )

    description = models.TextField(
        blank=True,
    )

    # Human-readable, VillaHub-generated reference, e.g. VH-TRX-20260711-000001.
    # Always present, unlike the gateway's own reference.
    internal_reference = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        editable=False,
    )

    # Free-form reference supplied by the caller (e.g. a related refund's
    # internal_reference, a manual note, ...). Distinct from
    # internal_reference, which is always system-generated.
    reference = models.CharField(
        max_length=100,
        blank=True,
    )

    authority = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
    )

    gateway_ref_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
    )

    gateway_name = models.CharField(
        max_length=50,
        blank=True,
    )

    gateway_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Raw response payload from the last gateway call (create/verify).",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="IP, user agent, device, client version, callback payload, etc.",
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    failed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    failure_reason = models.TextField(
        blank=True,
    )

    objects = WalletTransactionQuerySet.as_manager()

    class Meta:

        db_table = "wallet_transactions"

        ordering = [
            "-created_at",
        ]

        constraints = [
            # A transaction that hasn't reached a terminal state can't
            # already carry a verification/payment timestamp, and vice
            # versa for FAILED transactions without a failure reason is
            # allowed (system-side failures), but SUCCESS always needs
            # paid_at + verified_at.
            models.CheckConstraint(
                check=~models.Q(status="SUCCESS") | (
                    models.Q(paid_at__isnull=False)
                    & models.Q(verified_at__isnull=False)
                ),
                name="wallettransaction_success_requires_timestamps",
            ),
            models.CheckConstraint(
                check=~models.Q(status="FAILED") | models.Q(failed_at__isnull=False),
                name="wallettransaction_failed_requires_failed_at",
            ),
            models.UniqueConstraint(
                fields=["authority"],
                condition=~models.Q(authority=""),
                name="wallettransaction_unique_authority",
            ),
        ]

        indexes = [
            models.Index(fields=["wallet", "status"]),
            models.Index(fields=["wallet", "transaction_type"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["gateway_ref_id"]),
        ]

    def __str__(self):

        return f"{self.internal_reference} · {self.wallet} · {self.amount}"

    def clean(self):

        super().clean()

        if self.pk:
            old_status = (
                WalletTransaction.objects.filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )

            if old_status and old_status != self.status:
                allowed = self.ALLOWED_TRANSITIONS.get(old_status, set())

                if self.status not in allowed:
                    raise ValidationError(
                        f"Invalid transaction status transition: "
                        f"{old_status} -> {self.status}."
                    )

    def can_transition_to(self, new_status):

        current_allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())

        return new_status in current_allowed


# ----------------------------------------
# Settlement Status
# ----------------------------------------

class SettlementStatus(models.TextChoices):

    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    PAID = "PAID", "Paid"


# ----------------------------------------
# Settlement
# ----------------------------------------

class Settlement(BaseModel):

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="settlements",
    )

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=SettlementStatus.choices,
        default=SettlementStatus.PENDING,
        db_index=True,
    )

    bank_name = models.CharField(max_length=100, blank=True)
    account_owner = models.CharField(max_length=150, blank=True)
    card_number = models.CharField(max_length=20, blank=True)
    sheba_number = models.CharField(max_length=30, blank=True)
    tracking_code = models.CharField(max_length=100, blank=True)

    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:

        db_table = "wallet_settlements"

        ordering = [
            "-created_at",
        ]

    def __str__(self):

        return f"{self.wallet} - {self.amount}"


# ----------------------------------------
# Commission Rule
# ----------------------------------------

class CommissionRule(BaseModel):

    township = models.OneToOneField(
        "townships.Township",
        on_delete=models.CASCADE,
        related_name="commission_rule",
    )

    monthly_subscription = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    transaction_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:

        db_table = "wallet_commission_rules"

    def __str__(self):

        return self.township.name


# ----------------------------------------
# Commission Transaction
# ----------------------------------------

class CommissionTransaction(BaseModel):

    wallet_transaction = models.OneToOneField(
        WalletTransaction,
        on_delete=models.CASCADE,
        related_name="commission",
    )

    township = models.ForeignKey(
        "townships.Township",
        on_delete=models.CASCADE,
        related_name="commissions",
    )

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )

    percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    class Meta:

        db_table = "wallet_commissions"

    def __str__(self):

        return str(self.amount)


# ----------------------------------------
# Payment Gateway
# ----------------------------------------

class PaymentGateway(BaseModel):

    name = models.CharField(max_length=100)

    slug = models.SlugField(unique=True)

    merchant_id = models.CharField(max_length=255)

    api_key = models.CharField(max_length=255, blank=True)

    sandbox = models.BooleanField(default=True)

    sandbox_merchant_id = models.CharField(max_length=255, blank=True)

    production_merchant_id = models.CharField(max_length=255, blank=True)

    is_active = models.BooleanField(default=False, db_index=True)

    priority = models.PositiveIntegerField(default=1)

    description = models.TextField(blank=True)

    callback_url = models.URLField(blank=True)

    verify_url = models.URLField(blank=True)

    payment_url = models.URLField(blank=True)

    icon = models.ImageField(
        upload_to="payment_gateways/",
        blank=True,
        null=True,
    )

    class Meta:

        ordering = [
            "priority",
        ]

        indexes = [
            models.Index(fields=["is_active", "priority"]),
        ]

    def __str__(self):

        return self.name

    def get_merchant_id(self):

        return self.sandbox_merchant_id if self.sandbox else self.production_merchant_id


# ----------------------------------------
# Gateway Transaction
# ----------------------------------------

class GatewayTransaction(BaseModel):

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="gateway_transactions",
    )

    invoice = models.ForeignKey(
        "billing.Invoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gateway_transactions",
    )

    gateway = models.ForeignKey(
        PaymentGateway,
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    wallet_transaction = models.ForeignKey(
        "wallets.WalletTransaction",
        on_delete=models.CASCADE,
        related_name="gateway_transactions",
        null=True,
        blank=True,
    )

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )

    authority = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
    )

    ref_id = models.CharField(
        max_length=255,
        blank=True,
    )

    is_verified = models.BooleanField(default=False)

    is_success = models.BooleanField(default=False)

    is_wallet_updated = models.BooleanField(default=False)

    raw_request = models.JSONField(null=True, blank=True)

    raw_response = models.JSONField(null=True, blank=True)

    class Meta:

        db_table = "gateway_transactions"

        constraints = [
            models.UniqueConstraint(
                fields=["authority"],
                condition=~models.Q(authority=""),
                name="gatewaytransaction_unique_authority",
            ),
        ]

        indexes = [
            models.Index(fields=["gateway", "is_verified"]),
        ]

    def __str__(self):

        return self.authority or str(self.id)


# ----------------------------------------
# Gateway Callback
# ----------------------------------------

class GatewayCallback(BaseModel):

    gateway_transaction = models.ForeignKey(
        GatewayTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="callbacks",
    )

    raw_data = models.JSONField(default=dict, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    user_agent = models.TextField(blank=True)

    processed = models.BooleanField(default=False)

    class Meta:

        db_table = "gateway_callbacks"

        ordering = [
            "-created_at",
        ]


# ----------------------------------------
# Withdrawal Request
# ----------------------------------------

class WithdrawalRequest(BaseModel):

    class Status(models.TextChoices):

        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="withdraw_requests",
    )

    wallet_transaction = models.OneToOneField(
        WalletTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="withdraw_request",
    )

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    bank_name = models.CharField(max_length=100, blank=True)
    account_owner = models.CharField(max_length=150, blank=True)
    card_number = models.CharField(max_length=20, blank=True)
    sheba_number = models.CharField(max_length=30, blank=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_withdrawals",
    )

    approved_at = models.DateTimeField(null=True, blank=True)

    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paid_withdrawals",
    )

    paid_at = models.DateTimeField(null=True, blank=True)

    tracking_code = models.CharField(max_length=100, blank=True)

    bank_reference = models.CharField(max_length=100, blank=True)

    reject_reason = models.TextField(blank=True)

    description = models.TextField(blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:

        db_table = "withdraw_requests"

        ordering = [
            "-created_at",
        ]

        indexes = [
            models.Index(fields=["wallet", "status"]),
        ]

    def __str__(self):

        return f"{self.wallet} - {self.amount}"
