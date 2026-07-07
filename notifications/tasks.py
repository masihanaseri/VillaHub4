from .utils.sms import SMSProvider
from .utils.email import EmailProvider
from .utils.push import PushProvider


from celery import shared_task

@shared_task
def send_welcome_sms(phone):
    return f"SMS sent to {phone}"


def send_sms_task(log):

    provider = SMSProvider()

    result = provider.send(

        receiver=log.receiver,

        title=log.notification.title,

        message=log.notification.message,

    )

    return result


def send_email_task(log):

    provider = EmailProvider()

    result = provider.send(

        receiver=log.receiver,

        title=log.notification.title,

        message=log.notification.message,

    )

    return result


def send_push_task(log):

    provider = PushProvider()

    result = provider.send(

        receiver=log.receiver,

        title=log.notification.title,

        message=log.notification.message,

    )

    return result