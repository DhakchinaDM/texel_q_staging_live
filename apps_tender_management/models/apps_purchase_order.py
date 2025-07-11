from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError


class ShPurchase(models.Model):
    _inherit = 'purchase.order'

    agreement_id = fields.Many2one('purchase.agreement', 'Purchase Tender')
    cancel_lines = fields.Boolean("Cancel Lines", compute='get_cancel_lines', store=True)
    selected_order = fields.Boolean("Selected Orders")
    tender_order = fields.Boolean("Tender Orders")
    sh_msg = fields.Char("Message", compute='_compute_sh_msg')

    @api.depends('partner_id')
    def _compute_sh_msg(self):
        if self:
            for rec in self:
                rec.sh_msg = ''
                if rec.agreement_id and rec.partner_id.id not in rec.agreement_id.email_partner_ids.ids:
                    rec.sh_msg = ('Info: The selected vendor is not listed in the chosen tender.''\n'
                                  'However, you can still proceed to create a quotation for them.')

    def get_cancel_lines(self):
        if self:
            for rec in self:
                if rec.state == 'cancel':
                    rec.cancel_lines = True
                else:
                    rec.cancel_lines = False


class ShPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    status = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('cancel', 'Cancel')], string="State",
                              default='draft')
    agreement_id = fields.Many2one('purchase.agreement', 'Purchase Tender', related='order_id.agreement_id', store=True)
    cancel_lines = fields.Boolean("Cancel Lines", related='order_id.cancel_lines', store=True)
    on_hand = fields.Float(string='On Hand', compute='_compute_qty_available', store=True)
    hsn_code = fields.Char(string='HSN/SAC Code')


    @api.onchange('stock_done')
    def _onchange_validation_stock_done(self):
        for i in self:
            if i.stock_done > i.balanced_delivery:
                raise ValidationError("Reserved Quantity is not higher than Demand Quantity")

    @api.depends('product_id')
    def _compute_qty_available(self):
        for rec in self:
            rec.on_hand = rec.product_id.qty_available if rec.product_id else 0.00

    def action_confirm(self):
        for rec in self:
            rec.status = 'confirm'
        if self.price_unit == 0:
            raise ValidationError("Please Check the Unit Price")

    def action_cancel(self):
        for rec in self:
            rec.status = 'cancel'

    def action_update_qty(self):
        return {
            'name': _('Update Quantity'),
            'type': 'ir.actions.act_window',
            'res_model': 'update.qty',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'
        }
