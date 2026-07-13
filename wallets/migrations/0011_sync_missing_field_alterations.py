"""
Applies field-level changes (``db_index``, ``related_name``,
``help_text``) that were made directly on the model classes at some
point but never had a matching migration generated, so Django kept
reporting "changes not yet reflected in a migration" on every
``migrate`` run.

NOTE: an earlier revision of this fix also shipped a
``0011_remove_orphaned_uuid_fields`` migration that dropped the
``uuid`` column from WalletTransaction/CommissionRule/
CommissionTransaction/Settlement/PaymentGateway/GatewayTransaction/
GatewayCallback/WithdrawalRequest, based on a stale copy of
``models.py`` that no longer declared those fields. The actual,
currently-deployed models still declare and rely on ``uuid`` (unique,
used in ``validate_unique()``), so that migration was wrong and has
been removed; the fields are restored on the model classes instead.
This migration now depends directly on 0010.
"""

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallets', '0010_wallettransaction_timestamp_constraints'),
    ]

    operations = [
        migrations.AlterField(
            model_name='settlement',
            name='status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('PAID', 'Paid')], db_index=True, default='PENDING', max_length=20),
        ),
        migrations.AlterField(
            model_name='wallet',
            name='balance',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Never edit directly. Use wallets.services.WalletService.', max_digits=18),
        ),
        migrations.AlterField(
            model_name='wallet',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='wallet',
            name='wallet_type',
            field=models.CharField(choices=[('SYSTEM', 'System'), ('TOWNSHIP', 'Township'), ('RESIDENT', 'Resident')], db_index=True, max_length=20),
        ),
        migrations.AlterField(
            model_name='wallettransaction',
            name='gateway',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='wallet_transactions', to='wallets.paymentgateway'),
        ),
        migrations.AlterField(
            model_name='wallettransaction',
            name='gateway_response',
            field=models.JSONField(blank=True, default=dict, help_text='Raw response payload from the last gateway call (create/verify).'),
        ),
        migrations.AlterField(
            model_name='wallettransaction',
            name='metadata',
            field=models.JSONField(blank=True, default=dict, help_text='IP, user agent, device, client version, callback payload, etc.'),
        ),
    ]
