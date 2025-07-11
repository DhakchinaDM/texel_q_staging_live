from odoo import models, fields, api, _


class SelfInspection(models.Model):
    _name = 'self.inspection'
    _description = 'Self Inspection'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _order = "create_date desc"

    user_id = fields.Many2one('res.users', string='User Name', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    logged_user = fields.Many2one('res.users', string='Logged User', compute='get_logged_user')
    active = fields.Boolean(default=True)

    name = fields.Char(string="Name", default='New', store=True, readonly=True)
    product_id = fields.Many2one('product.template', string='Part No.')
    part_name = fields.Char(string='Part Name', related='product_id.name')
    operation_no = fields.Many2one('process.master', string='Operation No')
    operation_name = fields.Char(string='Operation Name', related='operation_no.name')
    operator_name = fields.Many2one('hr.employee', string='Operator Name')
    machine_no = fields.Many2one('maintenance.equipment', string='M/C No.')
    date = fields.Date(string='Date')
    shift = fields.Selection([
        ('a', 'Shift I'),
        ('b', 'Shift II'),
        ('c', 'Shift III'),
        ('g', 'Shift G'),
    ], string='Shift')
    self_state = fields.Selection([
        ('draft', 'Draft'),
        ('accept', 'Accepted'),
        ('conditional_accept', 'Conditionally Accepted'),
        ('reject', 'Rejected'),
    ], default='draft', string="State")
    inspect_ids = fields.One2many('inspection.control', 'control_id')

    def self_accept(self):
        self.write({
            'self_state': 'accept'
        })

    def self_conditionally_accept(self):
        self.write({
            'self_state': 'conditional_accept'
        })

    def self_reject(self):
        self.write({
            'self_state': 'reject'
        })

    def get_logged_user(self):
        self.logged_user = self.env.uid

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.sudo().env['ir.sequence'].get('self.inspection') or '/'
            res = super(SelfInspection, self).create(vals)
        return res


class InspectionControl(models.Model):
    _name = 'inspection.control'
    _description = 'Inspection Control'

    control_id = fields.Many2one('self.inspection')
    parameter = fields.Many2one('quality.parameter', string='Parameter')
    inspection_method = fields.Many2one('quality.check.method', string='Inspection Method')
    control_specification = fields.Char(string='Control Specification (mm)')
