from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64


class SpareMake(models.Model):
    _name = 'spare.make'
    _description = 'Spare Make'

    name = fields.Char(string='Make')
    user_id = fields.Many2one('res.users', string='User Name', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    logged_user = fields.Many2one('res.users', string='Logged User', compute='get_logged_user')
    active = fields.Boolean(default=True)

    def get_logged_user(self):
        self.logged_user = self.env.uid


class SpareDetails(models.Model):
    _name = 'spare.details'
    _description = 'Spare Details'
    _rec_name = 'product_id'

    user_id = fields.Many2one('res.users', string='User Name', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    logged_user = fields.Many2one('res.users', string='Logged User', compute='get_logged_user')
    active = fields.Boolean(default=True)
    machine_id = fields.Many2one('maintenance.equipment', string='Machine No')
    product_id = fields.Many2one('product.product', string='Description of Critical Spare')
    product_name = fields.Char(string='Part Name', related='product_id.name')
    supplier_part_no = fields.Char(string='Supplier Part No', related='product_id.supplier_part')
    default_code = fields.Char('product.product',related='product_id.default_code')
    make_id = fields.Many2one('spare.make', string='Make ')
    make_name = fields.Char(string='Make', related='product_id.make')
    specification = fields.Char(string='Specification', related='product_id.specification')
    minimum_stock = fields.Float(string='Minimum Stock', compute='get_min_stock')
    on_hand = fields.Float(string='Re-Order Level', compute='get_on_hand')
    uom_id = fields.Many2one('uom.uom', string='Uom', related='product_id.uom_id')

    @api.depends('product_id')
    def get_on_hand(self):
        for record in self:
            record.on_hand = record.product_id.qty_available

    @api.depends('product_id')
    def get_min_stock(self):
        for rec in self:
            rec.minimum_stock = rec.product_id.min_stock_quan

    def minimum_stock_alert(self):
        min_stock_data = []
        seen_products = set()
        for record in self:
            spares = self.env['spare.details'].search([])
            for i in spares:
                if i.on_hand <= i.minimum_stock:
                    if i.product_id.id not in seen_products:
                        seen_products.add(i.product_id.id)
                        val = {
                            'product_name': i.product_id.name,
                            'product_code': i.product_id.default_code,
                            'product_id': i.product_id.id,
                            'part_no': i.product_id.default_code,
                            'machine': i.machine_id.name,
                            'on_hand': i.on_hand,
                            'minimum_stock': i.minimum_stock,
                        }
                        min_stock_data.append(val)
        return min_stock_data

    def send_minimum_stock_alert_mail(self):
        template = self.env.ref('maintenance_extended.stock_replenishment_maintenance_mail', False)
        email_values = {'email_to': "",
                        'email_from': ""}
        template.send_mail(self.id, email_values=email_values, force_send=True)

    def get_logged_user(self):
        self.logged_user = self.env.uid
