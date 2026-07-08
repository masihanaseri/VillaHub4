from django.db import models


class ConversationManager(

    models.Manager,

):

    def for_user(

        self,

        user,

    ):

        return self.filter(

            members=user,

        )