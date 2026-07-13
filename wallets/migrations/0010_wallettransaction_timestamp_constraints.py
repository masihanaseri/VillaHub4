from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallets', '0009_backfill_wallettransaction_timestamps'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='wallettransaction',
            constraint=models.CheckConstraint(
                condition=models.Q(('status', 'SUCCESS'), _negated=True)
                | (models.Q(paid_at__isnull=False) & models.Q(verified_at__isnull=False)),
                name='wallettransaction_success_requires_timestamps',
            ),
        ),
        migrations.AddConstraint(
            model_name='wallettransaction',
            constraint=models.CheckConstraint(
                condition=models.Q(('status', 'FAILED'), _negated=True) | models.Q(failed_at__isnull=False),
                name='wallettransaction_failed_requires_failed_at',
            ),
        ),
    ]
