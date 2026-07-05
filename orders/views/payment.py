from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import CardPaymentForm
from ..models import Order
from ..payments import get_payment_gateway


@login_required
def pay_order(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)

    if order.status == Order.Status.PAID:
        return redirect("tickets:create", order_id=order.pk)

    is_card = order.payment_method == Order.PaymentMethod.CARD
    card_form = CardPaymentForm() if is_card else None
    error = None

    if request.method == "POST":
        if is_card:
            card_form = CardPaymentForm(request.POST)
            if not card_form.is_valid():
                return render(
                    request,
                    "orders/payment.html",
                    {"order": order, "card_form": card_form, "error": None},
                )
            # Card details are validated for format only and deliberately
            # discarded here — never stored, logged, or passed onward.

        gateway = get_payment_gateway(order.payment_method)
        result = gateway.charge(order)
        if result.success:
            order.mark_paid()
            messages.success(
                request,
                "Плащането мина, баце! Сега опиши какво да свършим.",
            )
            return redirect("tickets:create", order_id=order.pk)
        order.status = Order.Status.FAILED
        order.save(update_fields=["status"])
        error = result.message or "Плащането е неуспешно."

    return render(
        request,
        "orders/payment.html",
        {"order": order, "card_form": card_form, "error": error},
    )
