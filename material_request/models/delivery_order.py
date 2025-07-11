from odoo import models, fields, api, _

class deliveryOrder(models.Model):
    _inherit = 'stock.picking'
    _description = 'Delevery Order'

    delivery_order_id = fields.Many2one('stock.move.line', 'Indentor', tracking=True)
    show_lot_serial = fields.Boolean(compute="_compute_show_lot_serial", store=False)

    @api.depends('picking_type_code', 'picking_type_id')
    def _compute_show_lot_serial(self):
        for rec in self:
            rec.show_lot_serial = rec.picking_type_id.id == self.env.ref('stock.picking_type_out').id


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    mr_delivery_ids = fields.Many2many('stock.picking', string='Stock')
    picking_id = fields.Many2one('stock.picking', string="Picking",domain="[('id', 'in', mr_delivery_ids)]")

    @api.onchange('mr_delivery_ids')
    def _onchange_mr_delivery_ids(self):
        domain = [('id', 'in', self.mr_delivery_ids.ids)] if self.mr_delivery_ids else []
        return {'domain': {'picking_id': domain}}


