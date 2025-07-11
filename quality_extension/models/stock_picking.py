from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _description = "Stock Picking"

    income_inspection_ids = fields.Many2many('incoming.inspection', string='Income Inspection', store=True)
    inspection_count = fields.Integer(string="Quality Count", compute='compute_inspection')
    ins_type = fields.Selection([
        ('incoming_raw', 'Raw'),
        ('incoming_part', 'Parts'),
    ], string="Inspection Type")
    process_no = fields.Many2one('process.master', string='Process No & Name')

    # part_operation_line_id = fields.Many2one('part.operation.line', string='Part Operation Line')

    def compute_inspection(self):
        for rec in self:
            rec.inspection_count = self.env['incoming.inspection'].sudo().search_count(
                [('picking_id', '=', rec.id)])

    def view_inspection_raw(self):
        return {
            'name': _('Income Inspection'),
            'type': 'ir.actions.act_window',
            'res_model': 'incoming.inspection',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': self.id,
            'domain': [('picking_id', '=', self.id)],
            'target': 'current'
        }

    # def button_validate(self):
    #     res = super().button_validate()
    #     if any(inspection.state in ['draft'] for inspection in self.income_inspection_ids):
    #         inspection_name = next(
    #             inspection.name for inspection in self.income_inspection_ids if inspection.state != 'done')
    #         raise UserError(
    #             _("Inspection %s is not yet completed. Please ensure all inspections are marked as 'done' before proceeding." % inspection_name))
    #
    #     return res

    # @api.model_create_multi
    # def create(self, vals_list):
    #     res = super().create(vals_list)
    #     for vals, picking in zip(vals_list, res):
    #         if self._is_incoming_picking(vals['picking_type_id']):
    #             purchase = self._get_related_purchase(vals['origin'])
    #             if purchase:
    #                 for move in picking.move_ids_without_package:
    #                     if move.product_id.categ_id.id == self.env.ref('inventory_extended.category_raw_materials').id:
    #                         inspection_vals = self._prepare_inspection_vals(picking, move, purchase)
    #                         income = self.env['incoming.inspection'].create(inspection_vals)
    #                         res.income_inspection_ids = [(4, income.id)]
    #     return res

    def button_validate(self):
        res = super(StockPicking, self).button_validate()

        for vals in self:
            if self._is_incoming_picking(vals.picking_type_id.id):
                purchase = self._get_related_purchase(vals.origin)
                if purchase:
                    for move in vals.move_ids_without_package:
                        if move.product_id.categ_id.id == self.env.ref('inventory_extended.category_raw_materials').id:
                            # inspection_vals = self._prepare_inspection_vals(vals, move, purchase)
                            income = self.env['incoming.inspection'].create({
                                'material_grade': move.product_tmpl_id.material_grade,
                                'product_id': move.product_tmpl_id.id,
                                'partner_id': move.partner_id.id,
                                'picking_id': vals.id,
                                'purchase_id': purchase.id if purchase else False,
                                'po_date': purchase.confirm_date if purchase else False,
                                'draw_rev_no': move.product_tmpl_id.draw_rev_no,
                                'draw_rev_date': move.product_tmpl_id.draw_rev_date,
                                'lot_qty': move.quantity,
                                'lot_id': move.lot_ids[0].id if move.lot_ids else False,
                                'dc_invoice_no': move.supplier_reference,
                                'grn_date': vals.create_date,
                                'stock_move_id': move.id,
                                'inspection_incoming_type': vals.ins_type,
                                'parameters_ids': self._prepare_parameters_vals(move)
                            })
                            vals.income_inspection_ids = [(4, income.id)]
        return res
    def _is_incoming_picking(self, picking_type_id):
        picking_type = self.env['stock.picking.type'].browse(picking_type_id)
        return picking_type.code == 'incoming'

    def _get_related_purchase(self, origin):
        return self.env['purchase.order'].search([('name', '=', origin), ('state', '=', 'purchase')], limit=1)

    def _prepare_inspection_vals(self, picking, move, purchase):
        return {
            'material_grade': move.product_tmpl_id.material_grade,
            'product_id': move.product_tmpl_id.id,
            'partner_id': move.partner_id.id,
            'picking_id': picking.id,
            'purchase_id': purchase.id if purchase else False,
            'po_date': purchase.confirm_date if purchase else False,
            'draw_rev_no': move.product_tmpl_id.draw_rev_no,
            'draw_rev_date': move.product_tmpl_id.draw_rev_date,
            'lot_qty': move.quantity,
            'lot_id': move.lot_ids.id,
            'dc_invoice_no': move.supplier_reference,
            'grn_date': picking.create_date,
            'stock_move_id': move.id,
            'inspection_incoming_type': picking.ins_type,
            'parameters_ids': self._prepare_parameters_vals(move)
        }

    def _prepare_parameters_vals(self, move):
        return [(0, 0, {
            'parameter_id': p.parameter_id.id,
            'check_method_id': [(6, 0, p.check_method_id.ids)],
            'specification': p.specification,
            'min_level': p.min_level,
            'max_level': p.max_level,
            'baloon_no': p.baloon_no,
        }) for p in move.product_tmpl_id.quality_parameters]


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def generate_grn(self):
        picking = self.env.ref('stock.picking_type_in')
        if self.stock_done == 0.00:
            raise ValidationError("Done quantity cannot be zero.")
        elif self.stock_done > self.balanced_delivery:
            raise ValidationError("Done value must be greater than Quantity.")
        stock_location = self.env.ref('stock.stock_location_stock')
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        grn = self.env['stock.picking'].sudo().create({
            'partner_id': self.partner_id.id,
            'origin': self.order_id.name,
            'purchase_id': self.order_id.id,
              'location_id': picking.default_location_src_id.id,
                'location_dest_id': picking.default_location_dest_id.id,
            # 'supplier_reference': self.supplier_reference,
            # 'inv_date': self.inv_date,
            'state': 'assigned',
            'ins_type': 'incoming_raw',
            'picking_type_id': picking.id,
            'move_ids_without_package': [(0, 0, {
                'name': self.product_id.name,
                'product_id': self.product_id.id,
                'product_uom': self.product_id.uom_id.id,
                'product_uom_qty': self.stock_done,
                'quantity': 0,
                'location_id': picking.default_location_src_id.id,
                'location_dest_id': picking.default_location_dest_id.id,
                'purchase_line_id': self.id,
                'price_unit': self.price_unit,
                'mfg_date': self.mfg_date,
                'supplier_reference': self.supplier_reference,
                'inv_date': self.inv_date,
            })],
        })
        print('====================grn', grn)
        self.order_id.grn_reference = grn.id
        self.order_id.picking_ids = [(4, grn.id)]
        self.balance = self.balanced_delivery - self.stock_done
        self.stock_done = 0.00
        self.balanced_delivery = self.balance
        if self.balanced_delivery != 0.00:
            self.write({
                # 'grn_created': True,
                'status': 'progress',
            })
        else:
            self.write({
                'grn_created': True,
                'status': 'confirm',
            })
        grn.action_confirm()
        stock = self.env['stock.picking'].search([('origin', '=', self.order_id.name), ('state', '=', 'assigned')])
        stock.write({
            'po_date_time': self.order_id.confirm_date
        })
        stock.button_validate()
        stock.print_grn_label()
        stock.create_bill()
        if self.product_id.print_grn_label:
            val = self.env.ref('supplier_perfomance.report_grn_label_pdf').report_action(stock)
        else:
            val = False
        return val

    def generate_grn_po(self):
        picking = self.env.ref('stock.picking_type_in')

        stock_location = self.env.ref('stock.stock_location_stock')
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        context = dict(self._context or {})
        purchase_order_line = self.env['purchase.order.line'].sudo().search([('id', 'in', context.get('active_ids'))])
        po_list = []

        for rec in purchase_order_line:
            if rec.state != 'confirm':
                if rec.order_id and rec.order_id not in po_list:
                    po_list.append(rec.order_id)

        for po in po_list:
            move_lines = []

            for pol in purchase_order_line:
                if po.partner_id.id == pol.partner_id.id:
                    move_line_vals = {
                        'product_id': pol.product_id.id,
                        'name': pol.product_id.name,
                        'product_uom': pol.product_id.uom_id.id,
                        'product_uom_qty': pol.stock_done,
                        'quantity': 0,
                        'location_id': picking.default_location_src_id.id,
                        'location_dest_id': picking.default_location_dest_id.id,
                        'purchase_line_id': pol.id,
                        'supplier_reference': pol.supplier_reference,
                        'inv_date': pol.inv_date,
                    }
                    print('====move_line_vals=====', move_line_vals)
                    move_lines.append((0, 0, move_line_vals))

                    pol.balance = pol.balanced_delivery - pol.stock_done
                    pol.stock_done = 0.00
                    pol.balanced_delivery = pol.balance

                    if pol.balanced_delivery != 0.00:
                        pol.write({'status': 'progress'})
                    else:
                        pol.write({'grn_created': True, 'status': 'confirm'})

            picking_vals = {
                'partner_id': po.partner_id.id,
                'origin': po.name,
                'purchase_id': po.id,
                'ins_type': 'incoming_raw',
                'user_id': self.env.user.id,
                'scheduled_date': fields.Datetime.now(),
                'picking_type_id': picking.id,
                 'location_id': picking.default_location_src_id.id,
                'location_dest_id': picking.default_location_dest_id.id,
                'state': 'assigned',
                'move_ids_without_package': move_lines,
            }

            picking = self.env['stock.picking'].create(picking_vals)

            po.picking_ids = [(4, picking.id)]

            self.order_id.grn_reference = picking.id

            picking.action_confirm()
            picking.print_grn_label()
            picking.create_bill()
            picking.button_validate()

            for r in purchase_order_line:
                if r.product_id.print_grn_label:
                    return self.env.ref('supplier_perfomance.report_grn_label_pdf').report_action(picking)
            else:
                return False
