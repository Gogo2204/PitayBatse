from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from departments.models import Department
from logs.models import ActivityLog
from orders.models import Order
from services.models import Service
from tickets.models import Ticket

User = get_user_model()

STAFF_URL_NAMES = [
    "staff:tickets",
    "staff:users",
    "staff:orders",
    "staff:departments",
    "staff:logs",
]


class StaffBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dept_x = Department.objects.create(name="Отдел Х", slug="otdel-x")
        cls.dept_y = Department.objects.create(name="Отдел Y", slug="otdel-y")
        cls.service_x = Service.objects.create(
            name="Услуга Х",
            service_type=Service.ServiceType.ONE_TIME,
            price="10.00",
            department=cls.dept_x,
        )
        cls.service_y = Service.objects.create(
            name="Услуга Y",
            service_type=Service.ServiceType.ONE_TIME,
            price="10.00",
            department=cls.dept_y,
        )
        cls.client_user = User.objects.create_user(
            username="klientfix", password="Baceparola123", role=User.Role.CLIENT
        )
        cls.expert_x = User.objects.create_user(
            username="ekspertx",
            password="Baceparola123",
            role=User.Role.EXPERT,
            department=cls.dept_x,
        )
        cls.superuser = User.objects.create_superuser(
            username="admin", password="Baceparola123"
        )
        cls.ticket_x = cls._ticket(cls.service_x, cls.dept_x, "Тикет в Х")
        cls.ticket_y = cls._ticket(cls.service_y, cls.dept_y, "Тикет в Y")

    @classmethod
    def _ticket(cls, service, department, name):
        order = Order.objects.create(
            user=cls.client_user,
            service=service,
            amount=service.price,
            payment_method=Order.PaymentMethod.CARD,
            status=Order.Status.PAID,
        )
        return Ticket.objects.create(
            name=name, order=order, client=cls.client_user, department=department
        )


class PermissionBoundaryTests(StaffBase):
    def test_anonymous_redirected_to_login(self):
        for name in STAFF_URL_NAMES:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn(reverse("accounts:login"), response.url, name)

    def test_client_gets_403(self):
        self.client.force_login(self.client_user)
        for name in STAFF_URL_NAMES:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 403, name)

    def test_expert_gets_200(self):
        self.client.force_login(self.expert_x)
        for name in STAFF_URL_NAMES:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)

    def test_superuser_gets_200(self):
        self.client.force_login(self.superuser)
        for name in STAFF_URL_NAMES:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)


class TicketScopeTests(StaffBase):
    def test_expert_sees_only_own_department_tickets(self):
        self.client.force_login(self.expert_x)
        response = self.client.get(reverse("staff:tickets"))
        self.assertContains(response, "Тикет в Х")
        self.assertNotContains(response, "Тикет в Y")

    def test_superuser_sees_all_department_tickets(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("staff:tickets"))
        self.assertContains(response, "Тикет в Х")
        self.assertContains(response, "Тикет в Y")

    def test_unassigned_open_ticket_is_highlighted(self):
        self.client.force_login(self.expert_x)
        response = self.client.get(reverse("staff:tickets"))
        self.assertContains(response, "unassigned")


class UserManagementTests(StaffBase):
    def _promote_url(self, user):
        return reverse("staff:promote_user", args=[user.id])

    def _department_url(self, user):
        return reverse("staff:set_department", args=[user.id])

    def test_only_superuser_sees_promote_button(self):
        self.client.force_login(self.expert_x)
        expert_response = self.client.get(reverse("staff:users"))
        self.assertNotContains(expert_response, "Направи пустиняк")

        self.client.force_login(self.superuser)
        super_response = self.client.get(reverse("staff:users"))
        self.assertContains(super_response, "Направи пустиняк")

    def test_superuser_role_renders_as_admin(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("staff:users"))
        self.assertContains(response, "Админ")
        self.assertNotContains(response, "(админ)")
        self.assertContains(response, "Експерт")
        self.assertContains(response, "Клиент")

    def test_expert_gets_403_on_promote_endpoint(self):
        self.client.force_login(self.expert_x)
        response = self.client.post(
            self._promote_url(self.client_user), {"department": self.dept_x.pk}
        )
        self.assertEqual(response.status_code, 403)
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.role, User.Role.CLIENT)

    def test_expert_gets_403_on_set_department_endpoint(self):
        self.client.force_login(self.expert_x)
        response = self.client.post(
            self._department_url(self.expert_x), {"department": self.dept_y.pk}
        )
        self.assertEqual(response.status_code, 403)

    def test_promotion_requires_department(self):
        self.client.force_login(self.superuser)
        response = self.client.post(self._promote_url(self.client_user), {})
        self.assertEqual(response.status_code, 400)
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.role, User.Role.CLIENT)
        self.assertIsNone(self.client_user.department)

    def test_superuser_promotes_client_and_logs(self):
        self.client.force_login(self.superuser)
        response = self.client.post(
            self._promote_url(self.client_user), {"department": self.dept_x.pk}
        )
        self.assertRedirects(response, reverse("staff:users"))
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.role, User.Role.EXPERT)
        self.assertEqual(self.client_user.department, self.dept_x)
        self.assertTrue(
            ActivityLog.objects.filter(
                actor=self.superuser, action="user_promoted"
            ).exists()
        )

    def test_superuser_changes_expert_department_and_logs(self):
        self.client.force_login(self.superuser)
        response = self.client.post(
            self._department_url(self.expert_x), {"department": self.dept_y.pk}
        )
        self.assertRedirects(response, reverse("staff:users"))
        self.expert_x.refresh_from_db()
        self.assertEqual(self.expert_x.department, self.dept_y)
        self.assertTrue(
            ActivityLog.objects.filter(
                actor=self.superuser, action="department_changed"
            ).exists()
        )
