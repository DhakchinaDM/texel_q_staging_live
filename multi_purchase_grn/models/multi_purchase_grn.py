from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError


class MultiPurchaseGRN(models.Model):
    _name = 'purchase.grn'
    _description = "Purchase Grn Forms"
    _order = 'name Desc'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']

    @api.model
    def _default_picking_type(self):
        return self._get_picking_type(self.env.context.get('company_id') or self.env.company.id)

    name = fields.Char(string='Name', tracking=True)
    vendor = fields.Many2one('res.partner', string='Receiver From', tracking=True)
    date = fields.Datetime('Date', default=lambda self: fields.Datetime.now())
    product_move_lines = fields.One2many('purchase.grn.lines', 'purchase_grn', tracking=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('validate', 'Validated')], string='State', default="draft", tracking=True)
    picking_count = fields.Integer(string='Receipt Count', compute="picking_count_func")
    picking_type_id = fields.Many2one('stock.picking.type', 'Deliver To', required=True, default=_default_picking_type,
                                      domain="['|', ('warehouse_id', '=', False), ('warehouse_id.company_id', '=', "
                                             "company_id)]",
                                      help="This will determine operation type of incoming shipment")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user)

    @api.model
    def _get_picking_type(self, company_id):
        picking_type = self.env['stock.picking.type'].search(
            [('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)])
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search(
                [('code', '=', 'incoming'), ('warehouse_id', '=', False)])
        return picking_type[:1]

    def picking_count_func(self):
        self.picking_count = self.env['stock.picking'].search_count([('origin', '=', self.name)])

    def get_picking_view(self):
        self.sudo().ensure_one()
        context = dict(self._context or {})
        active_model = context.get('active_model')
        form_view = self.sudo().env.ref('stock.view_picking_form')
        tree_view = self.sudo().env.ref('stock.vpicktree')
        return {
            'name': _('Stock History'),
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('origin', '=', self.name)],
        }

    @api.onchange('vendor')
    def onchange_vendor(self):
        self.product_move_lines = [(5, 0, 0)]
        if self.vendor:
            lines = self.env['purchase.order.line'].search([('partner_id', '=', self.vendor.id)])
            order_lines = [(0, 0, {
                'product_id': line.product_id.id,
                'purchase_order': line.order_id.id,
                'purchase_order_line': line.id,
            }) for line in lines if line.order_id.state == 'purchase' and line.product_qty != line.qty_received]
            self.product_move_lines = order_lines

    def set_to_validate(self):
        StockPicking = self.env['stock.picking']
        StockMove = self.env['stock.move']
        location_id = self.picking_type_id.default_location_src_id.id if self.picking_type_id else False
        location_dest_id = self.picking_type_id.default_location_dest_id.id if self.picking_type_id else False
        for order in self:
            picking_vals = {
                'partner_id': order.vendor.id,
                'picking_type_id': order.picking_type_id.id,
                'origin': order.name,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
            }
            picking = StockPicking.create(picking_vals)

            for line in self.product_move_lines:
                if line.qty > 0.00:
                    move_vals = {
                        'name': line.product_id.name,
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.qty,
                        'quantity': line.qty,
                        'price_unit': line.price_unit,
                        'product_uom': line.uom.id,
                        'picking_id': picking.id,
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'purchase_line_id': line.purchase_order_line.id,
                    }
                    StockMove.create(move_vals)
            # picking.action_confirm()
            self.write({'state': 'validate'})
            return {
                'name': _('GRN'),
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': picking.id,
                'domain': [('origin', '=', self.name)],
                'target': 'current'
            }

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.sudo().env['ir.sequence'].next_by_code('purchase.grn') or '/'
        return super().create(vals_list)


class MultiPurchaseGRNLines(models.Model):
    _name = 'purchase.grn.lines'
    _description = "Purchase Grn Lines"

    purchase_grn = fields.Many2one('purchase.grn')
    purchase_order = fields.Many2one('purchase.order', string='Source Document')
    purchase_order_line = fields.Many2one('purchase.order.line', string='Order Line')
    product_id = fields.Many2one('product.product', string='Product')
    uom = fields.Many2one('uom.uom', string='Uom', related='product_id.uom_id')
    qty = fields.Float(string='Receive Qty')
    order_qty = fields.Float(string='Demand Qty', related='purchase_order_line.product_qty')
    receive_qty = fields.Float(string='Received', related='purchase_order_line.qty_received')
    price_unit = fields.Float(string="Unit Price", related='purchase_order_line.price_unit')

    @api.onchange('qty')
    def _demand_qty_check(self):
        for i in self:
            if i.qty:
                demand_limit = i.receive_qty + i.qty
                if i.order_qty < demand_limit:
                    raise ValidationError(_("Demand Qty Must me Less than or Equal to %s", i.order_qty))


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _order = 'name desc'

    invoice_count = fields.Integer(string='Invoices', compute='_compute_invoice_count')
    operation_code = fields.Selection(string="", related='picking_type_id.code')

    def action_open_picking_invoice(self):
        """This is the function of the smart button which redirect to the
        invoice related to the current picking"""
        return {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('invoice_origin', '=', self.name)],
            'context': {'create': False},
            'target': 'current'
        }

    def _compute_invoice_count(self):
        """This compute function used to count the number of invoice for the picking"""
        self.invoice_count = self.env['account.move'].search_count([('invoice_origin', '=', self.name)])

    def create_bill(self):
        """This is the function for creating vendor bill from the picking"""
        for picking_id in self:
            current_user = self.env.uid
            if picking_id.picking_type_id.code == 'incoming':
                invoice_line_list = []
                for move_ids_without_package in picking_id.move_ids_without_package:
                    vals = (0, 0, {
                        'name': move_ids_without_package.description_picking,
                        'product_id': move_ids_without_package.product_id.id,
                        'price_unit': move_ids_without_package.price_unit,
                        'account_id': move_ids_without_package.product_id.property_account_income_id.id if move_ids_without_package.product_id.property_account_income_id
                        else move_ids_without_package.product_id.categ_id.property_account_income_categ_id.id,
                        'tax_ids': [(6, 0, [picking_id.company_id.account_purchase_tax_id.id])],
                        'quantity': move_ids_without_package.quantity,
                    })
                    invoice_line_list.append(vals)
                invoice = picking_id.env['account.move'].create({
                    'move_type': 'in_invoice',
                    'invoice_origin': picking_id.name,
                    'invoice_user_id': current_user,
                    'narration': picking_id.name,
                    'partner_id': picking_id.partner_id.id,
                    'currency_id': picking_id.env.user.company_id.currency_id.id,
                    'payment_reference': picking_id.name,
                    'picking_id': picking_id.id,
                    'invoice_line_ids': invoice_line_list,
                    'ref': picking_id.supplier_reference,
                    'invoice_date': picking_id.inv_date,
                })

                picking_id.purchase_id.invoice_ids = [(4, invoice.id)]
            for line in picking_id.move_ids_without_package:
                if line.purchase_line_id:
                    purchase_line = line.purchase_line_id
                    billed_qty = purchase_line.qty_invoiced + line.quantity
                    purchase_line.write({'qty_invoiced': billed_qty})



class AccountMove(models.Model):
    _inherit = 'account.move'

    picking_id = fields.Many2one('stock.picking', string='Picking')


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    balance_qty = fields.Float(string="Balance Qty", compute='_compute_balance_qty', store=True)

    @api.depends('qty_received', 'product_qty')
    def _compute_balance_qty(self):
        for i in self:
            if i.product_qty and i.qty_received:
                i.balance_qty = i.product_qty - i.qty_received
            elif i.product_qty and not i.qty_received:
                i.balance_qty = i.product_qty
            else:
                i.balance_qty = 0.00
