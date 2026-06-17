import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

export const POS_CUSTOM_CURRENT_ORDER_CATEGORY_ID = "__pos_custom_current_order__";
export const POS_CUSTOM_ORDERLINE_FOCUS_EVENT = "pos-custom:orderline-focus-product-card";

const originalSetSelectedCategory = PosStore.prototype.setSelectedCategory;
const originalProductToDisplayByCategGetter = Object.getOwnPropertyDescriptor(
    PosStore.prototype,
    "productToDisplayByCateg"
)?.get;

patch(PosStore.prototype, {
    get isPosCustomCurrentOrderCategorySelected() {
        return this._posCustomCurrentOrderCategorySelected === true;
    },

    setSelectedCategory(categoryId) {
        if (categoryId === POS_CUSTOM_CURRENT_ORDER_CATEGORY_ID) {
            this._posCustomCurrentOrderCategorySelected = true;
            // Keep base selected category on "All" while virtual category is active.
            this.selectedCategory = this.models["pos.category"].get(0);
            this._searchTriggered = false;
            return;
        }
        this._posCustomCurrentOrderCategorySelected = false;
        return originalSetSelectedCategory.call(this, categoryId);
    },

    getCurrentOrderProductsForVirtualCategory() {
        const order = this.getOrder();
        if (!order) {
            return [];
        }

        const seenProductTemplateIds = new Set();
        const currentOrderProducts = [];

        for (const line of order.lines || []) {
            if (line.combo_parent_id) {
                continue;
            }
            const productTemplate = line.product_id?.product_tmpl_id;
            if (!productTemplate?.id || seenProductTemplateIds.has(productTemplate.id)) {
                continue;
            }
            seenProductTemplateIds.add(productTemplate.id);
            currentOrderProducts.push(productTemplate);
        }

        return this.filterExcludedProducts(currentOrderProducts);
    },

    get productToDisplayByCateg() {
        if (!this.isPosCustomCurrentOrderCategorySelected) {
            return originalProductToDisplayByCategGetter
                ? originalProductToDisplayByCategGetter.call(this)
                : [];
        }

        let products = this.getCurrentOrderProductsForVirtualCategory();
        if (!products.length) {
            // Avoid getting stuck on the virtual category when opening a new empty order.
            this._posCustomCurrentOrderCategorySelected = false;
            this.posCustomSelectedProductTemplateId = null;
            return originalProductToDisplayByCategGetter
                ? originalProductToDisplayByCategGetter.call(this)
                : [];
        }

        const searchWord = this.searchProductWord.trim();
        if (searchWord) {
            products = this.getProductsBySearchWord(searchWord, products);
        }
        // Keep products in orderline order (no sequence/fav sort for this virtual category).

        return products.length ? [[POS_CUSTOM_CURRENT_ORDER_CATEGORY_ID, products]] : [];
    },
});
