"""
Human-facing landing pages the frontend/gateway redirects to after
``PaymentCallbackView`` finishes processing. All actual verification
and wallet-crediting logic lives in
``wallets.services.payment_service.PaymentGatewayService`` — there is
now a single implementation of the callback flow (see urls.py).
"""

from django.http import HttpResponse


def payment_success_page(request):

    return HttpResponse(
        "<h2>پرداخت با موفقیت انجام شد ✅</h2>",
        content_type="text/html; charset=utf-8",
    )


def payment_failed_page(request):

    return HttpResponse(
        "<h2>پرداخت ناموفق بود ❌</h2>",
        content_type="text/html; charset=utf-8",
    )
