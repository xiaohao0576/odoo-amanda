import { Component, onWillUpdateProps, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export class SelfOrderPanel extends Component {
    static template = "pos_custom_ui.SelfOrderPanel";
    static props = {
        selfOrder: Object,
        tableNumber: [String, Number],
        onAccept: Function,
        onDelete: Function,
    };

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.state = useState({
            selfOrderId: null,
            lines: [],
            parseError: false,
            rawOrderLines: "",
        });

        this._syncFromSelfOrder(this.props.selfOrder);
        onWillUpdateProps((nextProps) => {
            this._syncFromSelfOrder(nextProps.selfOrder);
        });
    }

    _syncFromSelfOrder(selfOrder) {
        if (!selfOrder || selfOrder.id === this.state.selfOrderId) {
            return;
        }

        this.state.selfOrderId = selfOrder.id;
        this.state.rawOrderLines = selfOrder.order_lines || "";
        this.state.parseError = false;
        this.state.lines = [];

        try {
            const payload = JSON.parse(selfOrder.order_lines || "{}");
            const commands = Array.isArray(payload.lines) ? payload.lines : [];
            const parsedLines = [];

            for (let i = 0; i < commands.length; i++) {
                const command = commands[i];
                if (!Array.isArray(command)) {
                    continue;
                }

                let lineVals = null;
                if (command[0] === "create" && command[1]) {
                    // Some serializers use symbolic command names.
                    lineVals = command[1];
                } else if (command[0] === 0 && command[2]) {
                    // Odoo ORM command format: [0, 0, values].
                    lineVals = command[2];
                }

                if (!lineVals || typeof lineVals !== "object") {
                    continue;
                }

                const productId = Number(lineVals.product_id) || null;
                const product = productId ? this.pos.models["product.product"].get(productId) : null;
                const qty = Math.max(0, Number(lineVals.qty || 0));

                parsedLines.push({
                    key: `${selfOrder.id}-${i}`,
                    productId,
                    product,
                    qty,
                    priceUnit: Number(lineVals.price_unit || 0),
                    name:
                        product?.display_name ||
                        lineVals.full_product_name ||
                        product?.name ||
                        _t("Unknown product"),
                });
            }

            this.state.lines = parsedLines;
        } catch {
            this.state.parseError = true;
        }
    }

    get hasEditableLines() {
        return !this.state.parseError && this.state.lines.length > 0;
    }

    get actionableItemsCount() {
        if (this.state.parseError) {
            return 0;
        }
        return this.state.lines.reduce((count, line) => count + Math.max(0, Number(line.qty || 0)), 0);
    }

    get currentNote() {
        return this.props.selfOrder.general_customer_note || "-";
    }

    get showProductDebugId() {
        const debugValue = new URLSearchParams(window.location.search).get("debug");
        return Boolean(debugValue && debugValue !== "0" && debugValue !== "false");
    }

    getImageUrl(line) {
        if (!line.productId) {
            return null;
        }
        return `/web/image/product.product/${line.productId}/image_128`;
    }

    increase(line) {
        line.qty += 1;
    }

    removeLine(line) {
        this.state.lines = this.state.lines.filter((item) => item.key !== line.key);
    }

    isLastUnit(line) {
        return line.qty <= 1;
    }

    decrease(line) {
        if (this.isLastUnit(line)) {
            this.removeLine(line);
            return;
        }
        line.qty = Math.max(0, line.qty - 1);
    }

    async accept() {
        const lines = this.state.lines.filter((line) => line.qty > 0);
        await this.props.onAccept(lines, this.props.selfOrder);
    }

    deleteOrder() {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Delete self order"),
            body: _t("Are you sure you want to cancel this self order?"),
            confirmLabel: _t("Delete"),
            cancelLabel: _t("Keep"),
            confirm: async () => {
                await this.props.onDelete(this.props.selfOrder);
            },
        });
    }
}
