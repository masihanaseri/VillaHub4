from .models import (
    MaintenanceHistory,
)


class MaintenanceService:

    @staticmethod
    def change_status(
        maintenance,
        user,
        new_status,
        note="",
    ):

        old_status = maintenance.status

        maintenance.status = new_status

        maintenance.save(
            update_fields=[
                "status",
            ]
        )

        MaintenanceHistory.objects.create(
            maintenance=maintenance,
            user=user,
            old_status=old_status,
            new_status=new_status,
            note=note,
        )

        return maintenance