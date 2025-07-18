from odoo import models, fields, api, _


class ShUpdateQtyWizard(models.TransientModel):
    _name = 'update.qty'
    _description = 'Update Qty'

    sh_qty = fields.Float("Quantity", required=True)
    comments = fields.Text("Comments")

    def action_change_qty(self):
        context = dict(self._context or {})
        purchase_order_line_id = self.env['purchase.order.line'].sudo().search([('id', '=', context.get('active_id'))],
                                                                               limit=1)
        if purchase_order_line_id:
            purchase_order_line_id.product_qty = self.sh_qty
            purchase_order_line_id.comments = self.comments
