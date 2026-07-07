import re

from django.core.exceptions import ValidationError

GATE_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9\-_]{1,29}$")

MIN_LATITUDE = -90
MAX_LATITUDE = 90

MIN_LONGITUDE = -180
MAX_LONGITUDE = 180


def validate_gate_code(value):
    """
    کد درب باید فقط شامل حروف بزرگ انگلیسی، عدد، خط تیره و آندرلاین باشد
    و حداقل ۲ و حداکثر ۳۰ کاراکتر داشته باشد.
    """

    if not value:

        raise ValidationError(
            "کد درب الزامی است.",
        )

    normalized = value.strip().upper()

    if not GATE_CODE_PATTERN.match(normalized):

        raise ValidationError(
            "کد درب فقط می‌تواند شامل حروف بزرگ انگلیسی، عدد، "
            "خط تیره (-) و آندرلاین (_) باشد و حداقل ۲ کاراکتر باشد.",
        )


def validate_latitude(value):

    if value is None:

        return

    if value < MIN_LATITUDE or value > MAX_LATITUDE:

        raise ValidationError(
            f"عرض جغرافیایی باید بین {MIN_LATITUDE} و {MAX_LATITUDE} باشد.",
        )


def validate_longitude(value):

    if value is None:

        return

    if value < MIN_LONGITUDE or value > MAX_LONGITUDE:

        raise ValidationError(
            f"طول جغرافیایی باید بین {MIN_LONGITUDE} و {MAX_LONGITUDE} باشد.",
        )


def validate_coordinates_pair(latitude, longitude):
    """
    اگر یکی از دو مقدار طول یا عرض جغرافیایی وارد شده، دیگری هم باید وارد شود.
    """

    if (latitude is None) != (longitude is None):

        raise ValidationError(
            "طول و عرض جغرافیایی باید همزمان وارد شوند یا هر دو خالی باشند.",
        )
