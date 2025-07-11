from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta


class MachineHistory(models.Model):
    _name = 'machine.history'
    _description = 'Machine History'
    _rec_name = 'reference'
    _inherit = ['mail.thread']  # ✅ Add this line



    doc_num = fields.Char(string='Document Number', tracking=True )
    rev_date = fields.Date(string='Revision Date', tracking=True)
    rev_num = fields.Char(string='Revision Number', tracking=True)


    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    logged_user = fields.Many2one('res.users', string='Logged User', compute='get_logged_user')

    def get_logged_user(self):
        self.logged_user = self.env.uid

    machine_id = fields.Many2one('maintenance.equipment', string='Machine')
    type = fields.Selection([('corrective', 'BreakDown'), ('preventive', 'Preventive'), ('predictive', 'Predictive')], string='Type ')
    reference = fields.Reference(selection=[('preventive.maintenance.check', 'Preventive'), ('corrective.maintenance', 'BreakDown')], string="Reference")
    user_id = fields.Many2one('res.users', string='Created By')
    plan_date = fields.Date(string='Plan/Breakdown Date')
    plan_hours = fields.Float(string='Planned Hours/Duration')
    actual_date = fields.Date(string='Actual/Restart Date')
    remarks = fields.Text(string='Remarks ')
    preventive_maintenance_type = fields.Selection([
        ('annually', 'Annually'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annually', 'Semi-Annually'),
    ], string="PMC Type ",)


