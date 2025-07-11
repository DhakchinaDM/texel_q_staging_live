# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError


class InternalServiceWizard(models.TransientModel):
    _name = 'internal.service.wizard'
    _description = 'Internal Service Wizard'

    maintenance_service_order_ref = fields.Char(string="Reference")
    equipment_id = fields.Many2one('maintenance.equipment', string='Equipment id')
    machine = fields.Char(string="Equipment Name", related='equipment_id.name')
    category = fields.Many2one('maintenance.equipment.category', string="Category",
                               related='equipment_id.category_id', store=True)
    remarks = fields.Html(string="Remarks", default='Internal Service has begins & I confirm that')
    service_duration = fields.Datetime(string="Service Start  Time ")
    service_end_duration = fields.Datetime(string="Service End Time ", default=lambda self: fields.Datetime.now())
    service_started = fields.Boolean()
    service_ended = fields.Boolean()

    def tick_ok(self):
        applicant_id = self._context.get('active_ids')[0]
        active_id = self.env['maintenance.request'].search([('id', '=', applicant_id)])
        today = datetime.now()
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        text = self.remarks
        active_id.write({
            'internal_remarks': text,
            'cur_user': self.env.user.id,
            'cur_time': current_date,
            'service_started': True,
        })
        return True

    def service_finish(self):
        applicant_id = self._context.get('active_ids')[0]
        active_id = self.env['maintenance.request'].search([('id', '=', applicant_id)])
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        text = self.remarks
        active_id.write({
            'end_remarks': text,
            'end_cur_user': self.env.user.id,
            'cur_time': self.service_duration,
            'end_cur_time': self.service_end_duration or current_date,
            'service_ended': True,
            'stage_id': self.env.ref('maintenance_extended.stage_completed').id
        })
        line_vals = []
        vals = {
            'maintenance_request_name': active_id.id,
            'maintenance_request_code': active_id.request_code,
            'maintenance_team_id': active_id.maintenance_team_id.id,
            'request_created_by': active_id.employee_id.id,
            'request_responsible': active_id.user_id.employee_id.id,
            'maintenance_request_ref': active_id.reference,
            'maintenance_type': active_id.maintenance_type,
            'maintenance_duration': active_id.duration,
            'maintenance_end_date': active_id.end_cur_time,
        }
        line_vals.append((0, 0, vals))
        self.equipment_id.equipment_history_ids = line_vals
        self.equipment_id.last_maintenance_date = current_date
        # if active_id.cur_time and active_id.end_cur_time:
        #     date1 = str(active_id.cur_time)
        #     datetimeFormat = '%Y-%m-%d %H:%M:%S'
        #     date2 = str(active_id.end_cur_time)
        #     date11 = datetime.strptime(date1, datetimeFormat)
        #     date12 = datetime.strptime(date2, datetimeFormat)
        #     if active_id.cur_time and active_id.end_cur_time:
        #         timedelta = date12 - date11
        #         tot_sec = timedelta.total_seconds()
        #         h = tot_sec // 3600
        #         m = (tot_sec % 3600) // 60
        #         duration_hour = ("%d.%d" % (h, m))
        #         active_id.duration_one = float(duration_hour)
        #         active_id.duration = timedelta
        #     else:
        #         active_id.duration = False
        #         active_id.duration_one = False
        return True
