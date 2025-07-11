from odoo import models, fields, api, _
from odoo.tests.common import Form, tagged
from odoo.exceptions import AccessError, UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    job_work_status = fields.Selection([
        ('new', 'New'),
        ('send', 'Send'),
        ('received', 'Received'),
        ('completed', 'Completed'),
    ], string='Job Work Status', default='new')
    job_work_id = fields.Many2one('stock.picking', string='Job Work Order', store=True)
    return_job_work_id = fields.Many2one('stock.picking', string='Return Job Work Order', store=True)
    job_work_ids = fields.One2many('stock.picking', 'job_work_id', string='Job Work Orders')
    return_job_work_ids = fields.One2many('stock.picking', 'return_job_work_id', string='Return Job Work Orders')


    def create_r_dc(self):
        # context = dict(self._context or {})
        # stock_picking_ids = self.env['stock.picking'].sudo().search([('id', 'in', context.get('active_ids'))])
        # print('lllllll', stock_picking_ids)

        return {
            'name': _('Combine Job'),
            'res_model': 'merge.dc',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('merge_delivery_dc.view_merger_dc_form').id,
            'target': 'new',
            # 'context': {'default_picking_ids': [(6, 0, self.ids)]},
        }


class MergeDC(models.Model):
    _name = 'merge.dc'
    _description = "Merge DC"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)

        line_val = []
        context = dict(self._context or {})
        stock_picking_ids = self.env['stock.picking'].sudo().search([('id', 'in', context.get('active_ids'))])

        if not stock_picking_ids:
            return res

        first_partner = stock_picking_ids[0].partner_id

        if any(picking.partner_id != first_partner for picking in stock_picking_ids):
            raise UserError(_("All selected pickings must belong to the same partner."))
        if any(picking.state != 'assigned' for picking in stock_picking_ids):
            raise UserError(_("All selected pickings must be in the 'Assigned' state."))

        for line in stock_picking_ids:
            for l in line.move_ids_without_package:
                line_data = (0, 0, {
                    'picking_id': l.picking_id.id,
                    'return_picking_id': l.picking_id.return_id.id,
                    'product_id': l.product_id.id,
                    'product_qty': l.product_uom_qty,
                    'confirm_qty': l.product_uom_qty,
                    'lot_ids': [(6, 0, l.lot_ids.ids)],
                })
                line_val.append(line_data)

        res["picking_ids"] = [(6, 0, stock_picking_ids.ids)]
        res['merge_order_ids'] = line_val
        return res

    name = fields.Char(string='Name')
    picking_ids = fields.Many2many('stock.picking', string='Delivery Challan')
    merge_order_ids = fields.One2many('merge.order', 'merge_dc_id', string='Merge Order')

    def create_r_dc(self):
        StockPicking = self.env['stock.picking']
        StockMove = self.env['stock.move']

        if not self.merge_order_ids:
            raise UserError(_("No product lines found to process."))

        first_picking = self.picking_ids[0]
        partner = first_picking.partner_id
        picking_type_id = first_picking.picking_type_id.id
        location_dest_id = first_picking.location_dest_id.id
        location_id = first_picking.location_id.id

        # Create Received Picking Entry
        received_picking = StockPicking.create({
            'partner_id': partner.id,
            'picking_type_id': picking_type_id,
            'quality': first_picking.quality,
            'location_id': location_id,
            'ins_type': 'incoming_part',
            'location_dest_id': location_dest_id,
            'origin': ', '.join(self.picking_ids.mapped('name')),
            'move_ids_without_package': []
        })

        # Prepare balance picking data
        original_product_quantities = {}  # Store original picking quantities
        selected_product_quantities = {}  # Store received quantities from popup

        for picking in self.picking_ids:
            for move in picking.move_ids_without_package:
                product = move.product_id
                if product in original_product_quantities:
                    original_product_quantities[product] += move.product_uom_qty
                else:
                    original_product_quantities[product] = move.product_uom_qty

        from collections import defaultdict

        product_lines = defaultdict(list)
        for line in self.merge_order_ids:
            if line.product_qty > 0:
                product_lines[line.product_id].append(line)

        # Loop through each product group
        for product, lines in product_lines.items():
            total_received_qty = sum(line.product_qty for line in lines)

            # Create one stock move per product
            move = StockMove.create({
                'picking_id': received_picking.id,
                'name': "Merge DC",
                'product_id': product.id,
                'product_uom_qty': total_received_qty,
                'product_uom': product.uom_id.id,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
            })

            # Store total received quantity
            selected_product_quantities[product] = total_received_qty

            # Collect all lot lines from all merge_order_ids
            for line in lines:
                for lot_line in line.lot_ids:
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'picking_id': received_picking.id,
                        'product_id': product.id,
                        'product_uom_id': product.uom_id.id,
                        'quantity': lot_line.product_qty,  # Or line.qty_done if you're using that
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'lot_id': lot_line.id,
                    })

        # Prepare balance picking moves
        balance_moves = []
        for product, original_qty in original_product_quantities.items():
            received_qty = selected_product_quantities.get(product, 0)
            balance_qty = original_qty - received_qty

            if balance_qty > 0:
                balance_moves.append({
                    'product_id': product.id,
                    'product_uom_qty': balance_qty,
                    'name': "Balance DC",
                    'product_uom': product.uom_id.id,
                    'location_id': location_id,
                    'location_dest_id': location_dest_id,
                })

        # Create balance picking if needed
        balance_picking = None
        if balance_moves:
            balance_picking = StockPicking.create({
                'partner_id': partner.id,
                'ins_type': 'incoming_part',
                'picking_type_id': picking_type_id,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'origin': ', '.join(self.picking_ids.mapped('name')),
                'move_ids_without_package': []
            })

            for move in balance_moves:
                move['picking_id'] = balance_picking.id
                StockMove.create(move)

        # Confirm pickings
        received_picking.action_confirm()
        # received_picking.button_validate()
        received_picking.write({
            'job_work_status': 'send',
        })
        if balance_picking:
            balance_picking.action_confirm()

        # Cancel original pickings
        for picking in self.picking_ids:
            picking.action_cancel()
            picking.write({
                'job_work_id': received_picking.id,
                'job_work_status': 'send' if picking.picking_type_code == 'outgoing' else 'completed',
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': received_picking.id,
            'target': 'current',
        }


class MergeDCOrder(models.Model):
    _name = 'merge.order'
    _description = "Merge Order"

    merge_dc_id = fields.Many2one('merge.dc', string='Merge DC')
    picking_id = fields.Many2one('stock.picking', string='Job work')
    return_picking_id = fields.Many2one('stock.picking', string='R-Job Work')
    product_id = fields.Many2one('product.product', string='Product')
    product_qty = fields.Float(string='Qty')

    confirm_qty = fields.Float(string='Confirm Qty')

    lot_ids = fields.Many2many('stock.lot', string='Lot/Serial Number', store=True)
