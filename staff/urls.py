from django.urls import path

from . import views

app_name = "staff"

urlpatterns = [
    path("", views.tickets, name="tickets"),
    path("users/", views.users, name="users"),
    path("users/<int:user_id>/promote/", views.promote_user, name="promote_user"),
    path("users/<int:user_id>/department/", views.set_department, name="set_department"),
    path("orders/", views.orders, name="orders"),
    path("departments/", views.departments, name="departments"),
    path("logs/", views.logs, name="logs"),
]
