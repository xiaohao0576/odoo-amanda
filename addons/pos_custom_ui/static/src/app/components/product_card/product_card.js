import { patch } from "@web/core/utils/patch";
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import { useService } from "@web/core/utils/hooks";

const USD_TO_KHR_RATE = 4000;

patch(ProductCard.prototype, {
    setup() {
        super.setup?.();
        this.ui = useService("ui");
    },

    getPosCustomUsdPrice() {
        const price = this.props.product?.list_price || 0;
        const formatted = Number.isInteger(price)
            ? String(price)
            : price.toFixed(2).replace(/\.0+$|(?<=\..*?)0+$/g, "");
        return `${formatted}$`;
    },

    getPosCustomKhrPrice() {
        const price = this.props.product?.list_price || 0;
        return `\u17db${Math.round(price * USD_TO_KHR_RATE)}`;
    },

    getPosCustomCode() {
        return (this.props.product?.default_code || "").trim();
    },


    getPosCustomProductName(languageCode) {
        const names = this.props.product?.all_language_names_json || {};
        return (names[languageCode] || "").trim();
    },

    getPosCustomEnglishName() {
        const en = this.getPosCustomProductName("en_US");
        return en ? en.toUpperCase() : (this.props.name || "").toUpperCase();
    },

    getPosCustomKhmerName() {
        const km = this.getPosCustomProductName("km_KH");
        const en = this.getPosCustomProductName("en_US") || this.props.name || "";
        return km && km !== en ? km : "";
    },

    getPosCustomChineseName() {
        const zh = this.getPosCustomProductName("zh_CN");
        const en = this.getPosCustomProductName("en_US") || this.props.name || "";
        return zh && zh !== en ? zh : "";
    },
});
