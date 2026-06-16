import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { debounce } from "@web/core/utils/timing";

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
        this.longPressHandlers = createProductInfoLongPressHandlers((product) =>
            this.pos.onProductInfoClick(product)
        );
        this.onScroll = debounce(this.longPressHandlers.onScroll, 200, { leading: true });
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
});
