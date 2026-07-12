from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsWalletOwner(BasePermission):
    """
    Grants access only to the wallet's own user (or staff/superusers).
    Applies to ``Wallet`` instances directly.
    """

    def has_object_permission(self, request, view, obj):

        if request.user.is_superuser or request.user.is_staff:
            return True

        return obj.user_id == request.user.id


class IsWalletTransactionOwner(BasePermission):
    """
    Object-level guard for ``WalletTransaction``, ``GatewayTransaction``
    and ``WithdrawalRequest`` instances: only the owning wallet's user
    (or staff/superusers) may view/act on the object. Prevents one
    resident from reading or acting on another wallet's transactions
    purely by guessing an ID.
    """

    def has_object_permission(self, request, view, obj):

        if request.user.is_superuser or request.user.is_staff:
            return True

        wallet = getattr(obj, "wallet", None)

        return wallet is not None and wallet.user_id == request.user.id


class IsFinanceStaff(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated
            and (request.user.is_superuser or request.user.is_staff)
        )


class ReadOnlyOrFinanceStaff(BasePermission):
    """Anyone authenticated can read; only finance staff can write."""

    def has_permission(self, request, view):

        if not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return request.user.is_superuser or request.user.is_staff
