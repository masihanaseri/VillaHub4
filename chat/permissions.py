from rest_framework.permissions import BasePermission


class IsConversationMember(BasePermission):

    def has_object_permission(

        self,

        request,

        view,

        obj,

    ):

        return obj.members.filter(

            id=request.user.id,

        ).exists()