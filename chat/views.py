from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .filters import ConversationFilter
from .models import Conversation
from .permissions import IsConversationMember
from .serializers import ConversationSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import Message
from .serializers import MessageSerializer


class ConversationViewSet(

    viewsets.ModelViewSet,

):

    serializer_class = ConversationSerializer

    permission_classes = [

        IsAuthenticated,

        IsConversationMember,

    ]

    filterset_class = ConversationFilter

    def get_queryset(

        self,

    ):

        return Conversation.objects.for_user(

            self.request.user,

        )
    
    @action(
        detail=True,
        methods=["post"],
    )
    def send_message(
        self,
        request,
        pk=None,
    ):

        conversation = self.get_object()

        serializer = MessageSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        serializer.save(
            sender=request.user,
            conversation=conversation,
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )
    
    @action(
        detail=True,
        methods=["get"],
    )
    def messages(
        self,
        request,
        pk=None,
    ):

        conversation = self.get_object()

        serializer = MessageSerializer(
            conversation.messages.all(),
            many=True,
        )

        return Response(serializer.data)


    @action(
        detail=True,
        methods=["patch"],
    )
    def edit_message(
        self,
        request,
        pk=None,
    ):

        message = Message.objects.get(

            id=request.data["message_id"],
            sender=request.user,

        )

        message.text = request.data["text"]

        message.is_edited = True

        message.save()

        return Response(

            MessageSerializer(message).data,

        )


    @action(
        detail=True,
        methods=["delete"],
    )
    def delete_message(
        self,
        request,
        pk=None,
    ):

        message = Message.objects.get(

            id=request.data["message_id"],
            sender=request.user,

        )

        message.delete()

        return Response(

            {

                "success": True,

            }

        )

    @action(
        detail=True,
        methods=["post"],
    )
    def seen(
        self,
        request,
        pk=None,
    ):

        message = Message.objects.get(
            id=request.data["message_id"],
        )

        message.is_seen = True

        message.seen_at = timezone.now()

        message.save()

        return Response(
            {
                "success": True,
            }
        )

    @action(
        detail=True,
        methods=["post"],
    )
    def upload(
        self,
        request,
        pk=None,
    ):

        conversation = self.get_object()

        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            text=request.data.get("text", ""),
            attachment=request.FILES["file"],
        )

        return Response(
            MessageSerializer(message).data
        )

    @action(
        detail=True,
        methods=["get"],
    )
    def search(
        self,
        request,
        pk=None,
    ):

        conversation = self.get_object()

        q = request.GET.get(
            "q",
            "",
        )

        messages = conversation.messages.filter(
            text__icontains=q,
        )

        serializer = MessageSerializer(
            messages,
            many=True,
        )

        return Response(
            serializer.data,
        )
    @action(
        detail=True,
        methods=["post"],
    )
    def archive(
        self,
        request,
        pk=None,
    ):

        conversation = self.get_object()

        conversation.is_archived = True

        conversation.save()

        return Response(
            {
                "success":True
            }
        )

    @action(
        detail=True,
        methods=["post"],
    )
    def mute(
        self,
        request,
        pk=None,
    ):

        conversation = self.get_object()

        conversation.is_muted = True

        conversation.save()

        return Response(
            {
                "success":True
            }
        )
    @action(
        detail=True,
        methods=["post"],
    )
    def star(
        self,
        request,
        pk=None,
    ):

        message = Message.objects.get(
            id=request.data["message"],
        )

        message.is_starred = True

        message.save()

        return Response(
            {
                "success":True
            }
        )