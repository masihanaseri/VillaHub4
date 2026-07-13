from django.test import SimpleTestCase

from wallets.payment_gateways.factory import GatewayFactory
from wallets.payment_gateways.idpay import IDPayGateway
from wallets.payment_gateways.nextpay import NextPayGateway
from wallets.payment_gateways.zarinpal import ZarinPalGateway


class GatewayFactoryTests(SimpleTestCase):

    def test_get_returns_zarinpal_adapter(self):

        adapter = GatewayFactory.get("zarinpal")

        self.assertIsInstance(adapter, ZarinPalGateway)

    def test_get_returns_idpay_adapter(self):

        adapter = GatewayFactory.get("idpay")

        self.assertIsInstance(adapter, IDPayGateway)

    def test_get_returns_nextpay_adapter(self):

        adapter = GatewayFactory.get("nextpay")

        self.assertIsInstance(adapter, NextPayGateway)

    def test_get_is_case_and_whitespace_insensitive(self):

        adapter = GatewayFactory.get("  ZarinPal  ")

        self.assertIsInstance(adapter, ZarinPalGateway)

    def test_unsupported_gateway_raises_value_error(self):

        with self.assertRaises(ValueError):
            GatewayFactory.get("some-unknown-gateway")

    def test_available_gateways_lists_all_supported_slugs(self):

        self.assertEqual(
            set(GatewayFactory.available_gateways()),
            {"zarinpal", "idpay", "nextpay"},
        )
