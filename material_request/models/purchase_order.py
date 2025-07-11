from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purachse_rfq_request = fields.Boolean(string="Material RFQ Request", copy=False)
    indent_id = fields.Many2one('material.request.indent', 'Indent')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    responsible = fields.Many2one('res.partner', string='Request Raised By')
    requested = fields.Many2one('res.partner', string='Request Raised For')
    shipment = fields.Boolean('Shipment', copy=False)

    def create_qty_material(self):

        print("##############    def create_qty_material(self):###################")
        material_requisition_sr = self.env['material.request.indent'].search([('name', '=', self.origin)])
        purchase_order = self.env['purchase.order'].search([('name', '=', self.origin), ('state', '=', 'purchase')])
        mr_list = self.env['material.request.indent'].search([('name', '=', purchase_order.origin)])
        stock_pic = self.env['stock.picking'].search([('origin', '=', self.origin)])
        if self.origin:
            mr_list.update({
                'grn_status': True,
                'ribbon_state': 'grn_completed',
            })
        for num in stock_pic:
            if num.state == 'assigned':
                material_requisition_sr.update({
                    'state': 'done',
                    'stock_transferred': True,
                    'ribbon_state': 'delivery_done',
                    'issued_date': num.write_date,
                    'inward_date': num.scheduled_date,
                })
            added_qty = 0.0
            for line in material_requisition_sr.product_lines:
                added_qty = 0.0
                for val in stock_pic:
                    for qty in val.move_ids_without_package:
                        if qty.product_id.id == line.product_id.id:
                            added_qty += qty.quantity
                            product_id = qty.product_id
                    if val.product_id.id == line.product_id.id:
                        line.update({
                            'qty_shipped': added_qty,
                        })
            return True

    # def button_validate(self):
    #     self.create_qty_material()
    #     print('MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMn')
    #     return super().button_validate()

    def button_validate(self):
        print('LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLl')
        for picking in self:
            StockQuant = self.env['stock.quant']
            self.create_qty_material()
            if picking.picking_type_id.code == 'internal':
                print('LLLLLLLLLLLLLLLLLLLLLLLLLLLL            if picking.picking_type_id.code ==:LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLl')

                for move_line in picking.move_line_ids:
                    if move_line.lot_id and move_line.quantity:
                        # Calculate remaining quantity in the original lot
                        remaining_qty = move_line.lot_id.product_qty - move_line.quantity
                        if remaining_qty < 0:
                            raise UserError('Insufficient quantity in the original lot.')

                        original_quant = StockQuant.search([
                            ('product_id', '=', move_line.product_id.id),
                            ('lot_id', '=', move_line.lot_id.id),
                            ('location_id', '=', self.env.ref('stock.stock_location_stock').id)
                        ], limit=1)
                        if original_quant:
                            original_quant.quantity = remaining_qty

                        # Create a new lot
                        new_lot = self.env['stock.lot'].create({
                            'product_id': move_line.product_id.id,
                        })
                        new_quant = StockQuant.create({
                            'product_id': move_line.product_id.id,
                            'location_id': self.env.ref('stock.stock_location_stock').id,
                            'lot_id': new_lot.id,
                            'quantity': move_line.quantity,
                        })

                        # Assign the new lot to the move line
                        move_line.lot_id = new_lot.id
        return super(StockPicking, self).button_validate()


