import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/app/services/self_order_service";
import { _t } from "@web/core/l10n/translation";

const TERMINAL_SELFORDER_STATES = new Set(["done", "cancel", "stale"]);

patch(SelfOrder.prototype, {
    setup() {
        const result = super.setup(...arguments);
        this.data.connectWebSocket("SELFORDER_STATE", (payload) => this._onPosCustomSelfOrderState(payload));
        return result;
    },

    _onPosCustomSelfOrderState(payload) {
        if (!payload || !TERMINAL_SELFORDER_STATES.has(payload.state)) {
            return;
        }

        const currentOrder = this.getOrder();
        const isCurrentOrder = currentOrder && currentOrder.uuid === payload.uuid;
        const isSelectedOrder = this.selectedOrderUuid === payload.uuid;
        if (!isCurrentOrder && !isSelectedOrder) {
            return;
        }

        // Terminal states must clear transient dialogs (e.g., waiter call popup)
        // before route changes to avoid stale overlays on landing page.
        if (this.dialog?.closeAll) {
            this.dialog.closeAll();
        }

        if (currentOrder) {
            this.data.localDeleteCascade(currentOrder);
        }
        this.selectedOrderUuid = null;

        // Initialize a fresh in-memory order so the next submission uses a new uuid.
        const newOrder = this.createNewOrder();
        this.selectedOrderUuid = newOrder.uuid;

        if (this.router.activeSlot !== "default") {
            this.router.navigate("default");
        }

        this.notification.add(_t("Your previous order has been processed. Please start a new order."), {
            type: "info",
        });
    },
});
