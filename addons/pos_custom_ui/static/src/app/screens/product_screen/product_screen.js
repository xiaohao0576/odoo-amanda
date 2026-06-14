import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
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
