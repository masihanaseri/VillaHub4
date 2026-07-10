from .zarinpal import ZarinPalGateway
from .idpay import IDPayGateway
from .nextpay import NextPayGateway


class GatewayFactory:

    GATEWAYS = {
        "zarinpal": ZarinPalGateway,
        "idpay": IDPayGateway,
        "nextpay": NextPayGateway,
    }

    @classmethod
    def get(
        cls,
        slug,
    ):

        slug = slug.lower().strip()

        gateway_class = cls.GATEWAYS.get(
            slug,
        )

        if gateway_class is None:

            raise ValueError(
                f"Unsupported payment gateway: {slug}"
            )

        return gateway_class()

    @classmethod
    def available_gateways(cls):

        return list(
            cls.GATEWAYS.keys()
        )