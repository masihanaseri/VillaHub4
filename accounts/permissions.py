from rest_framework.permissions import BasePermission


class HasPermission(BasePermission):

    def has_permission(self, request, view):

        required_permission = getattr(view, "required_permission", None)

        if not required_permission:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.has_permission(required_permission)