from odoo import models
from odoo.tools import float_round


KHR_RATE = 4000
KHR_ROUNDING = 100


class PosOrderReceipt(models.AbstractModel):
    _inherit = "pos.order.receipt"

    def _pos_custom_compute_khr_total_amount(self):
        khr_total = float_round(
            (self.amount_total or 0.0) * KHR_RATE,
            precision_rounding=KHR_ROUNDING,
        )
        return int(khr_total)

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt=basic_receipt)
        data.setdefault("extra_data", {}).update(
            {
                "khr_exchange_rate_label": f"1 USD = {KHR_RATE} KHR",
                "khr_total_amount": self._pos_custom_compute_khr_total_amount(),
                "khr_currency_label": "KHR",
            }
        )
        return data
