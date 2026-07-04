from django.urls import path

from . import views

app_name = "staff"

urlpatterns = [
    path("", views.tickets, name="tickets"),
    path("users/", views.users, name="users"),
    path("orders/", views.orders, name="orders"),
    path("departments/", views.departments, name="departments"),
    path("logs/", views.logs, name="logs"),
]
