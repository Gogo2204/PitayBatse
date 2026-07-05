from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string

from logs.models import ActivityLog

from .models import Message, Ticket

User = get_user_model()

Status = Ticket.Status

ALLOWED_TRANSITIONS = {
    Status.OPEN: {
        Status.IN_PROGRESS,
        Status.WAITING_REPLY,
        Status.CLIENT_REPLIED,
        Status.RESOLVED,
    },
    Status.IN_PROGRESS: {
        Status.OPEN,
        Status.WAITING_REPLY,
        Status.CLIENT_REPLIED,
        Status.RESOLVED,
    },
    Status.WAITING_REPLY: {
        Status.OPEN,
        Status.IN_PROGRESS,
        Status.CLIENT_REPLIED,
        Status.RESOLVED,
    },
    Status.CLIENT_REPLIED: {
        Status.IN_PROGRESS,
        Status.WAITING_REPLY,
        Status.RESOLVED,
    },
    Status.RESOLVED: {
        Status.IN_PROGRESS,
        Status.WAITING_REPLY,
    },
}


class TicketWorkflowError(Exception):
    pass


class InvalidTransition(TicketWorkflowError):
    pass


class ResolvedTicketError(TicketWorkflowError):
    pass


def is_expert(user):
    if user is None:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return getattr(user, "role", None) == User.Role.EXPERT


def _guard_resolved(ticket, actor):
    if ticket.status == Status.RESOLVED and not is_expert(actor):
        raise ResolvedTicketError(
            "Клиент не може да извършва действия по приключен тикет."
        )


def _log(ticket, actor, action, description):
    ActivityLog.objects.create(
        actor=actor, action=action, description=description, ticket=ticket
    )


def _notify_client(ticket, old_status, new_status, reason):
    email = (ticket.client.email or "").strip()
    if not email:
        return
    body = render_to_string(
        "tickets/emails/status_change.txt",
        {
            "ticket_name": ticket.name,
            "old_status": Status(old_status).label,
            "new_status": Status(new_status).label,
            "reason": reason,
        },
    )
    send_mail(
        f"Тикет „{ticket.name}“ - промяна на статуса",
        body,
        settings.DEFAULT_FROM_EMAIL,
        [email],
    )


def change_status(ticket, new_status, actor=None, reason=""):
    if new_status not in Status.values:
        raise InvalidTransition(f"Непознат статус: {new_status}.")

    _guard_resolved(ticket, actor)

    old_status = ticket.status
    if new_status not in ALLOWED_TRANSITIONS.get(old_status, set()):
        raise InvalidTransition(
            f"Невалиден преход от „{Status(old_status).label}“ "
            f"към „{Status(new_status).label}“."
        )

    ticket.status = new_status
    ticket.save(update_fields=["status"])

    description = f"Статус: „{Status(old_status).label}“ → „{Status(new_status).label}“."
    if reason:
        description = f"{description} {reason}"
    _log(ticket, actor, "status_change", description)
    _notify_client(ticket, old_status, new_status, reason)
    return ticket


def assign_main_expert(ticket, expert, actor=None):
    _guard_resolved(ticket, actor or expert)

    ticket.main_expert = expert
    ticket.save(update_fields=["main_expert"])

    if ticket.status != Status.IN_PROGRESS:
        change_status(
            ticket,
            Status.IN_PROGRESS,
            actor=actor or expert,
            reason="Роди се пустиняк.",
        )
    return ticket


def add_message(ticket, author, body, is_internal=False):
    _guard_resolved(ticket, author)

    message = Message.objects.create(
        ticket=ticket, author=author, body=body, is_internal=is_internal
    )

    if not is_internal:
        ticket.last_message_at = message.created_at
        ticket.save(update_fields=["last_message_at"])

        target = Status.WAITING_REPLY if is_expert(author) else Status.CLIENT_REPLIED
        if target != ticket.status:
            change_status(ticket, target, actor=author, reason="Ново съобщение.")

    return message


def resolve(ticket, actor):
    return change_status(
        ticket, Status.RESOLVED, actor=actor, reason="Тикетът е приключен."
    )
