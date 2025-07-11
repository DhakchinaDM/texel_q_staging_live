from odoo import models, fields, api, _
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class CalibrationRequest(models.Model):
    _name = 'calibration.request'
    _description = 'Calibration Request'
    _inherit = ['mail.thread']

    @api.model
    def get_finished_goods(self):
        fg_products = self.env.ref('inventory_extended.category_finished_goods').id
        return [('categ_id', 'in', [fg_products]), ('type', 'in', ['product', 'consu'])]

    user_id = fields.Many2one('res.users', string='User Name', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    active = fields.Boolean(default=True)
    name = fields.Char(string='Name',tracking=True,)
    mmr_id = fields.Many2one('mmr.list', string='MMR Code No.',tracking=True,)
    mmr_name = fields.Char(string='Description',tracking=True,)
    mmr_frequency = fields.Char(related='mmr_id.calib_frequency', string='Frequency duplicate',tracking=True,)
    mmr_frequency_selection = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarter', 'Quarter'),
        ('half', 'Half-yearly'),
        ('year', 'Yearly')
    ], string='Frequency',tracking=True,)

    calib_state = fields.Selection([
        ('draft', 'Draft'),
        ('obsolete', 'Obsolete'),
        ('done', 'Done')
    ], default='draft', string='Draft',tracking=True,)
    request_instruments = fields.Selection([
        ('calibration', 'Instruments'),
        ('gauges', 'Gauges')
    ],tracking=True,)
    calib_attachment = fields.Binary(string='Attachment')
    file_name = fields.Char("File Name")
    create_date = fields.Date("Date")
    due_date_request = fields.Date("Request Date",default=lambda self: fields.Date.today(),tracking=True,)

    mmr_range = fields.Char(string='Range',compute='compute_fields_all')
    part_char_name = fields.Char(string='Part Name',compute='compute_fields_all')
    part_no = fields.Many2one('product.template', string='Part No', domain=lambda self: self.get_finished_goods(),compute='compute_fields_all')
    size = fields.Char(string='Size',compute='compute_fields_all')


    def compute_fields_all(self):
        for request in self:
            if request.mmr_id:
                request.mmr_range = request.mmr_id.mmr_range
                request.size = request.mmr_id.size
                request.part_char_name = request.mmr_id.part_char_name
                request.part_no = request.mmr_id.part_no

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals['request_instruments'] == 'calibration':
                vals['name'] = self.sudo().env['ir.sequence'].get('calibration.request') or '/'
            else:
                vals['name'] = self.sudo().env['ir.sequence'].get('calibration.request.gauge') or '/'
            res = super(CalibrationRequest, self).create(vals)
        return res

    def action_approve(self):
        today = fields.Date.context_today(self)
        next_due_date = ''

        for request in self:
            if request.mmr_frequency_selection == 'monthly':
                next_due_date = request.due_date_request + relativedelta(months=1, days=-1)
            elif request.mmr_frequency_selection == 'quarter':
                next_due_date = request.due_date_request + relativedelta(months=3, days=-1)
            elif request.mmr_frequency_selection == 'half':
                next_due_date = request.due_date_request + relativedelta(months=6, days=-1)
            elif request.mmr_frequency_selection == 'year':
                next_due_date = request.due_date_request + relativedelta(years=1, days=-1)
            if not request.calib_attachment:
                raise ValidationError(_('Alert! Please Add the Attachment Required'))
            request.write({
                'calib_state': 'done'
            })
            request.mmr_id.write({
                'calib_date': request.due_date_request,
                'due_date': next_due_date,
                'mmr_state': 'working'
            })

    def action_obsolete(self):
        for request in self:
            request.write({
                'calib_state': 'obsolete'
            })
            request.mmr_id.write({
                'mmr_state': 'obsolete'
            })
