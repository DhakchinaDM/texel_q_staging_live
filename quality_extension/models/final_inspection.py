from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import math


class FinalInspection(models.Model):
    _name = 'final.inspection'
    _description = 'Final Inspection'
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
    customer = fields.Many2one('res.partner', string='Customer')
    product_id = fields.Many2one('product.template', string='Part No.',
                                 domain=lambda self: self.get_finished_products())
    part_name = fields.Char(string='Part Name', related='product_id.name')
    rev_no = fields.Char(compute='compute_rev_no')
    rev_date = fields.Date(compute='compute_rev_no')
    invoice_no = fields.Char(string='Invoice No')
    inspect_date = fields.Date()
    qty = fields.Float(string='QTY')
    sample_qty = fields.Float(string='Sample Qty', compute='compute_sample_qty')
    tc_no = fields.Char(string='TC No', help='')
    tc_date = fields.Date()
    actual = fields.Char(string='Actual')
    specified = fields.Char(string='Specified', default='SAE J403 1018')
    inspected_by = fields.Many2one('res.users', string='Inspected By')
    approved_by = fields.Many2one('res.users', string='Approved By')
    final_parameter_ids = fields.One2many('final.parameter.line', 'final_inspect')
    inspect_ids = fields.One2many('final.observation', 'final_inspect_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting for Approval'),
        ('approve', 'Approved'),
        ('reject', 'Rejected')
    ], string='State', default='draft')

    def get_logged_user(self):
        self.logged_user = self.env.uid

    def action_submit(self):
        for record in self:
            for rec in record.inspect_ids:
                if (not rec.final_obs1
                        and not rec.final_obs2
                        and not rec.final_obs3
                        and not rec.final_obs4
                        and not rec.final_obs5):
                    raise ValidationError(_('Alert! Enter the Observations to Save the Inspection Details'))
        self.write({
            'state': 'waiting'
        })

    def action_approval(self):
        self.write({
            'state': 'approve'
        })

    def action_rejection(self):
        self.write({
            'state': 'reject'
        })

    def set_to_draft(self):
        self.write({
            'state': 'draft'
        })

    @api.model
    def get_finished_products(self):
        fg_category = self.env.ref('inventory_extended.category_finished_goods').id
        return [('categ_id', '=', fg_category)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.sudo().env['ir.sequence'].get('final.inspection') or '/'
            res = super(FinalInspection, self).create(vals)
        return res

    @api.constrains('tc_no', 'tc_date')
    def check_material_reference(self):
        for record in self:
            if not record.tc_no and not record.tc_date:
                raise ValidationError(_('Alert! Please enter TC No and Date for Material Check Reference'))

    @api.constrains('inspect_date')
    def check_date(self):
        for record in self:
            if not record.inspect_date:
                raise ValidationError(_('Alert! Kindly mention the Inspection Date'))

    @api.depends('qty')
    def compute_sample_qty(self):
        for record in self:
            record.sample_qty = 0
            sample = self.env['quality.sampling'].search([('model_id', '=', self._name)], limit=1)
            for i in sample.sampling_ids.filtered(
                    lambda x: x.min_lot_qty <= record.qty <= x.max_lot_qty):
                record.sample_qty = i.sample_size

    @api.onchange('product_id')
    def compute_rev_no(self):
        for i in self:
            if i.product_id:
                i.rev_no = i.product_id.draw_rev_no
                i.rev_date = i.product_id.draw_rev_date
            else:
                i.rev_no = False
                i.rev_date = False

    @api.onchange('product_id')
    def get_final_parameter_details(self):
        for rec in self:
            rec.inspect_ids = [(2, fm.id, 0) for fm in rec.inspect_ids]
            if rec.product_id:
                rec.inspect_ids = [(0, 0, {
                    'balloon_no': k.balloon_no,
                    'characteristics': k.characteristics.id,
                    'final_specification': k.final_specification,
                    'min_final': k.min_final,
                    'max_final': k.max_final,
                    'check_method_final': k.check_method_final.id,
                }) for k in rec.product_id.final_parameters]


class FinalObservation(models.Model):
    _name = 'final.observation'
    _description = 'Final Observation'

    final_inspect_id = fields.Many2one('final.inspection')

    sl_no = fields.Integer(string='Sl. No')
    balloon_no = fields.Char(string='Ball No')
    characteristics = fields.Many2one('quality.parameter', string='Characteristics')
    final_specification = fields.Char(string='Specification')
    min_final = fields.Float(string='Minimum', digits=(16, 3))
    max_final = fields.Float(string='Maximum', digits=(16, 3))
    check_method_final = fields.Many2one('quality.check.method', string='Method of Checking')
    final_obs1 = fields.Char(string='Obs 1')
    final_obs2 = fields.Char(string='Obs 2')
    final_obs3 = fields.Char(string='Obs 3')
    final_obs4 = fields.Char(string='Obs 4')
    final_obs5 = fields.Char(string='Obs 5')
    remarks = fields.Text(string='Remarks/Status')
    obser_1_check = fields.Boolean(string='Check One', compute='_compute_level_checks')
    obser_2_check = fields.Boolean(string='Check Two', compute='_compute_level_checks')
    obser_3_check = fields.Boolean(string='Check Three', compute='_compute_level_checks')
    obser_4_check = fields.Boolean(string='Check Four', compute='_compute_level_checks')
    obser_5_check = fields.Boolean(string='Check Five', compute='_compute_level_checks')

    obs_status = fields.Selection([
        ('okay', 'Okay'),
        ('not_okay', 'Not Okay'),
    ], string='Status')

    # @api.onchange('final_obs1', 'final_obs2', 'final_obs3', 'final_obs4', 'final_obs5')
    # def _check_decimal_place(self):
    #     for record in self:
    #         try:
    #             if not record.characteristics.observation_no_need:
    #                 def format_decimal(value):
    #                     dec_value = Decimal(str(value)).quantize(Decimal('1.0000'), rounding='ROUND_DOWN')
    #                     return dec_value.normalize()
    #                 record.final_obs1 = format_decimal(record.final_obs1)
    #                 record.final_obs2 = format_decimal(record.final_obs2)
    #                 record.final_obs3 = format_decimal(record.final_obs3)
    #                 record.final_obs4 = format_decimal(record.final_obs4)
    #                 record.final_obs5 = format_decimal(record.final_obs5)
    #         except (InvalidOperation, ValueError):
    #             raise ValidationError(_('Alert! Observation must have a Numeric Value'))

    @api.depends('final_obs1', 'final_obs2', 'final_obs3', 'final_obs4', 'final_obs5')
    def _compute_level_checks(self):
        for rec in self:
            for i in range(1, 6):
                setattr(rec, f'obser_{i}_check', False)
            setattr(rec, 'obs_status', 'okay')
            if not any(getattr(rec, f'final_obs{i}') for i in range(1, 6)):
                rec.obs_status = False
                continue
            if not rec.characteristics.observation_no_need:
                for i in range(1, 6):
                    observation = getattr(rec, f'final_obs{i}')
                    try:
                        if observation and (float(observation) < rec.min_final or float(observation) > rec.max_final):
                            setattr(rec, f'obser_{i}_check', True)
                            setattr(rec, 'obs_status', 'not_okay')
                    except ValueError as e:
                        pass
