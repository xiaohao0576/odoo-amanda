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

    _posCustomSelfOrderSort(a, b) {
        const aDate = a.create_date ? +new Date(a.create_date) : 0;
        const bDate = b.create_date ? +new Date(b.create_date) : 0;
        if (aDate !== bDate) {
            return aDate - bDate;
        }
        return (a.id || 0) - (b.id || 0);
    },

    getSelfOrdersByTable(tableId) {
        if (!tableId || !this.models["pos.selforder"]) {
            return [];
        }
        return this.models["pos.selforder"]
            .filter((order) => order.state === "draft" && order.table_id?.id === tableId)
            .sort((a, b) => this._posCustomSelfOrderSort(a, b));
    },

    getSelfOrderDraftCount(tableId) {
        return this.getSelfOrdersByTable(tableId).length;
    },

    getNextSelfOrderForSelectedTable() {
        const tableId = this.selectedTable?.id;
        if (!tableId) {
            return null;
        }
        return this.getSelfOrdersByTable(tableId)[0] || null;
    },

    async markSelfOrderDone(selfOrderId) {
        if (!selfOrderId) {
            return false;
        }
        return await this.data.call("pos.selforder", "action_mark_done", [[selfOrderId]]);
    },

    async markSelfOrderCancelled(selfOrderId) {
        if (!selfOrderId) {
            return false;
        }
        return await this.data.call("pos.selforder", "action_mark_cancel", [[selfOrderId]]);
    },
});
