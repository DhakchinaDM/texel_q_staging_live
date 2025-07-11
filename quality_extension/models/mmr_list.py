from email.policy import default
from odoo import models, fields, api, _
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class MmrList(models.Model):
    _name = 'mmr.list'
    _description = 'MMR List'
    _inherit = ['mail.thread']
    _rec_name = 'code_no'

    @api.model
    def get_finished_goods(self):
        fg_products = self.env.ref('inventory_extended.category_finished_goods').id
        return [('categ_id', 'in', [fg_products]), ('type', 'in', ['product', 'consu'])]

    code_no = fields.Char()
    pdf_file = fields.Many2many('ir.attachment', string="Attachment File")

    description = fields.Char(string='Description', tracking=True, )
    old_gage_no = fields.Char(string='Old Gage No', tracking=True, )
    customer_gage_no = fields.Char(string='Customer Gage No', tracking=True, )
    mmr_code_number = fields.Char(string='MMR Code No', tracking=True, )
    doc_num = fields.Char(string='Document Number', tracking=True )
    rev_date = fields.Date(string='Revision Date', tracking=True )
    rev_num = fields.Char(string='Revision Number', tracking=True)

    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('obsolete', 'Obsolete')])
    mmr_range = fields.Char(string='Range', tracking=True, )
    least_count = fields.Char(string='Least Count', tracking=True, )
    acceptance_criteria = fields.Char(string='Acceptance Criteria', tracking=True, )
    make = fields.Char(string='Make', tracking=True, )
    size = fields.Char(string='Size', tracking=True, )
    machine_name = fields.Char(string='Machine n', tracking=True, )
    machine_name_new = fields.Many2one('maintenance.equipment', string='Machine Name', tracking=True, )
    department = fields.Many2one('hr.department', string='Department', domain=[('gauges', '=', True)], tracking=True, )
    machine_no = fields.Char(string='Mach No', tracking=True, )
    machine_no_new = fields.Char(related="machine_name_new.Equipmentcode", string='Machine No', tracking=True, )
    part_name = fields.Many2one('product.template', string='Part test  Name', tracking=True, )
    part_char_name = fields.Char(string='Part Name', tracking=True, )
    calib_frequency = fields.Char(string='Calibration Frequency duplicate', default='Yearly', tracking=True, )
    calib_frequency_selection = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarter', 'Quarter'),
        ('half', 'Half-yearly'),
        ('year', 'Yearly')
    ], default='year', string='Calibration Frequency', tracking=True)
    calib_source = fields.Char(string='Calibration Source', tracking=True, )
    part_no = fields.Many2one('product.template', string='Part No', domain=lambda self: self.get_finished_goods(),
                              tracking=True)

    mmr_state = fields.Selection([
        ('working', 'Working'),
        ('not_working', 'Not Working'),
        ('obsolete', 'Obsolete')
    ], string='Condition', default='working', tracking=True, readonly=False)
    calib_date = fields.Date(tracking=True)
    due_date = fields.Date(tracking=True)
    remarks = fields.Text(tracking=True)
    instruments = fields.Selection([
        ('calibration', 'Instruments'),
        ('gauges', 'Gauges')
    ], tracking=True)
    location = fields.Many2one('mmr.location', string='Location', tracking=True)
    parameter_id = fields.Many2one('quality.parameter', string='Parameter', tracking=True)
    report_no = fields.Char(tracking=True)
    attachment = fields.Binary("Image")
    attachment_report = fields.Binary("Report")

    @api.onchange('report_no')
    def onchange_certificate_no(self):
        for i in self:
            test = self.env['mmr.list'].search([('report_no', '=', i.report_no)])
            if i.report_no:
                if test:
                    raise ValidationError(_('Alert! Kindly enter a Unique Number'))

    @api.onchange('part_no')
    def onchange_value(self):
        for i in self.part_no:
            self.part_char_name = i.name

    @api.onchange('calib_date', 'calib_frequency_selection')
    def create_due_date(self):
        for record in self:
            if record.calib_date:
                if record.calib_frequency_selection == 'monthly':
                    record.due_date = record.calib_date + relativedelta(months=1, days=-1)
                elif record.calib_frequency_selection == 'quarter':
                    record.due_date = record.calib_date + relativedelta(months=3, days=-1)
                elif record.calib_frequency_selection == 'half':
                    record.due_date = record.calib_date + relativedelta(months=6, days=-1)
                elif record.calib_frequency_selection == 'year':
                    record.due_date = record.calib_date + relativedelta(years=1, days=-1)

    def _create_calibration_requests(self):
        today = fields.Date.today()
        due_date_limit = date.today() + timedelta(days=20)
        mmr_instruments = self.env['mmr.list'].search([
            ('mmr_state', '=', 'working'),
            ('due_date', '<=', due_date_limit),
            ('due_date', '>=', today)
        ])
        for instrument in mmr_instruments:
            existing_requests = self.env['calibration.request'].search([
                ('mmr_id', '=', instrument.id),
                ('calib_state', '=', 'draft')
            ])
            if not existing_requests:
                self.env['calibration.request'].create({
                    'mmr_id': instrument.id,
                    'mmr_name': instrument.description,
                    'mmr_frequency': instrument.calib_frequency_selection,
                    'request_instruments': instrument.instruments
                })
                self.send_calibration_mail()

    def _create_calibration_requests_test(self):
        today = fields.Date.today()
        # due_date_limit = date.today() + timedelta(days=20)
        due_date_limit = date(2025, 1, 1)

        mmr_instruments = self.env['mmr.list'].search([
            ('status', '=', 'active'),
            ('due_date', '>=', due_date_limit),
            ('due_date', '<=', today)
        ])
        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@", mmr_instruments)
        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@", today)
        for instrument in mmr_instruments:
            existing_requests = self.env['calibration.request'].search([
                ('mmr_id', '=', instrument.id),
                ('calib_state', '=', 'draft')
            ])
            if not existing_requests:
                self.env['calibration.request'].create({
                    'mmr_id': instrument.id,
                    'mmr_name': instrument.description,
                    'mmr_frequency_selection': instrument.calib_frequency_selection,
                    'request_instruments': instrument.instruments
                })

    def send_calibration_mail(self):
        today = fields.Date.today()
        due_date_limit = today + timedelta(days=20)
        records = self.env['mmr.list'].search(
            [('mmr_state', '=', 'working'),
             ('due_date', '<=', due_date_limit),
             ('due_date', '>=', today)])
        if records:
            mmr_ids = records.mapped('code_no')
            if mmr_ids:
                mmr = ', '.join(mmr_ids)
                body = f"""
                    Dear Quality Team,<br/><br/>
                    The following Instruments need to be Calibrated before {due_date_limit}:<br/><br/>
                    {mmr}<br/><br/>
                    Please take the necessary action to proceed the process.<br/><br/>
                    Regards,<br/>
                    Administrator<br/><br/>
                    <p align="center">
                    ----------------------------------This is a system-generated email----------------------------------------------</p>
                """
                mail_value = {
                    'subject': 'Instruments Calibration',
                    'body_html': body,
                    'email_cc': "",
                    'email_to': "",
                    'email_from': "",
                }
                mail = self.env['mail.mail'].create(mail_value)
                mail.send()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('instruments') == 'calibration':
                vals['code_no'] = self.env['ir.sequence'].next_by_code('instrument.seq') or '/'
            if vals.get('instruments') == 'gauges':
                vals['code_no'] = self.env['ir.sequence'].next_by_code('gauge.seq') or '/'
        return super(MmrList, self).create(vals_list)


class MmrLocation(models.Model):
    _name = 'mmr.location'
    _description = 'MMR Location'
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char(string='Name', tracking=True)
