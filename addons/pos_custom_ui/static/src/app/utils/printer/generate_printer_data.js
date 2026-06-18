import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

const KHR_RATE = 4000;
const KHR_ROUNDING = 100;

function toKhrRounded(amountUsd) {
    const rawKhr = (amountUsd || 0) * KHR_RATE;
    return Math.round(rawKhr / KHR_ROUNDING) * KHR_ROUNDING;
}

patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);
        const amountTotalUsd = this.order?.amount_total || 0;
        const amountTotalKhr = toKhrRounded(amountTotalUsd);

        data.extra_data = {
            ...data.extra_data,
            khr_exchange_rate_label: `1 USD = ${KHR_RATE} KHR`,
            khr_total_amount: amountTotalKhr,
            khr_currency_label: "KHR",
        };

        return data;
    },
});
