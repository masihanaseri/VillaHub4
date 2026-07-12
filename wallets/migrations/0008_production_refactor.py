import secrets

import django.db.models.deletion
from django.db import migrations, models


def backfill_internal_reference(apps, schema_editor):
    """
    Populate internal_reference for every pre-existing WalletTransaction
    row before the column is made unique + non-null. Ordered by
    created_at so historical references stay roughly chronological.
    """

    WalletTransaction = apps.get_model("wallets", "WalletTransaction")

    seen_dates = {}

    for wallet_transaction in WalletTransaction.objects.order_by("created_at").iterator():

        date_key = wallet_transaction.created_at.strftime("%Y%m%d")
        seen_dates[date_key] = seen_dates.get(date_key, 0) + 1
        sequence = seen_dates[date_key]
        suffix = secrets.token_hex(2).upper()

        wallet_transaction.internal_reference = (
            f"VH-TRX-{date_key}-{sequence:06d}-{suffix}"
        )
        wallet_transaction.save(update_fields=["internal_reference"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('wallets', '0007_alter_withdrawalrequest_options_and_more'),
    ]

    operations = [

        # ---------------- Wallet ----------------

        migrations.AddIndex(
            model_name='wallet',
            index=models.Index(fields=['wallet_type', 'is_active'], name='wallets_type_active_idx'),
        ),
        migrations.AddIndex(
            model_name='wallet',
            index=models.Index(fields=['user', 'wallet_type'], name='wallets_user_type_idx'),
        ),
        migrations.AddIndex(
            model_name='wallet',
            index=models.Index(fields=['township', 'wallet_type'], name='wallets_township_type_idx'),
        ),
        migrations.AddConstraint(
            model_name='wallet',
            constraint=models.CheckConstraint(
                check=models.Q(balance__gte=0),
                name='wallet_balance_non_negative',
            ),
        ),
        migrations.AddConstraint(
            model_name='wallet',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(wallet_type='SYSTEM')
                    | models.Q(wallet_type='TOWNSHIP', township__isnull=False)
                    | models.Q(wallet_type='RESIDENT', user__isnull=False)
                ),
                name='wallet_owner_matches_type',
            ),
        ),

        # ---------------- WalletTransaction ----------------

        migrations.AlterField(
            model_name='wallettransaction',
            name='transaction_type',
            field=models.CharField(
                choices=[
                    ('DEPOSIT', 'Deposit'),
                    ('WITHDRAW', 'Withdraw'),
                    ('TRANSFER_IN', 'Transfer In'),
                    ('TRANSFER_OUT', 'Transfer Out'),
                    ('COMMISSION', 'Commission'),
                    ('PAYMENT', 'Payment'),
                    ('REFUND', 'Refund'),
                    ('SETTLEMENT', 'Settlement'),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='wallettransaction',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pending'),
                    ('SUCCESS', 'Success'),
                    ('FAILED', 'Failed'),
                    ('CANCELLED', 'Cancelled'),
                    ('EXPIRED', 'Expired'),
                    ('REFUNDED', 'Refunded'),
                ],
                db_index=True,
                default='PENDING',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='wallettransaction',
            name='failed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='wallettransaction',
            name='gateway_response',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='wallettransaction',
            name='internal_reference',
            field=models.CharField(editable=False, max_length=64, null=True),
        ),
        migrations.RunPython(backfill_internal_reference, noop_reverse),
        migrations.AlterField(
            model_name='wallettransaction',
            name='internal_reference',
            field=models.CharField(db_index=True, editable=False, max_length=64, unique=True),
        ),
        migrations.RemoveField(
            model_name='wallettransaction',
            name='is_completed',
        ),
        migrations.AlterField(
            model_name='wallettransaction',
            name='authority',
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='wallettransaction',
            name='gateway_ref_id',
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.AddIndex(
            model_name='wallettransaction',
            index=models.Index(fields=['wallet', 'status'], name='wallettxn_wallet_status_idx'),
        ),
        migrations.AddIndex(
            model_name='wallettransaction',
            index=models.Index(fields=['wallet', 'transaction_type'], name='wallettxn_wallet_type_idx'),
        ),
        migrations.AddIndex(
            model_name='wallettransaction',
            index=models.Index(fields=['status', 'created_at'], name='wallettxn_status_created_idx'),
        ),
        migrations.AddIndex(
            model_name='wallettransaction',
            index=models.Index(fields=['gateway_ref_id'], name='wallettxn_gateway_ref_idx'),
        ),
        migrations.AddConstraint(
            model_name='wallettransaction',
            constraint=models.CheckConstraint(
                check=models.Q(('status', 'SUCCESS'), _negated=True)
                | (models.Q(paid_at__isnull=False) & models.Q(verified_at__isnull=False)),
                name='wallettransaction_success_requires_timestamps',
            ),
        ),
        migrations.AddConstraint(
            model_name='wallettransaction',
            constraint=models.CheckConstraint(
                check=models.Q(('status', 'FAILED'), _negated=True) | models.Q(failed_at__isnull=False),
                name='wallettransaction_failed_requires_failed_at',
            ),
        ),
        migrations.AddConstraint(
            model_name='wallettransaction',
            constraint=models.UniqueConstraint(
                condition=models.Q(('authority', ''), _negated=True),
                fields=('authority',),
                name='wallettransaction_unique_authority',
            ),
        ),

        # ---------------- GatewayTransaction ----------------

        migrations.AddField(
            model_name='gatewaytransaction',
            name='is_success',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='gatewaytransaction',
            name='authority',
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddIndex(
            model_name='gatewaytransaction',
            index=models.Index(fields=['gateway', 'is_verified'], name='gatewaytxn_gateway_verif_idx'),
        ),
        migrations.AddConstraint(
            model_name='gatewaytransaction',
            constraint=models.UniqueConstraint(
                condition=models.Q(('authority', ''), _negated=True),
                fields=('authority',),
                name='gatewaytransaction_unique_authority',
            ),
        ),

        # ---------------- GatewayCallback ----------------

        migrations.AddField(
            model_name='gatewaycallback',
            name='gateway_transaction',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='callbacks',
                to='wallets.gatewaytransaction',
            ),
        ),
        migrations.AddField(
            model_name='gatewaycallback',
            name='processed',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='gatewaycallback',
            name='raw_data',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='gatewaycallback',
            name='ip_address',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='gatewaycallback',
            name='user_agent',
            field=models.TextField(blank=True),
        ),
        migrations.AlterModelOptions(
            name='gatewaycallback',
            options={'ordering': ['-created_at']},
        ),

        # ---------------- PaymentGateway ----------------

        migrations.AlterField(
            model_name='paymentgateway',
            name='is_active',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddIndex(
            model_name='paymentgateway',
            index=models.Index(fields=['is_active', 'priority'], name='paymentgw_active_priority_idx'),
        ),

        # ---------------- WithdrawalRequest ----------------

        migrations.AlterField(
            model_name='withdrawalrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pending'),
                    ('APPROVED', 'Approved'),
                    ('REJECTED', 'Rejected'),
                    ('PAID', 'Paid'),
                    ('CANCELLED', 'Cancelled'),
                ],
                db_index=True,
                default='PENDING',
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name='withdrawalrequest',
            index=models.Index(fields=['wallet', 'status'], name='withdrawreq_wallet_status_idx'),
        ),
    ]
