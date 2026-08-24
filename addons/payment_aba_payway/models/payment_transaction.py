from datetime import datetime
import base64
import pprint
from urllib.parse import urljoin
import logging

from odoo import _, api, models
from odoo.addons.payment import utils as payment_utils
from odoo.tools import float_compare, float_round
from odoo.exceptions import ValidationError

from odoo.addons.payment_aba_payway import const
from odoo.addons.payment_aba_payway import utils as payway_utils

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        """Override of `payment` to ensure that PayWay requirement for references is satisfied.

        PayWay requires for references to be at most 20 characters long.
        Make sure that on DB change, the PayWay transaction id will not be duplicate.
        Preserve Odoo original reference in PayWay transaction id for easy reconciliation.

        """

        if provider_code != 'aba_payway':
            return super()._compute_reference(provider_code, prefix=prefix, **kwargs)

        if not prefix:
            prefix = self.sudo()._compute_reference_prefix(separator, **kwargs)

        prefix = payway_utils._compute_payway_tran_id(prefix=prefix, separator=separator)

        return super()._compute_reference(provider_code, prefix=prefix, **kwargs)

    def _get_specific_processing_values(self, processing_values):
        """Override of payment to return ABA Payway specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """

        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'aba_payway':
            return res

        api_url, merchant_id, api_key, _ = self.provider_id._payway_get_api_cred()

        req_time = datetime.now().strftime('%Y%m%d%H%M%S')
        partner_first_name, partner_last_name = (
            payment_utils.split_partner_name(self.partner_name) 
            if self.partner_name 
            else (None, None)
        )
        payment_option = const.PAYMENT_METHODS_MAPPING[self.payment_method_id.code]
        payment_lifetime_minutes = const.PAYWAY_LIFETIME_MINUTES

        # The amount is explicitly converted to a string to prevent a hash mismatch.
        # This avoids issues where JavaScript drops trailing zeros from numbers (e.g., 23.0 becomes 23),
        rounded_amount = str(
            float_round(
                processing_values.get('amount'),
                const.CURRENCY_DECIMALS.get(self.currency_id.name),
                rounding_method='DOWN',
            )
        )

        base_odoo_url: str = (
            self.env['ir.config_parameter'].sudo().get_str('web.base.url')
        )

        webhook_url = urljoin(
            (
                base_odoo_url.replace('http://', 'https://', 1)
                if base_odoo_url and base_odoo_url.startswith('http://')
                else base_odoo_url
            ),
            const.WEB_HOOK_PATH['webhook'],
        )
        encoded_return_url = base64.b64encode(webhook_url.encode('utf-8')).decode('utf-8')

        rendering_values = {
            'form_url': api_url + '/api/payment-gateway/v1/payments/purchase',
            'tran_id': self.reference,
            'req_time': req_time,
            'firstname': partner_first_name and partner_first_name[:20] or '',
            'lastname': partner_last_name and partner_last_name[:20] or '',
            'email': (
                self.partner_email
                if self.partner_email and len(self.partner_email) <= 50
                else ''
            ),
            'phone': self.partner_phone and self.partner_phone[:20] or '',
            'type': 'pre-auth' if self.provider_id.capture_manually else 'purchase',
            'payment_option': payment_option,
            'amount': rounded_amount,
            'payment_gate': 0,
            'merchant_id': merchant_id,
            'currency': self.currency_id.name,
            'skip_success_page': 1,
            'lifetime': payment_lifetime_minutes,
            'return_url': encoded_return_url,
            'continue_success_url': urljoin(base_odoo_url, '/payment/status'),
        }

        rendering_values.update(
            {
                'hash': self.provider_id._payway_calculate_payment_secure_hash(
                    api_key, rendering_values, const.PURCHASE_PAYMENT_SECURE_HASH_KEYS
                )
            }
        )

        return rendering_values
    
    def _send_refund_request(self):
        """Override of `payment` to send a refund request to ABA PayWay."""
        if self.provider_code != 'aba_payway':
            return super()._send_refund_request()

        source_tx = self.source_transaction_id or self
        provider_reference = source_tx.provider_reference or self.provider_reference
        if not provider_reference:
            raise ValidationError(_("Cannot refund an ABA PayWay transaction without a provider reference."))

        _, merchant_id, _, public_key_pem = self.provider_id._payway_get_api_cred()
        payload_merchant_auth = {
            "mc_id": merchant_id,
            "tran_id": provider_reference,
            "refund_amount": -self.amount,
        }
        merchant_auth = self.provider_id._payway_calculate_merchant_auth(
            public_key_pem, payload_merchant_auth
        )

        data: dict = self.provider_id._payway_api_refund_transaction(merchant_auth)
        _logger.info(
            "Payway refund request response for transaction with reference %s; payway_reference %s:\n%s",
            self.reference, provider_reference, pprint.pformat(data)
        )

        data.update({
            'reference': self.reference,
            'tran_id': provider_reference,
        })
        self._process('aba_payway', data)

    def _send_capture_request(self):
        """Override of `payment` to send a capture request to ABA PayWay."""
        if self.provider_code != 'aba_payway':
            return super()._send_capture_request()

        source_tx = self.source_transaction_id or self
        provider_reference = source_tx.provider_reference or self.provider_reference
        if not provider_reference:
            raise ValidationError(_("Cannot capture an ABA PayWay transaction without a provider reference."))

        _, merchant_id, _, public_key_pem = self.provider_id._payway_get_api_cred()
        payload_merchant_auth = {
            "mc_id": merchant_id,
            "tran_id": provider_reference,
            "complete_amount": self.amount,
        }
        merchant_auth = self.provider_id._payway_calculate_merchant_auth(
            public_key_pem, payload_merchant_auth
        )

        data: dict = self.provider_id._payway_api_capture_transaction(merchant_auth)
        _logger.info(
            "Payway capture request response for transaction with reference %s; payway_reference %s:\n%s",
            self.reference, provider_reference, pprint.pformat(data)
        )

        data.update({
            'reference': self.reference,
            'tran_id': provider_reference,
        })
        self._process('aba_payway', data)

    def _send_void_request(self):
        """Override of `payment` to send a void request to ABA PayWay."""
        if self.provider_code != 'aba_payway':
            return super()._send_void_request()

        source_tx = self.source_transaction_id or self
        provider_reference = source_tx.provider_reference or self.provider_reference
        if not provider_reference:
            raise ValidationError(_("Cannot void an ABA PayWay transaction without a provider reference."))

        # PayWay automatically voids the remaining balance after a partial capture.
        if source_tx.state != 'done':
            _, merchant_id, _, public_key_pem = self.provider_id._payway_get_api_cred()
            payload_merchant_auth = {
                "mc_id": merchant_id,
                "tran_id": provider_reference,
            }
            merchant_auth = self.provider_id._payway_calculate_merchant_auth(
                public_key_pem, payload_merchant_auth
            )
            data: dict = self.provider_id._payway_api_void_transaction(merchant_auth)
            _logger.info(
                "Payway cancel request response for transaction with reference %s; payway_reference %s:\n%s",
                self.reference, provider_reference, pprint.pformat(data)
            )
        else:
            data = {
                'payment_status': const.STATUS_MAPPING['CANCELLED'],
            }
            _logger.info(
                "Payway transaction with reference %s; payway_reference %s already reflects a partial capture, skipping void API call.",
                self.reference, provider_reference
            )

        data.update({
            'reference': self.reference,
            'tran_id': provider_reference,
        })
        self._process('aba_payway', data)


    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from ABA PayWay payloads."""
        if provider_code != 'aba_payway':
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get('reference') or payment_data.get('tran_id')

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to skip the generic amount check.

        The amount and currency are already validated against the PayWay API response in
        `_payway_validate_transaction_detail`, called from `_apply_updates`.
        """
        if self.provider_code != 'aba_payway':
            return super()._extract_amount_data(payment_data)
        return None

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction from ABA PayWay data."""
        super()._apply_updates(payment_data)
        if self.provider_code != 'aba_payway':
            return

        tran_id = payment_data.get('tran_id') or self.provider_reference or self.reference
        is_from_webhook = self.env.context.get('payway_from_webhook', False)

        upstream_payment_status = payment_data.get('payment_status', '').upper()
        try:
            payway_transaction_detail: dict = self.provider_id._payway_api_get_transaction_detail(tran_id)
        except ValidationError as err:
            _logger.warning(
                "Failed to fetch payment method details for reference %s; payway reference %s; Error: %s",
                self.reference, tran_id, str(err)
            )
            return

        api_payment_status = payway_transaction_detail.get('data', {}).get('payment_status', '').upper()
        payment_status = (
            api_payment_status
            if is_from_webhook
            else (
                upstream_payment_status
                if upstream_payment_status and upstream_payment_status == const.STATUS_MAPPING['CANCELLED']
                else api_payment_status
            )
        )

        if is_from_webhook and payment_status in (
            const.STATUS_MAPPING['APPROVED'],
            const.STATUS_MAPPING['PRE-AUTH'],
            const.STATUS_MAPPING['CANCELLED'],
        ):
            try:
                confirm_detail = self.provider_id._payway_api_get_transaction_detail(tran_id)
            except ValidationError as err:
                _logger.warning(
                    "Webhook confirmation check failed for transaction %s and provider reference %s; Error: %s",
                    self.reference,
                    tran_id,
                    str(err),
                )
            else:
                payment_status = confirm_detail.get('data', {}).get('payment_status', '').upper() or payment_status

        is_valid_settlement, settlement_validation_message = self._payway_validate_transaction_detail(
            payway_transaction_detail,
            payment_status,
        )
        if not is_valid_settlement:
            _logger.warning(
                "PayWay settlement validation failed for transaction %s and provider reference %s: %s; payload=%s",
                self.reference,
                tran_id,
                settlement_validation_message,
                pprint.pformat(payway_transaction_detail.get('data', {})),
            )
            self._set_pending(settlement_validation_message)
            return

        # Update the provider reference.
        self.provider_reference = tran_id 
        
        if (
            (
                payment_status == const.STATUS_MAPPING["APPROVED"]
                or payment_status == const.STATUS_MAPPING["PRE-AUTH"]
            )
            and self.state not in ('done', 'authorized')
        ):
            if self.payment_method_id.code == 'card':
                # Update the payment method for card
                payment_method_type = payway_transaction_detail.get('data', {}).get('payment_type', '').lower()
                payment_method = self.env['payment.method']._get_from_code(
                    payment_method_type, mapping=const.PAYWAY_PAYMENT_METHODS_MAPPING
                )
                self.payment_method_id = payment_method or self.payment_method_id

        if (
            payment_status == const.STATUS_MAPPING["APPROVED"]
            or payment_status == const.STATUS_MAPPING["REFUNDED"]
        ):
            self._set_done()

            # Immediately post-process the transaction if it is a refund, as the post-processing
            # will not be triggered by a customer browsing the transaction from the portal.
            if self.operation == 'refund':
                self.env.ref('payment.cron_post_process_payment_tx')._trigger()

        elif payment_status == const.STATUS_MAPPING["PRE-AUTH"]:
            self._set_authorized()

        elif payment_status == const.STATUS_MAPPING["CANCELLED"]:
            self._set_canceled()

        else:
            _logger.warning(
                "Received data with invalid payment status: (%s) for transaction with "
                "reference %s and payway reference %s", payment_status, self.reference, self.provider_reference
            )

            self._set_pending(_(
                "Received unknown payment status: %(payment_status)s; reference %(reference)s; payway reference %(provider_reference)s", 
                payment_status=payment_status, reference=self.reference, provider_reference=self.provider_reference
            ))

    # === Custom validation methods ===
    def _payway_validate_transaction_detail(self, payway_transaction_detail, payment_status):
        """Validate PayWay amount/currency against the Odoo transaction.

        The validation is enforced only for statuses that can complete/authorize a payment.
        """
        self.ensure_one()

        detail_data = payway_transaction_detail.get('data', {})
        if payment_status not in (
            const.STATUS_MAPPING['APPROVED'],
            const.STATUS_MAPPING['PRE-AUTH'],
        ):
            return True, None

        expected_currency = (self.currency_id.name or '').upper()
        payway_currency = str(detail_data.get('original_currency') or '').upper().strip()

        if not payway_currency or payway_currency != expected_currency:
            return False, _(
                "Payment validation failed: currency mismatch (expected %(expected)s, got %(actual)s).",
                expected=expected_currency,
                actual=payway_currency or 'N/A',
            )

        expected_precision = const.CURRENCY_DECIMALS.get(payway_currency)
        expected_amount = float_round(
            self.amount,
            precision_digits=expected_precision,
            rounding_method='DOWN',
        )

        payway_amount = float(detail_data.get('original_amount'))
        if payway_amount is None:
            return False, _(
                "Payment validation failed: gateway amount is missing or invalid."
            )

        amount_matches = (
            float_compare(
                expected_amount,
                payway_amount,
                precision_digits=expected_precision,
            )
            == 0
        )
        if not amount_matches:
            return False, _(
                "Payment validation failed: amount mismatch (expected %(expected_amount)s %(currency)s, got %(actual_amount)s %(actual_currency)s).",
                expected_amount=expected_amount,
                currency=expected_currency,
                actual_amount=payway_amount,
                actual_currency=payway_currency,
            )

        return True, None