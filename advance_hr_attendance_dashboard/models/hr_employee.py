from odoo import api, fields, models
from odoo.http import request
from odoo.tools import date_utils
from datetime import datetime
import pandas

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def get_employee_leave_data(self, option):
        start_date = option.get('start_date')
        end_date = option.get('end_date')

        employee_data = []
        present = self.env['ir.config_parameter'].sudo().get_param('advance_hr_attendance_dashboard.present')
        absent = self.env['ir.config_parameter'].sudo().get_param('advance_hr_attendance_dashboard.absent')
        dates = []
        public_holidays = []

        if start_date and end_date:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
            dates = pandas.date_range(
                date_utils.start_of(start_date, 'day'),
                date_utils.end_of(end_date_obj, 'day'),
                freq='d'
            ).strftime("%Y-%m-%d").tolist()

            holiday_lines = self.env['hr.public.holidays.line'].sudo().search([
                ('date', '>=', start_date),
                ('date', '<=', end_date)
            ])
            for holiday in holiday_lines:
                public_holidays.append({'date': holiday.date.strftime("%Y-%m-%d"), 'name': holiday.name})

        cids = request.httprequest.cookies.get('cids')
        allowed_company_ids = [int(cid) for cid in cids.split(',')]

        for employee in self.env['hr.employee'].search([('company_id', 'in', allowed_company_ids)]):
            leave_data = []
            employee_leave_dates = []
            total_absent_count = 0

            query = f"""
                SELECT hl.id, employee_id, request_date_from, request_date_to,
                       hlt.leave_code, hlt.color
                FROM hr_leave hl
                INNER JOIN hr_leave_type hlt ON hlt.id = hl.holiday_status_id 
                WHERE hl.state = 'validate' AND employee_id = {employee.id}
            """
            self._cr.execute(query)
            all_leave_rec = self._cr.dictfetchall()

            for leave in all_leave_rec:
                leave_dates = pandas.date_range(
                    leave.get('request_date_from'),
                    leave.get('request_date_to'),
                    freq='d'
                ).strftime("%Y-%m-%d").tolist()
                leave_dates.insert(0, leave.get('leave_code'))
                leave_dates.insert(1, leave.get('color'))
                for leave_date in leave_dates[2:]:
                    if leave_date in dates:
                        employee_leave_dates.append(leave_date)

            for leave_date in dates:
                color = "#ffffff"
                state = None
                attendance_records = employee.attendance_ids.filtered(
                    lambda att: str(att.check_in.date()) == leave_date
                )
                onduty_type = attendance_records[0].onduty_type if attendance_records else None

                if onduty_type == 'automatic':
                    state = present
                elif onduty_type == 'onduty':
                    state = "OD"
                elif onduty_type == 'compensatory':
                    state = "COMP-OFF"
                else:
                    state = absent

                is_sunday = datetime.strptime(leave_date, "%Y-%m-%d").weekday() == 6
                is_public_holiday = any(ph['date'] == leave_date for ph in public_holidays)

                if is_sunday and is_public_holiday:
                    state = "W/O-P/H"
                    color = "#9c8cd8"
                elif is_sunday:
                    state = "W/O"
                    color = "#c78373"
                elif is_public_holiday:
                    state = "P/H"
                    color = "#73c77a"

                if leave_date in employee_leave_dates:
                    state = leave_dates[0]
                    color = {
                        1: "#F06050", 2: "#F4A460", 3: "#F7CD1F",
                        4: "#6CC1ED", 5: "#814968", 6: "#EB7E7F",
                        7: "#2C8397", 8: "#475577", 9: "#D6145F",
                        10: "#30C381", 11: "#9365B8"
                    }.get(leave_dates[1], "#ffffff")
                    total_absent_count += 1

                leave_data.append({
                    'id': employee.id,
                    'leave_date': leave_date,
                    'state': state,
                    'color': color,
                    'is_sunday': is_sunday,
                    'is_public_holiday': is_public_holiday
                })

            employee_data.append({
                'id': employee.id,
                'emp_code': employee.emp_code,
                'name': employee.name,
                'leave_data': leave_data[::-1],
                'total_absent_count': total_absent_count
            })

        return {
            'employee_data': employee_data,
            'filtered_duration_dates': dates[::-1],
            'public_holidays': public_holidays
        }
