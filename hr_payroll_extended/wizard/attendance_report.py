import pytz
from odoo import api, fields, models, _
from datetime import datetime, timedelta
import xlwt
from io import BytesIO
import base64
from xlwt import easyxf
import math


class AttendanceSummaryReport(models.TransientModel):
    _name = 'attendance.summary.report'
    _description = 'Wizard Report'

    start_date = fields.Date(string='Start date', required=True)
    end_date = fields.Date(string='End date', required=True, default=fields.Date.today())
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    summary_file = fields.Binary('Attendance Report')
    file_name = fields.Char('File Name')
    report_printed = fields.Boolean(' Attendance Report')
    ams_time = datetime.now() + timedelta(hours=5, minutes=30)
    date = ams_time.strftime('%d-%m-%Y %H:%M:%S')
    report_all_attendance_report = fields.Boolean(string="All Attendance report")
    report_all_present_absent = fields.Boolean(string="Present Absent")


    def print_attendance_report_pdf(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'report_all_attendance_report': self.report_all_attendance_report,
            'report_all_present_absent': self.report_all_present_absent,
            'start_date': self.start_date,
            'end_date': self.end_date
        }
        return self.env.ref('hr_payroll_extended.report_attendance_pdf').report_action(self, data=data)

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

    def print_product_excel_report(self):
        workbook = xlwt.Workbook()
        xlwt.add_palette_colour("light_green", 0x21)
        xlwt.add_palette_colour("light_red", 0x22)
        xlwt.add_palette_colour("light_blue", 0x23)
        xlwt.add_palette_colour("light_orange", 0x24)
        xlwt.add_palette_colour("light_yellow", 0x25)
        workbook.set_colour_RGB(0x21, 128, 255, 128)
        workbook.set_colour_RGB(0x22, 255, 112, 77)
        workbook.set_colour_RGB(0x23, 153, 204, 255)
        workbook.set_colour_RGB(0x24, 255, 179, 102)
        workbook.set_colour_RGB(0x25, 255, 179, 102)
        design_light_green = easyxf('align: horiz center;font: bold 1;pattern: pattern solid,fore_colour light_green')
        design_light_red = easyxf('align: horiz center;font: bold 1;pattern: pattern solid,fore_colour light_red')
        design_light_blue = easyxf('align: horiz center;font: bold 1;pattern: pattern solid,fore_colour light_blue')
        design_light_orange = easyxf('align: horiz center;font: bold 1;pattern: pattern solid,fore_colour light_orange')
        design_light_yellow = easyxf('align: horiz center;font: bold 1;pattern: pattern solid,fore_colour light_yellow')
        worksheet1 = workbook.add_sheet('Attendance Sheet')
        design_7 = easyxf('align: horiz center;font: bold 1;')
        design_8 = easyxf('align: horiz left;')
        design_13 = easyxf('align: horiz center;font: bold 1;pattern: pattern solid, fore_colour grey25;')
        design_emp = easyxf('align: horiz left;font: bold 1;')
        design_14 = easyxf('align: horiz left;font: bold 1;pattern: pattern solid, fore_colour gray25;')
        worksheet1.col(0).width = 5000
        worksheet1.col(1).width = 5000
        worksheet1.col(2).width = 4000
        worksheet1.col(3).width = 4000
        worksheet1.col(4).width = 4000
        worksheet1.col(5).width = 4000
        worksheet1.col(6).width = 5000
        rows = 0
        cols = 0
        worksheet1.set_panes_frozen(True)
        worksheet1.set_horz_split_pos(rows + 1)
        rows += 1
        worksheet1.write_merge(rows, rows, 2, 3, 'Attendance Report', design_13)
        rows += 1
        worksheet1.write(rows, 2, 'Start Date', design_14)
        worksheet1.write(rows, 3, self.start_date.strftime('%d-%m-%Y'), design_13)
        rows += 1
        worksheet1.write(rows, 2, 'End Date', design_14)
        worksheet1.write(rows, 3, self.end_date.strftime('%d-%m-%Y'), design_13)
        rows += 3

        start_date = self.start_date
        end_date = self.end_date

        local_timezone = pytz.timezone("Asia/Kolkata")
        attendance_details_read = self.env['hr.attendance'].search_read([
            ('check_in', '>=', start_date),
            ('check_in', '<=', end_date)
        ], fields=['employee_id', 'check_in', 'check_out', 'worked_hours'], order='check_in asc')
        hr_employee = self.env['hr.employee'].search([])
        list_month_val = self.get_lmd_dict_value(start_date, end_date)[1]
        present_absent = []
        for he in hr_employee:
            lmd = self.get_lmd_dict_value(start_date, end_date)[0]
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

        if self.report_all_attendance_report:
            cols_heads = ['S.No', 'Employee Name', 'Check In Date', 'Check In Time', 'Check Out Date', 'Check Out Time',
                          'Worked Hours']
            for i in cols_heads:
                worksheet1.write(rows, cols, _(i), design_13)
                cols += 12
            rows += 1
            count = 0
            val_true_false = False
            date_val = False
            for d in attendance_details_read:
                count += 1
                if not val_true_false:
                    val_true_false = True
                    date_val = d['check_in'].strftime('%d-%m-%Y')
                    worksheet1.write_merge(rows, rows, 0, 6, d['check_in'].strftime('%d-%m-%Y'), design_13)
                    rows += 1
                if d['check_in'].strftime('%d-%m-%Y') == date_val:
                    worksheet1.write(rows, 0, count, design_8)
                    worksheet1.write(rows, 1, d['employee_id'][1], design_8)
                    if d['check_in']:
                        worksheet1.write(rows, 2,
                                         d['check_in'].strftime('%d-%m-%Y'), design_8)
                        worksheet1.write(rows, 3,
                                         d['check_in'].astimezone(local_timezone).strftime(
                                             '%I:%M %p'), design_8)
                    else:
                        worksheet1.write(rows, 2, '-', design_8)
                        worksheet1.write(rows, 3, '-', design_8)
                    if d['check_out']:
                        worksheet1.write(rows, 4,
                                         d['check_out'].strftime('%d-%m-%Y'), design_8)
                        worksheet1.write(rows, 5,
                                         d['check_out'].astimezone(local_timezone).strftime(
                                             '%I:%M %p'), design_8)
                    else:
                        worksheet1.write(rows, 4, '-', design_8)
                        worksheet1.write(rows, 5, '-', design_8)
                    if d['worked_hours']:
                        worksheet1.write(rows, 6,
                                         str(int(d['worked_hours'])) + ' Hours ' + str(
                                             int((d['worked_hours'] - int(d['worked_hours'])) * 60)) + ' Mins',
                                         design_8)
                    else:
                        worksheet1.write(rows, 6, '-', design_8)
                if d['check_in'].strftime('%d-%m-%Y') != date_val:
                    rows += 1
                    val_true_false = True
                    date_val = d['check_in'].strftime('%d-%m-%Y')
                    worksheet1.write_merge(rows, rows, 0, 6, d['check_in'].strftime('%d-%m-%Y'), design_13)
                    rows += 1
                    worksheet1.write(rows, 0, count, design_8)
                    worksheet1.write(rows, 1, d['employee_id'][1], design_8)
                    if d['check_in']:
                        worksheet1.write(rows, 2,
                                         d['check_in'].strftime('%d-%m-%Y'), design_8)
                        worksheet1.write(rows, 3,
                                         d['check_in'].astimezone(local_timezone).strftime(
                                             '%I:%M %p'), design_8)
                    else:
                        worksheet1.write(rows, 2, '-', design_8)
                        worksheet1.write(rows, 3, '-', design_8)
                    if d['check_out']:
                        worksheet1.write(rows, 4,
                                         d['check_out'].strftime('%d-%m-%Y'), design_8)
                        worksheet1.write(rows, 5,
                                         d['check_out'].astimezone(local_timezone).strftime(
                                             '%I:%M %p'), design_8)
                    else:
                        worksheet1.write(rows, 4, '-', design_8)
                        worksheet1.write(rows, 5, '-', design_8)
                    if d['worked_hours']:
                        worksheet1.write(rows, 6,
                                         str(int(d['worked_hours'])) + ' Hours ' + str(
                                             int((d['worked_hours'] - int(d['worked_hours'])) * 60)) + ' Mins',
                                         design_8)
                    else:
                        worksheet1.write(rows, 6, '-', design_8)
                rows += 1

        rows += 1
        if self.report_all_present_absent:
            worksheet1.write_merge(rows, rows, 2, 3, 'Employee Present And Absent List', design_13)
            rows += 2

            for lmv in list_month_val:
                # Write the month header
                worksheet1.write_merge(rows, rows, 0, 6, lmv, design_13)
                rows += 1

                # Write the common date header
                date_row_start = rows
                worksheet1.write(rows, 0, 'Employee Name', design_13)
                cc = 0
                for jj in present_absent[0]['list_month_dic'][lmv]['val']:
                    cc += 1
                    worksheet1.write(rows, cc, present_absent[0]['list_month_dic'][lmv]['val'][jj]['date'], design_13)
                rows += 1  # Move to the next row for data

                # Write employee data
                for val in present_absent:
                    for month in val['list_month_dic']:
                        if month == lmv:
                            worksheet1.write(rows, 0, val['employee_name'], design_emp)
                            cc = 0

                            # Write attendance data
                            for jj in val['list_month_dic'][month]['val']:
                                cc += 1
                                if val['list_month_dic'][month]['val'][jj]['week_day'] != 6:  # Not a Saturday
                                    if val['list_month_dic'][month]['val'][jj]['val']:
                                        if not val['list_month_dic'][month]['val'][jj]['public_holidays']:
                                            if not val['list_month_dic'][month]['val'][jj]['half']:
                                                if val['list_month_dic'][month]['val'][jj]['val'] == 'P':
                                                    worksheet1.write(rows, cc,
                                                                     val['list_month_dic'][month]['val'][jj]['val'],
                                                                     design_light_green)
                                                else:
                                                    worksheet1.write(rows, cc,
                                                                     val['list_month_dic'][month]['val'][jj]['val'],
                                                                     design_light_blue)
                                            else:
                                                worksheet1.write(rows, cc,
                                                                 val['list_month_dic'][month]['val'][jj]['val'] +
                                                                 val['list_month_dic'][month]['val'][jj]['half'],
                                                                 design_light_orange)
                                        else:
                                            worksheet1.write(rows, cc, 'PH', design_light_yellow)
                                    else:
                                        if val['list_month_dic'][month]['val'][jj]['public_holidays']:
                                            worksheet1.write(rows, cc, 'PH', design_light_yellow)
                                        else:
                                            worksheet1.write(rows, cc, '-', design_7)
                                else:
                                    worksheet1.write(rows, cc, 'H', design_light_red)

                            rows += 1  # Move to the next row for the next employee

                rows += 2  # Add space between months

        if self.report_all_attendance_report == False and self.report_all_present_absent == False:
            cols_heads = ['S.No', 'Employee Name', 'Check In Date', 'Check In Time', 'Check Out Date',
                          'Check Out Time',
                          'Worked Hours']
            for i in cols_heads:
                worksheet1.write(rows, cols, _(i), design_13)
                cols += 1
            rows += 1
            count = 0
            val_true_false = False
            date_val = False
            for d in attendance_details_read:
                count += 1
                if not val_true_false:
                    val_true_false = True
                    date_val = d['check_in'].strftime('%d-%m-%Y')
                    worksheet1.write_merge(rows, rows, 0, 6, d['check_in'].strftime('%d-%m-%Y'), design_13)
                    rows += 1
                if d['check_in'].strftime('%d-%m-%Y') == date_val:
                    worksheet1.write(rows, 0, count, design_8)
                    worksheet1.write(rows, 1, d['employee_id'][1], design_8)
                    if d['check_in']:
                        worksheet1.write(rows, 2,
                                         d['check_in'].strftime('%d-%m-%Y'), design_8)
                        worksheet1.write(rows, 3,
                                         d['check_in'].astimezone(local_timezone).strftime(
                                             '%I:%M %p'), design_8)
                    else:
                        worksheet1.write(rows, 2, '-', design_8)
                        worksheet1.write(rows, 3, '-', design_8)
                    if d['check_in']:
                        worksheet1.write(rows, 4,
                                         d['check_out'].strftime('%d-%m-%Y'), design_8)
                        worksheet1.write(rows, 5,
                                         d['check_out'].astimezone(local_timezone).strftime(
                                             '%I:%M %p'), design_8)
                    else:
                        worksheet1.write(rows, 4, '-', design_8)
                        worksheet1.write(rows, 5, '-', design_8)
                    if d['worked_hours']:
                        worksheet1.write(rows, 6,
                                         str(int(d['worked_hours'])) + ' Hours ' + str(
                                             int((d['worked_hours'] - int(d['worked_hours'])) * 60)) + ' Mins',
                                         design_8)
                    else:
                        worksheet1.write(rows, 6, '-', design_8)
                if d['check_in'].strftime('%d-%m-%Y') != date_val:
                    rows += 1
                    val_true_false = True
                    date_val = d['check_in'].strftime('%d-%m-%Y')
                    worksheet1.write_merge(rows, rows, 0, 6, d['check_in'].strftime('%d-%m-%Y'), design_13)
                    rows += 1
                    worksheet1.write(rows, 0, count, design_8)
                    worksheet1.write(rows, 1, d['employee_id'][1], design_8)
                    if d['check_in']:
                        worksheet1.write(rows, 2,
                                         d['check_in'].strftime('%d-%m-%Y'), design_8)
                        worksheet1.write(rows, 3,
                                         d['check_in'].astimezone(local_timezone).strftime(
                                             '%I:%M %p'), design_8)
                    else:
                        worksheet1.write(rows, 2, '-', design_8)
                        worksheet1.write(rows, 3, '-', design_8)
                    if d['check_in']:
                        worksheet1.write(rows, 4,
                                         d['check_out'].strftime('%d-%m-%Y'), design_8)
                        worksheet1.write(rows, 5,
                                         d['check_out'].astimezone(local_timezone).strftime(
                                             '%I:%M %p'), design_8)
                    else:
                        worksheet1.write(rows, 4, '-', design_8)
                        worksheet1.write(rows, 5, '-', design_8)
                    if d['worked_hours']:
                        worksheet1.write(rows, 6,
                                         str(int(d['worked_hours'])) + ' Hours ' + str(
                                             int((d['worked_hours'] - int(d['worked_hours'])) * 60)) + ' Mins',
                                         design_8)
                    else:
                        worksheet1.write(rows, 6, '-', design_8)
                rows += 1

            rows += 1
            worksheet1.write_merge(rows, rows, 2, 3, 'Employee Present And Absent List', design_13)
            rows += 2
            for lmv in list_month_val:
                worksheet1.write_merge(rows, rows, 0, 6, lmv, design_13)
                rows += 3
                for val in present_absent:
                    for month in val['list_month_dic']:
                        if month == lmv:
                            worksheet1.write(rows - 1, 0, val['employee_name'], design_13)
                            cc = 0
                            for jj in val['list_month_dic'][month]['val']:
                                cc += 1
                                worksheet1.write(rows - 1, cc, val['list_month_dic'][month]['val'][jj]['date'],
                                                 design_13)
                            cc = 0
                            for jj in val['list_month_dic'][month]['val']:

                                cc += 1
                                if val['list_month_dic'][month]['val'][jj]['week_day'] != 6:
                                    if val['list_month_dic'][month]['val'][jj]['val']:
                                        if not val['list_month_dic'][month]['val'][jj]['public_holidays']:
                                            if not val['list_month_dic'][month]['val'][jj]['half']:
                                                if val['list_month_dic'][month]['val'][jj]['val'] == 'P':
                                                    worksheet1.write(rows, cc,
                                                                     val['list_month_dic'][month]['val'][jj]['val'],
                                                                     design_light_green)
                                                else:
                                                    worksheet1.write(rows, cc,
                                                                     val['list_month_dic'][month]['val'][jj]['val'],
                                                                     design_light_blue)
                                            else:
                                                worksheet1.write(rows, cc,
                                                                 val['list_month_dic'][month]['val'][jj]['val'] +
                                                                 val['list_month_dic'][month]['val'][jj]['half'],
                                                                 design_light_orange)

                                        else:
                                            worksheet1.write(rows, cc, 'PH', design_light_yellow)
                                    else:
                                        if val['list_month_dic'][month]['val'][jj]['public_holidays']:
                                            worksheet1.write(rows, cc, 'PH', design_light_yellow)
                                        else:
                                            worksheet1.write(rows, cc, '-', design_7)
                                else:
                                    worksheet1.write(rows, cc, 'H', design_light_red)
                            rows += 3
                rows += 2

        fp = BytesIO()
        o = workbook.save(fp)
        fp.read()
        excel_file = base64.b64encode(fp.getvalue())
        self.write(
            {'summary_file': excel_file,
             'file_name': 'Employee Attendance Excel Report - [ %s ].xls' % self.start_date.strftime('%d/%m/%Y'),
             'report_printed': True})
        fp.close()
        return {
            'view_mode': 'form',
            'name': 'Attendance Summary Report',
            'res_id': self.id,
            'res_model': 'attendance.summary.report',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'target': 'new',
        }
