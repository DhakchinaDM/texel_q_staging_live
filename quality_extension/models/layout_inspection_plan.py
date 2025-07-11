from dataclasses import field

from odoo import fields, models, api, _
from datetime import date
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class LayoutInspectionPlan(models.Model):
    _name = 'layout.inspection.plan'
    _description = 'Layout Inspection Plan'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _order = "create_date desc"

    user_id = fields.Many2one('res.users', string='User Name', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    active = fields.Boolean(default=True)
    name = fields.Char(string='Name', default='New')
    doc_no = fields.Char(string='Doc No', default='QA/DI/D/22')
    rev_no = fields.Char(string='Rev No')
    date = fields.Date(string='Date')
    select_year = fields.Many2one('hr.payroll.year', string='', compute='_compute_year', readonly=False, store=True)
    end_year = fields.Many2one('hr.payroll.year', string='', store=True)
    prepared_by = fields.Many2one('hr.employee')
    approved_by = fields.Many2one('hr.employee')
    line_ids = fields.One2many('layout.inspection.plan.lines', 'lip_id', string='Plan Lines')

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

    @api.constrains('select_year')
    def _check_year(self):
        for record in self:
            if record.select_year:
                domain = [('select_year', '=', record.select_year.id)]
                codes = self.search(domain)
                if len(codes) > 1:
                    for code in codes:
                        if code.id != record.id:
                            raise ValidationError(
                                _('Alert! The Layout Inspection Plan Already Exists for the Year.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.sudo().env['ir.sequence'].get('layout.inspection.plan') or '/'
            res = super(LayoutInspectionPlan, self).create(vals)
        return res

    @api.model
    def default_get(self, fields):
        result = super(LayoutInspectionPlan, self).default_get(fields)
        line_val = []
        part = self.env['product.template'].search(
            [('categ_id', '=', self.env.ref('inventory_extended.category_finished_goods').id)])
        for i in part:
            line = (0, 0, {
                'part_no': i.id,
                'part_name': i.name,
            })
            line_val.append(line)
        result.update({
            'line_ids': line_val,
        })
        return result

    def plan_schedule(self):
        today = date.today()
        current_year = today.year
        year_end = current_year + 1
        year_record = self.env['hr.payroll.year'].search(
            [('name', '=', str(current_year))], limit=1)
        nxt_year = self.env['hr.payroll.year'].search(
            [('name', '=', str(year_end))], limit=1)
        self.create({
            'select_year': year_record.id,
            'end_year': nxt_year.id,
            'date': fields.Date.today(),
        })
        next_year = today.year + 1
        next_april_last = date(next_year, 4, 30)
        cron_job = self.env.ref('quality_extension.ir_cron_layout_inspection_year')
        cron_job.write({'nextcall': next_april_last})


class LayoutInspectionPlanLines(models.Model):
    _name = 'layout.inspection.plan.lines'
    _description = 'Layout Inspection Plan Lines'

    lip_id = fields.Many2one('layout.inspection.plan', string='Layout Inspection Plan')
    part_no = fields.Many2one('product.template', string='Part Name',
                              domain=lambda self: self._get_layout_product_domain())
    part_name = fields.Char(string='Part No', related='part_no.default_code')
    partner_id = fields.Many2one('res.partner', string='Customer', compute='_compute_values')
    may = fields.Boolean(string='May', compute='_compute_values')
    june = fields.Boolean(string='June', compute='_compute_values')
    july = fields.Boolean(string='July', compute='_compute_values')
    august = fields.Boolean(string='August', compute='_compute_values')
    september = fields.Boolean(string='September', compute='_compute_values')
    october = fields.Boolean(string='October', compute='_compute_values')
    november = fields.Boolean(string='November', compute='_compute_values')
    december = fields.Boolean(string='December', compute='_compute_values')
    january = fields.Boolean(string='January', compute='_compute_values')
    february = fields.Boolean(string='February', compute='_compute_values')
    march = fields.Boolean(string='March', compute='_compute_values')
    april = fields.Boolean(string='April', compute='_compute_values')
    remarks = fields.Text(string='Remarks')

    @api.depends('part_no', 'lip_id.select_year')
    def _compute_values(self):
        for record in self:
            record.may = False
            record.june = False
            record.july = False
            record.august = False
            record.september = False
            record.october = False
            record.november = False
            record.december = False
            record.january = False
            record.february = False
            record.march = False
            record.april = False
            record.partner_id = False
            inspections = self.env['layout.inspection'].search(
                [('layout_product', '=', record.part_no.id), ('state', '=', 'approve'),
                 ('select_year', '=', record.lip_id.select_year.id)], limit=1)
            for inspection in inspections:
                record.partner_id = inspection.customer.id
                month = inspection.date.strftime('%B')
                if month == 'May':
                    record.may = True
                elif month == 'June':
                    record.june = True
                elif month == 'July':
                    record.july = True
                elif month == 'August':
                    record.august = True
                elif month == 'September':
                    record.september = True
                elif month == 'October':
                    record.october = True
                elif month == 'November':
                    record.november = True
                elif month == 'December':
                    record.december = True
                elif month == 'January':
                    record.january = True
                elif month == 'February':
                    record.february = True
                elif month == 'March':
                    record.march = True
                elif month == 'April':
                    record.april = True

    @api.model
    def _get_layout_product_domain(self):
        finished_goods_category = self.env.ref('inventory_extended.category_finished_goods')
        return [('categ_id', '=', finished_goods_category.id)]
