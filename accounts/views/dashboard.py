from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from orders.models import Order
from tickets.models import Ticket


@login_required
def dashboard(request):
    tickets = Ticket.objects.filter(client=request.user).select_related(
        "department", "order__service"
    )

    status = request.GET.get("status")
    if status in Ticket.Status.values:
        tickets = tickets.filter(status=status)
    else:
        status = ""

    orders = Order.objects.filter(user=request.user).select_related("service")

    context = {
        "tickets": tickets,
        "orders": orders,
        "statuses": Ticket.Status.choices,
        "current_status": status,
    }
    return render(request, "accounts/dashboard.html", context)
