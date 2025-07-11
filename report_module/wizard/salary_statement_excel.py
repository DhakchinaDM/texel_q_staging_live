from odoo import models, fields, api, _
from datetime import date, datetime
import xlwt
from io import BytesIO
from xlwt import easyxf
import base64


class SalaryStatementExcel(models.TransientModel):
    _name = 'salary.statement.excel'
    _description = 'Salary Statement Excel'

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    summary_file = fields.Binary('Purchase Report')
    file_name = fields.Char('File Name')
    report_printed = fields.Boolean('Report')
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
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

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

    def tick_ok(self):
        payslips = self.env['hr.payslip'].search(
            [('date_from', '>=', self.start_date), ('date_to', '<=', self.end_date)], order='emp_code asc', )
        data = []
        for payslip in payslips:
            ls = {
                'emp_id': payslip.employee_id.emp_code,
                'emp_name': payslip.employee_id.name,
                'dept': payslip.employee_id.department_id.name,
                'designation': payslip.employee_id.job_id.name,
                'bank_acc': payslip.employee_id.bank_account_id.acc_number,
                'ifsc': payslip.employee_id.bank_account_id.bank_id.name,
                'join': payslip.employee_id.date_of_joining,
                'leaving': '',
                'uan': payslip.employee_id.uan_number,
                'esi': payslip.employee_id.esi_number,
                'pan': payslip.employee_id.pan_number,
                'days_in_mo': payslip.total_days_of_month,
                'lop_days': payslip.employee_loptotal_days,
                'lop_amount': payslip.allowance_amount_deduction,
                'employee_final_present_days': payslip.employee_final_present_days,
                'ot_hours': payslip.overtime_hours,
                'salary_master': payslip.employee_id.contract_id.ctc,
                'basic': payslip.basic_salary,
                'hra': payslip.hra,
                'conveyance': payslip.conveyance,
                'medical': payslip.medical,
                'other_allowance': payslip.other_allowance,
                'ot_amount': payslip.overtime,
                'att_bonus': payslip.attendance_bonus,
                'food_allow': payslip.food_allowance,
                'incentive': payslip.incentive,
                'night_shift_allowance_amount': payslip.night_shift_allowance_amount,
                'production_incentive': payslip.production_incentive,
                'leave_encashment': payslip.leave_encashment,
                'gross': payslip.gross_salary,
                'employee_pf_amount': payslip.employee_pf_amount,
                'esi_amount': payslip.esi,
                'actual_professional_tax': payslip.actual_professional_tax,
                'income_tax': payslip.income_tax,
                'tds': payslip.tds,
                'other_loan': payslip.other_loan,
                'food_deduction': payslip.food_deduction,
                'other_deduction': payslip.other_deduction,
                'room_rent_deduction': payslip.room_rent_deduction,
                'shoe_and_uniform_deduction': payslip.shoe_and_uniform_deduction,
                'amount_deduction_only': payslip.amount_deduction_only,
                'total_amount': payslip.total_amount,
                'remarks': payslip.remarks,
            }
            data.append(ls)
        address = f"{self.company_id.street or ''} {self.company_id.street2 or ''} {self.company_id.city or ''} {self.company_id.state_id.name or ''}-{self.company_id.zip or ''}"
        workbook = xlwt.Workbook()
        worksheet1 = workbook.add_sheet('Salary Statement Report')
        design_1 = easyxf('align: horiz center;')
        design_2 = easyxf('align: horiz left;')
        design_9 = easyxf('align: horiz right;')
        design_5 = easyxf('align: horiz center;font: bold 1;pattern: pattern solid, fore_colour gray25;')
        design_6 = easyxf('align: horiz center;font: bold 1;')
        design_7 = easyxf('align: horiz right;font: bold 1;')
        column_widths = [1800, 4500, 7000, 5000, 5000, 5000, 5000, 4000, 4000, 4500, 4500, 4500, 4000, 3000, 3500, 6000,
                         3000, 4000, 3500, 3500, 3500, 4500, 4000, 3500, 4500, 4000, 3500, 5000, 5000, 4500, 4500, 4500,
                         4500,
                         4500, 4500, 4500, 4500, 4500, 4500, 5500, 6500, 4500, 4500, ]
        for i, width in enumerate(column_widths):
            worksheet1.col(i).width = width
        rows = 0
        serial_no = 1
        cols = 0
        worksheet1.set_panes_frozen(True)
        worksheet1.set_horz_split_pos(rows + 7)
        worksheet1.set_vert_split_pos(cols + 3)

        rows += 1
        worksheet1.write_merge(rows, rows, 0, 13, self.company_id.name, design_5)
        rows += 1
        worksheet1.write_merge(rows, rows, 0, 13, address, design_5)
        rows += 2
        title = "Salary Statement for the Month " + str(self.select_month) + "-" + str(self.select_year.name)
        worksheet1.write_merge(rows, rows, 0, 13, title, design_5)
        rows += 2
        cols_head = ['Sl No', 'Employee No', 'Name', 'Department', 'Designation', 'Bank Acc No', 'IFSC Code',
                     'Join Date', 'Leaving Date', 'UAN', 'ESI Number', 'Pan No', 'Days in Month', 'LOP', 'LOP Amount',
                     'Emp Effective Workdays', 'OT Hours', 'Salary Master', 'Basic', 'HRA', 'Conveyance',
                     'Medical Allowance', 'Other Allowance', 'Overtime', 'Attendance Bonus', 'Food Allowance',
                     'Incentive', 'Night Shift Allowance', 'Production Incentive', 'Leave Encashment', 'Gross', 'PF',
                     'ESI', 'Professional Tax', 'Income Tax', 'TDS', 'Other Loan', 'Food Deduction', 'Other Deduction',
                     'Room Rent Deduction', 'Shoe & Uniform Deduction', 'Total Deductions', 'Net Pay']
        for j in cols_head:
            worksheet1.write(rows, cols, j, design_5)
            cols += 1
        rows += 1
        days_in_month = 0.00
        lop_total = 0.00
        lop_amot_total = 0.00
        ewd_total = 0.00
        ot_total = 0.00
        salary_master_total = 0.00
        basic_total = 0.00
        hra_total = 0.00
        conveyance_total = 0.00
        medical_total = 0.00
        other_allowance_total = 0.00
        ot_amount_total = 0.00
        att_bonus_total = 0.00
        food_allow_total = 0.00
        incentive_total = 0.00
        night_shift_allowance_total = 0.00
        production_incentive_total = 0.00
        leave_encashment_total = 0.00
        gross_total = 0.00
        employee_pf_amount_total = 0.00
        esi_amount_total = 0.00
        actual_professional_tax_total = 0.00
        income_tax_total = 0.00
        tds_total = 0.00
        other_loan_total = 0.00
        food_deduction_total = 0.00
        other_deduction_total = 0.00
        room_rent_deduction_total = 0.00
        shoe_and_uniform_deduction_total = 0.00
        amount_deduction_only_total = 0.00
        total_amount_total = 0.00
        for datas in data:
            worksheet1.write(rows, 0, serial_no, design_2)
            worksheet1.write(rows, 1, datas.get('emp_id', '-'), design_2)
            worksheet1.write(rows, 2, datas.get('emp_name', '-'), design_2)
            worksheet1.write(rows, 3, datas.get('dept', '-'), design_2)
            worksheet1.write(rows, 4, datas.get('designation', '-'), design_2)
            if datas.get('bank_acc'):
                worksheet1.write(rows, 5, datas.get('bank_acc', ), design_2)
            else:
                worksheet1.write(rows, 5, '-', design_1)
            if datas.get('ifsc'):
                worksheet1.write(rows, 6, datas.get('ifsc', ), design_2)
            else:
                worksheet1.write(rows, 6, '-', design_1)

            worksheet1.write(rows, 7, datas.get('join', '-').strftime('%d-%m-%Y') if datas.get('join') else '-',
                             design_2)
            worksheet1.write(rows, 8, datas.get('leaving', '-'), design_2)
            if datas.get('uan'):
                worksheet1.write(rows, 9, datas.get('uan', ), design_2)
            else:
                worksheet1.write(rows, 9, '-', design_1)

            if datas.get('esi'):
                worksheet1.write(rows, 10, datas.get('esi', ), design_2)
            else:
                worksheet1.write(rows, 10, '-', design_1)
            if datas.get('pan'):
                worksheet1.write(rows, 11, datas.get('pan', ), design_2)
            else:
                worksheet1.write(rows, 11, '-', design_1)
            worksheet1.write(rows, 12, datas.get('days_in_mo', '-'), design_9)
            worksheet1.write(rows, 13, datas.get('lop_days', '-'), design_9)
            worksheet1.write(rows, 14, datas.get('lop_amount', '-'), design_9)
            worksheet1.write(rows, 15, datas.get('employee_final_present_days', '-'), design_9)
            worksheet1.write(rows, 16, str('%.2f' % datas.get('ot_hours', '-')), design_9)
            worksheet1.write(rows, 17, str('%.2f' % datas.get('salary_master', '-')), design_9)
            worksheet1.write(rows, 18, str('%.2f' % datas.get('basic', '-')), design_9)
            worksheet1.write(rows, 19, str('%.2f' % datas.get('hra', '-')), design_9)
            worksheet1.write(rows, 20, str('%.2f' % datas.get('conveyance', '-')), design_9)
            worksheet1.write(rows, 21, str('%.2f' % datas.get('medical', '-')), design_9)
            worksheet1.write(rows, 22, str('%.2f' % datas.get('other_allowance', '-')), design_9)
            worksheet1.write(rows, 23, str('%.2f' % datas.get('ot_amount', '-')), design_9)
            worksheet1.write(rows, 24, str('%.2f' % datas.get('att_bonus', '-')), design_9)
            worksheet1.write(rows, 25, str('%.2f' % datas.get('food_allow', '-')), design_9)
            worksheet1.write(rows, 26, str('%.2f' % datas.get('incentive', '-')), design_9)
            worksheet1.write(rows, 27, str('%.2f' % datas.get('night_shift_allowance_amount', '-')), design_9)
            worksheet1.write(rows, 28, str('%.2f' % datas.get('production_incentive', '-')), design_9)
            worksheet1.write(rows, 29, str('%.2f' % datas.get('leave_encashment', '-')), design_9)
            worksheet1.write(rows, 30, str('%.2f' % datas.get('gross', '-')), design_9)
            worksheet1.write(rows, 31, str('%.2f' % datas.get('employee_pf_amount', '-')), design_9)
            worksheet1.write(rows, 32, str('%.2f' % datas.get('esi_amount', '-')), design_9)
            worksheet1.write(rows, 33, str('%.2f' % datas.get('actual_professional_tax', '-')), design_9)
            worksheet1.write(rows, 34, str('%.2f' % datas.get('income_tax', '-')), design_9)
            worksheet1.write(rows, 35, str('%.2f' % datas.get('tds', '-')), design_9)
            worksheet1.write(rows, 36, str('%.2f' % datas.get('other_loan', '-')), design_9)
            worksheet1.write(rows, 37, str('%.2f' % datas.get('food_deduction', '-')), design_9)
            worksheet1.write(rows, 38, str('%.2f' % datas.get('other_deduction', '-')), design_9)
            worksheet1.write(rows, 39, str('%.2f' % datas.get('room_rent_deduction', '-')), design_9)
            worksheet1.write(rows, 40, str('%.2f' % datas.get('shoe_and_uniform_deduction', '-')), design_9)
            worksheet1.write(rows, 41, str('%.2f' % datas.get('amount_deduction_only', '-')), design_9)
            worksheet1.write(rows, 42, str('%.2f' % datas.get('total_amount', '-')), design_9)
            days_in_month += datas.get('days_in_mo', 0)
            lop_total += datas.get('lop_days', 0)
            lop_amot_total += datas.get('lop_amount', 0)
            ewd_total += datas.get('employee_final_present_days', 0)
            ot_total += datas.get('ot_hours', 0)
            salary_master_total += datas.get('salary_master', 0)
            basic_total += datas.get('basic', 0)
            hra_total += datas.get('hra', 0)
            conveyance_total += datas.get('conveyance', 0)
            medical_total += datas.get('medical', 0)
            other_allowance_total += datas.get('other_allowance', 0)
            ot_amount_total += datas.get('ot_amount', 0)
            att_bonus_total += datas.get('att_bonus', 0)
            food_allow_total += datas.get('food_allow', 0)
            incentive_total += datas.get('incentive', 0)
            night_shift_allowance_total += datas.get('night_shift_allowance_amount', 0)
            production_incentive_total += datas.get('production_incentive', 0)
            leave_encashment_total += datas.get('leave_encashment', 0)
            gross_total += datas.get('gross', 0)
            employee_pf_amount_total += datas.get('employee_pf_amount', 0)
            esi_amount_total += datas.get('esi_amount', 0)
            actual_professional_tax_total += datas.get('actual_professional_tax', 0)
            income_tax_total += datas.get('income_tax', 0)
            tds_total += datas.get('tds', 0)
            other_loan_total += datas.get('other_loan', 0)
            food_deduction_total += datas.get('food_deduction', 0)
            other_deduction_total += datas.get('other_deduction', 0)
            room_rent_deduction_total += datas.get('room_rent_deduction', 0)
            shoe_and_uniform_deduction_total += datas.get('shoe_and_uniform_deduction', 0)
            amount_deduction_only_total += datas.get('amount_deduction_only', 0)
            total_amount_total += datas.get('total_amount', 0)
            rows += 1
            serial_no += 1
        rows += 2
        worksheet1.write(rows, 10, 'Grand Total', design_6)
        worksheet1.write(rows, 12, days_in_month, design_7)
        worksheet1.write(rows, 13, lop_total, design_7)
        worksheet1.write(rows, 14, lop_amot_total, design_7)
        worksheet1.write(rows, 15, ewd_total, design_7)
        worksheet1.write(rows, 16, str('%.2f' % ot_total), design_7)
        worksheet1.write(rows, 17, str('%.2f' % salary_master_total), design_7)
        worksheet1.write(rows, 18, str('%.2f' % basic_total), design_7)
        worksheet1.write(rows, 19, str('%.2f' % hra_total), design_7)
        worksheet1.write(rows, 20, str('%.2f' % conveyance_total), design_7)
        worksheet1.write(rows, 21, str('%.2f' % medical_total), design_7)
        worksheet1.write(rows, 22, str('%.2f' % other_allowance_total), design_7)
        worksheet1.write(rows, 23, str('%.2f' % ot_amount_total), design_7)
        worksheet1.write(rows, 24, str('%.2f' % att_bonus_total), design_7)
        worksheet1.write(rows, 25, str('%.2f' % food_allow_total), design_7)
        worksheet1.write(rows, 26, str('%.2f' % incentive_total), design_7)
        worksheet1.write(rows, 27, str('%.2f' % night_shift_allowance_total), design_7)
        worksheet1.write(rows, 28, str('%.2f' % production_incentive_total), design_7)
        worksheet1.write(rows, 29, str('%.2f' % leave_encashment_total), design_7)
        worksheet1.write(rows, 30, str('%.2f' % gross_total), design_7)
        worksheet1.write(rows, 31, str('%.2f' % employee_pf_amount_total), design_7)
        worksheet1.write(rows, 32, str('%.2f' % esi_amount_total), design_7)
        worksheet1.write(rows, 33, str('%.2f' % actual_professional_tax_total), design_7)
        worksheet1.write(rows, 34, str('%.2f' % income_tax_total), design_7)
        worksheet1.write(rows, 35, str('%.2f' % tds_total), design_7)
        worksheet1.write(rows, 36, str('%.2f' % other_loan_total), design_7)
        worksheet1.write(rows, 37, str('%.2f' % food_deduction_total), design_7)
        worksheet1.write(rows, 38, str('%.2f' % other_deduction_total), design_7)
        worksheet1.write(rows, 39, str('%.2f' % room_rent_deduction_total), design_7)
        worksheet1.write(rows, 40, str('%.2f' % shoe_and_uniform_deduction_total), design_7)
        worksheet1.write(rows, 41, str('%.2f' % amount_deduction_only_total), design_7)
        worksheet1.write(rows, 42, str('%.2f' % total_amount_total), design_7)

        fp = BytesIO()
        workbook.save(fp)
        fp.seek(0)
        excel_file = base64.b64encode(fp.read())
        fp.close()

        self.write({
            'summary_file': excel_file,
            'file_name': 'Salary Statement Report  - [ %s ].xls' % self.start_date.strftime('%d/%m/%Y'),
            'report_printed': True
        })

        return {
            'view_mode': 'form',
            'name': 'Salary Statement Report',
            'res_id': self.id,
            'res_model': 'salary.statement.excel',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'target': 'new',
        }

    # def tick_ok(self):
    #     payslips = self.env['hr.payslip'].search(
    #         [('date_from', '>=', self.start_date), ('date_to', '<=', self.end_date)], order='emp_code asc',)
    #     salary_rule = self.env['hr.salary.rule'].search([])
    #     var = [rule.name for rule in salary_rule]
    #     var = list(dict.fromkeys(var))
    #     data = []
    #     columns_with_values = set()
    #     for payslip in payslips:
    #         line_data = {line.name: line.total for line in payslip.line_ids}
    #         for name in var:
    #             if name in line_data:
    #                 columns_with_values.add(name)
    #         ls = {
    #             'emp_id': payslip.employee_id.emp_code,
    #             'emp_name': payslip.employee_id.name,
    #             'dept': payslip.employee_id.department_id.name,
    #             'designation': payslip.employee_id.job_id.name,
    #             'bank_acc': payslip.employee_id.bank_account_id.acc_number,
    #             'ifsc': payslip.employee_id.bank_account_id.bank_id.name,
    #             'join': payslip.employee_id.date_of_joining,
    #             'leaving': '',
    #             'uan': payslip.employee_id.uan_number,
    #             'esi': payslip.employee_id.esi_number,
    #             'pan': payslip.employee_id.pan_number,
    #             'days_in_mo': payslip.total_days_of_month,
    #             'lop_days': payslip.employee_loptotal_days,
    #             'employee_final_present_days': payslip.employee_final_present_days,
    #             'ot_hours': payslip.overtime_hours,
    #             'salary_master': payslip.employee_id.contract_id.ctc,
    #             'remarks': payslip.remarks,
    #             'line_data': line_data
    #         }
    #         data.append(ls)
    #     address = f"{self.company_id.street or ''} {self.company_id.street2 or ''} {self.company_id.city or ''} {self.company_id.state_id.name or ''}-{self.company_id.zip or ''}"
    #     workbook = xlwt.Workbook()
    #     worksheet1 = workbook.add_sheet('Salary Statement Report')
    #     design_1 = easyxf('align: horiz center;')
    #     design_2 = easyxf('align: horiz left;')
    #     design_9 = easyxf('align: horiz right;')
    #     design_5 = easyxf('align: horiz center;font: bold 1;pattern: pattern solid, fore_colour gray25;')
    #     design_6 = easyxf('align: horiz center;font: bold 1;')
    #     design_7 = easyxf('align: horiz right;font: bold 1;')
    #     column_widths = [1800, 4500, 7000, 5000, 5000, 5000, 5000, 4000, 4000, 4500, 4500, 4500, 4000, 3000, 3000, 3000,
    #                      3000]
    #     for i, width in enumerate(column_widths):
    #         worksheet1.col(i).width = width
    #     for i in range(len(column_widths), len(column_widths) + len(columns_with_values)):
    #         worksheet1.col(i).width = 6000
    #     rows = 0
    #     serial_no = 1
    #     cols = 0
    #     worksheet1.set_panes_frozen(True)
    #     worksheet1.set_horz_split_pos(rows + 5)
    #     rows += 1
    #     worksheet1.write_merge(rows, rows, 0, 13, self.company_id.name, design_5)
    #     rows += 1
    #     worksheet1.write_merge(rows, rows, 0, 13, address, design_5)
    #     rows += 2
    #     title = "Salary Statement for the Month " + str(self.select_month) + "-" + str(self.select_year.name)
    #     worksheet1.write_merge(rows, rows, 0, 13, title, design_5)
    #     rows += 2
    #     cols_head = ['Sl No', 'Employee No', 'Name', 'Department', 'Designation', 'Bank Acc No', 'IFSC Code',
    #                  'Join Date', 'Leaving Date', 'UAN', 'ESI Number', 'Pan No', 'Days in Month', 'LOP Days',
    #                  'Emp Effective Workdays', 'OT Hours', 'Salary Master']
    #     cols_head.extend([name for name in var if name in columns_with_values])
    #     cols_head.append('Remarks')
    #     for j in cols_head:
    #         worksheet1.write(rows, cols, j, design_5)
    #         cols += 1
    #     rows += 1
    #     days_in_month = 0.00
    #     lop_total = 0.00
    #     ewd_total = 0.00
    #     ot_total = 0.00
    #     salary_master_total = 0.00
    #     line_data_totals = {name: 0.00 for name in columns_with_values}
    #     for datas in data:
    #         worksheet1.write(rows, 0, serial_no, design_2)
    #         worksheet1.write(rows, 1, datas.get('emp_id', '-'), design_2)
    #         worksheet1.write(rows, 2, datas.get('emp_name', '-'), design_2)
    #         worksheet1.write(rows, 3, datas.get('dept', '-'), design_2)
    #         worksheet1.write(rows, 4, datas.get('designation', '-'), design_2)
    #         worksheet1.write(rows, 5, datas.get('bank_acc', '-'), design_2)
    #         worksheet1.write(rows, 6, datas.get('ifsc', '-'), design_2)
    #         worksheet1.write(rows, 7, datas.get('join', '-').strftime('%d-%m-%Y') if datas.get('join') else '-',
    #                          design_2)
    #         worksheet1.write(rows, 8, datas.get('leaving', '-'), design_2)
    #         worksheet1.write(rows, 9, datas.get('uan', '-'), design_2)
    #         worksheet1.write(rows, 10, datas.get('esi', '-'), design_2)
    #         worksheet1.write(rows, 11, datas.get('pan', '-'), design_2)
    #         worksheet1.write(rows, 12, datas.get('days_in_mo', '-'), design_9)
    #         worksheet1.write(rows, 13, datas.get('lop_days', '-'), design_9)
    #         worksheet1.write(rows, 14, datas.get('employee_final_present_days', '-'), design_9)
    #         worksheet1.write(rows, 15, str('%.2f' % datas.get('ot_hours', '-')), design_9)
    #         worksheet1.write(rows, 16, str('%.2f' % datas.get('salary_master', '-')), design_9)
    #         days_in_month += datas.get('days_in_mo', 0)
    #         lop_total += datas.get('lop_days', 0)
    #         ewd_total += datas.get('employee_final_present_days', 0)
    #         ot_total += datas.get('ot_hours', 0)
    #         salary_master_total += datas.get('salary_master', 0)
    #         col_index = 17
    #         for var_item in cols_head[17:-1]:
    #             value = datas['line_data'].get(var_item, 0)
    #             worksheet1.write(rows, col_index, str('%.2f' % value), design_9)
    #             line_data_totals[var_item] += value
    #             col_index += 1
    #         worksheet1.col(col_index).width = 30000
    #         worksheet1.write(rows, col_index, datas.get('remarks', '-'), design_2)
    #         rows += 1
    #         serial_no += 1
    #     rows += 2
    #     worksheet1.write(rows, 10, 'Grand Total', design_6)
    #     worksheet1.write(rows, 12, days_in_month, design_7)
    #     worksheet1.write(rows, 13, lop_total, design_7)
    #     worksheet1.write(rows, 14, ewd_total, design_7)
    #     worksheet1.write(rows, 15, str('%.2f' % ot_total), design_7)
    #     worksheet1.write(rows, 16, str('%.2f' % salary_master_total), design_7)
    #
    #     col_index = 17
    #     for var_item in cols_head[17:-1]:
    #         worksheet1.write(rows, col_index, str('%.2f' % line_data_totals[var_item]), design_7)
    #         col_index += 1
    #
    #     fp = BytesIO()
    #     workbook.save(fp)
    #     fp.seek(0)
    #     excel_file = base64.b64encode(fp.read())
    #     fp.close()
    #
    #     self.write({
    #         'summary_file': excel_file,
    #         'file_name': 'Salary Statement Report  - [ %s ].xls' % self.start_date.strftime('%d/%m/%Y'),
    #         'report_printed': True
    #     })
    #
    #     return {
    #         'view_mode': 'form',
    #         'name': 'Salary Statement Report',
    #         'res_id': self.id,
    #         'res_model': 'salary.statement.excel',
    #         'view_type': 'form',
    #         'type': 'ir.actions.act_window',
    #         'context': self.env.context,
    #         'target': 'new',
    #     }
