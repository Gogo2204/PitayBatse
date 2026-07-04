from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from departments.models import Department
from services.models import Service

User = get_user_model()


class ServiceListViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(
            name="Тест отдел", slug="test-otdel"
        )
        cls.active_service = Service.objects.create(
            name="Активна услуга за сайто",
            description="Показва се в списъка.",
            service_type=Service.ServiceType.ONE_TIME,
            price="10.00",
            department=cls.department,
            is_active=True,
        )
        cls.inactive_service = Service.objects.create(
            name="Скрита услуга за сайто",
            service_type=Service.ServiceType.SUBSCRIPTION,
            price="20.00",
            department=cls.department,
            is_active=False,
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("services:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_logged_in_user_sees_active_services(self):
        self.client.force_login(
            User.objects.create_user(username="client1", password="Baceparola123")
        )
        response = self.client.get(reverse("services:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Активна услуга за сайто")
        self.assertContains(response, "Поръчай")

    def test_inactive_services_are_hidden(self):
        self.client.force_login(
            User.objects.create_user(username="client2", password="Baceparola123")
        )
        response = self.client.get(reverse("services:list"))
        self.assertNotContains(response, "Скрита услуга за сайто")
