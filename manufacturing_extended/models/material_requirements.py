from odoo.exceptions import ValidationError, UserError
from odoo import api, fields, models, _


class MaterialRequirements(models.Model):
    _name = 'material.requirements'
    _description = 'Material Requirements'
    _inherit = ['mail.thread.cc', 'mail.thread.main.attachment', 'mail.activity.mixin']

    # INVISIBLE FIELDS START
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    active = fields.Boolean(default=True)
    # INVISIBLE FIELDS END

    name = fields.Char(string='Name', default='New')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], string='Status')
    part_id = fields.Many2one('product.template', string='Part')
    excess_only = fields.Boolean(string='Excess Only')