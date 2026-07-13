from unittest import mock

import requests
from django.test import SimpleTestCase

from wallets.payment_gateways.idpay import IDPayGateway
from wallets.payment_gateways.nextpay import NextPayGateway
from wallets.payment_gateways.zarinpal import ZarinPalGateway


def _mock_response(json_data, status_code=200, ok=True):

    response = mock.Mock()
    response.json.return_value = json_data
    response.status_code = status_code
    response.ok = ok
    response.text = str(json_data)
    response.raise_for_status = mock.Mock()

    if not ok:
        response.raise_for_status.side_effect = requests.HTTPError(response=response)

    return response


class ZarinPalCreatePaymentTests(SimpleTestCase):

    def setUp(self):

        self.gateway = ZarinPalGateway()

    @mock.patch("wallets.payment_gateways.zarinpal.requests.post")
    def test_create_payment_success(self, post_mock):

        post_mock.return_value = _mock_response(
            {"data": {"authority": "A-1", "code": 100}, "errors": []},
        )

        result = self.gateway.create_payment(
            merchant_id="m-1",
            amount=1000,
            callback_url="https://example.com/callback/",
            sandbox=True,
            description="test",
        )

        self.assertEqual(result["data"]["authority"], "A-1")
        post_mock.assert_called_once()
        called_url = post_mock.call_args[0][0]
        self.assertIn("sandbox.zarinpal.com", called_url)

    @mock.patch("wallets.payment_gateways.zarinpal.requests.post")
    def test_create_payment_timeout_propagates(self, post_mock):

        post_mock.side_effect = requests.Timeout("timed out")

        with self.assertRaises(requests.Timeout):
            self.gateway.create_payment(
                merchant_id="m-1",
                amount=1000,
                callback_url="https://example.com/callback/",
                sandbox=True,
            )

    @mock.patch("wallets.payment_gateways.zarinpal.requests.post")
    def test_create_payment_connection_error_propagates(self, post_mock):

        post_mock.side_effect = requests.ConnectionError("connection refused")

        with self.assertRaises(requests.ConnectionError):
            self.gateway.create_payment(
                merchant_id="m-1",
                amount=1000,
                callback_url="https://example.com/callback/",
                sandbox=True,
            )

    @mock.patch("wallets.payment_gateways.zarinpal.requests.post")
    def test_create_payment_http_error_status_propagates(self, post_mock):

        post_mock.return_value = _mock_response(
            {"errors": {"message": "bad request"}}, status_code=400, ok=False,
        )

        with self.assertRaises(requests.HTTPError):
            self.gateway.create_payment(
                merchant_id="m-1",
                amount=1000,
                callback_url="https://example.com/callback/",
                sandbox=True,
            )

    def test_get_payment_url_sandbox_vs_production(self):

        sandbox_url = self.gateway.get_payment_url("A-1", sandbox=True)
        production_url = self.gateway.get_payment_url("A-1", sandbox=False)

        self.assertIn("sandbox.zarinpal.com", sandbox_url)
        self.assertIn("payment.zarinpal.com", production_url)
        self.assertNotIn("sandbox", production_url)


class ZarinPalVerifyPaymentTests(SimpleTestCase):

    def setUp(self):

        self.gateway = ZarinPalGateway()

    @mock.patch("wallets.payment_gateways.zarinpal.requests.post")
    def test_verify_payment_success(self, post_mock):

        post_mock.return_value = _mock_response(
            {"data": {"code": 100, "ref_id": 999}},
        )

        result = self.gateway.verify_payment(
            merchant_id="m-1", authority="A-1", amount=1000, sandbox=True,
        )

        self.assertEqual(result["data"]["code"], 100)

    @mock.patch("wallets.payment_gateways.zarinpal.requests.post")
    def test_verify_payment_timeout_propagates(self, post_mock):

        post_mock.side_effect = requests.Timeout("timed out")

        with self.assertRaises(requests.Timeout):
            self.gateway.verify_payment(
                merchant_id="m-1", authority="A-1", amount=1000, sandbox=True,
            )

    @mock.patch("wallets.payment_gateways.zarinpal.requests.post")
    def test_verify_payment_connection_error_propagates(self, post_mock):

        post_mock.side_effect = requests.ConnectionError("connection refused")

        with self.assertRaises(requests.ConnectionError):
            self.gateway.verify_payment(
                merchant_id="m-1", authority="A-1", amount=1000, sandbox=True,
            )

    @mock.patch("wallets.payment_gateways.zarinpal.requests.post")
    def test_verify_payment_non_ok_response_raises(self, post_mock):

        post_mock.return_value = _mock_response(
            {"errors": {"message": "invalid authority"}}, status_code=422, ok=False,
        )

        with self.assertRaises(Exception):
            self.gateway.verify_payment(
                merchant_id="m-1", authority="A-1", amount=1000, sandbox=True,
            )

    @mock.patch("wallets.payment_gateways.zarinpal.requests.post")
    def test_verify_payment_invalid_json_propagates(self, post_mock):

        response = _mock_response({}, status_code=200, ok=True)
        response.json.side_effect = ValueError("invalid JSON")
        post_mock.return_value = response

        with self.assertRaises(ValueError):
            self.gateway.verify_payment(
                merchant_id="m-1", authority="A-1", amount=1000, sandbox=True,
            )


class UnimplementedGatewayAdapterTests(SimpleTestCase):
    """
    IDPay/NextPay are registered in the factory but intentionally not
    yet implemented; every method must fail loudly (not silently
    no-op) so a misconfigured `PaymentGateway.slug` can never look
    like a successful, unverified payment.
    """

    def test_idpay_every_method_raises_not_implemented(self):

        adapter = IDPayGateway()

        with self.assertRaises(NotImplementedError):
            adapter.create_payment(
                merchant_id="m", amount=1, callback_url="https://x", sandbox=True,
            )

        with self.assertRaises(NotImplementedError):
            adapter.verify_payment(merchant_id="m", authority="a", amount=1, sandbox=True)

        with self.assertRaises(NotImplementedError):
            adapter.get_payment_url("a", sandbox=True)

    def test_nextpay_every_method_raises_not_implemented(self):

        adapter = NextPayGateway()

        with self.assertRaises(NotImplementedError):
            adapter.create_payment(
                merchant_id="m", amount=1, callback_url="https://x", sandbox=True,
            )

        with self.assertRaises(NotImplementedError):
            adapter.verify_payment(merchant_id="m", authority="a", amount=1, sandbox=True)

        with self.assertRaises(NotImplementedError):
            adapter.get_payment_url("a", sandbox=True)
