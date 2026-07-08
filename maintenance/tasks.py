from celery import shared_task

from .models import MaintenanceRequest


@shared_task
def notify_assigned_maintenance(
    maintenance_id,
):

    maintenance = (
        MaintenanceRequest.objects
        .select_related(
            "assigned_to",
        )
        .get(
            id=maintenance_id,
        )
    )

    print(
        f"Maintenance Assigned => {maintenance.title}"
    )

    return True