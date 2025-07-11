from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from datetime import date, datetime
import xlwt
from io import BytesIO
import base64
from base64 import b64decode, b64encode
from xlwt import easyxf, Borders
import io
import base64
from odoo.tools import base64_to_image
from PIL import Image


class ProvidentFundStatement(models.TransientModel):
    _name = 'provident.fund'
    _description = 'Provident Fund Statement'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    summary_file = fields.Binary('PF Report')
    file_name = fields.Char('File Name')
    report_printed = fields.Boolean('Report')
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    select_month = fields.Selection([
        ('January', 'January'),
        ('February', 'February'),
        ('March', 'March'),
        ('April', 'April'),
        ('May', 'May'),
        ('June', 'June'),
        ('July', 'July'),
        ('August', 'August'),
        ('September', 'September'),
        ('October', 'October'),
        ('November', 'November'),
        ('December', 'December'),
    ], string="Month", default=lambda self: datetime.now().strftime('%B'))
    select_year = fields.Many2one('hr.payroll.year', string='Year',
                                  default=lambda self: self._default_year())

    @api.model
    def _default_year(self):
        current_year = datetime.now().year
        year = self.env['hr.payroll.year'].search([('name', '=', str(current_year))])
        return year and year.id or False

    @api.onchange('select_month', 'select_year', )
    def _compute_dates(self):
        for record in self:
            if record.select_month:
                current_year = datetime.now().year
                year = int(record.select_year.name) if record.select_year and record.select_year.name else current_year
                month = datetime.strptime(record.select_month, '%B').month
                date_to = date(year, month, 25)
                if month == 1:
                    prev_month_year = year - 1
                    prev_month = 12
                else:
                    prev_month_year = year
                    prev_month = month - 1
                date_from = date(prev_month_year, prev_month, 26)
                record.start_date = date_from
                record.end_date = date_to

    def action_provident_fund_excel(self):
        workbook = xlwt.Workbook()
        worksheet1 = workbook.add_sheet('Provident Fund Report')
        design_1 = easyxf(
            'align: horiz center, vert center; font: bold 1; pattern:pattern solid, fore_colour gray25;borders: left thin, right thin, top thin, bottom thin, left_colour 0x17, right_colour 0x17, top_colour 0x17, bottom_colour 0x17;')
        design_4 = easyxf('align: horiz center; font: bold 1,height 200; ')
        design_5 = easyxf(
            'align: horiz left, vert center;font: bold 1;')
        design_6 = easyxf('align: horiz center; font: bold 1,height 350; ')
        design_7 = easyxf('align: horiz center; font: bold 1,height 250; ')
        design_8 = easyxf(
            'align: horiz center, vert center;')
        design_9 = easyxf(
            'align: horiz left, vert center;')
        design_10 = easyxf(
            'align: horiz right, vert center;')

        design_11 = easyxf(
            'align: horiz center, vert center;font: bold 1;')
        design_12 = easyxf(
            'align: horiz right, vert center;font: bold 1;')

        worksheet1.row(0).height_mismatch = True
        worksheet1.row(0).height = 500
        worksheet1.row(1).height = 300
        worksheet1.row(2).height = 450
        worksheet1.row(5).height = 450

        worksheet1.col(0).width = 1500
        worksheet1.col(1).width = 4000
        worksheet1.col(2).width = 7000
        worksheet1.col(3).width = 5000
        worksheet1.col(4).width = 5000
        worksheet1.col(5).width = 7000
        worksheet1.col(6).width = 5000
        worksheet1.col(7).width = 5000
        worksheet1.col(8).width = 2300
        worksheet1.col(9).width = 2300
        worksheet1.col(10).width = 2300
        worksheet1.col(11).width = 2300
        worksheet1.col(12).width = 2300
        worksheet1.col(13).width = 2300
        worksheet1.col(14).width = 2300
        worksheet1.col(15).width = 2300
        worksheet1.col(16).width = 2300
        worksheet1.col(17).width = 3000
        worksheet1.col(18).width = 3000
        worksheet1.col(19).width = 3000
        worksheet1.col(20).width = 5000
        worksheet1.col(21).width = 5000
        worksheet1.col(22).width = 6000
        worksheet1.col(23).width = 6000

        rows = 0
        serial_no = 1
        cols = 0

        # TO SET THE 1ST 4 ROW FREEZE
        worksheet1.set_panes_frozen(True)
        worksheet1.set_horz_split_pos(rows + 7)

        worksheet1.write_merge(rows, rows, 0, 23, str(self.company_id.name), design_6)
        rows += 1
        address = str(self.company_id.street) + str(self.company_id.street2) + str(self.company_id.state_id.name) + str(
            self.company_id.zip)
        worksheet1.write_merge(rows, rows, 0, 23, address, design_4)
        rows += 1
        title = "Provident Fund Statement For The Month " + str(self.select_month) + "-" + str(self.select_year.name)
        worksheet1.write_merge(rows, rows, 0, 23, title,
                               design_7)
        rows += 1

        worksheet1.write_merge(rows, rows + 2, 0, 0, 'Sl No', design_1)
        worksheet1.write_merge(rows, rows + 2, 1, 1, 'Employee No', design_1)
        worksheet1.write_merge(rows, rows + 2, 2, 2, 'Name', design_1)
        worksheet1.write_merge(rows, rows + 2, 3, 3, 'Date of Joining', design_1)
        worksheet1.write_merge(rows, rows + 2, 4, 4, 'Date of Leaving', design_1)
        worksheet1.write_merge(rows, rows + 2, 5, 5, 'PF No', design_1)
        worksheet1.write_merge(rows, rows + 2, 6, 6, 'UAN No', design_1)
        worksheet1.write_merge(rows, rows + 2, 7, 7, 'Gross Wages', design_1)
        worksheet1.write_merge(rows, rows, 8, 12, 'Employees Contribution', design_1)
        worksheet1.write_merge(rows, rows, 13, 17, 'Employer Contribution', design_1)
        worksheet1.write_merge(rows, rows + 2, 18, 18, 'PF Basic', design_1)
        worksheet1.write_merge(rows, rows + 2, 19, 19, 'EPS Basic', design_1)
        worksheet1.write_merge(rows, rows + 2, 20, 20, 'EDLI Basic', design_1)
        worksheet1.write_merge(rows, rows + 2, 21, 21, 'PF Admin Acc 2', design_1)
        worksheet1.write_merge(rows, rows + 2, 22, 22, 'EDLI Contribution 21', design_1)
        worksheet1.write_merge(rows, rows + 2, 23, 23, 'EDLI Admin Charges 22', design_1)

        rows += 1
        worksheet1.write_merge(rows, rows, 8, 9, 'Basic + DA', design_1)
        worksheet1.write_merge(rows, rows, 10, 11, 'PF', design_1)
        worksheet1.write(rows, 12, 'VPF', design_1)
        worksheet1.write_merge(rows, rows, 13, 14, 'PF', design_1)
        worksheet1.write_merge(rows, rows, 15, 16, 'EPS', design_1)
        worksheet1.write_merge(rows, rows + 1, 17, 17, 'Total', design_1)

        rows += 1
        worksheet1.write(rows, 8, 'Regular', design_1)
        worksheet1.write(rows, 9, 'Arrear', design_1)
        worksheet1.write(rows, 10, 'Regular', design_1)
        worksheet1.write(rows, 11, 'Arrear', design_1)
        worksheet1.write(rows, 12, '', design_1)
        worksheet1.write(rows, 13, 'Regular', design_1)
        worksheet1.write(rows, 14, 'Arrear', design_1)
        worksheet1.write(rows, 15, 'Regular', design_1)
        worksheet1.write(rows, 16, 'Arrear', design_1)
        rows += 1
        worksheet1.write_merge(rows, rows, 0, 7, f'For Location {self.company_id.city}', design_5)

        rows += 1
        data = [{
            'employee_id': i.employee_id.name,
            'emp_code': i.employee_id.emp_code,
            'date_of_joining': i.employee_id.date_of_joining,
            'date_of_leaving': '-',
            'pf_no': i.employee_id.provident_fund_number,
            'uan_no': i.employee_id.uan_number,
            'gross_wages': i.gross_salary,
            'basic_da': i.contract_id.wage,
            'basic_da_arrear': 0.00,
            'employee_pf_regular': i.employee_pf_amount,
            'employee_pf_arrear': 0.00,
            'employee_vpf': 0.00,
            'employer_pf_regular': i.pf_second_regular_amt,
            'employer_pf_arrear': 0.00,
            'employer_pension_regular': i.pf_second_regular_pension_amt,
            'employer_pension_arrear': 0.00,
            'employer_pf_total': i.employer_pf_amount,
            'pf_admin': i.pf_admin_amt,
            'edli_admin_charges_22': 0.00,

        } for i in self.env['hr.payslip'].search([
            ('date_from', '>=', self.start_date),
            ('date_to', '<=', self.end_date)
        ])]
        gross_wages_total = 0.00
        basic_da_total = 0.00
        basic_da_arrear_total = 0.00
        employee_pf_regular_total = 0.00
        employee_pf_arrear_total = 0.00
        employee_vpf_total = 0.00
        employer_pf_regular_total = 0.00
        employer_pf_arrear_total = 0.00
        employer_pension_regular_total = 0.00
        employer_pension_arrear_total = 0.00
        employer_pf_total_total = 0.00
        pf_admin_total = 0.00
        edli_admin_charges_22_total = 0.0
        overall_basic_da = 0.00
        for j in data:
            worksheet1.write(rows, 0, serial_no, design_8)
            worksheet1.write(rows, 1, j['emp_code'] if j['emp_code'] else '-', design_9)
            worksheet1.write(rows, 2, j['employee_id'] if j['employee_id'] else '-', design_9)
            worksheet1.write(rows, 3, j['date_of_joining'].strftime('%d-%m-%Y') if j['date_of_joining'] else '-',
                             design_8)
            worksheet1.write(rows, 4, j['date_of_leaving'] if j['date_of_leaving'] else '-',
                             design_8)
            worksheet1.write(rows, 5, j['pf_no'] if j['pf_no'] else '-', design_9)
            worksheet1.write(rows, 6, j['uan_no'] if j['uan_no'] else '-', design_9)
            worksheet1.write(rows, 7, str('%.2f' % j['gross_wages']) if j['gross_wages'] else '-', design_10)
            worksheet1.write(rows, 8, str('%.2f' % j['basic_da']) if j['basic_da'] else '-', design_10)
            worksheet1.write(rows, 9, j['basic_da_arrear'] if j['basic_da_arrear'] else '-', design_10)
            worksheet1.write(rows, 10, str('%.2f' % j['employee_pf_regular']) if j['employee_pf_regular'] else '-',
                             design_10)
            worksheet1.write(rows, 11, j['employee_pf_arrear'] if j['employee_pf_arrear'] else '-', design_10)
            worksheet1.write(rows, 12, j['employee_vpf'] if j['employee_vpf'] else '-', design_10)
            worksheet1.write(rows, 13, str('%.2f' % j['employer_pf_regular']) if j['employer_pf_regular'] else '-',
                             design_10)
            worksheet1.write(rows, 14, j['employer_pf_arrear'] if j['employer_pf_arrear'] else '-', design_10)
            worksheet1.write(rows, 15,
                             str('%.2f' % j['employer_pension_regular']) if j['employer_pension_regular'] else '-',
                             design_10)
            worksheet1.write(rows, 16, j['employer_pension_arrear'] if j['employer_pension_arrear'] else '-', design_10)
            worksheet1.write(rows, 17, str('%.2f' % j['employer_pf_total']) if j['employer_pf_total'] else '-',
                             design_10)
            worksheet1.write(rows, 18, str('%.2f' % j['basic_da']) if j['basic_da'] else '-', design_10)
            worksheet1.write(rows, 19, str('%.2f' % j['basic_da']) if j['basic_da'] else '-', design_10)
            worksheet1.write(rows, 20, str('%.2f' % j['basic_da']) if j['basic_da'] else '-', design_10)
            worksheet1.write(rows, 21, str('%.2f' % j['pf_admin']) if j['pf_admin'] else '-', design_10)
            worksheet1.write(rows, 22, str('%.2f' % j['pf_admin']) if j['pf_admin'] else '-', design_10)
            worksheet1.write(rows, 23, j['edli_admin_charges_22'] if j['edli_admin_charges_22'] else '-', design_10)
            gross_wages_total += j['gross_wages']
            basic_da_total += j['basic_da']
            basic_da_arrear_total += j['basic_da_arrear']
            employee_pf_regular_total += j['employee_pf_regular']
            employee_pf_arrear_total += j['employee_pf_arrear']
            employee_vpf_total += j['employee_vpf']
            employer_pf_regular_total += j['employer_pf_regular']
            employer_pf_arrear_total += j['employer_pf_arrear']
            employer_pension_regular_total += j['employer_pension_regular']
            employer_pension_arrear_total += j['employer_pension_arrear']
            employer_pf_total_total += j['employer_pf_total']
            pf_admin_total += j['pf_admin']
            edli_admin_charges_22_total += j['edli_admin_charges_22']
            overall_basic_da += j['basic_da']
            rows += 1
            serial_no += 1
        rows += 2
        worksheet1.write(rows, 6, 'Total', design_11)
        worksheet1.write(rows, 7, str('%.2f' % gross_wages_total), design_12)
        worksheet1.write(rows, 8, str('%.2f' % basic_da_total), design_12)
        worksheet1.write(rows, 9, str('%.2f' % basic_da_arrear_total), design_12)
        worksheet1.write(rows, 10, str('%.2f' % employee_pf_regular_total), design_12)
        worksheet1.write(rows, 11, str('%.2f' % employee_pf_arrear_total), design_12)
        worksheet1.write(rows, 12, str('%.2f' % employee_vpf_total), design_12)
        worksheet1.write(rows, 13, str('%.2f' % employer_pf_regular_total), design_12)
        worksheet1.write(rows, 14, str('%.2f' % employer_pf_arrear_total), design_12)
        worksheet1.write(rows, 15, str('%.2f' % employer_pension_regular_total), design_12)
        worksheet1.write(rows, 16, str('%.2f' % employer_pension_arrear_total), design_12)
        worksheet1.write(rows, 17, str('%.2f' % employer_pf_total_total), design_12)
        worksheet1.write(rows, 18, str('%.2f' % overall_basic_da), design_12)
        worksheet1.write(rows, 19, str('%.2f' % overall_basic_da), design_12)
        worksheet1.write(rows, 20, str('%.2f' % overall_basic_da), design_12)
        worksheet1.write(rows, 21, str('%.2f' % pf_admin_total), design_12)
        worksheet1.write(rows, 22, str('%.2f' % pf_admin_total), design_12)
        worksheet1.write(rows, 23, str('%.2f' % edli_admin_charges_22_total), design_12)

        rows += 1
        fp = BytesIO()
        o = workbook.save(fp)
        fp.read()
        excel_file = base64.b64encode(fp.getvalue())
        self.write({'summary_file': excel_file, 'file_name': f'Provident Fund Statement Report.xls',
                    'report_printed': True})
        fp.close()
        return {
            'view_mode': 'form',
            'name': 'Provident Fund Statement',
            'res_id': self.id,
            'res_model': 'provident.fund',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'target': 'new',
        }
