from django.db import models
from django.utils import timezone


class InvoiceQuerySet(models.QuerySet):
    def for_residence(self, residence_id):
        return self.filter(residence_id=residence_id)

    def for_township(self, township_id):
        return self.filter(township_id=township_id)

    def unpaid(self):
        return self.filter(status__in=["issued", "partially_paid", "overdue"])

    def overdue(self):
        today = timezone.localdate()
        return self.filter(
            due_date__lt=today,
            status__in=["issued", "partially_paid"],
        )

    def paid(self):
        return self.filter(status="paid")

    def in_period(self, start_date, end_date):
        return self.filter(issue_date__gte=start_date, issue_date__lte=end_date)


class PaymentQuerySet(models.QuerySet):
    def successful(self):
        return self.filter(status="success")

    def pending(self):
        return self.filter(status="pending")

    def for_invoice(self, invoice_id):
        return self.filter(invoice_id=invoice_id)

    def in_period(self, start_date, end_date):
        return self.filter(paid_at__date__gte=start_date, paid_at__date__lte=end_date)


class BillingCycleQuerySet(models.QuerySet):
    def due_for_generation(self, as_of=None):
        as_of = as_of or timezone.localdate()
        return self.filter(is_active=True, auto_generate=True, next_run_date__lte=as_of)
