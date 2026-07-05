from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from departments.models import Department
from logs.models import ActivityLog
from orders.models import Order
from services.models import Service

User = get_user_model()

CARD_NUMBER = "4242424242424242"
CARD_NAME = "Ivan Testov"


class CardPaymentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="Плащане отдел", slug="plashtane")
        cls.service = Service.objects.create(
            name="Услуга за плащане",
            service_type=Service.ServiceType.ONE_TIME,
            price="30.00",
            department=cls.department,
        )
        cls.user = User.objects.create_user(username="platec", password="Baceparola123")

    def setUp(self):
        self.client.force_login(self.user)

    def _card_order(self):
        return Order.objects.create(
            user=self.user,
            service=self.service,
            amount=self.service.price,
            payment_method=Order.PaymentMethod.CARD,
        )

    def _valid_card(self, **overrides):
        data = {
            "card_name": CARD_NAME,
            "card_number": "4242 4242 4242 4242",
            "expiry": "12/40",
            "cvv": "123",
        }
        data.update(overrides)
        return data

    def test_card_form_shown_for_card_orders(self):
        order = self._card_order()
        response = self.client.get(reverse("orders:pay", args=[order.pk]))
        self.assertContains(response, "Номер на картата")
        self.assertContains(response, "Демо режим")

    def test_valid_card_marks_order_paid(self):
        order = self._card_order()
        response = self.client.post(
            reverse("orders:pay", args=[order.pk]), self._valid_card()
        )
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertIsNotNone(order.paid_at)
        self.assertRedirects(response, reverse("tickets:create", args=[order.pk]))

    def test_success_message_carried_through_redirect(self):
        order = self._card_order()
        response = self.client.post(
            reverse("orders:pay", args=[order.pk]), self._valid_card(), follow=True
        )
        stored = list(response.context["messages"])
        self.assertEqual(len(stored), 1)
        self.assertIn("Плащането мина, баце", str(stored[0]))

    def test_invalid_card_number_blocks_payment(self):
        order = self._card_order()
        response = self.client.post(
            reverse("orders:pay", args=[order.pk]),
            self._valid_card(card_number="1234 5678"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "16 цифри")
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_past_expiry_blocks_payment(self):
        order = self._card_order()
        response = self.client.post(
            reverse("orders:pay", args=[order.pk]), self._valid_card(expiry="01/20")
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_invalid_expiry_month_blocks_payment(self):
        order = self._card_order()
        response = self.client.post(
            reverse("orders:pay", args=[order.pk]), self._valid_card(expiry="13/40")
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_invalid_cvv_blocks_payment(self):
        order = self._card_order()
        response = self.client.post(
            reverse("orders:pay", args=[order.pk]), self._valid_card(cvv="12")
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_card_data_is_not_persisted_or_logged(self):
        order = self._card_order()
        self.client.post(reverse("orders:pay", args=[order.pk]), self._valid_card())
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)

        self.assertNotIn(CARD_NUMBER, str(order.__dict__))
        self.assertFalse(
            ActivityLog.objects.filter(description__icontains=CARD_NUMBER).exists()
        )
        self.assertFalse(
            ActivityLog.objects.filter(description__icontains=CARD_NAME).exists()
        )
