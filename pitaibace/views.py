from django.shortcuts import redirect


def home(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    return redirect("services:list")
