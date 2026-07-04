from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("service/<int:service_id>/create/", views.create_order, name="create"),
    path("<int:order_id>/pay/", views.pay_order, name="pay"),
]
