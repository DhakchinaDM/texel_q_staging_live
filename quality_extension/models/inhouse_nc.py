from odoo import fields, models, api, _
from datetime import date
from odoo.exceptions import UserError, ValidationError


class InHouseNc(models.Model):
    _name = 'in.house.nc'
    _description = 'In House Non Conformance'
    _inherit = ['mail.thread']
    _order = "create_date desc"

    user_id = fields.Many2one('res.users', string='User Name', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    logged_user = fields.Many2one('res.users', string='Logged User', compute='get_logged_user')
    active = fields.Boolean(default=True)
    name = fields.Char(string="Name", default='New', store=True, readonly=True)
    date = fields.Date(string='Date')
    category = fields.Selection([
        ('automotive', 'Automotive'),
        ('non_automotive', 'Non Automotive'),
        ('aero_space', 'Aero Space'),
    ], string='Category')
    product_id = fields.Many2one('product.template', string="Part No")
    partner_id = fields.Many2one('res.partner', string='Vendor/Customer')
    process_no = fields.Many2one('process.master', string='Operation No & Name')
    problem_id = fields.Many2one('problem.master', string='Problem')
    actual = fields.Char(string='Actual')
    process_rejected_qty = fields.Integer(string='Process Rejected Qty')
    for_rework_qty = fields.Integer(string='For R/W', help='For Rework Quantity')
    machine_no = fields.Many2one('maintenance.equipment', string='Machine No')
    stage = fields.Selection([
        ('in_process', 'In Progress'),
        ('pdi', 'PDI'),
        ('incoming', 'Incoming'),
    ], string='Stage')
    four_m_cause = fields.Char(string='4M Cause')
    disposition_action = fields.Selection([
        ('scrap', 'Scrap'),
        ('rework', 'Rework'),
    ], string='Disposition Action')

    def get_logged_user(self):
        self.logged_user = self.env.uid

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.sudo().env['ir.sequence'].next_by_code('in.house.nc') or '/'
        return super().create(vals_list)
