from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from billing.models import InvoiceStatus
from billing.services import InvoiceService
from billing.tests.factories import (
    ChargeTypeFactory,
    get_or_create_test_residence,
    get_or_create_test_township,
)

User = get_user_model()


class ChargeTypeAPITests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="finance", password="pass1234", is_staff=True, mobile="09120000001"
        )
        self.client.force_authenticate(self.staff)

    def test_create_charge_type(self):
        url = reverse("billing:charge-type-list")
        response = self.client.post(url, {"name": "Gym", "description": "Gym fee"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["slug"], "gym")

    def test_non_staff_cannot_create_charge_type(self):
        regular_user = User.objects.create_user(
            username="resident", password="pass1234", mobile="09120000002"
        )
        self.client.force_authenticate(regular_user)
        url = reverse("billing:charge-type-list")
        response = self.client.post(url, {"name": "Gym"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_is_searchable(self):
        ChargeTypeFactory(name="Swimming Pool")
        ChargeTypeFactory(name="Parking")
        url = reverse("billing:charge-type-list")
        response = self.client.get(url, {"search": "Pool"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)


class InvoiceAPITests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="finance2", password="pass1234", is_staff=True, mobile="09120000003"
        )
        self.client.force_authenticate(self.staff)
        self.residence = get_or_create_test_residence()
        self.township = get_or_create_test_township()
        self.charge_type = ChargeTypeFactory()

    def test_create_invoice_with_nested_items(self):
        url = reverse("billing:invoice-list")
        payload = {
            "residence": str(self.residence.id),
            "township": str(self.township.id),
            "items": [
                {
                    "charge_type": str(self.charge_type.id),
                    "title": "Monthly Fee",
                    "unit_price": "150.00",
                    "quantity": "1.00",
                }
            ],
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["total"], "150.00")

    def test_issue_action_transitions_status(self):
        invoice = InvoiceService.create_invoice(
            residence=self.residence, township=self.township,
            items=[{"charge_type": self.charge_type, "title": "Fee", "unit_price": Decimal("100.00")}],
        )
        url = reverse("billing:invoice-issue", args=[invoice.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], InvoiceStatus.ISSUED)

    def test_record_payment_action(self):
        invoice = InvoiceService.create_invoice(
            residence=self.residence, township=self.township,
            items=[{"charge_type": self.charge_type, "title": "Fee", "unit_price": Decimal("100.00")}],
        )
        InvoiceService.issue(invoice)
        url = reverse("billing:invoice-record-payment", args=[invoice.id])
        response = self.client.post(url, {
            "amount": "100.00", "method": "cash", "mark_successful": True,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "success")

    def test_filter_invoices_by_status(self):
        invoice = InvoiceService.create_invoice(
            residence=self.residence, township=self.township,
            items=[{"charge_type": self.charge_type, "title": "Fee", "unit_price": Decimal("50.00")}],
        )
        InvoiceService.issue(invoice)
        url = reverse("billing:invoice-list")
        response = self.client.get(url, {"status": "issued"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(item["status"] == "issued" for item in response.data["results"]))
