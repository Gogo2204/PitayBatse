from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from services.models import Service


class Order(models.Model):
    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Месечно"
        QUARTERLY = "quarterly", "Тримесечно"
        YEARLY = "yearly", "Годишно"

    class PaymentMethod(models.TextChoices):
        CARD = "card", "Карта"
        PAYPAL = "paypal", "PayPal"
        EPAY = "epay", "ePay"

    class Status(models.TextChoices):
        PENDING = "pending", "Чакащо"
        PAID = "paid", "Платено"
        FAILED = "failed", "Неуспешно"
        CANCELLED = "cancelled", "Отказано"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    billing_cycle = models.CharField(
        max_length=20,
        choices=BillingCycle.choices,
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Поръчка #{self.pk} - {self.service}"

    def clean(self):
        super().clean()
        if self.service_id:
            if self.service.is_subscription and not self.billing_cycle:
                raise ValidationError(
                    {"billing_cycle": "Абонаментната услуга изисква период на таксуване."}
                )
            if not self.service.is_subscription and self.billing_cycle:
                raise ValidationError(
                    {"billing_cycle": "Еднократната услуга не може да има период на таксуване."}
                )

    def mark_paid(self):
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "paid_at"])
