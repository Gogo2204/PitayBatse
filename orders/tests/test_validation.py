from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from departments.models import Department
from orders.models import Order
from services.models import Service

User = get_user_model()


class BillingCycleValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        department = Department.objects.create(name="Тест отдел", slug="test-otdel")
        cls.one_time = Service.objects.create(
            name="Еднократна услуга",
            service_type=Service.ServiceType.ONE_TIME,
            price="50.00",
            department=department,
        )
        cls.subscription = Service.objects.create(
            name="Абонамент услуга",
            service_type=Service.ServiceType.SUBSCRIPTION,
            price="20.00",
            department=department,
        )
        cls.user = User.objects.create_user(username="pesho", password="Baceparola123")

    def _order(self, service, billing_cycle=None):
        return Order(
            user=self.user,
            service=service,
            billing_cycle=billing_cycle,
            amount=service.price,
            payment_method=Order.PaymentMethod.CARD,
        )

    def test_subscription_requires_billing_cycle(self):
        with self.assertRaises(ValidationError) as ctx:
            self._order(self.subscription).full_clean()
        self.assertIn("billing_cycle", ctx.exception.message_dict)

    def test_subscription_with_billing_cycle_is_valid(self):
        self._order(self.subscription, Order.BillingCycle.MONTHLY).full_clean()

    def test_one_time_rejects_billing_cycle(self):
        with self.assertRaises(ValidationError) as ctx:
            self._order(self.one_time, Order.BillingCycle.YEARLY).full_clean()
        self.assertIn("billing_cycle", ctx.exception.message_dict)

    def test_one_time_without_billing_cycle_is_valid(self):
        self._order(self.one_time).full_clean()
