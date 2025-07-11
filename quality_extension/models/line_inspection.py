from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import math


class LineInspection(models.Model):
    _name = 'line.inspection'
    _description = 'Line Inspection'
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
    part_no = fields.Char(related='product_id.default_code')
    rev_no = fields.Char(compute='compute_rev_no')
    rev_date = fields.Date(compute='compute_rev_no')
    operation_no = fields.Many2one('process.master', string='Operation No & Name')
    operation_name = fields.Char(string='Operation Name', related='operation_no.name')
    machine_no = fields.Many2one('maintenance.equipment', string='Machine No')
    machine_name = fields.Char(string='Machine Name', related='machine_no.name')
    product_parameter_ids = fields.One2many('product.parameter', 'setting_id')
    inspector_name = fields.Many2one('hr.employee', string='Inspector Name')
    operator_name = fields.Many2one('hr.employee', string='Operator Name')
    date = fields.Date(string='Date')
    shift = fields.Selection([
        ('a', 'Shift I'),
        ('b', 'Shift II'),
        ('c', 'Shift III'),
        ('g', 'Shift G'),
    ], string='Shift')
    inspected_by = fields.Many2one('res.users', string='Inspected By', compute='get_logged_user')
    approved_by = fields.Many2one('hr.employee', string='Approved By')
    line_state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('accept', 'Accepted'),
        ('conditional_accept', 'Conditionally Accepted'),
        ('reject', 'Rejected'),
    ], default='draft', string="State")
    line_ids = fields.One2many('line.observation', 'observation_id')

    def line_submit(self):
        for record in self:
            for rec in record.line_ids:
                if (not rec.observation1
                        and not rec.observation2
                        and not rec.observation3
                        and not rec.observation4
                        and not rec.observation5
                        and not rec.observation6
                        and not rec.observation7
                        and not rec.observation8):
                    raise ValidationError(_('Alert! Enter the Observations to Save the Inspection Details'))
        self.write({
            'line_state': 'submit'
        })

    def line_accept(self):
        self.write({
            'line_state': 'accept'
        })

    def line_conditionally_accept(self):
        self.write({
            'line_state': 'conditional_accept'
        })

    def line_reject(self):
        self.write({
            'line_state': 'reject'
        })

    def line_set_to_draft(self):
        self.write({
            'line_state': 'draft'
        })

    def get_logged_user(self):
        self.logged_user = self.env.uid
        self.inspected_by = self.env.uid

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.sudo().env['ir.sequence'].get('line.inspection') or '/'
            res = super(LineInspection, self).create(vals)
        return res

    @api.onchange('product_id')
    def compute_rev_no(self):
        for i in self:
            if i.product_id:
                i.rev_no = i.product_id.draw_rev_no
                i.rev_date = i.product_id.draw_rev_date
            else:
                i.rev_no = False
                i.rev_date = False

    @api.onchange('operation_no')
    def get_product_parameter_details(self):
        for rec in self:
            rec.line_ids = [(2, pm.id, 0) for pm in rec.line_ids]
            rec.product_id = False
            if rec.operation_no:
                rec.product_parameter_ids = [(2, pm.id, 0) for pm in rec.product_parameter_ids]
                rec.product_id = rec.operation_no.part_no
                rec.line_ids = [(0, 0, {
                    'characteristics': k.characteristics.id,
                    'spc': k.spl_class,
                    'line_specification': k.specification,
                    'line_min': k.minimum,
                    'line_max': k.maximum,
                    'method_of_check': k.method_of_check.id,
                    'sample_size': k.sample_size,
                    'frequency': k.frequency,
                    'remarks': k.remarks,
                }) for k in rec.operation_no.product_parameter_ids]


