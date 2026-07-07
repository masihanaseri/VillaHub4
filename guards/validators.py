import re

from django.core.exceptions import ValidationError

EMPLOYEE_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9\-_]{1,29}$")

PHONE_PATTERN = re.compile(r"^0\d{10}$")


def validate_employee_code(value):

    if not value:

        raise ValidationError(
            "کد پرسنلی الزامی است.",
        )

    if not EMPLOYEE_CODE_PATTERN.match(value.strip().upper()):

        raise ValidationError(
            "کد پرسنلی فقط می‌تواند شامل حروف بزرگ انگلیسی، عدد، "
            "خط تیره (-) و آندرلاین (_) باشد و حداقل ۲ کاراکتر باشد.",
        )


def validate_guard_phone(value):

    if not value:

        raise ValidationError(
            "شماره تلفن الزامی است.",
        )

    if not PHONE_PATTERN.match(value.strip()):

        raise ValidationError(
            "شماره تلفن باید به فرمت صحیح و ۱۱ رقمی باشد (مثال: 09121234567).",
        )


def validate_shift_times(started_at, ended_at):

    if ended_at is not None and ended_at <= started_at:

        raise ValidationError(
            "زمان پایان شیفت باید بعد از زمان شروع باشد.",
        )
