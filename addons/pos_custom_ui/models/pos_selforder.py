import json
from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import api, fields, models


class PosSelfOrder(models.Model):
    _name = "pos.selforder"
    _description = "POS Self Order Queue"
    _inherit = ["pos.load.mixin"]
    _order = "create_date asc, id asc"
    _check_company_auto = True

    uuid = fields.Char(required=True, index=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("cancel", "Cancelled"),
            ("done", "Done"),
            ("stale", "Stale"),
        ],
        default="draft",
        required=True,
        index=True,
    )
    table_id = fields.Many2one("restaurant.table", index=True)
    session_id = fields.Many2one("pos.session", required=True, index=True, check_company=True)
    config_id = fields.Many2one("pos.config", required=True, index=True, check_company=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    general_customer_note = fields.Text()
    order_lines = fields.Text(required=True)
    processed_at = fields.Datetime()
    processed_by = fields.Many2one("hr.employee")

    _sql_constraints = [
        ("pos_selforder_uuid_uniq", "unique(uuid)", "Self order uuid must be unique."),
    ]

    def init(self):
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS pos_selforder_cfg_tbl_state_create_idx
            ON pos_selforder (company_id, config_id, table_id, state, create_date, id)
            """
        )

    @api.model
    def _load_pos_data_domain(self, data, config):
        if not config.module_pos_restaurant:
            return [(False, "=", True)]
        return [
            ("company_id", "=", config.company_id.id),
            ("config_id", "=", config.id),
            ("state", "=", "draft"),
        ]

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "uuid",
            "state",
            "table_id",
            "session_id",
            "config_id",
            "company_id",
            "general_customer_note",
            "order_lines",
            "processed_at",
            "processed_by",
            "create_date",
            "write_date",
        ]

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        # Keep self-order client payload lean and private.
        return [(False, "=", True)]

    @api.model
    def _load_pos_self_data_fields(self, config):
        return ["id"]

    @api.model
    def _serialize_frontend_order(self, order_payload):
        return json.dumps(order_payload or {}, separators=(",", ":"))

    @api.model
    def _build_vals_from_frontend(self, order_payload, pos_config, table):
        uuid = (order_payload or {}).get("uuid")
        if not uuid:
            raise ValueError("Missing order uuid")

        return {
            "uuid": uuid,
            "state": "draft",
            "table_id": table.id if table and table.exists() else False,
            "session_id": pos_config.current_session_id.id,
            "config_id": pos_config.id,
            "company_id": pos_config.company_id.id,
            "general_customer_note": (order_payload or {}).get("general_customer_note") or "",
            "order_lines": self._serialize_frontend_order(order_payload),
            "processed_at": False,
            "processed_by": False,
        }

    @api.model
    def _check_creation_limits(self, pos_config, table, uuid):
        existing = self.search([("uuid", "=", uuid)], limit=1)
        if existing:
            return existing

        if not table:
            return existing

        params = self.env["ir.config_parameter"].sudo()
        max_draft_per_table = params.get_int("pos_custom_ui.selforder.max_draft_per_table", 3)
        max_new_per_minute = params.get_int("pos_custom_ui.selforder.max_new_per_minute", 20)

        draft_count = self.search_count(
            [
                ("company_id", "=", pos_config.company_id.id),
                ("config_id", "=", pos_config.id),
                ("table_id", "=", table.id),
                ("state", "=", "draft"),
            ]
        )
        if draft_count >= max_draft_per_table:
            raise ValueError("Too many pending orders for this table")

        now = fields.Datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        recent_creates = self.search_count(
            [
                ("company_id", "=", pos_config.company_id.id),
                ("config_id", "=", pos_config.id),
                ("table_id", "=", table.id),
                ("create_date", ">=", one_minute_ago),
            ]
        )
        if recent_creates >= max_new_per_minute:
            raise ValueError("Submission rate exceeded for this table")

        return existing

    @api.model
    def upsert_from_frontend(self, order_payload, pos_config, table):
        vals = self._build_vals_from_frontend(order_payload, pos_config, table)
        existing = self._check_creation_limits(pos_config, table, vals["uuid"])

        if existing and existing.state != "draft":
            return existing, "ignored"

        if existing and existing.state == "draft":
            existing.write(vals)
            return existing, "updated"

        try:
            with self.env.cr.savepoint():
                record = self.create(vals)
                return record, "created"
        except IntegrityError:
            # Concurrent request created it first.
            pass

        record = self.search([("uuid", "=", vals["uuid"])], limit=1)
        if not record:
            raise ValueError("Unable to create or locate self order")
        if record.state == "draft":
            record.write(vals)
            return record, "updated"
        return record, "ignored"

    def _notify_state_to_mobile(self):
        self.ensure_one()
        self.config_id._notify(
            "SELFORDER_STATE",
            {
                "uuid": self.uuid,
                "state": self.state,
                "table_id": self.table_id.id if self.table_id else False,
                "table_identifier": self.table_id.identifier if self.table_id else False,
            },
        )

    def _notify_state_change(self):
        by_config = {}
        for record in self:
            config_id = record.config_id.id
            by_config.setdefault(config_id, self.env["pos.selforder"])
            by_config[config_id] |= record

        for config_id, records in by_config.items():
            config = self.env["pos.config"].browse(config_id)
            session_id = config.current_session_id.id if config.current_session_id else False
            if session_id:
                config.notify_synchronisation(session_id, "self-order-mobile", {"pos.selforder": records.ids})
            for record in records:
                record._notify_state_to_mobile()

    def _mark_processed(self, new_state):
        allowed = {"done", "cancel", "stale"}
        if new_state not in allowed:
            return False

        updated = self.filtered(lambda r: r.state == "draft")
        if not updated:
            return False

        updated.write(
            {
                "state": new_state,
                "processed_at": fields.Datetime.now(),
                "processed_by": self.env.user.employee_id.id or False,
            }
        )
        updated._notify_state_change()
        return True

    def action_mark_done(self):
        return self._mark_processed("done")

    def action_mark_cancel(self):
        return self._mark_processed("cancel")

    @api.model
    def cron_mark_stale_drafts(self):
        params = self.env["ir.config_parameter"].sudo()
        stale_minutes = params.get_int("pos_custom_ui.selforder.stale_minutes", 30)
        deadline = fields.Datetime.now() - timedelta(minutes=stale_minutes)
        stale_candidates = self.search([("state", "=", "draft"), ("create_date", "<", deadline)])
        stale_candidates._mark_processed("stale")
        return True


class PosSession(models.Model):
    _inherit = "pos.session"

    @api.model
    def _load_pos_data_models(self, config):
        models = super()._load_pos_data_models(config)
        if "pos.selforder" not in models:
            models.append("pos.selforder")
        return models


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _load_self_data_models(self):
        models = super()._load_self_data_models()
        if "pos.selforder" in models:
            models.remove("pos.selforder")
        return models
