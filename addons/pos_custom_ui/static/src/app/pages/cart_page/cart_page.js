import { patch } from "@web/core/utils/patch";
import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { WaiterCallPopup } from "@pos_custom_ui/app/components/waiter_call_popup/waiter_call_popup";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

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

        const noteText = this.state?.orderNoteValue?.trim();
        if (noteText) {
            this.selfOrder.currentOrder.general_customer_note = noteText;
        }

        this.selfOrder.rpcLoading = true;
        try {
            await rpc(`/pos-self-order/process-selforder/${this.selfOrder.config.self_ordering_mode}/`, {
                order: this.selfOrder.currentOrder.serializeForORM(),
                access_token: this.selfOrder.access_token,
                table_identifier: this.selfOrder.router.getTableIdentifier(),
            });
        } catch (error) {
            const message =
                error?.message ||
                error?.data?.message ||
                _t("Failed to submit your order. Please check your network and try again.");
            this.selfOrder.notification.add(message, {
                type: "danger",
            });
            this.selfOrder.rpcLoading = false;
            return;
        }
        this.selfOrder.rpcLoading = false;

        this.dialog.add(WaiterCallPopup, {});
    },
});
