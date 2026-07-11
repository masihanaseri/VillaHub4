import uuid

from django.conf import settings
from django.db import models

from core.models import BaseModel


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
    )

    wallet_type = models.CharField(
        max_length=20,
        choices=WalletType.choices,
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
    )


    is_active = models.BooleanField(
        default=True,
    )

    class Meta:

        db_table = "wallets"

    def __str__(self):

        if self.wallet_type == WalletType.SYSTEM:
            return "VillaHub"

        if self.wallet_type == WalletType.TOWNSHIP:
            return self.township.name

        return self.user.username


# ----------------------------------------
# Transaction Types
# ----------------------------------------

class TransactionType(models.TextChoices):

    DEPOSIT = "DEPOSIT", "Deposit"

    WITHDRAW = "WITHDRAW", "Withdraw"

    COMMISSION = "COMMISSION", "Commission"

    PAYMENT = "PAYMENT", "Payment"

    REFUND = "REFUND", "Refund"

    SETTLEMENT = "SETTLEMENT", "Settlement"


# ----------------------------------------
# Wallet Transaction
# ----------------------------------------

class WalletTransaction(BaseModel):

    class TransactionStatus(models.TextChoices):

        PENDING = "PENDING", "Pending"

        SUCCESS = "SUCCESS", "Success"

        FAILED = "FAILED", "Failed"

        CANCELLED = "CANCELLED", "Cancelled"

        REFUNDED = "REFUNDED", "Refunded"

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
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

    description = models.TextField(
        blank=True,
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
    )

    status = models.CharField(

        max_length=20,

        choices=TransactionStatus.choices,

        default=TransactionStatus.PENDING,

    )

    authority = models.CharField(

        max_length=100,

        blank=True,

    )

    invoice = models.ForeignKey(
        "billing.Invoice",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="wallet_transactions",
    )    

    is_completed = models.BooleanField(
        default=False,
    )    
    gateway_ref_id = models.CharField(

        max_length=100,

        blank=True,

    )

    gateway_name = models.CharField(

        max_length=50,

        blank=True,

    )

    paid_at = models.DateTimeField(

        null=True,

        blank=True,

    )

    verified_at = models.DateTimeField(

        null=True,

        blank=True,

    )

    failure_reason = models.TextField(

        blank=True,

    )

    metadata = models.JSONField(

        default=dict,

        blank=True,

    )  

    gateway = models.ForeignKey(
        "wallets.PaymentGateway",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )      

    class Meta:

        db_table = "wallet_transactions"

        ordering = [
            "-created_at",
        ]

    def __str__(self):

        return f"{self.wallet} - {self.amount}"

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
    )

    bank_name = models.CharField(
        max_length=100,
        blank=True,
    )

    account_owner = models.CharField(
        max_length=150,
        blank=True,
    )

    card_number = models.CharField(
        max_length=20,
        blank=True,
    )

    sheba_number = models.CharField(
        max_length=30,
        blank=True,
    )

    tracking_code = models.CharField(
        max_length=100,
        blank=True,
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

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

    name = models.CharField(
        max_length=100,
    )

    slug = models.SlugField(
        unique=True,
    )

    merchant_id = models.CharField(
        max_length=255,
    )

    api_key = models.CharField(
        max_length=255,
        blank=True,
    )

    sandbox = models.BooleanField(
        default=True,
    )

    sandbox_merchant_id = models.CharField(
        max_length=255,
        blank=True,
    )

    production_merchant_id = models.CharField(
        max_length=255,
        blank=True,
    )

    is_active = models.BooleanField(
        default=False,
    )

    priority = models.PositiveIntegerField(
        default=1,
    )

    description = models.TextField(
        blank=True,
    )

    callback_url = models.URLField(
        blank=True,
    )

    verify_url = models.URLField(
        blank=True,
    )

    payment_url = models.URLField(
        blank=True,
    )

    icon = models.ImageField(
        upload_to="payment_gateways/",
        blank=True,
        null=True,
    )    

    class Meta:

        ordering = [
            "priority",
        ]

    def __str__(self):

        return self.name    
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

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )

    authority = models.CharField(
        max_length=255,
        blank=True,
    )

    ref_id = models.CharField(
        max_length=255,
        blank=True,
    )



    is_verified = models.BooleanField(
        default=False,
    )

    is_wallet_updated = models.BooleanField(
        default=False,
    )

    raw_request = models.JSONField(
        null=True,
        blank=True,
    )

    raw_response = models.JSONField(
        null=True,
        blank=True,
    )

    wallet_transaction = models.ForeignKey(
        "wallets.WalletTransaction",
        on_delete=models.CASCADE,
        related_name="gateway_transactions",
        null=True,
        blank=True,
    )

    class Meta:

        db_table = "gateway_transactions"

    def __str__(self):

        return self.authority
    
# ----------------------------------------
# Gateway Callback
# ----------------------------------------

class GatewayCallback(BaseModel):


    raw_data = models.JSONField()

    ip_address = models.GenericIPAddressField()

    user_agent = models.TextField()

    class Meta:

        db_table = "gateway_callbacks"

# ----------------------------------------
# Withdrawal Request
# ----------------------------------------




# ----------------------------------------
# Withdrawal Request
# ----------------------------------------

class WithdrawalRequest(BaseModel):

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="withdraw_requests",
    )

    class Status(models.TextChoices):

        PENDING = "PENDING", "Pending"

        APPROVED = "APPROVED", "Approved"

        REJECTED = "REJECTED", "Rejected"

        PAID = "PAID", "Paid"

        CANCELLED = "CANCELLED", "Cancelled"

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
    )

    bank_name = models.CharField(
        max_length=100,
        blank=True,
    )

    account_owner = models.CharField(
        max_length=150,
        blank=True,
    )

    card_number = models.CharField(
        max_length=20,
        blank=True,
    )

    sheba_number = models.CharField(
        max_length=30,
        blank=True,
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_withdrawals",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paid_withdrawals",
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    tracking_code = models.CharField(
        max_length=100,
        blank=True,
    )

    bank_reference = models.CharField(
        max_length=100,
        blank=True,
    )

    reject_reason = models.TextField(
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:

        db_table = "withdraw_requests"

        ordering = [
            "-created_at",
        ]

    def __str__(self):

        return f"{self.wallet} - {self.amount}"