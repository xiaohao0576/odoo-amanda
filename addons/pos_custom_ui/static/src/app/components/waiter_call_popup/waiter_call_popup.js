import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class WaiterCallPopup extends Component {
    static template = "pos_custom_ui.WaiterCallPopup";
    static props = {
        close: Function,
        closeLabel: { type: String, optional: true },
    };

    static defaultProps = {
        closeLabel: _t("Close"),
    };
}
