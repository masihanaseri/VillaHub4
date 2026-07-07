from django.conf import settings

from .kavenegar import KavenegarProvider
from .farazsms import FarazSmsProvider
from .melipayamak import MeliPayamakProvider
from .ippanel import IPPanelProvider


class SmsProviderFactory:

    @staticmethod
    def get_provider():

        provider = settings.SMS_PROVIDER

        if provider == "kavenegar":
            return KavenegarProvider()

        if provider == "farazsms":
            return FarazSmsProvider()

        if provider == "melipayamak":
            return MeliPayamakProvider()

        if provider == "ippanel":
            return IPPanelProvider()

        raise ValueError("SMS Provider Not Found")