"""
Service-layer helpers for the villas app.
"""
from villas.models import Residence


def iter_billable_residences_for_cycle(cycle):
    """
    Yields (residence, township, context) tuples for every active
    residence that should be billed by the given billing.BillingCycle.

    Consumed by billing.services.BillingCycleService.run_due_cycles via
    billing.tasks.generate_due_invoices.
    """
    residences = (
        Residence.objects.filter(
            is_active=True,
            villa__is_active=True,
        )
        .select_related("villa", "villa__township")
    )

    for residence in residences:
        villa = residence.villa
        context = {
            "area": villa.area,
            "persons": residence.family_count,
            "villa_type": None,
            "block": None,
        }
        yield residence, villa.township, context
