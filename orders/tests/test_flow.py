from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from departments.models import Department
from orders.models import Order
from services.models import Service

User = get_user_model()


class OrderFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        department = Department.objects.create(name="Поток отдел", slug="potok-otdel")
        cls.one_time = Service.objects.create(
            name="Еднократна за поток",
            service_type=Service.ServiceType.ONE_TIME,
            price="99.00",
            department=department,
        )
        cls.subscription = Service.objects.create(
            name="Абонамент за поток",
            service_type=Service.ServiceType.SUBSCRIPTION,
            price="15.00",
            department=department,
        )
        cls.user = User.objects.create_user(username="ivan", password="Baceparola123")

    def setUp(self):
        self.client.force_login(self.user)

    def test_order_create_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("orders:create", args=[self.one_time.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_one_time_order_creates_pending_and_redirects_to_payment(self):
        response = self.client.post(
            reverse("orders:create", args=[self.one_time.pk]),
            {"payment_method": Order.PaymentMethod.CARD},
        )
        order = Order.objects.get(service=self.one_time, user=self.user)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertIsNone(order.billing_cycle)
        self.assertEqual(order.amount, Decimal(self.one_time.price))
        self.assertRedirects(response, reverse("orders:pay", args=[order.pk]))

    def test_subscription_order_without_billing_cycle_shows_error(self):
        response = self.client.post(
            reverse("orders:create", args=[self.subscription.pk]),
            {"payment_method": Order.PaymentMethod.PAYPAL},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("billing_cycle", response.context["form"].errors)
        self.assertFalse(Order.objects.filter(service=self.subscription).exists())

    def test_subscription_order_with_billing_cycle_succeeds(self):
        response = self.client.post(
            reverse("orders:create", args=[self.subscription.pk]),
            {
                "billing_cycle": Order.BillingCycle.YEARLY,
                "payment_method": Order.PaymentMethod.EPAY,
            },
        )
        order = Order.objects.get(service=self.subscription, user=self.user)
        self.assertEqual(order.billing_cycle, Order.BillingCycle.YEARLY)
        self.assertRedirects(response, reverse("orders:pay", args=[order.pk]))

    def test_payment_marks_order_paid_and_redirects_to_ticket(self):
        order = Order.objects.create(
            user=self.user,
            service=self.one_time,
            amount=self.one_time.price,
            payment_method=Order.PaymentMethod.CARD,
        )
        response = self.client.post(reverse("orders:pay", args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertIsNotNone(order.paid_at)
        self.assertRedirects(response, reverse("tickets:create", args=[order.pk]))

    def test_user_cannot_pay_another_users_order(self):
        other = User.objects.create_user(username="drug", password="Baceparola123")
        order = Order.objects.create(
            user=other,
            service=self.one_time,
            amount=self.one_time.price,
            payment_method=Order.PaymentMethod.CARD,
        )
        response = self.client.post(reverse("orders:pay", args=[order.pk]))
        self.assertEqual(response.status_code, 404)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)
