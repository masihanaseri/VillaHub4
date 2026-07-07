import re

from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework.exceptions import ValidationError

PLATE_PATTERN = re.compile(r"^[A-Za-z0-9\u06F0-\u06F9\-\s]{2,20}$")


def validate_plate_number(value):
    """
    این تابع به‌عنوان model field validator استفاده می‌شود، پس باید
    django.core.exceptions.ValidationError را raise کند.
    """

    if not value:

        return

    if not PLATE_PATTERN.match(value.strip()):

        raise DjangoValidationError(
            "فرمت پلاک خودرو نامعتبر است.",
        )


def validate_subject_exclusivity(visitor, residence):
    """
    یک رکورد تردد نمی‌تواند همزمان هم به یک مهمان و هم به یک ساکن اشاره کند.
    هر دو هم می‌توانند خالی باشند (مثلاً تردد خودروی ناشناس).

    این تابع مستقیماً از Service صدا زده می‌شود (نه از model field
    validators)، پس از rest_framework.exceptions.ValidationError استفاده
    می‌کند تا خطا به‌صورت تمیز در پاسخ API نمایش داده شود.
    """

    if visitor is not None and residence is not None:

        raise ValidationError(
            "یک رکورد تردد نمی‌تواند همزمان به مهمان و ساکن مرتبط باشد.",
        )


def validate_gate_guard_township(gate, guard):
    """
    اگر نگهبان مشخص شده، باید متعلق به همان شهرکِ درب باشد.
    """

    if guard is not None and gate is not None and guard.township_id != gate.township_id:

        raise ValidationError(
            "نگهبان انتخاب‌شده متعلق به شهرک این درب نیست.",
        )
