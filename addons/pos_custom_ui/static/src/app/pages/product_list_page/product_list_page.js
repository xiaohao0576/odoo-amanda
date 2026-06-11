import { patch } from "@web/core/utils/patch";
import { ProductListPage } from "@pos_self_order/app/pages/product_list_page/product_list_page";

const USD_TO_KHR_RATE = 4000;

ProductListPage.template = "pos_custom_ui.ProductListPage";

patch(ProductListPage.prototype, {
    getProductCode(product) {
        return (product.default_code || "").trim();
    },

    getLocalizedProductName(product, languageCode) {
        const names = product.all_language_names_json || {};
        return (names[languageCode] || "").trim();
    },

    getEnglishProductName(product) {
        const englishName = this.getLocalizedProductName(product, "en_US") || (product.name || "").trim();
        return englishName.toUpperCase();
    },

    shouldDisplayTranslatedName(product, languageCode) {
        const translatedName = this.getLocalizedProductName(product, languageCode);
        const englishName = this.getLocalizedProductName(product, "en_US") || (product.name || "").trim();
        return Boolean(translatedName) && translatedName !== englishName;
    },

    getChineseProductName(product) {
        return this.shouldDisplayTranslatedName(product, "zh_CN")
            ? this.getLocalizedProductName(product, "zh_CN")
            : "";
    },

    getKhmerProductName(product) {
        return this.shouldDisplayTranslatedName(product, "km_KH")
            ? this.getLocalizedProductName(product, "km_KH")
            : "";
    },

    getUsdPrice(product) {
        return this.selfOrder.getProductDisplayPrice(product);
    },

    getKhrPrice(product) {
        return Math.round(this.getUsdPrice(product) * USD_TO_KHR_RATE);
    },

    formatUsdPrice(product) {
        const price = this.getUsdPrice(product);
        const formatted = Number.isInteger(price) ? String(price) : price.toFixed(2).replace(/\.0+$|(?<=\..*?)0+$/g, "");
        return `${formatted}$`;
    },

    formatKhrPrice(product) {
        return `៛${this.getKhrPrice(product)}`;
    },
});
