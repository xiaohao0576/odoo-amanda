import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { debounce } from "@web/core/utils/timing";

const PRODUCT_INFO_LONG_PRESS_DURATION = 5000;

function createProductInfoLongPressHandlers(callback, delay = PRODUCT_INFO_LONG_PRESS_DURATION) {
    let timer = null;

    function startLongPress(params) {
        timer = setTimeout(() => {
            callback(params);
        }, delay);
    }

    function cancelLongPress() {
        if (timer) {
            clearTimeout(timer);
            timer = null;
        }
    }

    return {
        onMouseDown(event, params) {
            if (event.button === 0) {
                startLongPress(params);
            }
        },
        onMouseUp: cancelLongPress,
        onTouchStart: startLongPress,
        onTouchEnd: cancelLongPress,
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
