from odoo.exceptions import ValidationError, UserError
from odoo import api, fields, models, _


class StdContainer(models.Model):
    _name = 'std.container'
    _description = 'Standard Container'
    _inherit = ['mail.thread.cc', 'mail.thread.main.attachment', 'mail.activity.mixin']

    # INVISIBLE FIELDS START
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    logged_user = fields.Many2one('res.users', string='Logged User', compute='get_logged_user')
    active = fields.Boolean(default=True)

    def get_logged_user(self):
        self.logged_user = self.env.uid

    # INVISIBLE FIELDS END
    name = fields.Char(string='Name')
