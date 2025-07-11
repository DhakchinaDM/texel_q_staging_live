from odoo.exceptions import ValidationError, UserError
from odoo import api, fields, models, _
import time


class CustomerRelease(models.Model):
    _name = 'customer.release'
    _description = 'Customer Release'
    _inherit = ['mail.thread.cc', 'mail.thread.main.attachment', 'mail.activity.mixin']

    # INVISIBLE FIELDS START
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    active = fields.Boolean(default=True)
    # INVISIBLE FIELDS END

    name = fields.Char(string='Name', default='New')
    partner_id = fields.Many2one('res.partner', string='Customer')
    po_ref = fields.Char(string='Po Ref')
    ship_to = fields.Char(string='Ship to')
    part_no = fields.Many2one('product.template', string='Part No Cust Part',
                              domain=lambda self: self._get_layout_product_domain())
    qty_ready = fields.Float(string='Qty Ready')
    qty_loaded = fields.Float(string='Qty Loaded')
    qty_wip = fields.Float(string='Qty WIP')
    ship_date_shipper_no = fields.Char(string='Ship date Shipper No')
    due_date = fields.Date(string='Due Date')
    rel_qty = fields.Float(string='Rel Qty')
    shipped = fields.Float(string='Shipped')
    rel_bal = fields.Float(string='Rel Bal')
    total_rel_due = fields.Float(string='Total Rel Due')
    rel_status = fields.Char(string='Rel Status')
    rel_type = fields.Char(string='Rel Type')
    schedule_qty = fields.Char(string='Schedule Quantity')
    state = fields.Selection([('new', 'New'), ('complete', 'Completed')], default='new')

    def action_create_delivery(self):
        self.ensure_one()
        delivery_vals = {
            'partner_id': self.partner_id.id,
            'move_type': 'direct',
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_ids_without_package': [(0, 0, {
                'product_id': self.part_no.product_variant_id.id,
                'product_uom': self.part_no.uom_id.id,
                'name': self.part_no.product_variant_id.name,
                'quantity': self.rel_qty,
                'product_uom_qty': self.rel_qty,
                'location_id': self.env.ref('stock.stock_location_stock').id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            })],
        }
        delivery = self.env['stock.picking'].create(delivery_vals)
        delivery.action_confirm()
        delivery.action_assign()
        return True

    @api.constrains('rel_qty')
    def restrict_job_qty(self):
        if self.rel_qty <= 0.00:
            raise ValidationError("Alert, Mr. %s.\nRel Quantity cannot be Zero."
                                  % self.env.user.name)

    @api.model
    def _get_layout_product_domain(self):
        finished_goods_category = self.env.ref('inventory_extended.category_finished_goods')
        return [('categ_id', '=', finished_goods_category.id)]

    def action_confirm(self):
        self.write({
            'state': 'complete'
        })

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.sudo().env['ir.sequence'].next_by_code('customer.release') or '/'
        return super().create(vals_list)