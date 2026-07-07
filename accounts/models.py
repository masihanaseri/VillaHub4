from django.db import models
from django.contrib.auth.models import AbstractUser
from core.models import BaseModel
import uuid


class Role(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "نقش"
        verbose_name_plural = "نقش‌ها"


class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=150)

    roles = models.ManyToManyField(Role, related_name="permissions", blank=True)

    def __str__(self):
        return f"{self.code} - {self.title}"

    class Meta:
        verbose_name = "مجوز"
        verbose_name_plural = "مجوزها"


class User(AbstractUser):

    mobile = models.CharField(
        max_length=15,
        unique=True,
        db_index=True,
        verbose_name="شماره موبایل",
    )

    active_township = models.ForeignKey(
        "townships.Township",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="شهرک فعال"
    )

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def get_permissions(self):
        """
        دریافت مجوزهای کاربر در شهرک فعال
        مسیر: Permission -> roles (M2M) -> memberships (FK) -> user/township
        """
        if not self.active_township:
            return Permission.objects.none()

        # نقش‌هایی که کاربر در این شهرک دارد
        active_role_ids = self.memberships.filter(
            township=self.active_township,
            is_active=True
        ).values_list("role_id", flat=True)

        # مجوزهای متصل به این نقش‌ها
        return Permission.objects.filter(
            roles__id__in=active_role_ids
        ).distinct()

    def has_permission(self, code):
        return self.get_permissions().filter(code=code).exists()

    def get_active_roles(self):
        """نقش‌های فعال کاربر در شهرک جاری"""
        if not self.active_township:
            return Role.objects.none()
        return Role.objects.filter(
            memberships__user=self,
            memberships__township=self.active_township,
            memberships__is_active=True
        ).distinct()


class Membership(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    township = models.ForeignKey("townships.Township", on_delete=models.CASCADE, related_name="memberships")
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "عضویت"
        verbose_name_plural = "عضویت‌ها"
        unique_together = [("user", "township", "role")]

    def __str__(self):
        return f"{self.user.username} - {self.township} - {self.role}"


class Invitation(BaseModel):

    township = models.ForeignKey("townships.Township", on_delete=models.CASCADE, verbose_name="شهرک")
    mobile = models.CharField(
    max_length=15,
    verbose_name="شماره موبایل",
)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name="نقش")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_used = models.BooleanField(default=False, verbose_name="استفاده شده")

    class Meta:
        verbose_name = "دعوت‌نامه"
        verbose_name_plural = "دعوت‌نامه‌ها"

    def __str__(self):
        return f"{self.mobile} -> {self.township}"
