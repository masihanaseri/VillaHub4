from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .permissions import HasPermission
from .models import Invitation, User, Membership
from .serializers import InvitationSerializer


class SetActiveTownshipView(APIView):
    """
    تغییر شهرک فعال کاربر
    """

    permission_classes = [IsAuthenticated, HasPermission]


    def post(self, request):

        township_id = request.data.get("township_id")

        if not township_id:
            return Response(
                {"error": "township_id الزامی است"},
                status=400,
            )

        membership = request.user.memberships.filter(
            township_id=township_id,
            is_active=True,
        ).select_related("township").first()

        if not membership:
            return Response(
                {"error": "دسترسی به این شهرک وجود ندارد"},
                status=403,
            )

        request.user.active_township = membership.township
        request.user.save(update_fields=["active_township"])

        return Response(
            {
                "message": "شهرک فعال تغییر کرد.",
                "township": {
                    "id": membership.township.id,
                    "name": membership.township.name,
                    "code": membership.township.code,
                },
            }
        )


class SignupView(APIView):
    """
    ثبت نام عمومی غیرفعال است.
    """

    permission_classes = [AllowAny]

    def post(self, request):

        return Response(
            {
                "error": "ثبت نام عمومی غیرفعال است. لطفاً از لینک دعوت استفاده کنید."
            },
            status=403,
        )


class CreateInvitationView(APIView):
    """
    ایجاد دعوت نامه
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):

        township = request.user.active_township

        if not township:
            return Response(
                {
                    "error": "ابتدا شهرک فعال را انتخاب کنید."
                },
                status=400,
            )

        if not request.user.has_permission("CREATE_INVITATION"):
            return Response(
                {
                    "error": "شما مجوز ایجاد دعوت نامه ندارید."
                },
                status=403,
            )

        serializer = InvitationSerializer(
            data=request.data,
            context={
                "township": township,
            },
        )

        serializer.is_valid(raise_exception=True)

        invitation = serializer.save()

        return Response(
            {
                "message": "دعوت نامه ایجاد شد.",
                "token": str(invitation.token),
                "invite_link": f"/invite/{invitation.token}",
            },
            status=201,
        )


class AcceptInviteView(APIView):
    """
    پذیرش دعوت نامه
    """

    permission_classes = [AllowAny]

    def post(self, request, token):

        invitation = Invitation.objects.filter(
            token=token,
            is_used=False,
        ).select_related(
            "township",
            "role",
        ).first()

        if not invitation:
            return Response(
                {
                    "error": "دعوت نامه معتبر نیست یا قبلاً استفاده شده است."
                },
                status=404,
            )

        mobile = request.data.get("mobile")
        username = request.data.get("username")
        password = request.data.get("password")

        if not all([mobile, username, password]):
            return Response(
                {
                    "error": "mobile ، username و password الزامی هستند."
                },
                status=400,
            )

        if invitation.mobile != mobile:
            return Response(
                {
                    "error": "شماره موبایل با دعوت نامه مطابقت ندارد."
                },
                status=403,
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {
                    "error": "این نام کاربری قبلاً ثبت شده است."
                },
                status=400,
            )

        if User.objects.filter(mobile=mobile).exists():
            return Response(
                {
                    "error": "این شماره موبایل قبلاً ثبت شده است."
                },
                status=400,
            )

        user = User.objects.create_user(
            username=username,
            mobile=mobile,
            password=password,
        )

        Membership.objects.create(
            user=user,
            township=invitation.township,
            role=invitation.role,
        )

        user.active_township = invitation.township
        user.save(update_fields=["active_township"])

        invitation.is_used = True
        invitation.save(update_fields=["is_used"])

        return Response(
            {
                "message": "حساب کاربری با موفقیت ایجاد شد.",
                "username": user.username,
            },
            status=201,
        )