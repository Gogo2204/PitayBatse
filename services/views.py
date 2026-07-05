from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Service


@login_required
def service_list(request):
    services = Service.objects.filter(is_active=True).select_related("department")
    return render(request, "services/service_list.html", {"services": services})
