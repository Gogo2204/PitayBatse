from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..forms import ProfileForm, ProfilePasswordChangeForm


def _render_profile(request, profile_form=None, password_form=None):
    context = {
        "profile_form": profile_form or ProfileForm(instance=request.user),
        "password_form": password_form or ProfilePasswordChangeForm(request.user),
    }
    return render(request, "accounts/profile.html", context)


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Профилът е обновен.")
            return redirect("accounts:profile")
        return _render_profile(request, profile_form=form)
    return _render_profile(request)


@login_required
def password_change(request):
    if request.method != "POST":
        return redirect("accounts:profile")

    form = ProfilePasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Паролата е сменена.")
        return redirect("accounts:profile")
    return _render_profile(request, password_form=form)
