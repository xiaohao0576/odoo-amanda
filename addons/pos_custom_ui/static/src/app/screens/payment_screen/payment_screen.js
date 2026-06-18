import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

const KHR_RATE = 4000;
const KHR_ROUNDING = 100;

function toKhrRounded(amountUsd) {
    const rawKhr = (amountUsd || 0) * KHR_RATE;
    return Math.round(rawKhr / KHR_ROUNDING) * KHR_ROUNDING;
}

patch(PaymentScreen.prototype, {
    getPosCustomKhrRateLabel() {
        return `1 USD = ${KHR_RATE} KHR`;
    },

    getPosCustomDueKhrLabel() {
        const dueUsd = this.currentOrder?.totalDue || 0;
        const dueKhr = toKhrRounded(dueUsd);

        return `${dueKhr.toLocaleString("en-US")} KHR`;
    },
});
