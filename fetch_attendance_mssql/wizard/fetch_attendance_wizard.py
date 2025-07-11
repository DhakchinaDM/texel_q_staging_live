from datetime import datetime, time, timedelta
from odoo import fields, models, api, _
import pymssql
import logging
from datetime import date
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def _default_start_date(self):
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    return start_of_week


def _default_end_date(self):
    today = date.today()
    end_of_week = today + timedelta(days=(6 - today.weekday()))
    return end_of_week


class FetchAttendanceWizard(models.TransientModel):
    _name = 'fetch.attendance.wizard'
    _description = 'Fetch Attendance'

    start_date = fields.Date(default=_default_start_date, required=True)
    end_date = fields.Date(default=_default_end_date, required=True)

    from datetime import datetime, timedelta

    def fetch_attendance_data(self):
        server = self.env['ir.config_parameter'].sudo().get_param('fetch_attendance_mssql.ip_address')
        user = self.env['ir.config_parameter'].sudo().get_param('fetch_attendance_mssql.mssql_db_user')
        password = self.env['ir.config_parameter'].sudo().get_param('fetch_attendance_mssql.mssql_db_password')
        database = self.env['ir.config_parameter'].sudo().get_param('fetch_attendance_mssql.mssql_db_name')

        try:
            conn = pymssql.connect(server=server, user=user, password=password, database=database, charset='UTF-8',
                                   tds_version='7.0')
        except pymssql.OperationalError as e:
            raise ValidationError(
                f"Unable to connect to the MSSQL database. Please check the connection details: {str(e)}")

        cursor = conn.cursor()
        print("----------------------------------Connection successful.")
        sql_query_punch = "SELECT UserID, Punch1, Punch2, UserName FROM Mx_VEW_APIDailyAttendance"
        cursor.execute(sql_query_punch)
        records = cursor.fetchall()
        time_difference = timedelta(hours=5, minutes=30)
        for record in records:
            user_id, punch_in, punch_out, user_name = record
            if punch_in:
                try:
                    punch_in_datetime = datetime.strptime(punch_in, '%d/%m/%Y %H:%M:%S') - time_difference
                    if self.start_date <= punch_in_datetime.date() <= self.end_date:
                        employee = self.env['hr.employee'].search([('emp_code', '=', str(user_id))], limit=1)
                        if employee:
                            attendance_vals = {
                                'employee_id': employee.id,
                                'check_in': punch_in_datetime}
                            current_time = datetime.now()
                            if current_time >= punch_in_datetime + timedelta(hours=10) and not punch_out:
                                auto_check_out = punch_in_datetime + timedelta(hours=8)
                                attendance_vals['check_out'] = auto_check_out
                                attendance_vals['auto_checked_out'] = True
                            elif punch_out:
                                punch_out_datetime = datetime.strptime(punch_out, '%d/%m/%Y %H:%M:%S') - time_difference
                                attendance_vals['check_out'] = punch_out_datetime
                            self.env.cr.execute("""
                                SELECT id FROM hr_attendance
                                WHERE employee_id = %s
                                AND DATE(check_in) = %s
                                LIMIT 1
                            """, (employee.id, punch_in_datetime.date()))
                            existing_attendance = self.env.cr.fetchone()
                            if existing_attendance:
                                if 'check_out' in attendance_vals:
                                    self.env.cr.execute("""
                                        UPDATE hr_attendance
                                        SET check_out = %s
                                        WHERE id = %s
                                    """, (attendance_vals['check_out'], existing_attendance[0]))
                            else:
                                type = 'automatic'
                                self.env.cr.execute("""
                                    INSERT INTO hr_attendance (employee_id, check_in, check_out, auto_checked_out,onduty_type)
                                    VALUES (%s, %s, %s, %s,%s)
                                """, (employee.id, punch_in_datetime, attendance_vals.get('check_out', None),
                                      attendance_vals.get('auto_checked_out', False),type))
                except ValueError as e:
                    print(f"Error parsing punch_in '{punch_in}': {e}")
        conn.close()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
