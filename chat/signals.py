from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Message
from .tasks import notify_new_message


@receiver(
    post_save,
    sender=Message,
)
def message_created(
    sender,
    instance,
    created,
    **kwargs,
):

    if created:

        notify_new_message.delay(

            instance.id,

        )