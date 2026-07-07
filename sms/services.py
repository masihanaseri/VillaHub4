import random
from .providers.factory import SmsProviderFactory
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import (
    SmsMessage,
    SmsOTP,
)


class SmsService:
    @staticmethod
    @transaction.atomic
    def generate_otp(

        mobile,

        expire_minutes=2,

    ):

        code = str(

            random.randint(

                100000,

                999999,

            )

        )

        otp = SmsOTP.objects.create(

            mobile=mobile,

            code=code,

            expires_at=timezone.now()
            + timezone.timedelta(
                minutes=expire_minutes
            ),

        )

        return otp
    @staticmethod
    @transaction.atomic
    def verify_otp(

        mobile,

        code,

    ):

        otp = SmsOTP.objects.filter(

            mobile=mobile,

            code=code,

            is_used=False,

        ).first()

        if otp is None:

            raise ValidationError(
                "کد معتبر نیست."
            )

        if otp.expires_at < timezone.now():

            raise ValidationError(
                "کد منقضی شده است."
            )

        otp.is_used = True

        otp.save()

        return True
    @staticmethod
    def create_message(

        mobile,

        message,

        user=None,

        template=None,

    ):

        sms = SmsMessage.objects.create(

            mobile=mobile,

            message=message,

            user=user,

            template=template,

        )

        return sms
    @staticmethod
    def mark_sent(

        sms,

        provider,

        provider_message_id,

    ):

        sms.status = SmsMessage.Status.SENT

        sms.provider = provider

        sms.provider_message_id = provider_message_id

        sms.sent_at = timezone.now()

        sms.save()

        return sms
    @staticmethod
    def mark_failed(

        sms,

        error,

    ):

        sms.status = SmsMessage.Status.FAILED

        sms.error = error

        sms.save()

        return sms
    @staticmethod
    @transaction.atomic
    def send_sms(

        mobile,

        message,

        user=None,

        template=None,

    ):

        sms = SmsService.create_message(

            mobile=mobile,

            message=message,

            user=user,

            template=template,

        )

        provider = SmsProviderFactory.get_provider()

        result = provider.send(

            mobile,

            message,

        )

        if result["success"]:

            SmsService.mark_sent(

                sms,

                provider=result["provider"],

                provider_message_id=result["message_id"],

            )

        else:

            SmsService.mark_failed(

                sms,

                result["error"],

            )

        return sms