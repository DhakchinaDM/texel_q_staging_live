from odoo import models, fields, api, _
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class HrDepartment(models.Model):
    _inherit = 'hr.department'


    gauges = fields.Boolean("Gauges")
