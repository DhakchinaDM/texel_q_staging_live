from odoo import fields, models, api, _
from datetime import date
from odoo.exceptions import UserError, ValidationError


class SettingApproval(models.Model):
    _name = 'setting.approval'
    _description = 'Setting Approval'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _order = "create_date desc"

    name = fields.Char(string="Name", default='New', store=True, readonly=True)
    product_id = fields.Many2one('product.template', string='Part No', compute='_compute_product', store=True)
    part_name = fields.Char(string='Part Name', related='product_id.name')
    partner_id = fields.Many2one('res.partner', string='Customer')
    process_no = fields.Many2one('process.master', string='Process No & Name')
    rev_no = fields.Char(related='product_id.draw_rev_no')
    rev_date = fields.Date(related='product_id.draw_rev_date')
    machine_no = fields.Many2one('maintenance.equipment', string='Machine No')
    date = fields.Date()
    shift = fields.Selection([
        ('a', 'Shift I'),
        ('b', 'Shift II'),
        ('c', 'Shift III'),
        ('g', 'Shift G'),
    ], string='Shift')
    setting_start_time = fields.Datetime()
    setting_end_time = fields.Datetime()
    qc_approval_time = fields.Datetime()
    supervisor_id = fields.Many2one('hr.employee', string='Supervisor')
    program_no = fields.Char(string='Program No')
    parameter_ids = fields.One2many('process.parameter', 'setting_id')
    tool_detail_ids = fields.One2many('tool.details', 'setting_id')
    product_parameter_ids = fields.One2many('product.parameter', 'setting_id')
    is_there_any_parts = fields.Boolean(string='Is there any parts rejected during setting')
    how_many = fields.Char(string='How many parts rejected')
    disposition_status = fields.Boolean(string='If Disposition status (Scrap with Red Paint)')
    are_previous = fields.Boolean(string="Are Pevious Part's Gauges Removed?")
    are_all_the = fields.Boolean(string="Are issued all the Guages as per the SOP?")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('accept', 'Accepted'),
        ('conditionally_accept', 'Conditionally Accepted'),
        ('reject', 'Rejected'),
    ], default='draft', string="State")
    quality_sign = fields.Binary(string='Quality Signature')
    production_sign = fields.Binary(string='Production Signature')

    @api.depends('process_no')
    def _compute_product(self):
        for rec in self:
            rec.product_id = False
            rec.product_id = rec.process_no.part_no.id

    def submit(self):
        for record in self:
            for a in record.parameter_ids:
                if not a.observation:
                    raise ValidationError(_('Alert! Enter the Required Observation in Process Parameter'))
            for b in record.tool_detail_ids:
                if not b.observations:
                    raise ValidationError(_('Alert! Enter the Required Observations in Tool Details'))
            for c in record.product_parameter_ids:
                if (not c.observation1
                        and not c.observation2
                        and not c.observation3
                        and not c.observation4
                        and not c.observation5):
                    raise ValidationError(_('Alert! Enter the Required Observations in Product Parameter'))
        self.write({
            'state': 'submit'
        })

    def accept(self):
        self.write({
            'state': 'accept'
        })

    def conditionally_accept(self):
        self.write({
            'state': 'conditionally_accept'
        })

    def reject(self):
        self.write({
            'state': 'reject'
        })

    def set_to_draft(self):
        self.write({
            'state': 'draft'
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.sudo().env['ir.sequence'].get('setting.approval') or '/'
            res = super(SettingApproval, self).create(vals)
        return res

    @api.onchange('process_no')
    def get_process_master_details(self):
        for rec in self:
            rec.parameter_ids = [(2, pm_id.id, 0) for pm_id in rec.parameter_ids]
            rec.tool_detail_ids = [(2, tool.id, 0) for tool in rec.tool_detail_ids]
            rec.product_parameter_ids = [(2, pm.id, 0) for pm in rec.product_parameter_ids]
            if rec.process_no:
                rec.parameter_ids = [(0, 0, {
                    'characteristics': i.characteristics.id,
                    'specification': i.specification,
                    'method_of_check': i.method_of_check.id,
                }) for i in rec.process_no.parameter_ids]
                rec.tool_detail_ids = [(0, 0, {
                    'characteristics': j.characteristics.id,
                    'no_of_edges': j.no_of_edges,
                    'holder': j.holder.id,
                    'insert': j.insert.id,
                    'method_of_check': j.method_of_check.id,
                    'speed': j.speed,
                    'feed': j.feed,
                    'tool_life': j.tool_life,
                }) for j in rec.process_no.tool_detail_ids]
                rec.product_parameter_ids = [(0, 0, {
                    'characteristics': k.characteristics.id,
                    'spl_class': k.spl_class,
                    'specification': k.specification,
                    'minimum': k.minimum,
                    'maximum': k.maximum,
                    'method_of_check': k.method_of_check.id,
                }) for k in rec.process_no.product_parameter_ids]
