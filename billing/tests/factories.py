"""
Test factories.

`residence` and `township` are produced by
`get_or_create_test_residence`/`get_or_create_test_township` below,
which build real `villas.Residence`/`villas.Villa`/`townships.Township`
records (there are no dedicated factory modules in those apps, so we
create the minimum valid records directly here).
"""
import uuid

from decimal import Decimal

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone

from billing.models import (
    ChargeType,
    ChargeRule,
    CalculationMethod,
    BillingCycle,
    BillingFrequency,
    Invoice,
    InvoiceStatus,
)

User = get_user_model()


def get_or_create_test_township():
    from townships.models import Township

    return Township.objects.create(
        code=f"TWN{uuid.uuid4().hex[:8]}",
        name="Test Township",
    )


def get_or_create_test_residence():
    from villas.models import Villa, Residence

    township = get_or_create_test_township()
    villa = Villa.objects.create(
        township=township,
        code=f"V{uuid.uuid4().hex[:8]}",
        name="Test Villa",
        area=Decimal("120.00"),
    )
    return Residence.objects.create(
        user=UserFactory(),
        villa=villa,
        resident_type=Residence.ResidentType.OWNER,
        start_date=timezone.localdate(),
    )


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"billing_user_{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    mobile = factory.Sequence(lambda n: f"0912{n:07d}")


class ChargeTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChargeType

    name = factory.Sequence(lambda n: f"Charge Type {n}")
    description = "Test charge type"
    is_active = True


class ChargeRuleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChargeRule

    charge_type = factory.SubFactory(ChargeTypeFactory)
    name = factory.Sequence(lambda n: f"Charge Rule {n}")
    calculation_method = CalculationMethod.FIXED_AMOUNT
    base_amount = "150.00"
    is_active = True


class BillingCycleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BillingCycle

    name = factory.Sequence(lambda n: f"Billing Cycle {n}")
    charge_rule = factory.SubFactory(ChargeRuleFactory)
    frequency = BillingFrequency.MONTHLY
    start_date = factory.LazyFunction(timezone.localdate)
    next_run_date = factory.LazyFunction(timezone.localdate)
    due_in_days = 14
    auto_generate = True
    is_active = True


class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invoice

    invoice_number = factory.Sequence(lambda n: f"INV-TEST-{n:06d}")
    residence = factory.LazyFunction(get_or_create_test_residence)
    township = factory.LazyAttribute(lambda o: o.residence.villa.township)
    due_date = factory.LazyFunction(timezone.localdate)
    status = InvoiceStatus.DRAFT
