import { patch } from "@web/core/utils/patch";
import { CategorySelector } from "@point_of_sale/app/components/category_selector/category_selector";
import { _t } from "@web/core/l10n/translation";
import { POS_CUSTOM_CURRENT_ORDER_CATEGORY_ID } from "@pos_custom_ui/app/services/pos_store";

const originalGetCategoriesAndSub = CategorySelector.prototype.getCategoriesAndSub;
const originalIsAncestorOrSelected = CategorySelector.prototype.isAncestorOrSelected;
const originalShowCategoryImg = CategorySelector.prototype.showCategoryImg;

patch(CategorySelector.prototype, {
    getPosCustomCurrentOrderCategory() {
        return {
            id: POS_CUSTOM_CURRENT_ORDER_CATEGORY_ID,
            name: _t("Current Order"),
            color: "custom_current_order",
            imgSrc: undefined,
            isSelected: this.pos.isPosCustomCurrentOrderCategorySelected,
            isChildren: false,
        };
    },

    getCategoriesAndSub() {
        const currentOrderCategory = this.getPosCustomCurrentOrderCategory();
        return [currentOrderCategory, ...originalGetCategoriesAndSub.call(this)];
    },

    isAncestorOrSelected(category) {
        if (category.id === POS_CUSTOM_CURRENT_ORDER_CATEGORY_ID) {
            return this.pos.isPosCustomCurrentOrderCategorySelected;
        }
        return originalIsAncestorOrSelected.call(this, category);
    },

    showCategoryImg(category) {
        if (category.id === POS_CUSTOM_CURRENT_ORDER_CATEGORY_ID) {
            return false;
        }
        return originalShowCategoryImg.call(this, category);
    },
});
