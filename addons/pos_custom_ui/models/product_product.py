# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    all_language_names_json = fields.Json(
        compute='_compute_all_language_names_json',
        store=False,
        readonly=True,
    )

    @api.depends('name', 'product_tmpl_id.name')
    def _compute_all_language_names_json(self):
        for product in self:
            product.all_language_names_json = product.product_tmpl_id.all_language_names_json or {}

    @api.model
    def _load_pos_data_fields(self, config):
        fields_list = super()._load_pos_data_fields(config)
        if 'all_language_names_json' not in fields_list:
            fields_list.append('all_language_names_json')
        return fields_list

    @api.model
    def _load_pos_self_data_fields(self, config):
        fields_list = super()._load_pos_self_data_fields(config)
        if 'all_language_names_json' not in fields_list:
            fields_list.append('all_language_names_json')
        return fields_list
