from odoo import api, fields, models, tools, _


class MatrixSkillLevel(models.Model):
    _name = 'matrix.skill.level'
    _description = 'Matrix Skill Level'

    name = fields.Char(string='Name')
    description = fields.Char(string='Description')
    progress = fields.Integer(string='Progress')
    image = fields.Binary('Image')
    user_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    logged_user = fields.Many2one('res.users', string='Logged User', compute='get_logged_user')
    active = fields.Boolean(default=True)

    def get_logged_user(self):
        self.logged_user = self.env.uid
