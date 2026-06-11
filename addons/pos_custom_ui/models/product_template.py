# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    all_language_names_json = fields.Json(
        compute='_compute_all_language_names_json',
        store=False,
        readonly=True,
    )

    @api.depends('name')
    def _compute_all_language_names_json(self):
        if not self:
            return

        language_codes = self.env['res.lang'].search([('active', '=', True)]).mapped('code')
        names_by_lang = {}
        for language_code in language_codes:
            records = self.with_context(lang=language_code).read(['name'], load=False)
            names_by_lang[language_code] = {record['id']: record['name'] for record in records}

        for template in self:
            template.all_language_names_json = {
                language_code: names_by_lang[language_code].get(template.id, template.name)
                for language_code in language_codes
            }

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
