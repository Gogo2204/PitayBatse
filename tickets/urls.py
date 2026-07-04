from django.urls import path

from . import views

app_name = "tickets"

urlpatterns = [
    path("create/<int:order_id>/", views.create, name="create"),
]
