"""
Orchestrates the online payment flow end to end:

    create_pending_transaction (WalletService)
        -> create_payment (opens a GatewayTransaction, gets a redirect URL)
        -> user pays on the gateway's site
        -> handle_callback (idempotent: verify once, settle once)

The same ``WalletTransaction`` row is created once and only updated
afterwards — see ``models.WalletTransaction`` docstring and Step 5 of
the design brief. ``handle_callback`` is the single entry point for
both the gateway redirect and any server-to-server callback, replacing
the two previously-duplicated implementations
(``wallets/callbacks.py`` + ``wallets/views.PaymentCallbackView``).
"""

import logging

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from ..models import (
    GatewayCallback,
    GatewayTransaction,
    PaymentGateway,
    WalletTransaction,
)
from ..payment_gateways.factory import GatewayFactory
from .wallet_service import WalletService

logger = logging.getLogger("wallets.services")


class PaymentVerificationError(Exception):
    """Raised when the gateway rejects verification or errors out."""


class NoActiveGatewayError(Exception):
    pass


class PaymentGatewayService:

    # ------------------------------------------------------------------
    # Gateway selection / redirect URL
    # ------------------------------------------------------------------

    @staticmethod
    def get_active_gateway():

        gateway = (
            PaymentGateway.objects.filter(is_active=True)
            .order_by("priority")
            .first()
        )

        if gateway is None:
            raise NoActiveGatewayError("No active payment gateway found.")

        return gateway

    @staticmethod
    def get_payment_url(gateway, authority):

        adapter = GatewayFactory.get(gateway.slug)

        return adapter.get_payment_url(authority, sandbox=gateway.sandbox)

    # ------------------------------------------------------------------
    # Create payment
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_payment(wallet_transaction, request):
        """
        Open a gateway payment session for an already-PENDING
        ``wallet_transaction`` and return the redirect URL.
        """

        if wallet_transaction.status != WalletTransaction.TransactionStatus.PENDING:
            raise PaymentVerificationError(
                "Only PENDING transactions can be sent to a payment gateway."
            )

        gateway = PaymentGatewayService.get_active_gateway()
        adapter = GatewayFactory.get(gateway.slug)

        callback_url = request.build_absolute_uri(
            reverse("wallet-payment-callback"),
        )

        result = adapter.create_payment(
            merchant_id=gateway.get_merchant_id(),
            amount=wallet_transaction.amount,
            callback_url=callback_url,
            sandbox=gateway.sandbox,
            description=(
                f"VillaHub wallet transaction {wallet_transaction.internal_reference}"
            ),
        )

        data = result.get("data") or {}
        authority = data.get("authority")

        if not authority:
            errors = result.get("errors")
            raise PaymentVerificationError(
                f"Gateway did not return an authority. Response: {errors or result}"
            )

        gateway_transaction = GatewayTransaction.objects.create(
            wallet=wallet_transaction.wallet,
            invoice=wallet_transaction.invoice,
            gateway=gateway,
            wallet_transaction=wallet_transaction,
            amount=wallet_transaction.amount,
            authority=authority,
            raw_request=result,
        )

        wallet_transaction.gateway = gateway
        wallet_transaction.gateway_name = gateway.slug
        wallet_transaction.authority = authority
        wallet_transaction.save(
            update_fields=["gateway", "gateway_name", "authority", "updated_at"],
        )

        logger.info(
            "payment.created",
            extra={
                "internal_reference": wallet_transaction.internal_reference,
                "authority": authority,
                "gateway": gateway.slug,
            },
        )

        return PaymentGatewayService.get_payment_url(gateway, authority)

    # ------------------------------------------------------------------
    # Verify payment (idempotent)
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def verify_payment(gateway_transaction):
        """
        Verify a ``GatewayTransaction`` with the underlying gateway.

        Idempotent: if it has already been verified, the existing
        record is returned as-is without a second call to the gateway
        (ZarinPal, like most gateways, will itself reject a double
        verify, so this also protects against relying on that).
        """

        locked = GatewayTransaction.objects.select_for_update().get(
            pk=gateway_transaction.pk,
        )

        if locked.is_verified:
            return locked

        gateway = locked.gateway
        adapter = GatewayFactory.get(gateway.slug)

        try:
            result = adapter.verify_payment(
                merchant_id=gateway.get_merchant_id(),
                authority=locked.authority,
                amount=locked.amount,
                sandbox=gateway.sandbox,
            )
        except Exception as exc:
            logger.exception(
                "payment.verify.gateway_error",
                extra={"authority": locked.authority},
            )
            raise PaymentVerificationError(str(exc)) from exc

        locked.raw_response = result
        data = result.get("data") or {}

        # ZarinPal: code 100 = fresh success, 101 = already verified
        # (also treated as success — the payment did go through).
        success_codes = {100, 101}

        if data.get("code") in success_codes:

            locked.is_success = True
            locked.is_verified = True
            locked.ref_id = str(data.get("ref_id", ""))

            wallet_transaction = locked.wallet_transaction
            if wallet_transaction is not None:
                wallet_transaction.gateway_ref_id = locked.ref_id
                wallet_transaction.gateway_response = result
                wallet_transaction.save(
                    update_fields=[
                        "gateway_ref_id",
                        "gateway_response",
                        "updated_at",
                    ],
                )

        else:

            locked.is_success = False
            locked.is_verified = True  # we DID get a definitive answer

        locked.save()

        logger.info(
            "payment.verified",
            extra={
                "authority": locked.authority,
                "is_success": locked.is_success,
            },
        )

        return locked

    # ------------------------------------------------------------------
    # Callback handling (single source of truth)
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def handle_callback(authority, gateway_status_param, request):
        """
        Process a gateway redirect/callback for the given ``authority``.

        Always idempotent and always logs a ``GatewayCallback`` audit
        row, regardless of outcome. Returns
        ``(gateway_transaction, wallet_transaction)``.
        """

        gateway_transaction = (
            GatewayTransaction.objects.select_related(
                "wallet_transaction", "gateway",
            )
            .select_for_update(of=("self",))
            .get(authority=authority)
        )

        GatewayCallback.objects.create(
            gateway_transaction=gateway_transaction,
            raw_data=dict(request.GET),
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        wallet_transaction = gateway_transaction.wallet_transaction

        # Already fully processed — return the current state without
        # touching anything (handles duplicate/replayed callbacks).
        if gateway_transaction.is_verified:
            return gateway_transaction, wallet_transaction

        # User cancelled on the gateway's page.
        if gateway_status_param != "OK":

            gateway_transaction.is_verified = True
            gateway_transaction.is_success = False
            gateway_transaction.save(
                update_fields=["is_verified", "is_success", "updated_at"],
            )

            if wallet_transaction is not None:
                wallet_transaction = WalletService.fail_pending_transaction(
                    wallet_transaction,
                    reason="Cancelled by user on gateway.",
                    new_status=WalletTransaction.TransactionStatus.CANCELLED,
                )

            return gateway_transaction, wallet_transaction

        gateway_transaction = PaymentGatewayService.verify_payment(
            gateway_transaction,
        )

        if not gateway_transaction.is_success:

            if wallet_transaction is not None:
                wallet_transaction = WalletService.fail_pending_transaction(
                    wallet_transaction,
                    reason="Gateway verification failed.",
                )

            return gateway_transaction, wallet_transaction

        # Success: settle the wallet transaction (idempotent) and, if
        # it's paying an invoice rather than a plain wallet top-up,
        # hand off to billing.
        if wallet_transaction is not None:

            wallet_transaction = WalletService.settle_pending_transaction(
                wallet_transaction,
            )

            if wallet_transaction.invoice_id:

                from billing.payment_service import InvoicePaymentService

                InvoicePaymentService.pay_from_wallet(
                    invoice=wallet_transaction.invoice,
                    wallet=wallet_transaction.wallet,
                )

        gateway_transaction.is_wallet_updated = True
        gateway_transaction.save(update_fields=["is_wallet_updated", "updated_at"])

        return gateway_transaction, wallet_transaction
