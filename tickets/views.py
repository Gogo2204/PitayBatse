from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from orders.models import Order

from .forms import TicketCreateForm
from .models import Attachment, Credential, Message, Ticket


def build_form_notices(order):
    notices = []
    if order.service.is_subscription:
        notices.append(
            "Това е абонаментна услуга с период на таксуване "
            f"„{order.get_billing_cycle_display()}“."
        )
    return notices


@login_required
def create(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)

    if order.status != Order.Status.PAID:
        return redirect("orders:pay", order_id=order.pk)

    if hasattr(order, "ticket"):
        return redirect("accounts:dashboard")

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
            return redirect("accounts:dashboard")
    else:
        form = TicketCreateForm()

    context = {
        "form": form,
        "order": order,
        "service": order.service,
        "notices": build_form_notices(order),
    }
    return render(request, "tickets/ticket_form.html", context)
