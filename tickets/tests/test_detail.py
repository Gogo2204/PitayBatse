from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from departments.models import Department
from logs.models import ActivityLog
from orders.models import Order
from services.models import Service
from tickets.models import Credential, Message, Ticket

User = get_user_model()


class TicketDetailBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="Поддръжка", slug="poddrazhka")
        cls.other_department = Department.objects.create(name="Друг отдел", slug="drug")
        service = Service.objects.create(
            name="Услуга детайл",
            service_type=Service.ServiceType.ONE_TIME,
            price="30.00",
            department=cls.department,
        )
        cls.client_user = User.objects.create_user(
            username="sobstvenik",
            password="Baceparola123",
            email="owner@example.com",
            role=User.Role.CLIENT,
        )
        cls.other_client = User.objects.create_user(
            username="drugklient", password="Baceparola123", role=User.Role.CLIENT
        )
        cls.expert = User.objects.create_user(
            username="ekspert",
            password="Baceparola123",
            email="expert@example.com",
            role=User.Role.EXPERT,
            department=cls.department,
        )
        cls.other_expert = User.objects.create_user(
            username="ekspert2",
            password="Baceparola123",
            role=User.Role.EXPERT,
            department=cls.other_department,
        )
        order = Order.objects.create(
            user=cls.client_user,
            service=service,
            amount="30.00",
            payment_method=Order.PaymentMethod.CARD,
            status=Order.Status.PAID,
        )
        cls.ticket = Ticket.objects.create(
            name="Детайлен тикет",
            order=order,
            client=cls.client_user,
            department=cls.department,
        )
        cls.public_message = Message.objects.create(
            ticket=cls.ticket, author=cls.client_user, body="Публично съобщение тук"
        )
        cls.internal_message = Message.objects.create(
            ticket=cls.ticket,
            author=cls.expert,
            body="Секретна вътрешна бележка",
            is_internal=True,
        )

    def _url(self):
        return reverse("tickets:detail", args=[self.ticket.public_id])


class AccessControlTests(TicketDetailBase):
    def test_anonymous_redirected_to_login(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_owner_client_can_view(self):
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(self._url()).status_code, 200)

    def test_other_client_gets_404(self):
        self.client.force_login(self.other_client)
        self.assertEqual(self.client.get(self._url()).status_code, 404)

    def test_expert_in_department_can_view(self):
        self.client.force_login(self.expert)
        self.assertEqual(self.client.get(self._url()).status_code, 200)

    def test_expert_in_other_department_gets_404(self):
        self.client.force_login(self.other_expert)
        self.assertEqual(self.client.get(self._url()).status_code, 404)


class InternalVisibilityTests(TicketDetailBase):
    def test_client_does_not_see_internal_messages(self):
        self.client.force_login(self.client_user)
        response = self.client.get(self._url())
        self.assertContains(response, "Публично съобщение тук")
        self.assertNotContains(response, "Секретна вътрешна бележка")

    def test_expert_sees_internal_messages(self):
        self.client.force_login(self.expert)
        response = self.client.get(self._url())
        self.assertContains(response, "Публично съобщение тук")
        self.assertContains(response, "Секретна вътрешна бележка")


class ResolvedVisibilityTests(TicketDetailBase):
    def _resolve(self):
        self.ticket.status = Ticket.Status.RESOLVED
        self.ticket.save(update_fields=["status"])

    def test_client_reply_and_resolve_hidden_when_resolved(self):
        self._resolve()
        self.client.force_login(self.client_user)
        response = self.client.get(self._url())
        self.assertNotContains(response, 'name="body"')
        self.assertNotContains(response, 'value="resolve"')
        self.assertContains(response, "приключен")

    def test_reply_form_hidden_for_expert_when_resolved_but_status_control_stays(self):
        self._resolve()
        self.client.force_login(self.expert)
        response = self.client.get(self._url())
        self.assertNotContains(response, 'name="body"')
        self.assertContains(response, "приключен")
        self.assertContains(response, "Смени статуса")

    def test_client_cannot_post_on_resolved_ticket(self):
        self._resolve()
        self.client.force_login(self.client_user)
        self.client.post(self._url(), {"action": "reply", "body": "След затваряне"})
        self.assertFalse(
            Message.objects.filter(ticket=self.ticket, body="След затваряне").exists()
        )

    def test_expert_cannot_post_on_resolved_ticket(self):
        self._resolve()
        self.ticket.main_expert = self.expert
        self.ticket.save(update_fields=["main_expert"])
        self.client.force_login(self.expert)
        self.client.post(
            self._url(),
            {"action": "reply", "body": "Експертна бележка", "is_internal": "on"},
        )
        self.assertFalse(
            Message.objects.filter(
                ticket=self.ticket, body="Експертна бележка"
            ).exists()
        )

    def test_expert_can_post_after_reopening(self):
        self._resolve()
        self.client.force_login(self.expert)
        self.client.post(
            self._url(), {"action": "status", "status": Ticket.Status.IN_PROGRESS}
        )
        self.client.post(self._url(), {"action": "reply", "body": "Пак работим"})
        self.assertTrue(
            Message.objects.filter(ticket=self.ticket, body="Пак работим").exists()
        )


