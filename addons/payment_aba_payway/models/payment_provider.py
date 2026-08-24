import logging
import json
import base64
import hashlib
import hmac
from datetime import datetime
from urllib.parse import urljoin
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import requests

from odoo.exceptions import ValidationError
from odoo import _, models, fields, api

from odoo.addons.payment_aba_payway import const

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

_logger = logging.getLogger(__name__)

MAX_RETRY = 2
def _make_payway_api_request(base_url: str, endpoint: str, payload: dict):
    url = urljoin(base_url, endpoint)

    retry_strategy = Retry(
        total=MAX_RETRY,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)

    try:
        _logger.info(
            "Making PayWay API request to %s with payload: %s", url, payload
        )
        response = session.post(
            url, json=payload, timeout=10, verify=True
        )
        _logger.info(
            "Payway reponse returned status code %s with response: %s", 
            response.status_code, response.text
        )
        return response.json()
    except (requests.RequestException, ValueError) as err:

        _logger.error("Error while making API request to PayWay: %s", err)
        raise ValidationError(
            _("Could not establish a connection to PayWay API. Error: %s", err)
        )

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('aba_payway', "ABA PayWay")], ondelete={'aba_payway': 'set default'}
    )

    production_payway_merchant_id = fields.Char(
        string='Merchant ID',
        help="Enter your production PayWay Merchant ID. You'll receive this by email after obtaining a Go Live approval from ABA PayWay.",
    )
    production_payway_key = fields.Char(
        string='API Key',
        help="Enter your production PayWay API Key. You'll receive this by email after obtaining a Go Live approval from ABA PayWay.",
        groups='base.group_system',
    )
    production_rsa_public_key = fields.Text(
        string='RSA Public Key',
        help="Enter your production PayWay RSA Public Key. You'll receive this by email after obtaining a Go Live approval from ABA PayWay.",
        groups='base.group_system',
    )

    sandbox_payway_merchant_id = fields.Char(
        string='Merchant ID',
        help='Enter your unique PayWay Merchant ID. You can find it in the email registered for your PayWay Sandbox account.',
    )
    sandbox_payway_key = fields.Char(
        string='API Key',
        help='Enter your unique PayWay API Key. You can find it in the email registered for your PayWay Sandbox account.',
        groups='base.group_system',
    )
    sandbox_rsa_public_key = fields.Text(
        string='RSA Public Key',
        help='Enter your unique PayWay RSA Public Key. You can find it in the email registered for your PayWay Sandbox account.',
        groups='base.group_system',
    )

    payway_environment = fields.Selection(
        [('disable', 'Disable'), ('production', 'Production'), ('sandbox', 'Sandbox')],
        string='Environment',
        default='disable',
        required_if_provider='aba_payway',
        help='Switch between Sandbox and Production payment environments for ABA PayWay.',
    )
    

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'aba_payway').update({
            'support_refund': 'partial',
            'support_manual_capture': 'partial',
        })

    @api.constrains(
        'payway_environment', 'production_payway_merchant_id', 'production_payway_key', 'production_rsa_public_key',
        'sandbox_payway_merchant_id', 'sandbox_payway_key', 'sandbox_rsa_public_key', 'state'
    )
    def _check_payway_credentials(self):
        """ Validate that required credentials are provided based on selected environment. """
        for provider in self:
            if provider.code == 'aba_payway' and provider.state != 'disabled':
                if provider.payway_environment == 'production':
                    if (
                        not provider.production_payway_merchant_id 
                        or not provider.production_payway_key 
                        or not provider.production_rsa_public_key
                    ):
                        raise ValidationError(_("Production credentials are required when using production environment."))

                elif provider.payway_environment == 'sandbox':
                    if (
                        not provider.sandbox_payway_merchant_id
                        or not provider.sandbox_payway_key
                        or not provider.sandbox_rsa_public_key
                    ):
                        raise ValidationError(_("Sandbox credentials are required when using sandbox environment."))

    # ==== CONSTRAINT METHODS ===#
    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'aba_payway':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _payway_get_api_cred(self):
        """Return the URL of the API corresponding to the selected payway environment.

        :return: (API URL, Merchant ID, API Key).
        :rtype: (str, str, str)
        """

        self.ensure_one()
        if self.payway_environment == 'production':
            api_url = const.API_URLS['production']
            return (
                api_url,
                self.production_payway_merchant_id,
                self.production_payway_key,
                self.production_rsa_public_key,
            )
        elif self.payway_environment == 'sandbox':
            api_url = const.API_URLS['sandbox']
            return (
                api_url,
                self.sandbox_payway_merchant_id,
                self.sandbox_payway_key,
                self.sandbox_rsa_public_key,
            )
    
    def _payway_calculate_payment_secure_hash(
            self, 
            api_key: str, 
            payload: dict, 
            secure_hash_keys: list
        ):
        """Compute the secure hash for the provided data according to the PayWay documentation.

        :param dict data: The data to hash.
        :return: The calculated hash.
        :rtype: str
        """
        
        self.ensure_one()

        data_to_sign = [str(payload.get(k, '')) for k in secure_hash_keys]
        signing_string = ''.join(data_to_sign)
        hmac_hash = hmac.new(
            api_key.encode(), signing_string.encode(), hashlib.sha512
        ).digest()
        base64_encoded = base64.b64encode(hmac_hash).decode()
        return base64_encoded

    def _payway_api_get_transaction_detail(self, tran_id: str):
        """Check transaction status with ABA PayWay V2 check-transaction API."""
        self.ensure_one()

        api_url, merchant_id, api_key, _ = self._payway_get_api_cred()
        payload = {
            'req_time': datetime.now().strftime("%Y%m%d%H%M%S"),
            'merchant_id': merchant_id,
            'tran_id': tran_id,
        }
        payload.update(
            {'hash': self._payway_calculate_payment_secure_hash(api_key, payload, const.CHECK_TXN_SECURE_HASH_KEYS)}
        )

        response = _make_payway_api_request(
            api_url, '/api/payment-gateway/v1/payments/check-transaction-2', payload
        )

        if str(response['status']['code']) == '00':
            return response

        raise ValidationError(self._payway_construct_error_message(response))

    def _payway_api_refund_transaction(self, merchant_auth: str):
        self.ensure_one()

        api_url, merchant_id, api_key, _ = self._payway_get_api_cred()
        req_time = datetime.now().strftime('%Y%m%d%H%M%S')

        payload = {
            "request_time": req_time,
            "merchant_id": merchant_id,
            "merchant_auth": merchant_auth,
        }
        payload.update(
            {'hash': self._payway_calculate_payment_secure_hash(api_key, payload, const.REFUND_TXN_SECURE_HASH_KEYS)}
        )

        response = _make_payway_api_request(
            api_url, '/api/merchant-portal/merchant-access/online-transaction/refund', payload
        )

        if str(response['status']['code']) == '00':
            return response

        raise ValidationError(self._payway_construct_error_message(response))

    def _payway_api_void_transaction(self, merchant_auth: str):
        self.ensure_one()

        api_url, merchant_id, api_key, _ = self._payway_get_api_cred()
        req_time = datetime.now().strftime('%Y%m%d%H%M%S')

        payload = {
            "merchant_id": merchant_id,
            "merchant_auth": merchant_auth,
            "request_time": req_time,
        }

        payload.update(
            {'hash': self._payway_calculate_payment_secure_hash(api_key, payload, const.VOID_TXN_SECURE_HASH_KEYS)}
        )

        response = _make_payway_api_request(
            api_url, '/api/merchant-portal/merchant-access/online-transaction/pre-auth-cancellation', payload
        )

        if str(response['status']['code']) == '00':
            return response

        raise ValidationError(self._payway_construct_error_message(response))
    
    
    def _payway_api_capture_transaction(self, merchant_auth: str):
        self.ensure_one()

        api_url, merchant_id, api_key, _ = self._payway_get_api_cred()
        req_time = datetime.now().strftime('%Y%m%d%H%M%S')

        payload = {
            "merchant_auth": merchant_auth,
            "request_time": req_time,
            "merchant_id": merchant_id,
        }
        payload.update(
            {'hash': self._payway_calculate_payment_secure_hash(api_key, payload, const.CAPTURE_TXN_SECURE_HASH_KEYS)}
        )

        response = _make_payway_api_request(
            api_url, '/api/merchant-portal/merchant-access/online-transaction/pre-auth-completion', payload
        )

        if str(response['status']['code']) == '00':
            return response

        raise ValidationError(self._payway_construct_error_message(response))
    

    def _payway_calculate_webhook_secure_hash(self, notification_data):
        self.ensure_one()

        _, _, api_key, _ = self._payway_get_api_cred()
        data_to_sign = sorted(notification_data.keys())
        signing_string = ''.join([str(notification_data.get(k, '')) for k in data_to_sign])
        hmac_hash = hmac.new(
            api_key.encode(), signing_string.encode(), hashlib.sha512
        ).digest()
        base64_encoded = base64.b64encode(hmac_hash).decode()
        return base64_encoded
    
    def _payway_calculate_merchant_auth(self, public_key_pem: str, payload: dict):

        self.ensure_one()
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        data = json.dumps(payload).encode("utf-8")

        encrypted = bytearray()
        for i in range(0, len(data), 117):
            chunk = data[i : i + 117]
            encrypted.extend(public_key.encrypt(chunk, padding.PKCS1v15()))

        return base64.b64encode(bytes(encrypted)).decode("utf-8")
    

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'aba_payway':
            return default_codes
        return const.DEFAULT_PAYMENT_METHODS_CODES


    def _payway_construct_error_message(self, response: dict) -> str:
        """Construct a user-friendly error message from the PayWay API response.

        :param dict response: The JSON response from PayWay API.
        :return: A formatted error string.
        :rtype: str
        """
        status = response.get('status', {})
        main_msg = status.get('message', _("An unexpected error occurred."))
        errors = status.get('errors', {})

        if not errors:
            return main_msg

        error_lines = []
        for field, messages in errors.items():
            # Format field name (e.g., 'tran_id' -> 'Tran id')
            fn = field.replace('_', ' ').capitalize()
            for msg in messages:
                error_lines.append(f"- {fn}: {msg}")

        return f"{main_msg}\n" + "\n".join(error_lines)