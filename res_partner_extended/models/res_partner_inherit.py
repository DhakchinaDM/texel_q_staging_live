from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    sales_person = fields.Char(string='Salesperson ', tracking=True)
    supplier_id = fields.Char(string="Supplier ID")
    supplier_code = fields.Char(string="Supplier Code")
    supplier_type = fields.Many2one('supplier.type', string="Supplier Type")

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['supplier_id'] = self.sudo().env['ir.sequence'].next_by_code('res.partner') or '/'
        return super().create(vals_list)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None, order=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', '|', '|', ('name', operator, name), ('supplier_id', operator, name),
                      ('supplier_code', operator, name),
                      ('mobile', operator, name), ('email', operator, name)]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid, order=None)


class SupplierType(models.Model):
    _name = 'supplier.type'
    _description = "Supplier Type"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Supplier Type")
