from odoo import fields, models, api, _


class ProblemMaster(models.Model):
    _name = 'problem.master'
    _description = 'Problem'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Name', tracking=True)
