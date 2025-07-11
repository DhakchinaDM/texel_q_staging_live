import pytz
from odoo import models, api
from datetime import date, timedelta
import math


class AttendanceReportParser(models.AbstractModel):
    _name = 'report.hr_payroll_extended.attendance_report_template'
    _description = 'Attendance Report Parser'

    def get_lmd_dict_value(self, start_date, end_date):
        public_holidays = self.sudo().env['resource.calendar.leaves'].search([('resource_id', '=', False)])
        step = timedelta(days=1)
        current_date = start_date
        list_month_val = []
        list_month_dic = {}
        while current_date <= end_date:
            if current_date.strftime("%b-%Y") not in list_month_val:
                list_month_val.append(current_date.strftime("%b-%Y"))
                list_month_dic[current_date.strftime("%b-%Y")] = {
                    "int": current_date.strftime("%m-%Y"),
                    "val": ""
                }
            current_date += step

        for i in list_month_val:
            date_list_val_dic = {}
            date_list_val_list = []
            current_date = start_date
            while current_date <= end_date:
                if current_date.strftime("%b-%Y") == i:
                    date_list_val_list.append(current_date.strftime("%d"))
                    date_list_val_dic[current_date.strftime("%d")] = {
                        'date': current_date.strftime("%d"),
                        'val': False,
                        'half': False,
                        'public_holidays': False,
                        'date_value': current_date,
                        'week_day': current_date.weekday()
                    }
                    for ph in public_holidays:
                        if ph.date_from.date() == current_date:
                            date_list_val_dic[current_date.strftime("%d")] = {
                                'date': current_date.strftime("%d"),
                                'val': False,
                                'half': False,
                                'public_holidays': True,
                                'date_value': current_date,
                                'week_day': current_date.weekday()
                            }
                current_date += step
            list_month_dic[i]['val'] = date_list_val_dic
        return list_month_dic, list_month_val

    def _get_report_values(self, docids, data=None):
        start_date = date.fromisoformat(data['start_date'])
        end_date = date.fromisoformat(data['end_date'])

        local_timezone = pytz.timezone("Asia/Kolkata")
        attendance_details_read = self.env['hr.attendance'].search_read([
            ('check_in', '>=', start_date),
            ('check_in', '<=', end_date)
        ], fields=['employee_id', 'check_in', 'check_out', 'worked_hours'], order='check_in asc')
        hr_employee = self.env['hr.employee'].search([])
        list_month_val = self.get_lmd_dict_value(start_date, end_date)[1]
        present_absent = []
        for he in hr_employee:
            # ---------------------
            lmd = self.get_lmd_dict_value(start_date, end_date)[0]
            # ---------------------
            for lm_dic in lmd:
                for qq in lmd[lm_dic]['val']:
                    for hr_add in attendance_details_read:
                        if lmd[lm_dic]['val'][qq]['date_value'] == hr_add['check_in'].date() and he.id == \
                                hr_add['employee_id'][0]:
                            lmd[lm_dic]['val'][qq]['val'] = "P"

            final_dic = {
                'employee_id': he.id,
                'employee_name': he.name,
                'list_month_dic': lmd
            }
            present_absent.append(final_dic)

        for fv in present_absent:

            leave = self.sudo().env['hr.leave'].search([('state', '=', 'validate'),
                                                        ('employee_id', '=', fv['employee_id'])])
            for gg in fv['list_month_dic']:
                for kk in fv['list_month_dic'][gg]['val']:
                    for ll in leave:
                        if ll.date_from.date() == fv['list_month_dic'][gg]['val'][kk]['date_value']:
                            if ll.number_of_days_display < 1:
                                start_val = ll.date_from.astimezone(local_timezone).strftime('%I:%M %p')
                                end_val = ll.date_to.astimezone(local_timezone).strftime('%I:%M %p')
                                fv['list_month_dic'][gg]['val'][kk]['half'] = str(start_val) + "-" + str(end_val)
                            result = math.ceil(ll.number_of_days_display)
                            cc = 0
                            for r in range(result):
                                aa = int(kk) + cc
                                bb = '{:02d}'.format(aa)
                                if fv['list_month_dic'][gg]['val'][bb]['week_day'] != 6:
                                    fv['list_month_dic'][gg]['val'][bb]['val'] = ll.holiday_status_id.code
                                    if fv['list_month_dic'][gg]['val'][bb]['public_holidays'] == True:
                                        while fv['list_month_dic'][gg]['val'][bb]['public_holidays'] == True:
                                            cc += 1
                                            aa = int(kk) + cc
                                            bb = '{:02d}'.format(aa)
                                            fv['list_month_dic'][gg]['val'][bb]['val'] = ll.holiday_status_id.code

                                else:
                                    cc += 1
                                    aa = int(kk) + cc
                                    bb = '{:02d}'.format(aa)
                                    fv['list_month_dic'][gg]['val'][bb]['val'] = ll.holiday_status_id.code
                                    if fv['list_month_dic'][gg]['val'][bb]['public_holidays'] == True:
                                        while fv['list_month_dic'][gg]['val'][bb]['public_holidays'] == True:
                                            cc += 1
                                            aa = int(kk) + cc
                                            bb = '{:02d}'.format(aa)
                                            fv['list_month_dic'][gg]['val'][bb]['val'] = ll.holiday_status_id.code
                                cc += 1
        # Header For Attendance List
        cols_heads = ['S.No', 'Employee Name', 'Check In Date', 'Check In Time', 'Check Out Date', 'Check Out Time',
                      'Worked Hours']
        return {
            'cols_heads': cols_heads,
            'data': data,
            'start_date': start_date,
            'end_date': end_date,
            'attendance_details_read': attendance_details_read,
            'list_month_val': list_month_val,
            'present_absent': present_absent,
            'local_timezone': local_timezone,
        }
