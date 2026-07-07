from django.core.management.base import BaseCommand
from accounts.models import Permission, Role


class Command(BaseCommand):

    help = "Seed default permissions and roles"

    def handle(self, *args, **kwargs):

        permissions = [
            ("CREATE_INVITATION", "ایجاد دعوت‌نامه"),
            ("VIEW_RESIDENTS", "مشاهده ساکنین"),
            ("MANAGE_PAYMENTS", "مدیریت پرداخت‌ها"),
            ("VIEW_REPORTS", "مشاهده گزارش‌ها"),
        ]

        for code, title in permissions:

            obj, created = Permission.objects.get_or_create(
                code=code,
                defaults={"title": title}
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created: {code}"))

        self.stdout.write(self.style.SUCCESS("Permissions seeded successfully"))