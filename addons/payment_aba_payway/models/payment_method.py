from odoo import _, models, fields, api
from odoo.addons.payment import utils as payment_utils
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__, default_lang='en_US')

class PaymentMethod(models.Model):
    _inherit = 'payment.method'
    
    def _get_compatible_payment_methods(
        self, provider_ids, partner_id, currency_id=None, force_tokenization=False,
        is_express_checkout=False, report=None, **kwargs
    ):
        payment_methods = super()._get_compatible_payment_methods(
            provider_ids, partner_id, currency_id, force_tokenization,
            is_express_checkout, report, **kwargs
        )

        providers = self.env['payment.provider'].browse(provider_ids)
        payway_providers = providers.filtered(lambda p: p.code == 'aba_payway')

        # Handle manual capture filtering for PayWay providers
        # On manual capture, wechat and alipay is not supported by Payway.
        if payway_providers:
            manual_capture_providers = payway_providers.filtered(
                lambda p: p.capture_manually
            )

            if manual_capture_providers:

                excluded_pm_codes = ['wechat_pay', 'alipay']
                
                unfiltered_pms = payment_methods
                payment_methods = payment_methods.filtered(
                    lambda pm: not (
                        pm.code in excluded_pm_codes
                        and any(p.id in manual_capture_providers.ids for p in pm.provider_ids)
                    )
                )

                payment_utils.add_to_report(
                    report,
                    unfiltered_pms - payment_methods,
                    available=False,
                    reason=_lt("Payway Manual capture is not supported for this payment method."),
                )

        return payment_methods
