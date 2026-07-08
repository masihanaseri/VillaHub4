from celery import shared_task


@shared_task
def notify_new_message(message_id):

    print(

        f"New Message : {message_id}"

    )