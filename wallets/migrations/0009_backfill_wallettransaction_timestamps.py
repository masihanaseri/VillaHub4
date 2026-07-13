from django.db import migrations, models


def backfill_success_timestamps(apps, schema_editor):
    """
    Some pre-existing rows were marked SUCCESS by earlier code paths
    without ever recording `paid_at` / `verified_at`. The
    `wallettransaction_success_requires_timestamps` CheckConstraint
    (added in the next migration) would otherwise refuse to install
    against real production data.

    Best available proxy for "when it became SUCCESS" is `updated_at`
    (falling back to `created_at` if that's somehow also missing);
    this only fills in historical gaps and does not change any
    business logic going forward.

    Deliberately kept in its own migration/transaction, separate from
    the AddConstraint operation that depends on it: running a
    RunPython UPDATE immediately followed by an ALTER TABLE on the
    same table inside a single transaction can make PostgreSQL raise
    "cannot ALTER TABLE ... because it has pending trigger events".
    Splitting them into two migrations means this data fix is fully
    committed before the constraint migration ever starts.
    """

    WalletTransaction = apps.get_model("wallets", "WalletTransaction")

    broken = WalletTransaction.objects.filter(status="SUCCESS").filter(
        models.Q(paid_at__isnull=True) | models.Q(verified_at__isnull=True)
    )

    for wallet_transaction in broken.iterator():

        fallback = wallet_transaction.updated_at or wallet_transaction.created_at
        wallet_transaction.paid_at = wallet_transaction.paid_at or fallback
        wallet_transaction.verified_at = wallet_transaction.verified_at or fallback
        wallet_transaction.save(update_fields=["paid_at", "verified_at"])


def backfill_failed_at(apps, schema_editor):
    """
    Same as `backfill_success_timestamps`, for the companion
    `wallettransaction_failed_requires_failed_at` constraint: any
    pre-existing FAILED row without a `failed_at` gets one backfilled
    from `updated_at` (falling back to `created_at`).
    """

    WalletTransaction = apps.get_model("wallets", "WalletTransaction")

    broken = WalletTransaction.objects.filter(status="FAILED", failed_at__isnull=True)

    for wallet_transaction in broken.iterator():

        wallet_transaction.failed_at = wallet_transaction.updated_at or wallet_transaction.created_at
        wallet_transaction.save(update_fields=["failed_at"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('wallets', '0008_production_refactor'),
    ]

    operations = [
        migrations.RunPython(backfill_success_timestamps, noop_reverse),
        migrations.RunPython(backfill_failed_at, noop_reverse),
    ]
