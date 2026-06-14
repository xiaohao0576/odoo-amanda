import { patch } from "@web/core/utils/patch";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { POS_CUSTOM_CURRENT_ORDER_CATEGORY_ID } from "@pos_custom_ui/app/services/pos_store";

const originalClickLine = OrderSummary.prototype.clickLine;

patch(OrderSummary.prototype, {
    clickLine(ev, orderline) {
        originalClickLine.call(this, ev, orderline);

        this.pos.setSelectedCategory(POS_CUSTOM_CURRENT_ORDER_CATEGORY_ID);

        const selectedLine = this.currentOrder.getSelectedOrderline();
        const targetLine = selectedLine?.combo_parent_id || selectedLine;
        const productTemplateId = targetLine?.product_id?.product_tmpl_id?.id || null;
        this.pos.posCustomSelectedProductTemplateId = productTemplateId;
    },
});
