from rest_framework.permissions import BasePermission


class IsMaintenanceManager(BasePermission):

    def has_permission(
        self,
        request,
        view,
    ):

        return (
            request.user.is_superuser
            or request.user.groups.filter(
                name__in=[
                    "System Manager",
                    "Township Manager",
                ]
            ).exists()
        )


class CanCreateMaintenance(BasePermission):

    def has_permission(
        self,
        request,
        view,
    ):

        if request.method == "POST":

            return request.user.is_authenticated

        return True


class CanEditMaintenance(BasePermission):

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):

        if request.user.is_superuser:
            return True

        if obj.created_by == request.user:
            return True

        if obj.assigned_to == request.user:
            return True

        if request.user.groups.filter(
            name__in=[
                "Township Manager",
            ]
        ).exists():
            return True

        return False