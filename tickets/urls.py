from django.urls import path

from . import views

app_name = "tickets"

urlpatterns = [
    path("", views.index, name="index"),
    path("create/<int:order_id>/", views.create, name="create"),
    path("<uuid:public_id>/", views.detail, name="detail"),
]
