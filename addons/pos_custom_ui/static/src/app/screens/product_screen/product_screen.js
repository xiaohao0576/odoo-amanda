import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { debounce } from "@web/core/utils/timing";
import { _t } from "@web/core/l10n/translation";
import { SelfOrderPanel } from "@pos_custom_ui/app/components/selforder_panel/selforder_panel";
import { POS_CUSTOM_CURRENT_ORDER_CATEGORY_ID } from "@pos_custom_ui/app/services/pos_store";

ProductScreen.components = {
    ...ProductScreen.components,
    SelfOrderPanel,
};

const PRODUCT_INFO_LONG_PRESS_DURATION = 5000;
const TOUCH_MOVE_CANCEL_THRESHOLD = 12;

function createProductInfoLongPressHandlers(callback, delay = PRODUCT_INFO_LONG_PRESS_DURATION) {
    let timer = null;
    let activePointerId = null;
    let touchStartPoint = null;

    function startLongPress(params, event = null) {
        cancelLongPress();
        activePointerId = event?.pointerId ?? null;
        touchStartPoint =
            typeof event?.clientX === "number" && typeof event?.clientY === "number"
                ? { x: event.clientX, y: event.clientY }
                : null;
        timer = setTimeout(() => {
            callback(params);
            timer = null;
            activePointerId = null;
            touchStartPoint = null;
        }, delay);
    }

    function cancelLongPress() {
        if (timer) {
            clearTimeout(timer);
        }
        timer = null;
        activePointerId = null;
        touchStartPoint = null;
    }

    return {
        onMouseDown(event, params) {
            if (event.button === 0) {
                startLongPress(params);
            }
        },
        onMouseUp: cancelLongPress,
        onTouchStart(event, params) {
            startLongPress(params, event);
        },
        onTouchEnd: cancelLongPress,
        onPointerCancel: cancelLongPress,
        onPointerLeave: cancelLongPress,
        onPointerMove(event) {
            if (!timer || !touchStartPoint) {
                return;
            }
            if (activePointerId !== null && event.pointerId !== activePointerId) {
                return;
            }
            const movedX = event.clientX - touchStartPoint.x;
            const movedY = event.clientY - touchStartPoint.y;
            if (Math.hypot(movedX, movedY) > TOUCH_MOVE_CANCEL_THRESHOLD) {
                cancelLongPress();
            }
        },
        onScroll: cancelLongPress,
    };
}

patch(ProductScreen.prototype, {
    setup() {
        super.setup?.();
        this.applyPosCustomPreferredCategoryOnEnter();
        this.longPressHandlers = createProductInfoLongPressHandlers((product) =>
            this.pos.onProductInfoClick(product)
        );
        this.onScroll = debounce(this.longPressHandlers.onScroll, 200, { leading: true });
    },

    applyPosCustomPreferredCategoryOnEnter() {
        const currentOrderProducts = this.pos.getCurrentOrderProductsForVirtualCategory?.() || [];
        if (currentOrderProducts.length > 0) {
            this.pos.setSelectedCategory(POS_CUSTOM_CURRENT_ORDER_CATEGORY_ID);
        }
    },

    onPointerDown(event, product) {
        if (isNaN(Number(product.id))) {
            return;
        }
        if (event.pointerType === "mouse") {
            this.longPressHandlers.onMouseDown(event, product);
            return;
        }
        this.longPressHandlers.onTouchStart(event, product);
    },

    getPosCustomProductCardClass(product) {
        const focusClass = "pos-custom-orderline-selected";
        const selectedProductTemplateId = this.pos.posCustomSelectedProductTemplateId;
        const highlightClass =
            this.pos.isPosCustomCurrentOrderCategorySelected &&
            selectedProductTemplateId === product.id
                ? focusClass
                : "";
        return `${this.pos.productViewMode} ${highlightClass}`.trim();
    },

    getPosCustomPendingSelfOrder() {
        return this.pos.getNextSelfOrderForSelectedTable();
    },

    getPosCustomTableNumber() {
        return this.pos.selectedTable?.table_number || "-";
    },

    async onPosCustomAcceptSelfOrder(lines, selfOrder) {
        const order = this.pos.getOrder();
        if (!order) {
            return;
        }

        for (const line of lines) {
            const product = line.product || this.pos.models["product.product"].get(line.productId);
            const productTemplateId = product?.product_tmpl_id?.id || product?.product_tmpl_id;
            const productTemplate =
                typeof productTemplateId === "number"
                    ? this.pos.models["product.template"].get(productTemplateId)
                    : product?.product_tmpl_id;
            if (!productTemplate || line.qty <= 0) {
                continue;
            }
            const priceUnit =
                typeof line.priceUnit === "number" && !isNaN(line.priceUnit)
                    ? line.priceUnit
                    : product.getPrice(order.pricelist_id, line.qty, 0, false, product);
            await this.pos.addLineToCurrentOrder(
                {
                    product_tmpl_id: productTemplate,
                    qty: line.qty,
                    price_unit: priceUnit,
                },
                {},
                false
            );
        }

        try {
            await this.pos.markSelfOrderDone(selfOrder.id);
        } catch (error) {
            this.notification.add(error?.message || _t("Failed to mark self order as done."), {
                type: "danger",
            });
        }
    },

    async onPosCustomDeleteSelfOrder(selfOrder) {
        try {
            await this.pos.markSelfOrderCancelled(selfOrder.id);
        } catch (error) {
            this.notification.add(error?.message || _t("Failed to cancel self order."), {
                type: "danger",
            });
        }
    },
});
