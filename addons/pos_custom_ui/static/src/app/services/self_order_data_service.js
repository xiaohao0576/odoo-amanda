import { patch } from "@web/core/utils/patch";
import { PosData } from "@point_of_sale/app/services/data_service";

patch(PosData.prototype, {
    initIndexedDB() {
        return true;
    },
    initListeners() {
        return true;
    },
    synchronizeLocalDataInIndexedDB() {
        return true;
    },
    synchronizeServerDataInIndexedDB() {
        return true;
    },
    async getCachedServerDataFromIndexedDB() {
        return {};
    },
    async getLocalDataFromIndexedDB() {
        return {};
    },
    async deleteRecordsInIndexedDB() {
        return true;
    },
});
