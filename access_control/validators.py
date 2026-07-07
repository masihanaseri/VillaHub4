import re

from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework.exceptions import ValidationError

MIN_LATITUDE = -90
MAX_LATITUDE = 90

MIN_LONGITUDE = -180
MAX_LONGITUDE = 180

DEVICE_PATTERN = re.compile(r"^[A-Za-z0-9\u06F0-\u06F9\-_. ]{0,100}$")


def validate_latitude(value):
    """
    این تابع به‌عنوان model field validator استفاده می‌شود، پس باید
    django.core.exceptions.ValidationError را raise کند.
    """

    if value is None:

        return

    if value < MIN_LATITUDE or value > MAX_LATITUDE:

        raise DjangoValidationError(
            f"عرض جغرافیایی باید بین {MIN_LATITUDE} و {MAX_LATITUDE} باشد.",
        )


def validate_longitude(value):

    if value is None:

        return

    if value < MIN_LONGITUDE or value > MAX_LONGITUDE:

        raise DjangoValidationError(
            f"طول جغرافیایی باید بین {MIN_LONGITUDE} و {MAX_LONGITUDE} باشد.",
        )


def validate_device_label(value):

    if not value:

        return

    if not DEVICE_PATTERN.match(value):

        raise DjangoValidationError(
            "شناسه دستگاه شامل کاراکترهای نامعتبر است.",
        )


def validate_valid_period(valid_from, valid_until):
    """
    بازه اعتبار AccessPass باید معتبر باشد: زمان پایان باید بعد از
    زمان شروع باشد. این اعتبارسنجی مستقیماً از Service صدا زده می‌شود.
    """

    if valid_from is None or valid_until is None:

        raise ValidationError(
            "بازه اعتبار (valid_from / valid_until) الزامی است.",
        )

    if valid_until <= valid_from:

        raise ValidationError(
            "زمان پایان اعتبار باید بعد از زمان شروع باشد.",
        )


def validate_visitor_township(visitor, township):
    """
    مهمان انتخاب‌شده باید متعلق به همان شهرکی باشد که کارت تردد برای آن
    صادر می‌شود.
    """

    if visitor is not None and township is not None and visitor.township_id != township.id:

        raise ValidationError(
            "این مهمان متعلق به شهرک انتخاب‌شده نیست.",
        )


def validate_gate_township(gate, township):
    """
    درب انتخاب‌شده (در صورت وجود) باید متعلق به همان شهرک کارت تردد باشد.
    """

    if gate is not None and township is not None and gate.township_id != township.id:

        raise ValidationError(
            "درب انتخاب‌شده متعلق به شهرک این کارت تردد نیست.",
        )


def validate_guard_township(guard, township):
    """
    نگهبان ثبت‌کننده رویداد (در صورت وجود) باید متعلق به همان شهرک باشد.
    """

    if guard is not None and township is not None and guard.township_id != township.id:

        raise ValidationError(
            "نگهبان انتخاب‌شده متعلق به این شهرک نیست.",
        )