class LineObservation(models.Model):
    _name = 'line.observation'
    _description = 'Line Observation'

    observation_id = fields.Many2one('line.inspection')
    observation_no = fields.Char(related='observation_id.name')
    characteristics = fields.Many2one('quality.parameter', string='Characteristics')
    spc = fields.Char(string='SPC')
    line_specification = fields.Char(string='Specification in mm')
    line_min = fields.Float(string='Minimum')
    line_max = fields.Float(string='Maximum')
    method_of_check = fields.Many2one('quality.check.method', string='Method of Check')
    sample_size = fields.Char(string='Sample Size')
    frequency = fields.Selection([
        ('fq_one', 'Once in Hour'),
        ('fq_two', 'Every 2 Hours'),
        ('fq_three', 'Every 4 Hours'),
        ('fq_four', 'Every Shift')
    ], string='Frequency')
    observation1 = fields.Char(string='Obs 1')
    observation2 = fields.Char(string='Obs 2')
    observation3 = fields.Char(string='Obs 3')
    observation4 = fields.Char(string='Obs 4')
    observation5 = fields.Char(string='Obs 5')
    observation6 = fields.Char(string='Obs 6')
    observation7 = fields.Char(string='Obs 7')
    observation8 = fields.Char(string='Obs 8')
    remarks = fields.Text(string='Remarks')
    obser_1_check = fields.Boolean(string='Check One', compute='_compute_level_checks')
    obser_2_check = fields.Boolean(string='Check Two', compute='_compute_level_checks')
    obser_3_check = fields.Boolean(string='Check Three', compute='_compute_level_checks')
    obser_4_check = fields.Boolean(string='Check Four', compute='_compute_level_checks')
    obser_5_check = fields.Boolean(string='Check Five', compute='_compute_level_checks')
    obser_6_check = fields.Boolean(string='Check six', compute='_compute_level_checks')
    obser_7_check = fields.Boolean(string='Check seven', compute='_compute_level_checks')
    obser_8_check = fields.Boolean(string='Check eight', compute='_compute_level_checks')
    obs_status = fields.Selection([
        ('okay', 'Okay'),
        ('not_okay', 'Not Okay'),
    ], string='Status',)

    # @api.onchange('observation1', 'observation2', 'observation3', 'observation4', 'observation5', 'observation6',
    #               'observation7', 'observation8')
    # def _check_decimal_place(self):
    #     for rec in self:
    #         try:
    #             if not rec.characteristics.observation_no_need:
    #                 def format_decimal(value):
    #                     dec_value = Decimal(str(value)).quantize(Decimal('1.0000'), rounding='ROUND_DOWN')
    #                     return dec_value.normalize()
    #
    #                 if rec.frequency == 'fq_one':
    #                     rec.observation1 = format_decimal(rec.observation1)
    #                     rec.observation2 = format_decimal(rec.observation2)
    #                     rec.observation3 = format_decimal(rec.observation3)
    #                     rec.observation4 = format_decimal(rec.observation4)
    #                     rec.observation5 = format_decimal(rec.observation5)
    #                     rec.observation6 = format_decimal(rec.observation6)
    #                     rec.observation7 = format_decimal(rec.observation7)
    #                     rec.observation8 = format_decimal(rec.observation8)
    #                 elif not rec.characteristics.observation_no_need and rec.frequency == 'fq_two':
    #                     rec.observation1 = format_decimal(rec.observation1)
    #                     rec.observation2 = False
    #                     rec.observation3 = format_decimal(rec.observation3)
    #                     rec.observation4 = False
    #                     rec.observation5 = format_decimal(rec.observation5)
    #                     rec.observation6 = False
    #                     rec.observation7 = format_decimal(rec.observation7)
    #                     rec.observation8 = False
    #                 elif not rec.characteristics.observation_no_need and rec.frequency == 'fq_three':
    #                     rec.observation1 = format_decimal(rec.observation1)
    #                     rec.observation2 = False
    #                     rec.observation3 = False
    #                     rec.observation4 = False
    #                     rec.observation5 = format_decimal(rec.observation5)
    #                     rec.observation6 = False
    #                     rec.observation7 = False
    #                     rec.observation8 = False
    #                 elif not rec.characteristics.observation_no_need and rec.frequency == 'fq_four':
    #                     rec.observation1 = format_decimal(rec.observation1)
    #                     rec.observation2 = False
    #                     rec.observation3 = False
    #                     rec.observation4 = False
    #                     rec.observation5 = False
    #                     rec.observation6 = False
    #                     rec.observation7 = False
    #                     rec.observation8 = False
    #         except (InvalidOperation, ValueError):
    #             raise ValidationError(_('Alert! Observations must have a numeric value.'))

    @api.depends('observation1', 'observation2', 'observation3', 'observation4', 'observation5', 'observation6',
                 'observation7', 'observation8')
    def _compute_level_checks(self):
        for rec in self:
            for i in range(1, 9):
                setattr(rec, f'obser_{i}_check', False)
            setattr(rec, 'obs_status', 'okay')
            if not any(getattr(rec, f'observation{i}') for i in range(1, 9)):
                rec.obs_status = False
                continue
            if not rec.characteristics.observation_no_need:
                for i in range(1, 9):
                    observation = getattr(rec, f'observation{i}')
                    try:
                        if observation and (float(observation) < rec.line_min or float(observation) > rec.line_max):
                            setattr(rec, f'obser_{i}_check', True)
                            setattr(rec, 'obs_status', 'not_okay')
                    except ValueError as e:
                        pass
