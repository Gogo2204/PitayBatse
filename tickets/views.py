from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from orders.models import Order


@login_required
def create(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, "tickets/create_placeholder.html", {"order": order})
