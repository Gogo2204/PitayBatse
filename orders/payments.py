from dataclasses import dataclass


@dataclass
class PaymentResult:
    success: bool
    reference: str = ""
    message: str = ""


class PaymentGateway:
    def charge(self, order) -> PaymentResult:
        raise NotImplementedError


class FakePaymentGateway(PaymentGateway):
    def charge(self, order) -> PaymentResult:
        return PaymentResult(
            success=True,
            reference=f"FAKE-{order.pk}",
            message="Плащането е успешно",
        )


GATEWAYS = {}


def get_payment_gateway(payment_method) -> PaymentGateway:
    return GATEWAYS.get(payment_method, FakePaymentGateway())