class ExpertActionTests(TicketDetailBase):
    def test_client_reply_creates_public_message(self):
        self.client.force_login(self.client_user)
        self.client.post(
            self._url(), {"action": "reply", "body": "Клиентски отговор"}
        )
        self.assertTrue(
            Message.objects.filter(
                ticket=self.ticket, body="Клиентски отговор", is_internal=False
            ).exists()
        )

    def test_expert_can_post_internal_note(self):
        self.client.force_login(self.expert)
        self.client.post(
            self._url(),
            {"action": "reply", "body": "Нова бележка", "is_internal": "on"},
        )
        self.assertTrue(
            Message.objects.filter(
                ticket=self.ticket, body="Нова бележка", is_internal=True
            ).exists()
        )

    def test_expert_assign_self_sets_in_progress(self):
        self.client.force_login(self.expert)
        self.client.post(self._url(), {"action": "assign"})
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.main_expert, self.expert)
        self.assertEqual(self.ticket.status, Ticket.Status.IN_PROGRESS)

    def test_assign_form_hidden_once_claimed(self):
        self.ticket.main_expert = self.expert
        self.ticket.save(update_fields=["main_expert"])
        self.client.force_login(self.expert)
        response = self.client.get(self._url())
        self.assertNotContains(response, 'value="assign"')
        self.assertContains(response, "Води го")

    def test_second_expert_cannot_reassign_claimed_ticket(self):
        self.ticket.main_expert = self.expert
        self.ticket.save(update_fields=["main_expert"])
        second_expert = User.objects.create_user(
            username="ekspert3",
            password="Baceparola123",
            role=User.Role.EXPERT,
            department=self.department,
        )
        self.client.force_login(second_expert)
        self.client.post(self._url(), {"action": "assign"})
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.main_expert, self.expert)

    def test_expert_change_priority(self):
        self.client.force_login(self.expert)
        self.client.post(
            self._url(), {"action": "priority", "priority": Ticket.Priority.HIGH}
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.priority, Ticket.Priority.HIGH)

    def test_client_cannot_use_expert_actions(self):
        self.client.force_login(self.client_user)
        self.client.post(self._url(), {"action": "assign"})
        self.ticket.refresh_from_db()
        self.assertIsNone(self.ticket.main_expert)


class CredentialRevealTests(TicketDetailBase):
    def setUp(self):
        self.ticket.main_expert = self.expert
        self.ticket.save(update_fields=["main_expert"])
        self.credential = Credential.objects.create(
            ticket=self.ticket,
            site_admin_url="https://example.com/wp-admin",
            site_username="siteuser",
            site_password="s1te-secret-parola",
            hosting_username="hostuser",
            hosting_password="host-secret-parola",
        )

    def test_credentials_hidden_by_default(self):
        self.client.force_login(self.expert)
        response = self.client.get(self._url())
        self.assertNotContains(response, "s1te-secret-parola")
        self.assertContains(response, "Виж тайните")

    def test_assigned_expert_can_reveal_and_it_is_logged(self):
        self.client.force_login(self.expert)
        response = self.client.post(self._url(), {"action": "reveal_credentials"})
        self.assertContains(response, "s1te-secret-parola")
        self.assertContains(response, "host-secret-parola")
        self.assertTrue(
            ActivityLog.objects.filter(
                action="credential_revealed", ticket=self.ticket, actor=self.expert
            ).exists()
        )

    def test_client_cannot_reveal_credentials(self):
        self.client.force_login(self.client_user)
        response = self.client.post(self._url(), {"action": "reveal_credentials"})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            ActivityLog.objects.filter(action="credential_revealed").exists()
        )

    def test_unassigned_expert_cannot_reveal_credentials(self):
        other_expert = User.objects.create_user(
            username="nenaznachen",
            password="Baceparola123",
            role=User.Role.EXPERT,
            department=self.department,
        )
        self.client.force_login(other_expert)
        response = self.client.post(self._url(), {"action": "reveal_credentials"})
        self.assertEqual(response.status_code, 404)
