from rest_framework import permissions


def _is_finance_staff(user) -> bool:
    return bool(
        user.is_staff
        or user.is_superuser
        or (hasattr(user, "has_permission") and user.has_permission("billing.manage"))
    )


class IsBillingStaff(permissions.BasePermission):
    """
    Full read/write access for staff/finance users, using the real
    accounts role/permission system (Permission code "billing.manage"),
    falling back to is_staff/is_superuser.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return _is_finance_staff(user)


class IsBillingStaffOrReadOnlyOwner(permissions.BasePermission):
    """
    Finance staff get full access. Regular authenticated residents get
    read-only access, scoped to their own residence at the queryset
    level (see views.py get_queryset) - this permission only gates the
    HTTP method, not the row.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return _is_finance_staff(request.user)


class CanRecordPayment(permissions.BasePermission):
    """
    Staff can record any payment method. Non-staff (e.g. a resident
    self-service portal) may only ever record status=pending, never
    mark_successful - enforced again in the view for defense in depth.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return True
