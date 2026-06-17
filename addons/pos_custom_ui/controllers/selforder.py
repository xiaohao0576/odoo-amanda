from werkzeug.exceptions import BadRequest, Unauthorized

from odoo import http
from odoo.http import request


class PosCustomSelfOrderController(http.Controller):
    @http.route(
        "/pos-self-order/process-selforder/<device_type>/",
        auth="public",
        type="jsonrpc",
        website=True,
    )
    def process_selforder(self, order, access_token, table_identifier, device_type):
        pos_config, table = self._verify_authorization(access_token, table_identifier, order)

        if pos_config.self_ordering_mode != device_type:
            raise Unauthorized("Invalid device type")

        if device_type != "mobile":
            raise Unauthorized("Selforder submit is only available in mobile mode")

        if not order:
            raise BadRequest("Missing order payload")

        try:
            record, status = (
                pos_config.env["pos.selforder"]
                .sudo()
                .with_company(pos_config.company_id.id)
                .upsert_from_frontend(order, pos_config, table)
            )
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc

        session_id = pos_config.current_session_id.id if pos_config.current_session_id else False
        if session_id:
            pos_config.notify_synchronisation(
                session_id,
                "self-order-mobile",
                {"pos.selforder": [record.id]},
            )

        return {
            "status": status,
            "selforder": {
                "id": record.id,
                "uuid": record.uuid,
                "state": record.state,
                "table_id": record.table_id.id if record.table_id else False,
                "create_date": record.create_date,
                "write_date": record.write_date,
            },
        }

    def _verify_pos_config(self, access_token, check_active_session=True):
        pos_config_sudo = request.env["pos.config"].sudo().search([("access_token", "=", access_token)], limit=1)
        if self._verify_config_constraint(pos_config_sudo, check_active_session):
            raise Unauthorized("Invalid access token")
        company = pos_config_sudo.company_id
        user = pos_config_sudo.self_ordering_default_user_id
        return (
            pos_config_sudo.sudo(False)
            .with_company(company)
            .with_user(user)
            .with_context(allowed_company_ids=company.ids)
        )

    def _verify_config_constraint(self, pos_config_sudo, check_active_session=True):
        return (
            not pos_config_sudo
            or (pos_config_sudo.self_ordering_mode != "mobile" and pos_config_sudo.self_ordering_mode != "kiosk")
            or (check_active_session and not pos_config_sudo.has_active_session)
        )

    def _verify_authorization(self, access_token, table_identifier, order):
        pos_config = self._verify_pos_config(access_token)
        table_sudo = request.env["restaurant.table"].sudo().search([("identifier", "=", table_identifier)], limit=1)
        preset = request.env["pos.preset"].sudo().browse(order.get("preset_id"))
        is_takeaway = order and pos_config.use_presets and preset and preset.service_at != "table"

        if (
            not table_sudo
            and pos_config.self_ordering_mode != "kiosk"
            and pos_config.self_ordering_service_mode == "table"
            and not is_takeaway
        ):
            raise Unauthorized("Table not found")

        company = pos_config.company_id
        user = pos_config.self_ordering_default_user_id
        table = (
            table_sudo.sudo(False)
            .with_company(company)
            .with_user(user)
            .with_context(allowed_company_ids=company.ids)
        )
        return pos_config, table
