from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..models import Order
from ..payments import get_payment_gateway


@login_required
def pay_order(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)

    if order.status == Order.Status.PAID:
        return redirect("tickets:create", order_id=order.pk)

    error = None
    if request.method == "POST":
        gateway = get_payment_gateway(order.payment_method)
        result = gateway.charge(order)
        if result.success:
            order.mark_paid()
            return redirect("tickets:create", order_id=order.pk)
        order.status = Order.Status.FAILED
        order.save(update_fields=["status"])
        error = result.message or "Плащането е неуспешно."

    return render(request, "orders/payment.html", {"order": order, "error": error})
