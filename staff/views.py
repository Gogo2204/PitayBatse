from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import F
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from departments.models import Department
from logs.models import ActivityLog
from orders.models import Order
from tickets.models import Ticket

from .decorators import expert_required, superuser_required

User = get_user_model()


def _department_tickets(user):
    tickets = Ticket.objects.select_related(
        "client", "department", "main_expert", "order__service"
    )
    if user.is_superuser:
        return tickets
    return tickets.filter(department_id=user.department_id)


@expert_required
def tickets(request):
    queryset = _department_tickets(request.user).order_by(
        F("last_message_at").desc(nulls_last=True), "-created_at"
    )
    return render(request, "staff/tickets.html", {"tickets": queryset})


@expert_required
def users(request):
    people = User.objects.select_related("department").order_by("username")
    context = {"people": people, "departments": Department.objects.all()}
    return render(request, "staff/users.html", context)


@superuser_required
@require_POST
def promote_user(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    department_id = request.POST.get("department")
    if not department_id:
        return HttpResponseBadRequest("Изберете отдел.")
    department = get_object_or_404(Department, pk=department_id)

    target.role = User.Role.EXPERT
    target.department = department
    target.save(update_fields=["role", "department"])

    ActivityLog.objects.create(
        actor=request.user,
        action="user_promoted",
        description=(
            f"Потребител „{target.username}“ стана експерт в отдел „{department.name}“."
        ),
    )
    return redirect("staff:users")


@superuser_required
@require_POST
def set_department(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target.role != User.Role.EXPERT:
        return HttpResponseBadRequest("Само експерт може да сменя отдел.")

    department_id = request.POST.get("department")
    if not department_id:
        return HttpResponseBadRequest("Изберете отдел.")
    department = get_object_or_404(Department, pk=department_id)

    target.department = department
    target.save(update_fields=["department"])

    ActivityLog.objects.create(
        actor=request.user,
        action="department_changed",
        description=f"Отделът на „{target.username}“ е сменен на „{department.name}“.",
    )
    return redirect("staff:users")


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
