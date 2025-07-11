from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError


class AnalyzeRfq(models.Model):
    _name = 'analyze.rfq'
    _description = 'Analyze RFQ'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    name = fields.Char(string="Name", default='New')
    partner_id = fields.Many2one('res.partner', string='Supplier')
    tender_order = fields.Boolean("Tender Orders")
    agreement_id = fields.Many2one('purchase.agreement', 'Purchase Tender')
    user_id = fields.Many2one('res.users', string='User')
    origin = fields.Char(string='Origin')
    order_line = fields.One2many('analyze.rfq.lines', 'order_id', string='Order Lines')

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.sudo().env['ir.sequence'].next_by_code('analyze.rfq') or '/'
        return super().create(vals_list)


class AnalyzeRfqLines(models.Model):
    _name = 'analyze.rfq.lines'
    _description = 'Analyze RFQ Lines'

    order_id = fields.Many2one('analyze.rfq', string='Order ID')
    status = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirmed'), ('cancel', 'Cancelled')], string="State",
        default='draft')
    agreement_id = fields.Many2one('purchase.agreement', 'Purchase Tender', related='order_id.agreement_id', store=True)
    partner_id = fields.Many2one('res.partner', related='order_id.partner_id', store=True)
    part_name = fields.Char(string='Part Name')
    name = fields.Char(string='Description')
    supplier_part = fields.Char(string='Supplier Part No')
    date_planned = fields.Datetime(string='Date Planned')
    product_qty = fields.Float(string='Quantity')
    product_uom = fields.Many2one('uom.uom', string='UoM')
    price_unit = fields.Float(string='Price Unit')
    price_subtotal = fields.Float(string='Subtotal', compute='_compute_price_subtotal', store=True)

    @api.depends('product_qty', 'price_unit')
    def _compute_price_subtotal(self):
        for record in self:
            record.price_subtotal = record.product_qty * record.price_unit

    def action_confirm(self):
        if self.price_unit == 0:
            raise ValidationError("Please Check the Unit Price")
        self.status = 'confirm'

    def action_cancel(self):
        self.status = 'cancel'
