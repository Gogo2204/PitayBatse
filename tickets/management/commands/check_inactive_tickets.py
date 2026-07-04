from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from tickets.models import Ticket
from tickets.services import change_status


class Command(BaseCommand):
    help = (
        "Връща към статус „отворен“ тикетите, по които експертът е бил неактивен "
        "по-дълго от TICKET_INACTIVITY_HOURS (по подразбиране 48 часа)."
    )

    def handle(self, *args, **options):
        hours = getattr(settings, "TICKET_INACTIVITY_HOURS", 48)
        cutoff = timezone.now() - timedelta(hours=hours)

        stale = Ticket.objects.filter(
            status__in=[Ticket.Status.WAITING_REPLY, Ticket.Status.IN_PROGRESS],
            last_message_at__lt=cutoff,
        )

        reopened = 0
        for ticket in list(stale):
            change_status(
                ticket,
                Ticket.Status.OPEN,
                actor=None,
                reason="Автоматично връщане поради липса на активност от експерта.",
            )
            reopened += 1

        self.stdout.write(
            self.style.SUCCESS(f"Върнати към „отворен“: {reopened} тикет(а).")
        )
