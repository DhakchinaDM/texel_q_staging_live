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


class EsiReport(models.TransientModel):
    _name = 'esi.report'
    _description = 'Esi Report'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    summary_file = fields.Binary('Esi Report')
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

    def print_esi_report(self):
        workbook = xlwt.Workbook()
        worksheet1 = workbook.add_sheet('ESI Report')
        design_15 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 320; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_16 = easyxf(
            'align: horiz center, vert center; font: height 200; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_17 = easyxf(
            'align: horiz left, vert center; font: bold 1, height 230; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_18 = easyxf(
            'align: horiz center, vert center; font:  bold 1, height 200; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_19 = easyxf(
            'align: horiz right, vert center; font:  bold 1, height 200;')
        design_20 = easyxf(
            'align: horiz left, vert center; font: height 200; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_21 = easyxf(
            'align: horiz right, vert center; font: height 200; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')

        worksheet1.col(0).width = 1600
        worksheet1.col(1).width = 4000
        worksheet1.col(2).width = 5000
        worksheet1.col(3).width = 6000
        worksheet1.col(4).width = 4000
        worksheet1.col(5).width = 3500
        worksheet1.col(6).width = 6000
        worksheet1.col(7).width = 6000
        worksheet1.col(8).width = 3000
        worksheet1.row(0).height_mismatch = True
        worksheet1.row(0).height = 800
        worksheet1.row(2).height = 450
        worksheet1.row(3).height = 450
        rows = 0
        cols = 0
        serial_no = 1
        #
        # TO SET THE 1ST 4 ROW FREEZE
        worksheet1.set_panes_frozen(True)
        worksheet1.set_horz_split_pos(rows + 4)
        # COMPANY LOGO
        if self.company_id.logo:
            pil_image = base64_to_image(self.company_id.logo)
            pil_image = pil_image.resize((140, 15))
            im = pil_image
            image_parts = im.split()
            r = image_parts[0]
            g = image_parts[1]
            b = image_parts[2]
            img = Image.merge("RGB", (r, g, b))
            fo = io.BytesIO()
            img.save(fo, format='bmp')
            #
            worksheet1.insert_bitmap_data(fo.getvalue(), rows, 0)
        cell_style_logo = easyxf(
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;'
        )
        worksheet1.write_merge(rows, rows, 0, 1, '', cell_style_logo)
        worksheet1.write_merge(rows, rows, 2, 8, str(self.company_id.name), design_15)
        rows += 1
        address = str(self.company_id.street) + str(self.company_id.street2) + str(self.company_id.state_id.name) + str(
            self.company_id.zip)
        worksheet1.write_merge(rows, rows, 0, 8, address, design_16)
        rows += 1
        title = "ESI Report for " + str(self.select_month) + "-" + str(self.select_year.name)
        worksheet1.write_merge(rows, rows, 0, 8, title, design_15)
        cols_head = ['SI No', 'Employee No', 'Insurance No', 'Name Of  Insured Person', 'Days Worked', 'ESI Gross',
                     "Employee's Contribution", "Employer's Contribution", 'Total']
        rows += 1
        for i in cols_head:
            worksheet1.write(rows, cols, _(i), design_18)
            cols += 1
        rows += 1
        location = "LOCATION : " + str(self.company_id.city)
        worksheet1.write_merge(rows, rows, 0, 8, location, design_17)
        rows += 1

        emp_contribution = 0.00
        employer_contribution = 0.00
        subtotal = 0.00
        gross = 0.00
        data = [{
            'employee_id': i.employee_id.name,
            'emp_code': i.employee_id.emp_code,
            'insurance_no': i.employee_id.esi_number,
            'worked_days': i.employee_final_present_days,
            'esi_gross': i.gross_salary,
            'esi_employee': i.esi,
            'esi_employer': i.esi_second,
            'total': float(i.esi) + float(i.esi_second),
        } for i in self.env['hr.payslip'].search([
            ('date_from', '>=', self.start_date),
            ('date_to', '<=', self.end_date)
        ])]
        for j in data:
            worksheet1.write(rows, 0, serial_no, design_16)
            worksheet1.write(rows, 1, j['emp_code'] if j['emp_code'] else '-', design_20)
            worksheet1.write(rows, 2, j['insurance_no'] if j['insurance_no'] else '-', design_16)
            worksheet1.write(rows, 3, j['employee_id'] if j['employee_id'] else '-', design_20)
            worksheet1.write(rows, 4, j['worked_days'] if j['worked_days'] else '-', design_21)
            worksheet1.write(rows, 5, j['esi_gross'] if j['esi_gross'] else '-', design_21)
            worksheet1.write(rows, 6, j['esi_employee'] if j['esi_employee'] else '-', design_21)
            worksheet1.write(rows, 7, j['esi_employer'] if j['esi_employer'] else '-', design_21)
            worksheet1.write(rows, 8, j['total'] if j['total'] else '-', design_21)
            emp_contribution += j['esi_employee']
            employer_contribution += j['esi_employer']
            subtotal += j['total']
            gross += j['esi_gross']
            rows += 1
            serial_no += 1
        rows += 1
        worksheet1.write(rows, 3, 'Total', design_19)
        worksheet1.write(rows, 5, gross, design_19)
        worksheet1.write(rows, 6, emp_contribution, design_19)
        worksheet1.write(rows, 7, employer_contribution, design_19)
        worksheet1.write(rows, 8, subtotal, design_19)
        rows += 1
        worksheet1.write(rows, 3, 'Grand Total', design_19)
        worksheet1.write(rows, 5, gross, design_19)
        worksheet1.write(rows, 6, emp_contribution, design_19)
        worksheet1.write(rows, 7, employer_contribution, design_19)
        worksheet1.write(rows, 8, subtotal, design_19)
        rows += 1
        worksheet1.write(rows, 3, 'As per the ESI Portal', design_19)
        worksheet1.write(rows, 5, gross, design_19)
        worksheet1.write(rows, 6, emp_contribution, design_19)
        worksheet1.write(rows, 7, employer_contribution, design_19)
        worksheet1.write(rows, 8, subtotal, design_19)

        fp = BytesIO()
        o = workbook.save(fp)
        fp.read()
        excel_file = base64.b64encode(fp.getvalue())
        self.write({
            'summary_file': excel_file,
            'file_name': f'Employee ESI Report of {self.select_month}-{self.select_year.name}.xls',
            'report_printed': True
        })

        fp.close()
        return {
            'view_mode': 'form',
            'name': 'ESI Report',
            'res_id': self.id,
            'res_model': 'esi.report',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'target': 'new',
        }
