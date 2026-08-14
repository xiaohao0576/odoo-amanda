from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_amount


class PaymentCaptureWizard(models.TransientModel):
    _inherit = 'payment.capture.wizard'

    _is_payway_provider = fields.Boolean(compute="_compute_is_payway_provider")
    
    @api.depends("transaction_ids.provider_id")
    def _compute_is_payway_provider(self):
        for wizard in self:
            wizard._is_payway_provider = any(
                tx.provider_id.code == "aba_payway" for tx in wizard.transaction_ids
            )

    def action_capture(self):
        for wizard in self:

            provider_codes = set(wizard.transaction_ids.mapped('provider_code'))
            if 'aba_payway' in provider_codes and len(provider_codes) > 1:
                raise ValidationError(_(
                    "ABA PayWay transactions must be captured separately. "
                    "Please select only PayWay transactions."
                ))

            if wizard._is_payway_provider and wizard.has_remaining_amount:
                # force void of remaining amount for PayWay partial captures, 
                # as PayWay does not support leaving an amount in authorized state after a partial capture
                wizard.void_remaining_amount = True

        return super().action_capture()
            



