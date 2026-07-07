from django.utils import timezone

from rest_framework import viewsets

from rest_framework.decorators import action

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from .models import Visitor

from .serializers import VisitorSerializer

from .services import VisitorService


class VisitorViewSet(viewsets.ModelViewSet):

    serializer_class = VisitorSerializer

    permission_classes = [

        IsAuthenticated,

    ]

    def get_queryset(self):

        township = self.request.user.active_township

        if township is None:

            return Visitor.objects.none()

        return (

            Visitor.objects.filter(

                township=township,

            )

            .select_related(

                "township",

                "residence",

                "residence__villa",

                "residence__user",

                "created_by",

                "approved_by",

            )

            .prefetch_related(

                "vehicles",

                "logs",

            )

            .order_by(

                "-created_at",

            )

        )

    def get_serializer_context(self):

        context = super().get_serializer_context()

        context["township"] = (

            self.request.user.active_township

        )

        return context

    @action(

        detail=True,

        methods=["post"],

    )

    def approve(

        self,

        request,

        pk=None,

    ):

        visitor = self.get_object()

        VisitorService.approve(

            visitor=visitor,

            approved_by=request.user,

        )

        visitor.refresh_from_db()

        serializer = self.get_serializer(

            visitor,

        )

        return Response(

            serializer.data,

        )
    
    @action(

        detail=True,

        methods=["post"],

    )

    def reject(

        self,

        request,

        pk=None,

    ):

        visitor = self.get_object()

        VisitorService.reject(

            visitor=visitor,

            rejected_by=request.user,

            reason=request.data.get(

                "reason",

                "",

            ),

        )

        visitor.refresh_from_db()

        serializer = self.get_serializer(

            visitor,

        )

        return Response(

            serializer.data,

        )
    
    @action(

        detail=True,

        methods=["post"],

    )

    def cancel(

        self,

        request,

        pk=None,

    ):

        visitor = self.get_object()

        VisitorService.cancel(

            visitor=visitor,

            cancelled_by=request.user,

            reason=request.data.get(

                "reason",

                "",

            ),

        )

        visitor.refresh_from_db()

        serializer = self.get_serializer(

            visitor,

        )

        return Response(

            serializer.data,

        )
    
    @action(

        detail=True,

        methods=["post"],

    )

    def checkin(

        self,

        request,

        pk=None,

    ):

        visitor = self.get_object()

        VisitorService.check_in(

            visitor,

        )

        visitor.refresh_from_db()

        serializer = self.get_serializer(

            visitor,

        )

        return Response(

            serializer.data,

        )
    
    @action(

        detail=True,

        methods=["post"],

    )

    def checkout(

        self,

        request,

        pk=None,

    ):

        visitor = self.get_object()

        VisitorService.check_out(

            visitor,

        )

        visitor.refresh_from_db()

        serializer = self.get_serializer(

            visitor,

        )

        return Response(

            serializer.data,

        )
    
    @action(

        detail=True,

        methods=["post"],

    )

    def add_vehicle(

        self,

        request,

        pk=None,

    ):

        visitor = self.get_object()

        plate_number = request.data.get("plate_number")

        if not plate_number:

            return Response(

                {"plate_number": ["پلاک خودرو الزامی است."]},

                status=400,

            )

        VisitorService.add_vehicle(

            visitor=visitor,

            plate_number=plate_number,

            car_model=request.data.get("car_model", ""),

            color=request.data.get("color", ""),

        )

        visitor.refresh_from_db()

        serializer = self.get_serializer(

            visitor,

        )

        return Response(

            serializer.data,

        )

    @action(

        detail=False,

        methods=["get"],

    )

    def today(

        self,

        request,

    ):

        queryset = self.get_queryset().filter(

            valid_from__date=timezone.localdate(),

        )

        serializer = self.get_serializer(

            queryset,

            many=True,

        )

        return Response(

            serializer.data,

        )
    
    @action(

        detail=False,

        methods=["get"],

    )

    def active(

        self,

        request,

    ):

        queryset = self.get_queryset().filter(

            status="CHECKED_IN",

        )

        serializer = self.get_serializer(

            queryset,

            many=True,

        )

        return Response(

            serializer.data,

        )
    
    @action(

        detail=False,

        methods=["get"],

    )

    def history(

        self,

        request,

    ):

        queryset = self.get_queryset()

        serializer = self.get_serializer(

            queryset,

            many=True,

        )

        return Response(

            serializer.data,

        )
    
