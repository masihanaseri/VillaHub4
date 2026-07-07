from django.db import transaction

from .models import (
    Notification,
    NotificationLog,
)


class NotificationService:

    # ============================================
    # ایجاد اعلان
    # ============================================

    @staticmethod
    @transaction.atomic
    def send(
        *,
        recipient,
        title,
        message,
        notification_type,
        priority=Notification.Priority.NORMAL,
        send_in_app=True,
        send_sms=False,
        send_email=False,
        send_push=False,
    ):

        notification = Notification.objects.create(

            recipient=recipient,

            title=title,

            message=message,

            notification_type=notification_type,

            priority=priority,

        )

        if send_in_app:

            NotificationLog.objects.create(

                notification=notification,

                channel=NotificationLog.Channel.IN_APP,

                receiver=str(recipient),

                status=NotificationLog.Status.SENT,

            )

        if send_sms:

            NotificationService.send_sms(
                notification=notification,
            )

        if send_email:

            NotificationService.send_email(
                notification=notification,
            )

        if send_push:

            NotificationService.send_push(
                notification=notification,
            )

        return notification

    # ============================================
    # پیامک
    # ============================================

    @staticmethod
    def send_sms(
        *,
        notification,
    ):

        NotificationLog.objects.create(

            notification=notification,

            channel=NotificationLog.Channel.SMS,

            receiver=str(notification.recipient),

            status=NotificationLog.Status.PENDING,

        )

    # ============================================
    # ایمیل
    # ============================================

    @staticmethod
    def send_email(
        *,
        notification,
    ):

        NotificationLog.objects.create(

            notification=notification,

            channel=NotificationLog.Channel.EMAIL,

            receiver=str(notification.recipient),

            status=NotificationLog.Status.PENDING,

        )

    # ============================================
    # Push
    # ============================================

    @staticmethod
    def send_push(
        *,
        notification,
    ):

        NotificationLog.objects.create(

            notification=notification,

            channel=NotificationLog.Channel.PUSH,

            receiver=str(notification.recipient),

            status=NotificationLog.Status.PENDING,

        )