from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Case, F, IntegerField, Value, When
from django.shortcuts import render

from departments.models import Department
from logs.models import ActivityLog
from orders.models import Order
from tickets.models import Ticket

from .decorators import expert_required

User = get_user_model()

PRIORITY_RANK = Case(
    When(priority=Ticket.Priority.URGENT, then=Value(0)),
    When(priority=Ticket.Priority.HIGH, then=Value(1)),
    When(priority=Ticket.Priority.NORMAL, then=Value(2)),
    When(priority=Ticket.Priority.LOW, then=Value(3)),
    default=Value(4),
    output_field=IntegerField(),
)


def _department_tickets(user):
    tickets = Ticket.objects.select_related(
        "client", "department", "main_expert", "order__service"
    )
    if user.is_superuser:
        return tickets
    return tickets.filter(department_id=user.department_id)


@expert_required
def tickets(request):
    queryset = _department_tickets(request.user).annotate(priority_rank=PRIORITY_RANK)

    status = request.GET.get("status")
    if status in Ticket.Status.values:
        queryset = queryset.filter(status=status)
    else:
        status = ""

    sort = request.GET.get("sort")
    if sort == "priority":
        queryset = queryset.order_by(
            "priority_rank", F("last_message_at").desc(nulls_last=True)
        )
    else:
        sort = "activity"
        queryset = queryset.order_by(
            F("last_message_at").desc(nulls_last=True), "-created_at"
        )

    context = {
        "tickets": queryset,
        "statuses": Ticket.Status.choices,
        "current_status": status,
        "current_sort": sort,
    }
    return render(request, "staff/tickets.html", context)


@expert_required
def users(request):
    people = User.objects.select_related("department").order_by("username")
    return render(request, "staff/users.html", {"people": people})


@expert_required
def orders(request):
    all_orders = Order.objects.select_related("user", "service").order_by("-created_at")
    return render(request, "staff/orders.html", {"orders": all_orders})


@expert_required
def departments(request):
    all_departments = Department.objects.all()
    return render(request, "staff/departments.html", {"departments": all_departments})


@expert_required
def logs(request):
    entries = ActivityLog.objects.select_related("actor", "ticket")
    paginator = Paginator(entries, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "staff/logs.html", {"page_obj": page_obj})
