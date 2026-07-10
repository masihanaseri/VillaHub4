from django.shortcuts import get_object_or_404
from django.shortcuts import redirect

from wallets.callbacks import CallbackService
from wallets.models import GatewayTransaction


def wallet_payment_callback(request):

    authority = request.GET.get("Authority")

    transaction = get_object_or_404(
        GatewayTransaction,
        authority=authority,
    )

    result = CallbackService.process(
        transaction,
        request,
    )

    if result.is_verified:

        return redirect(
            "/payment/success/"
        )

    return redirect(
        "/payment/failed/"
    )

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