from django.core.management.base import BaseCommand

from wallets.services import CleanupService


class Command(BaseCommand):

    help = (
        "Transitions stale PENDING wallet transactions to EXPIRED. "
        "Intended to run on a schedule (cron / celery beat) every few minutes."
    )

    def handle(self, *args, **options):

        count = CleanupService.expire_stale_pending_transactions()

        self.stdout.write(
            self.style.SUCCESS(f"Expired {count} stale pending transaction(s).")
        )
