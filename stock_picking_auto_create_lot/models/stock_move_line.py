# Copyright 2024 Quartile Limited
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _get_lot_sequence(self):
        self.ensure_one()
        if self.product_id.product_tmpl_id.lot_prefix and self.product_id.product_tmpl_id.lot_next_no:
            lot_seq = str(self.product_id.product_tmpl_id.lot_prefix) +  str(self.product_id.product_tmpl_id.lot_next_no)
            self.product_id.product_tmpl_id.lot_next_no += 1
        else:
            lot_seq = self.env["ir.sequence"].next_by_code("stock.lot.serial")

        return lot_seq
