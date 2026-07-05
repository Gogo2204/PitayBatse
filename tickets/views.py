from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from departments.models import Department
from logs.models import ActivityLog
from orders.models import Order

from .forms import ExpertReplyForm, ReplyForm, TicketCreateForm
from .models import Attachment, Credential, Message, Ticket
from .services import (
    TicketWorkflowError,
    add_message,
    assign_main_expert,
    change_status,
    is_expert,
    resolve,
)


def build_form_notices(order):
    notices = []
    if order.service.is_subscription:
        notices.append(
            "Това е абонаментна услуга с период на таксуване "
            f"„{order.get_billing_cycle_display()}“."
        )
    return notices


def visible_tickets(user):
    if user.is_superuser:
        return Ticket.objects.all()
    criteria = Q(client_id=user.id)
    if is_expert(user) and user.department_id is not None:
        criteria |= Q(department_id=user.department_id)
    return Ticket.objects.filter(criteria)


def _can_access(user, ticket):
    return visible_tickets(user).filter(pk=ticket.pk).exists()


@login_required
def index(request):
    tickets = visible_tickets(request.user).select_related(
        "order__service", "department"
    )
    return render(request, "tickets/ticket_list.html", {"tickets": tickets})


@login_required
def create(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)

    if order.status != Order.Status.PAID:
        return redirect("orders:pay", order_id=order.pk)

    if hasattr(order, "ticket"):
        return redirect("tickets:detail", public_id=order.ticket.public_id)

    if request.method == "POST":
        form = TicketCreateForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            with transaction.atomic():
                ticket = Ticket.objects.create(
                    name=data["name"],
                    order=order,
                    client=request.user,
                    department=order.service.department,
                    status=Ticket.Status.OPEN,
                    deadline=data.get("deadline"),
                )
                Credential.objects.create(
                    ticket=ticket,
                    site_admin_url=data.get("site_admin_url", ""),
                    site_username=data.get("site_username", ""),
                    site_password=data.get("site_password", ""),
                    hosting_username=data.get("hosting_username", ""),
                    hosting_password=data.get("hosting_password", ""),
                )
                message = Message.objects.create(
                    ticket=ticket,
                    author=request.user,
                    body=data["description"],
                )
                for uploaded in data.get("attachments", []):
                    Attachment.objects.create(
                        ticket=ticket,
                        message=message,
                        uploaded_by=request.user,
                        file=uploaded,
                    )
                ticket.last_message_at = message.created_at
                ticket.save(update_fields=["last_message_at"])
            return redirect("tickets:detail", public_id=ticket.public_id)
    else:
        form = TicketCreateForm()

    context = {
        "form": form,
        "order": order,
        "service": order.service,
        "notices": build_form_notices(order),
    }
    return render(request, "tickets/ticket_form.html", context)


@login_required
def detail(request, public_id):
    ticket = get_object_or_404(
        Ticket.objects.select_related("client", "department", "main_expert"),
        public_id=public_id,
    )
    if not _can_access(request.user, ticket):
        raise Http404

    expert_view = is_expert(request.user)
    is_assigned_expert = expert_view and ticket.main_expert_id == request.user.id
    reply_form = ExpertReplyForm() if expert_view else ReplyForm()
    error = None
    reveal_credentials = False

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "reply":
                form_class = ExpertReplyForm if expert_view else ReplyForm
                reply_form = form_class(request.POST, request.FILES)
                if reply_form.is_valid():
                    data = reply_form.cleaned_data
                    is_internal = expert_view and data.get("is_internal", False)
                    with transaction.atomic():
                        message = add_message(
                            ticket, request.user, data["body"], is_internal=is_internal
                        )
                        for uploaded in data.get("attachments", []):
                            Attachment.objects.create(
                                ticket=ticket,
                                message=message,
                                uploaded_by=request.user,
                                file=uploaded,
                            )
                    return redirect("tickets:detail", public_id=ticket.public_id)
            elif action == "resolve":
                resolve(ticket, request.user)
                return redirect("tickets:detail", public_id=ticket.public_id)
            elif action == "assign" and expert_view:
                if ticket.main_expert_id is None:
                    assign_main_expert(ticket, request.user, actor=request.user)
                return redirect("tickets:detail", public_id=ticket.public_id)
            elif action == "status" and expert_view:
                change_status(
                    ticket,
                    request.POST.get("status"),
                    actor=request.user,
                    reason="Ръчна промяна на статуса.",
                )
                return redirect("tickets:detail", public_id=ticket.public_id)
            elif action == "department" and expert_view:
                department = get_object_or_404(
                    Department, pk=request.POST.get("department")
                )
                ticket.department = department
                ticket.save(update_fields=["department"])
                return redirect("tickets:detail", public_id=ticket.public_id)
            elif action == "priority" and expert_view:
                new_priority = request.POST.get("priority")
                if new_priority in Ticket.Priority.values:
                    ticket.priority = new_priority
                    ticket.save(update_fields=["priority"])
                return redirect("tickets:detail", public_id=ticket.public_id)
            elif action == "reveal_credentials":
                if is_assigned_expert and hasattr(ticket, "credential"):
                    reveal_credentials = True
                    ActivityLog.objects.create(
                        actor=request.user,
                        action="credential_revealed",
                        ticket=ticket,
                        description=f"Разкрити достъпи за тикет „{ticket.name}“.",
                    )
                else:
                    raise Http404
        except TicketWorkflowError as exc:
            error = str(exc)

    public_messages = (
        ticket.messages.filter(is_internal=False)
        .select_related("author")
        .prefetch_related("attachments")
    )
    internal_messages = (
        ticket.messages.filter(is_internal=True)
        .select_related("author")
        .prefetch_related("attachments")
        if expert_view
        else []
    )

    context = {
        "ticket": ticket,
        "expert_view": expert_view,
        "is_assigned_expert": is_assigned_expert,
        "is_resolved": ticket.status == Ticket.Status.RESOLVED,
        "public_messages": public_messages,
        "internal_messages": internal_messages,
        "reply_form": reply_form,
        "error": error,
        "credential": getattr(ticket, "credential", None),
        "reveal_credentials": reveal_credentials,
        "statuses": Ticket.Status.choices,
        "priorities": Ticket.Priority.choices,
        "departments": Department.objects.all(),
    }
    return render(request, "tickets/ticket_detail.html", context)
