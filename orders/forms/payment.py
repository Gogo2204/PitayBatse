import re

from django import forms
from django.utils import timezone


class CardPaymentForm(forms.Form):
    """Validates fake card details for the demo payment step.

    The cleaned values are used only for format validation and must never be
    stored, logged, or persisted anywhere.
    """

    card_name = forms.CharField(label="Име на картата", max_length=100)
    card_number = forms.CharField(label="Номер на картата")
    expiry = forms.CharField(label="Валидност (MM/YY)")
    cvv = forms.CharField(label="CVV")

    def clean_card_number(self):
        digits = self.cleaned_data["card_number"].replace(" ", "")
        if not re.fullmatch(r"\d{16}", digits):
            raise forms.ValidationError("Номерът на картата трябва да е 16 цифри.")
        return digits

    def clean_cvv(self):
        cvv = self.cleaned_data["cvv"].strip()
        if not re.fullmatch(r"\d{3}", cvv):
            raise forms.ValidationError("CVV трябва да е 3 цифри.")
        return cvv

    def clean_expiry(self):
        value = self.cleaned_data["expiry"].strip()
        match = re.fullmatch(r"(\d{2})/(\d{2})", value)
        if not match:
            raise forms.ValidationError("Валидността трябва да е във формат MM/YY.")
        month = int(match.group(1))
        year = 2000 + int(match.group(2))
        if not 1 <= month <= 12:
            raise forms.ValidationError("Невалиден месец.")
        today = timezone.localdate()
        if (year, month) < (today.year, today.month):
            raise forms.ValidationError("Картата е изтекла.")
        return value
