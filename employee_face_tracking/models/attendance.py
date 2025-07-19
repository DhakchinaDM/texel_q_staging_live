from odoo import models, fields

from odoo import fields, models, api
from odoo.osv.expression import OR
import uuid
from werkzeug.urls import url_join


import base64
from pytz import timezone, UTC
from datetime import datetime, time
from random import choice
from string import digits
from werkzeug.urls import url_encode
from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError
from odoo.osv import expression
from odoo.tools import format_date

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    check_in_image = fields.Binary("Image")
    check_out_image = fields.Binary("Image")



# class ResCompany(models.Model):
#     _inherit = 'res.company'
#
#     attendance_face_key = fields.Char(default=lambda s: uuid.uuid4().hex, copy=False, groups='hr_attendance.group_hr_attendance_manager')
#     attendance_face_url = fields.Char(compute="_compute_attendance_face_url")
#
#     @api.depends("attendance_face_key")
#     def _compute_attendance_face_url(self):
#         for company in self:
#             company.attendance_face_url = url_join(self.env['res.company'].get_base_url(), '/face_tracking/%s' % company.attendance_face_key)
#
#
#
#     def _action_open_face_mode(self):
#         return {
#             'type': 'ir.actions.act_url',
#             'target': 'self',
#             'url': f'/hr_attendance/face_mode_menu/{self.env.company.id}',
#         }




# class HrEmployeePrivate(models.Model):
#     _inherit = "hr.employee"
#
#
#     def generate_random_barcode(self):
#         for employee in self:
#             employee.barcode = '041'+"".join(choice(digits) for i in range(9))