from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import render

from departments.models import Department

from .models import Service


@login_required
def service_list(request):
    departments = (
        Department.objects.filter(services__is_active=True)
        .distinct()
        .prefetch_related(
            Prefetch(
                "services",
                queryset=Service.objects.filter(is_active=True),
                to_attr="active_services",
            )
        )
        .order_by("name")
    )
    return render(request, "services/service_list.html", {"departments": departments})
