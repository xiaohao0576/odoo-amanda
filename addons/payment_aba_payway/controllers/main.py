import hmac
import logging
import pprint

from werkzeug.exceptions import Forbidden
from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


from odoo.addons.payment_aba_payway import const

_logger = logging.getLogger(__name__)

class PayWayController(http.Controller):
    _webhook_url =  const.WEB_HOOK_PATH['webhook']
    _poll_status_url = const.WEB_HOOK_PATH['poll']

    MONITORED_TX_ID_KEY = '__payment_monitored_tx_id__'

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def payway_webhook(self):
        try:
            data = request.get_json_data()
            _logger.info("Notification received from PayWay with data:\n%s", pprint.pformat(data))

            tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
                'aba_payway', data
            )
            if not tx_sudo:
                return request.make_json_response(['accepted'], status=200)

            received_signature = request.httprequest.headers.get('x-payway-hmac-sha512')
            self._verify_notification_signature(data, received_signature, tx_sudo)

            tx_sudo.with_context(payway_from_webhook=True)._process('aba_payway', data)

        except ValidationError:
            _logger.exception("Unable to handle the notification data; skipping to acknowledge.", exc_info=True)

        return request.make_json_response(['accepted'], status=200)


    @http.route(_poll_status_url, type='jsonrpc', auth='public')
    def payway_poll_check_transaction(self, **_kwargs):
        """ Fetch the payway transaction and verify its status.
        In case webhook notification is not received, this is the fallback method.

        :return: The post-processing values of the transaction.
        :rtype: dict
        """
        # We only poll the payment status if a payment was found, so the transaction should exist.
        monitored_tx = self._get_monitored_transaction()

        if not monitored_tx:
            return {
                'provider_code': None,
                'state': 'error',
            }

        poll_interval_seconds = const.PAYWAY_POLL_INTERVAL_SECONDS
        poll_lifetime_seconds = const.PAYWAY_LIFETIME_MINUTES * 60

        if monitored_tx and monitored_tx.provider_code == 'aba_payway':
            try:
                data = {
                    'reference': monitored_tx.reference,
                    'tran_id': monitored_tx.reference,
                }
                if monitored_tx.provider_reference:
                    data['tran_id'] = monitored_tx.provider_reference

                tx_sudo = request.env['payment.transaction'].sudo().browse(monitored_tx.id)
                tx_sudo._process('aba_payway', data)
                monitored_tx = tx_sudo

            except ValidationError:
                _logger.exception("Unable to handle the verify Payway transaction.", exc_info=True)

        return {
            'provider_code': monitored_tx.provider_code,
            'state': monitored_tx.state,
            'poll_interval_seconds': poll_interval_seconds,
            'poll_lifetime_seconds': poll_lifetime_seconds,
        }
    
    @staticmethod
    def _verify_notification_signature(notification_data, received_signature, tx_sudo):
        """ Check that the received signature matches the expected one.

        :param dict notification_data: The notification data
        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                   `payment.transaction` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the signatures don't match
        """

        if not received_signature:
            _logger.warning("Received notification with missing signature.")
            raise Forbidden()
        
        expected_signature = tx_sudo.provider_id._payway_calculate_webhook_secure_hash(notification_data)
        if (
            expected_signature is None
            or not hmac.compare_digest(received_signature, expected_signature)
        ):
            _logger.warning("Received notification with invalid signature.")
            raise Forbidden()


    def _get_monitored_transaction(self):
        """ Retrieve the user's last transaction from the session (the transaction being monitored).

        :return: the user's last transaction
        :rtype: payment.transaction
        """
        return request.env['payment.transaction'].sudo().browse(
            request.session.get(self.MONITORED_TX_ID_KEY)
        ).exists()