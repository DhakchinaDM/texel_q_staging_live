# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    auto_create_lot = fields.Boolean()
    lot_prefix = fields.Char(string='Lot Prefix')
    lot_next_no = fields.Integer(string='Lot Next No')
