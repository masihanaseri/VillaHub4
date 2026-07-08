import json
from channels.db import database_sync_to_async
from .models import Conversation
from .models import Message
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from accounts.models import User


class ChatConsumer(

    AsyncWebsocketConsumer,

):

    async def connect(

        self,

    ):

        self.room = self.scope["url_route"]["kwargs"]["room"]

        self.room_group = f"chat_{self.room}"

        await self.channel_layer.group_add(

            self.room_group,

            self.channel_name,

        )

        await self.accept()
        await self.user_connected()

    async def disconnect(

        self,

        close_code,

    ):

        await self.channel_layer.group_discard(

            self.room_group,

            self.channel_name,

        )

        await self.user_disconnected()

    async def receive(
        self,
        text_data,
    ):

        data = json.loads(text_data)

        action = data.get("action")

        if action == "typing":

            await self.channel_layer.group_send(

                self.room_group,

                {

                    "type": "typing",

                    "user": data["sender"],

                    "typing": data["typing"],

                },

            )

            return
        
        if action == "seen":

            message = await self.mark_seen(

                data["message"],

            )

            await self.channel_layer.group_send(

                self.room_group,

                {

                    "type": "message_seen",

                    "message": message.id,

                    "user": self.scope["user"].id,

                },

            )

            return        

        if action == "message":

            message = await self.save_message(

                sender_id=data["sender"],

                text=data["text"],

                reply_id=data.get("reply"),

            )
        if action == "delete":

            message = await self.delete_message(

                data["message"],

            )
        if action == "forward":

            message = await self.forward_message(

                self.scope["user"].id,

                data["message"],

            )

            await self.channel_layer.group_send(

                self.room_group,

                {

                    "type":"chat_message",

                    "message":{

                        "id":message.id,

                        "sender":message.sender_id,

                        "text":message.text,

                        "created_at":str(message.created_at),

                    }

                }

            )

            return
            await self.channel_layer.group_send(

                self.room_group,

                {

                    "type": "message_deleted",

                    "message": message.id,

                },

            )

            return            

            await self.channel_layer.group_send(

                self.room_group,

                {

                    "type": "chat_message",

                    "message": {

                        "id": message.id,

                        "sender": data["sender"],

                        "text": message.text,

                        "created_at": str(message.created_at),

                    },

                },

            )



    async def chat_message(

        self,

        event,

    ):

        await self.send(

            text_data=json.dumps(

                event["message"],

            )

        )
    @database_sync_to_async
    def save_message(
        self,
        sender_id,
        text,
        reply_id=None,
    ):

        conversation = Conversation.objects.get(
            id=self.room,
        )

        reply = None

        if reply_id:
            reply = Message.objects.get(
                id=reply_id,
            )

        return Message.objects.create(
            conversation=conversation,
            sender_id=sender_id,
            text=text,
            reply_to=reply,
        )
    @database_sync_to_async
    def user_connected(

        self,

    ):

        user = self.scope["user"]

        if user.is_authenticated:

            user.is_online = True

            user.last_seen = timezone.now()

            user.save(
                update_fields=[
                    "is_online",
                    "last_seen",
                ]
            )
    @database_sync_to_async
    def user_disconnected(

        self,

    ):

        user = self.scope["user"]

        if user.is_authenticated:

            user.is_online = False

            user.last_seen = timezone.now()

            user.save(
                update_fields=[
                    "is_online",
                    "last_seen",
                ]
            )
    async def typing(
        self,
        event,
    ):

        await self.send(

            text_data=json.dumps(

                {

                    "type": "typing",

                    "user": event["user"],

                    "typing": event["typing"],

                }

            )

        )

    @database_sync_to_async
    def mark_seen(

        self,

        message_id,

    ):

        message = Message.objects.get(

            id=message_id,

        )

        user = User.objects.get(

            id=self.scope["user"].id,

        )

        message.seen_by.add(

            user,

        )

        message.is_seen = True

        message.seen_at = timezone.now()

        message.save()

        return message
    
    async def message_seen(

        self,

        event,

    ):

        await self.send(

            text_data=json.dumps(

                {

                    "type": "seen",

                    "message": event["message"],

                    "user": event["user"],

                }

            )

        )

    @database_sync_to_async
    def delete_message(

        self,

        message_id,

    ):

        message = Message.objects.get(

            id=message_id,

        )

        message.deleted_for_everyone = True

        message.deleted_at = timezone.now()

        message.text = "این پیام حذف شده است."

        message.save()

        return message   

    async def message_deleted(

        self,

        event,

    ):

        await self.send(

            text_data=json.dumps(

                {

                    "type": "deleted",

                    "message": event["message"],

                }

            )

        )     

    @database_sync_to_async
    def forward_message(

        self,

        sender,

        message_id,

    ):

        old = Message.objects.get(
            id=message_id,
        )

        conversation = Conversation.objects.get(
            id=self.room,
        )

        return Message.objects.create(

            conversation=conversation,

            sender_id=sender,

            text=old.text,

            attachment=old.attachment,

        )