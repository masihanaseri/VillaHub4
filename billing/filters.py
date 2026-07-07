import django_filters as filters

from billing.models import Invoice, Payment, ChargeRule, BillingCycle


class InvoiceFilter(filters.FilterSet):
    status = filters.MultipleChoiceFilter(choices=Invoice._meta.get_field("status").choices)
    residence = filters.UUIDFilter(field_name="residence_id")
    township = filters.UUIDFilter(field_name="township_id")
    issue_date_after = filters.DateFilter(field_name="issue_date", lookup_expr="gte")
    issue_date_before = filters.DateFilter(field_name="issue_date", lookup_expr="lte")
    due_date_after = filters.DateFilter(field_name="due_date", lookup_expr="gte")
    due_date_before = filters.DateFilter(field_name="due_date", lookup_expr="lte")
    min_total = filters.NumberFilter(field_name="total", lookup_expr="gte")
    max_total = filters.NumberFilter(field_name="total", lookup_expr="lte")
    is_overdue = filters.BooleanFilter(method="filter_is_overdue")

    class Meta:
        model = Invoice
        fields = ["status", "residence", "township"]

    def filter_is_overdue(self, queryset, name, value):
        overdue_ids = [inv.id for inv in queryset if inv.is_overdue()] if value else None
        if value:
            return queryset.filter(id__in=overdue_ids)
        return queryset


class PaymentFilter(filters.FilterSet):
    status = filters.MultipleChoiceFilter(choices=Payment._meta.get_field("status").choices)
    method = filters.MultipleChoiceFilter(choices=Payment._meta.get_field("method").choices)
    invoice = filters.UUIDFilter(field_name="invoice_id")
    paid_after = filters.DateFilter(field_name="paid_at", lookup_expr="gte")
    paid_before = filters.DateFilter(field_name="paid_at", lookup_expr="lte")

    class Meta:
        model = Payment
        fields = ["status", "method", "invoice"]


class ChargeRuleFilter(filters.FilterSet):
    charge_type = filters.UUIDFilter(field_name="charge_type_id")
    calculation_method = filters.MultipleChoiceFilter(
        choices=ChargeRule._meta.get_field("calculation_method").choices
    )
    is_active = filters.BooleanFilter()

    class Meta:
        model = ChargeRule
        fields = ["charge_type", "calculation_method", "is_active"]


class BillingCycleFilter(filters.FilterSet):
    frequency = filters.MultipleChoiceFilter(
        choices=BillingCycle._meta.get_field("frequency").choices
    )
    is_active = filters.BooleanFilter()
    auto_generate = filters.BooleanFilter()

    class Meta:
        model = BillingCycle
        fields = ["frequency", "is_active", "auto_generate"]
