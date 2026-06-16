import { patch } from "@web/core/utils/patch";
import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { WaiterCallPopup } from "@pos_custom_ui/app/components/waiter_call_popup/waiter_call_popup";

patch(CartPage.prototype, {
    getPosCustomTableNumber() {
        const tableNumber =
            this.selfOrder?.currentTable?.table_number ||
            this.selfOrder?.currentOrder?.self_ordering_table_id?.table_number ||
            this.selfOrder?.currentOrder?.table_stand_number;
        return tableNumber ? String(tableNumber) : "-";
    },

    async pay() {
        if (this.selfOrder.rpcLoading || !this.selfOrder.verifyCart()) {
            return;
        }
        this.dialog.add(WaiterCallPopup, {});
    },
});
