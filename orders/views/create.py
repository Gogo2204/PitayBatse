from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from services.models import Service

from ..forms import OrderForm
from ..models import Order


@login_required
def create_order(request, service_id):
    service = get_object_or_404(Service, pk=service_id, is_active=True)

    if request.method == "POST":
        form = OrderForm(request.POST, service=service)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.service = service
            order.amount = service.price
            order.status = Order.Status.PENDING
            order.full_clean()
            order.save()
            return redirect("orders:pay", order_id=order.pk)
    else:
        form = OrderForm(service=service)

    return render(request, "orders/order_create.html", {"form": form, "service": service})
