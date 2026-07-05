from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from orders.models import Order
from tickets.models import Ticket


@login_required
def dashboard(request):
    tickets = Ticket.objects.filter(client=request.user).select_related(
        "department", "order__service"
    )
    orders = Order.objects.filter(user=request.user).select_related("service")

    context = {
        "tickets": tickets,
        "orders": orders,
    }
    return render(request, "accounts/dashboard.html", context)
