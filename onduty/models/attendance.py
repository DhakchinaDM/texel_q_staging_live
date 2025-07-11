from odoo import models, fields, api, _


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    _description = 'Hr Attendance'

    onduty_type = fields.Selection([
        ('onduty', 'On-Duty'),
        ('automatic', 'Automatic'),
        ('compensatory', 'Compensatory')
    ], default='automatic')