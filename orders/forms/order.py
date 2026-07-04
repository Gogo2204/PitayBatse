from django import forms

from ..models import Order


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["billing_cycle", "payment_method"]
        labels = {
            "billing_cycle": "Период на таксуване",
            "payment_method": "Начин на плащане",
        }

    def __init__(self, *args, service=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = service
        if service is not None and not service.is_subscription:
            self.fields.pop("billing_cycle", None)
        elif "billing_cycle" in self.fields:
            self.fields["billing_cycle"].required = True

    def clean(self):
        cleaned = super().clean()
        if self.service and self.service.is_subscription and not cleaned.get("billing_cycle"):
            self.add_error("billing_cycle", "Изберете период на таксуване за абонамент.")
        return cleaned
