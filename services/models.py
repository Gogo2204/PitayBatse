from django.db import models


class Service(models.Model):
    class ServiceType(models.TextChoices):
        ONE_TIME = "one_time", "Еднократна"
        SUBSCRIPTION = "subscription", "Абонамент"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    service_type = models.CharField(
        max_length=20,
        choices=ServiceType.choices,
        default=ServiceType.ONE_TIME,
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        related_name="services",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_subscription(self):
        return self.service_type == self.ServiceType.SUBSCRIPTION
