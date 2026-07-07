# Billing Module — Integration Guide

This module is now fully wired into the project. What was done:

1. **`requirements.txt`** — added `django-filter` and `factory-boy`.
2. **`config/settings.py`** — added `"django_filters"` to
   `INSTALLED_APPS` (`billing` was already listed).
3. **`config/urls.py`** — added
   `path("api/billing/", include("billing.urls"))`, plus
   `path("api/access-control/", include("access_control.urls"))`
   which had the same problem.
4. **`billing/models.py`** — `Invoice.residence` now points at
   `villas.Residence` (the real app is named `villas`, not
   `residences`).
5. **`billing/services.py`** (`NotificationDispatcher`) — now calls
   the real `notifications.services.NotificationService.send(recipient=,
   title=, message=, notification_type=)` and resolves the recipient
   via `residence.user`.
6. **`billing/views.py`** — resident self-service scoping now filters
   on `residence__user_id` (the real FK name on `villas.Residence`).
7. **`billing/permissions.py`** — `IsBillingStaff` /
   `IsBillingStaffOrReadOnlyOwner` now check
   `user.has_permission("billing.manage")` (the real accounts
   role/permission system), falling back to `is_staff`/`is_superuser`.
8. **`billing/tasks.py`** — dropped the `celery` dependency (this
   project doesn't use Celery anywhere else - see `gates/tasks.py`)
   and pointed `generate_due_invoices` at the real
   `villas.services.iter_billable_residences_for_cycle`, which was
   added to the `villas` app.
9. **`billing/tests/factories.py`** — builds real
   `townships.Township` / `villas.Villa` / `villas.Residence` records
   with their actual required fields, and `UserFactory` now supplies
   the required unique `mobile` field.

## Migrations

Billing has no migrations yet - generate them once:

```
python manage.py makemigrations billing
python manage.py migrate
```

## Celery beat (optional, for automatic invoice generation)

This project doesn't use Celery. `billing/tasks.py` functions are
plain Python callables (same convention as `gates/tasks.py`) meant to
be invoked from a management command or cron. If Celery is introduced
later, add `@shared_task` to each.

## What was intentionally NOT built (per spec)

- Payment gateway integration — `Payment.gateway_name` /
  `gateway_payload` fields are reserved for this.
- Finance dashboard UI — `services.ReportService` exposes the
  aggregate queries a dashboard would call.
- AI/analytics — models and `ReportService` are structured so an
  agent can answer "top debtors / monthly income / collection rate /
  penalty report" without new migrations.
- Receipt PDF rendering — `services.ReceiptService.render_pdf` is a
  documented `NotImplementedError` stub; plug in WeasyPrint/ReportLab.

## Running tests

```
python manage.py test billing
```
