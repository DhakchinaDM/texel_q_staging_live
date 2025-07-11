from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import math


class LayoutInspection(models.Model):
    _name = 'layout.inspection'
    _description = 'Layout Inspection'

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
    part_name = fields.Char(string='Part Name', related='layout_product.name')
    customer = fields.Many2one('res.partner', string='Customer')
    rev_no = fields.Char(compute='compute_rev_no', store=True)
    rev_date = fields.Date(compute='compute_rev_no', store=True)
    inspected_by = fields.Many2one('hr.employee')
    approved_by = fields.Many2one('hr.employee')
    date = fields.Date(string='Date')
    shift = fields.Selection([
        ('a', 'Shift I'),
        ('b', 'Shift II'),
        ('c', 'Shift III'),
        ('g', 'Shift G'),
    ], string='Shift')
    layout_ids = fields.One2many('layout.observation', 'layout_inspect_id')
    select_year = fields.Many2one('hr.payroll.year', string='Year', compute='_compute_year', store=True)
    layout_product = fields.Many2one(
        'product.template',
        string='Part No',
        domain=lambda self: self._get_layout_product_domain())
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting for Approval'),
        ('approve', 'Approved'),
        ('reject', 'Rejected')
    ], string='State', default='draft')

    @api.constrains('select_year', 'layout_product')
    def _check_year(self):
        for record in self:
            if record.select_year:
                domain = [('select_year', '=', record.select_year.id),
                          ('layout_product', '=', record.layout_product.id), ]
                codes = self.search(domain)
                if len(codes) > 1:
                    for code in codes:
                        if code.id != record.id:
                            raise ValidationError(
                                _('Alert! The Inspection Already exists for the Part No.'))

    def action_submit(self):
        for record in self:
            for rec in record.layout_ids:
                if (not rec.observation1
                        and not rec.observation2
                        and not rec.observation3
                        and not rec.observation4
                        and not rec.observation5):
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
    def _get_layout_product_domain(self):
        finished_goods_category = self.env.ref('inventory_extended.category_finished_goods')
        return [('categ_id', '=', finished_goods_category.id)]

    @api.depends('date')
    def _compute_year(self):
        for record in self:
            if record.date:
                date_object = fields.Date.from_string(record.date)
                year = date_object.year
                year_record = self.env['hr.payroll.year'].search([('name', '=', str(year))], limit=1)
                if year_record:
                    record.select_year = year_record
                else:
                    record.select_year = False
            else:
                record.select_year = False

    def get_logged_user(self):
        self.logged_user = self.env.uid

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.sudo().env['ir.sequence'].get('layout.inspection') or '/'
            res = super(LayoutInspection, self).create(vals)
        return res

    @api.depends('layout_product')
    def compute_rev_no(self):
        for i in self:
            if i.layout_product:
                i.rev_no = i.layout_product.draw_rev_no
                i.rev_date = i.layout_product.draw_rev_date
            else:
                i.rev_no = False
                i.rev_date = False

    @api.onchange('layout_product')
    def get_layout_parameter_details(self):
        for rec in self:
            rec.layout_ids = [(2, lp.id, 0) for lp in rec.layout_ids]
            if rec.layout_product:
                layout = self.env['layout.configuration'].sudo().search([('part_no', '=', rec.layout_product.id)],
                                                                        limit=1)
                rec.layout_ids = [(0, 0, {
                    'baloon_no': k.baloon_no,
                    'description': k.description.id,
                    'spl': k.spl,
                    'specification': k.specification,
                    'layout_min': k.minimum,
                    'layout_max': k.maximum,
                    'check_method': k.method_of_check.id,
                }) for k in layout.layout_parameter_ids]


class LayoutObservation(models.Model):
    _name = 'layout.observation'
    _description = 'Layout Observation'

    layout_inspect_id = fields.Many2one('layout.inspection')
    description = fields.Many2one('quality.parameter', string='Description')
    spl = fields.Char(string='SPL')
    specification = fields.Html(string='Specification')
    layout_min = fields.Float(string='Minimum')
    layout_max = fields.Float(string='Maximum')
    check_method = fields.Many2one('quality.check.method', string='Checking Method')
    observation1 = fields.Char(string='Obs 1')
    observation2 = fields.Char(string='Obs 2')
    observation3 = fields.Char(string='Obs 3')
    observation4 = fields.Char(string='Obs 4')
    observation5 = fields.Char(string='Obs 5')
    remarks = fields.Text(string='Remarks')

    obser_1_check = fields.Boolean(string='Check One', compute='_compute_level_checks')
    obser_2_check = fields.Boolean(string='Check Two', compute='_compute_level_checks')
    obser_3_check = fields.Boolean(string='Check Three', compute='_compute_level_checks')
    obser_4_check = fields.Boolean(string='Check Four', compute='_compute_level_checks')
    obser_5_check = fields.Boolean(string='Check Five', compute='_compute_level_checks')

    obs_status = fields.Selection([
        ('okay', 'Okay'),
        ('not_okay', 'Not Okay'),
    ], string='Status')
    baloon_no = fields.Char(string='Ball No')
    name = fields.Char('Ref')
    display_type = fields.Selection(
        selection=[
            ('line_section', "Section"),
            ('line_note', "Note"),
        ],
        default=False)

    sequence = fields.Integer(
        'Sequence', default=1, required=True,
        help="Gives the sequence order when displaying a list of Part Operations.")



    # @api.onchange('observation1', 'observation2', 'observation3', 'observation4', 'observation5')
    # def _check_decimal_places(self):
    #     for rec in self:
    #         try:
    #             if not rec.description.observation_no_need:
    #                 def format_decimal(value):
    #                     dec_val = Decimal(str(value)).quantize(Decimal('1.0000'), rounding='ROUND_DOWN')
    #                     return dec_val.normalize()
    #
    #                 rec.observation1 = format_decimal(rec.observation1)
    #                 rec.observation2 = format_decimal(rec.observation2)
    #                 rec.observation3 = format_decimal(rec.observation3)
    #                 rec.observation4 = format_decimal(rec.observation4)
    #                 rec.observation5 = format_decimal(rec.observation5)
    #         except (InvalidOperation, ValueError):
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
            if not rec.description.observation_no_need:
                for i in range(1, 6):
                    observation = getattr(rec, f'observation{i}')
                    try:
                        if observation and (float(observation) < rec.layout_min or float(observation) > rec.layout_max):
                            setattr(rec, f'obser_{i}_check', True)
                            setattr(rec, 'obs_status', 'not_okay')
                    except ValueError as e:
                        pass
