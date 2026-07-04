from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = "client", "Клиент"
        EXPERT = "expert", "Експерт"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT,
    )
    department = models.ForeignKey(
        "departments.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="experts",
    )

    def clean(self):
        super().clean()
        if self.role == self.Role.EXPERT and self.department is None:
            raise ValidationError(
                {"department": "Експертът трябва да принадлежи към отдел."}
            )
