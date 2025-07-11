from odoo import api, fields, models, _


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    _description = 'Pay Slip'

    auto_checked_out = fields.Boolean()