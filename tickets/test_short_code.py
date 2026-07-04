import uuid

from django.test import TestCase

from tickets.models import Ticket


class ShortCodeTests(TestCase):
    def test_short_code_is_first_eight_hex_uppercase(self):
        public_id = uuid.UUID("1a2b3c4d-5e6f-7081-9210-abcdefabcdef")
        ticket = Ticket(name="Пробен", public_id=public_id)
        self.assertEqual(ticket.short_code, "1A2B3C4D")

    def test_short_code_length_and_case(self):
        ticket = Ticket(name="Пробен")
        self.assertEqual(len(ticket.short_code), 8)
        self.assertEqual(ticket.short_code, ticket.short_code.upper())
        self.assertEqual(ticket.short_code, ticket.public_id.hex[:8].upper())
