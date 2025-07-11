from odoo import fields, models, api, _
from datetime import date
from odoo.exceptions import UserError, ValidationError
import math


class ProcessMaster(models.Model):
    _name = 'process.master'
    _description = 'Process Master'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _order = "create_date desc"

    name = fields.Char(compute='_compute_name', store=True)
    operation_no = fields.Char(string='Operation No')
    part_no = fields.Many2one('product.template', string='Part No')
    operation_id = fields.Many2many('mrp.routing.workcenter', string='Operation Name')
    opr_name = fields.Char(compute='_compute_opr_name')
    parameter_ids = fields.One2many('process.parameter', 'process_id')
    tool_detail_ids = fields.One2many('tool.details', 'process_id')
    product_parameter_ids = fields.One2many('product.parameter', 'process_id')

    @api.depends('operation_no', 'part_no')
    def _compute_name(self):
        for rec in self:
            if rec.operation_no:
                test = [i.name for i in rec.operation_id]
                val = str(rec.operation_no) + "  [" + str(rec.part_no.default_code) + "] - " + ", ".join(test)
                rec.name = val
            else:
                rec.name = False

    @api.onchange('operation_id')
    def _compute_opr_name(self):
        for rec in self:
            if rec.operation_no:
                test = [i.name for i in rec.operation_id]
                rec.opr_name = ', '.join(map(str, test))
            else:
                rec.opr_name = False


class ProcessParameter(models.Model):
    _name = 'process.parameter'
    _description = 'Process Parameter'

    process_id = fields.Many2one('process.master')
    characteristics = fields.Many2one('quality.parameter', string='Characteristics')
    specification = fields.Char()
    method_of_check = fields.Many2one('quality.check.method')
    observation = fields.Char(string='Observation')
    remarks = fields.Text(string='Remarks')
    setting_id = fields.Many2one('setting.approval')

    # @api.onchange('observation')
    # def _check_decimal_places(self):
    #     for rec in self:
    #         try:
    #             if not rec.characteristics.observation_no_need:
    #                 rec.observation = math.floor(float(rec.observation) * 10000) / 10000
    #         except ValueError:
    #             raise ValidationError(_('Alert! The Observation must have Only Numeric Values'))

    @api.constrains('observation')
    def check_observation(self):
        for rec in self:
            if not rec.characteristics.observation_no_need:
                try:
                    float(rec.observation)
                except ValueError:
                    raise ValidationError('Alert! The Observations must have only Numeric Values')


class ToolDetails(models.Model):
    _name = 'tool.details'
    _description = 'Tool Details'

    process_id = fields.Many2one('process.master')
    characteristics = fields.Many2one('quality.parameter')
    no_of_edges = fields.Integer(string='No of Edges')
    holder = fields.Many2one('product.template', string='Holder')
    insert = fields.Many2one('product.template', string='Insert')
    method_of_check = fields.Many2one('quality.check.method', string='Method of Check')
    speed = fields.Char(string='Speed')
    feed = fields.Char(string='Feed')
    tool_life = fields.Char(string='Tool Life')
    observations = fields.Text()
    remarks = fields.Text()
    setting_id = fields.Many2one('setting.approval')

    # @api.onchange('observations')
    # def _check_decimal_places(self):
    #     for rec in self:
    #         try:
    #             if not rec.characteristics.observation_no_need:
    #                 rec.observations = math.floor(float(rec.observations) * 10000) / 10000
    #         except ValueError:
    #             raise ValidationError(_('Alert! The Observations must have Only Numeric Values'))

    @api.constrains('observations')
    def check_observations(self):
        for rec in self:
            if not rec.characteristics.observation_no_need:
                try:
                    float(rec.observations)
                except ValueError:
                    raise ValidationError('Alert! The Observations must have only Numeric Values')


class ProductParameter(models.Model):
    _name = 'product.parameter'
    _description = 'Product Parameter'

    process_id = fields.Many2one('process.master')
    characteristics = fields.Many2one('quality.parameter')
    spl_class = fields.Char(string='SPL/Class')
    specification = fields.Char(string='Specification')
    minimum = fields.Float(string='Minimum')
    maximum = fields.Float(string='Maximum')
    method_of_check = fields.Many2one('quality.check.method')
    sample_size = fields.Char(string='Sample Size')
    frequency = fields.Selection([
        ('fq_one', 'Once in Hour'),
        ('fq_two', 'Every 2 Hours'),
        ('fq_three', 'Every 4 Hours'),
        ('fq_four', 'Every Shift')
    ], string='Frequency')
    fq_value = fields.Char(compute='_get_selection_value')
    observation1 = fields.Char(string='Obs 1')
    observation2 = fields.Char(string='Obs 2')
    observation3 = fields.Char(string='Obs 3')
    observation4 = fields.Char(string='Obs 4')
    observation5 = fields.Char(string='Obs 5')
    remarks = fields.Text(string='Remarks')
    invalid_min_max = fields.Boolean(compute='_compute_invalid_min_max')
    setting_id = fields.Many2one('setting.approval')
    obser_1_check = fields.Boolean(string='Check One', compute='_compute_level_checks')
    obser_2_check = fields.Boolean(string='Check Two', compute='_compute_level_checks')
    obser_3_check = fields.Boolean(string='Check Three', compute='_compute_level_checks')
    obser_4_check = fields.Boolean(string='Check Four', compute='_compute_level_checks')
    obser_5_check = fields.Boolean(string='Check Five', compute='_compute_level_checks')
    obs_status = fields.Selection([
        ('okay', 'Okay'),
        ('not_okay', 'Not Okay'),
    ], string='Status')

    # @api.onchange('observation1', 'observation2', 'observation3', 'observation4', 'observation5')
    # def _check_decimal_place(self):
    #     for rec in self:
    #         try:
    #             if not rec.characteristics.observation_no_need:
    #                 rec.observation1 = math.floor(float(rec.observation1) * 10000) / 10000
    #                 rec.observation2 = math.floor(float(rec.observation2) * 10000) / 10000
    #                 rec.observation3 = math.floor(float(rec.observation3) * 10000) / 10000
    #                 rec.observation4 = math.floor(float(rec.observation4) * 10000) / 10000
    #                 rec.observation5 = math.floor(float(rec.observation5) * 10000) / 10000
    #         except:
    #             raise ValidationError(_('Alert! Observations must Have Numeric Values'))

    @api.depends('observation1', 'observation2', 'observation3', 'observation4', 'observation5')
    def _compute_level_checks(self):
        for rec in self:
            for i in range(1, 6):
                setattr(rec, f'obser_{i}_check', False)
            setattr(rec, 'obs_status', 'okay')
            if not any(getattr(rec, f'observation{i}') for i in range(1, 6)):
                rec.obs_status = False
                continue
            if not rec.characteristics.observation_no_need:
                for i in range(1, 6):
                    observation = getattr(rec, f'observation{i}')
                    try:
                        if observation and (float(observation) < rec.minimum or float(observation) > rec.maximum):
                            setattr(rec, f'obser_{i}_check', True)
                            setattr(rec, 'obs_status', 'not_okay')
                    except ValueError as e:
                        pass

    @api.constrains('minimum', 'maximum')
    def _compute_invalid_min_max(self):
        for record in self:
            record.invalid_min_max = False
            if record.minimum > record.maximum:
                record.invalid_min_max = True
                raise ValidationError(_('Alert! Kindly enter the Minimum and Maximum values Properly'))
