from odoo import models, fields, api, _


class CalibrationListWizard(models.TransientModel):
    _name = 'calibration.list.wizard'
    _description = 'Calibration List Wizard'

    user_id = fields.Many2one('res.users', string='User Name', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    logged_user = fields.Many2one('res.users', string='Logged User', compute='get_logged_user')
    active = fields.Boolean(default=True)
    file_name = fields.Char('File Name')
    prepared_by = fields.Many2one('res.users', string='Prepared By', compute='get_logged_user')
    approved_by = fields.Many2one('hr.employee', string='Approved By')
    quality_instruments = fields.Many2many(
        'mmr.list',
        string='Instruments', domain="""[('id','in',quality_instrument_domain)]""")
    quality_instrument_domain = fields.Many2many('mmr.list', compute='_compute_domain')
    instrument_type = fields.Selection([
        ('gauges', 'Gauges'),
        ('calibration', 'Instruments')
    ], string='Type', default='gauges')


    @api.onchange('instrument_type')
    def allow_list(self):
        self.quality_instruments = False

    @api.onchange('approved_by')
    def get_logged_user(self):
        self.logged_user = self.env.uid
        self.prepared_by = self.env.uid

    @api.depends('instrument_type')
    def _compute_domain(self):
        for rec in self:
            rec.quality_instrument_domain = False
            if rec.instrument_type == 'calibration':
                domain = self.env['mmr.list'].sudo().search([('instruments', '=', 'calibration')])
                print('====quality_instrument_domain====', domain)
                rec.quality_instrument_domain = [(6, 0, [i.id for i in domain])]
            elif rec.instrument_type == 'gauges':
                domain = self.env['mmr.list'].sudo().search([('instruments', '=', 'gauges')])
                print('====quality_instrument_domain====', domain)
                rec.quality_instrument_domain = [(6, 0, [i.id for i in domain])]

    def print_pdf(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'quality_instruments': self.quality_instruments.ids,
            'instrument_type': self.instrument_type,
            'form': {
                'prepared_by': self.prepared_by.name,
                'approved_by': self.approved_by.name,
                'instrument_type': self.instrument_type,
            }
        }
        return self.env.ref('quality_extension.report_calibration_list').report_action(self, data=data)


class GaugesInstrumentsReport(models.AbstractModel):
    _name = 'report.quality_extension.gauges_instruments_template_pdf'
    _description = 'Gauges Instruments Report'

    def _get_report_values(self, docids, data=None):
        instrument_type = data['instrument_type']
        quality_instruments = data['quality_instruments']
        domain = []
        if instrument_type == 'calibration' and not quality_instruments:
            domain.append(('instruments', '=', 'calibration'))
        elif instrument_type == 'calibration' and quality_instruments:
            domain.append(('instruments', '=', 'calibration'))
            domain.append(('id', 'in', quality_instruments))
        elif instrument_type == 'gauges' and not quality_instruments:
            domain.append(('instruments', '=', 'gauges'))
        elif instrument_type == 'gauges' and quality_instruments:
            domain.append(('instruments', '=', 'gauges'))
            domain.append(('id', 'in', quality_instruments))

        mmr_list = self.env['mmr.list'].sudo().search(domain)

        data_mmr = [{
            'code_no': j.code_no,
            'description': j.description,
            'mmr_range': j.mmr_range,
            'least_count': j.least_count,
            'acceptance_criteria': j.acceptance_criteria,
            'make': j.make,
            'size': j.size,
            'part_name': j.part_name.name,
            'calib_frequency': j.calib_frequency,
            'calib_date': j.calib_date,
            'due_date': j.due_date,
            'calib_source': j.calib_source,
            'remarks': j.remarks,
        } for j in mmr_list]

        return {
            'doc_ids': docids,
            'data': data_mmr,
            'doc_model': 'calibration.list.wizard',
            'name': 'Gauges/Instrument Report',
        }
