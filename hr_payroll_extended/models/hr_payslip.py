from odoo import api, fields, models, tools, _
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError
from num2words import num2words
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta, date


def half_round(number):
    decimal_number = Decimal(number)
    rounded_number = decimal_number.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return int(rounded_number)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    _description = 'Pay Slip'

    name = fields.Char(string='Payslip Name', required=True, compute='_compute_name', store=True, readonly=False)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    emp_code = fields.Integer(string='Employee Code', related='employee_id.emp_code', store=True)
    date_year = fields.Char(string="Year")
    warning_message = fields.Char(compute='_compute_warning_message', store=True, readonly=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', tracking=True, domain="[]")
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
    select_year = fields.Many2one('hr.payroll.year', string='Year ',
                                  default=lambda self: self._default_year())
    pay_date = fields.Date(string='Pay Date', default=fields.Date.today())
    date_from = fields.Date(
        string='From', required=True, tracking=True, compute='_compute_dates', store=True)
    date_to = fields.Date(
        string='To', required=True, tracking=True, compute='_compute_dates', store=True)

    # EMPLOYEE ATTENDANCE INFO
    attendance_type = fields.Selection([
        ('manual', 'Manual Attendance'),
        ('automatic', 'Automatic Attendance'),
    ], default='manual', string="Attendance Type")
    employee_manual_present_days = fields.Float(string="Employee Present Days")
    employee_present_days = fields.Float(string="Present Days")
    extra_worked_days = fields.Float(string="Extra Worked Days")
    number_of_leave = fields.Float(string="Public Leave's and Weeksoffs ")
    leave_paid_timeoff = fields.Float(string="Paid Leave")
    employee_final_present_days = fields.Float(string="Total Payable Days")
    allowance_amount_deduction = fields.Float(string="Lop Amount")
    total_days_of_month = fields.Float(string="Total Days in Month ")

    # WORKING DAYS INFO
    lop_type = fields.Selection([
        ('actual_lop', 'Actual Lop'),
        ('overall_lop', 'Overall LOP'),
    ], string="LOP Type", default="actual_lop")
    employee_loptotal_days = fields.Float(string="LOP Days")
    employee_final_lop_total_days = fields.Float(string="LOP Days ")
    employee_one_day_salary = fields.Float(string="One Day Salary")
    number_working_of_days = fields.Float(string="Working Days ")

    # EXTRAS
    total_amount = fields.Float(string='Total Payable Amount', compute='_compute_amount_total', store=True)
    amount_deduction = fields.Float(string='Total Deduction', compute='_compute_amount_total', store=True)
    amount_deduction_only = fields.Float(string='Total Deduction only', compute='_compute_amount_total', store=True)
    gross_salary = fields.Float(string='Gross Salary', compute='_compute_amount_total', store=True)
    basic_salary = fields.Float(string='Basic Salary', compute='_compute_amount_total', store=True)
    hra = fields.Float(string='HRA', compute='_compute_amount_total', store=True)
    conveyance = fields.Float(string='Conveyance', compute='_compute_amount_total', store=True)
    medical = fields.Float(string='Medical', compute='_compute_amount_total', store=True)
    amount_in_words = fields.Char(string='Amount in Words', compute='_compute_number_to_words')

    # ALLOWANCE
    other_allowance = fields.Float(string='Other Allowance')
    overtime_per_day = fields.Float(string='Overtime Per Day')
    overtime_hours = fields.Float(string='Overtime Days')
    overtime = fields.Float(string='Overtime')
    attendance_bonus = fields.Float(string='Attendance Bonus')
    food_allowance = fields.Float(string='Food Allowance')
    incentive = fields.Float(string='Incentive')
    night_shift_allowance = fields.Float(string='Night Shift Allowance')
    total_days_worked = fields.Float(string='Total Days worked')
    night_shift_allowance_amount = fields.Float(string='Total Day worked')
    production_incentive = fields.Float(string='Production Incentive')
    fixed_production_amount = fields.Float(string='Production Fixed Amount', )
    one_day_production_cost = fields.Float(string='One day Production Cost', )
    night_shift_bool = fields.Boolean(string='Night Shift Bool', compute='_compute_night_shift_bool')
    production_bool = fields.Boolean(string='Production Bool', compute='_compute_production_bool')
    leave_encashment = fields.Float(string='Leave Encashment')
    remarks = fields.Text(string='Remarks', compute='_compute_remarks')

    # LEAVES
    time_off_ids = fields.One2many('hr.leave', 'payslip_id', string='Leave Details')
    casual_leave = fields.Float(string='Casual Leave', compute='_compute_leaves')
    sick_leave = fields.Float(string='Sick Leave', compute='_compute_leaves')
    earned_leave = fields.Float(string='Earned Leave', compute='_compute_leaves')
    weekoff_lop = fields.Float(string='Continuous Leave Weekoff in (CL/SL/EL)', compute='_compute_holiday_lop')

    # REMAINING LEAVES
    cl = fields.Float(string='CL', compute='_compute_remaining_leaves')
    sl = fields.Float(string='SL', compute='_compute_remaining_leaves')
    el = fields.Float(string='EL', compute='_compute_remaining_leaves')

    def _compute_remaining_leaves(self):
        for record in self:
            cl = sl = el = 0.00
            leaves = self.env['report.balance.leave'].search([('emp_id', '=', record.employee_id.id)])
            for i in leaves:
                if i.leave_type_id.id == self.env.ref('hr_holidays.holiday_status_sl').id:
                    sl += i.balance_days
                elif i.leave_type_id.id == self.env.ref('hr_payroll_extended.holiday_status_casual_leave').id:
                    cl += i.balance_days
                elif i.leave_type_id.id == self.env.ref('hr_payroll_extended.holiday_status_earned_leave').id:
                    el += i.balance_days
            record.cl = cl
            record.sl = sl
            record.el = el

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_holiday_lop(self):
        for record in self:
            holiday_lop = 0
            leaves = self.env['hr.leave'].search([
                ('date_from', '>=', record.date_from),
                ('date_to', '<=', record.date_to),
                ('employee_id', '=', record.employee_id.id)
            ])
            leave_dates = []
            for leave in leaves:
                leave_dates.extend(self._get_dates_range(leave.date_from.date(), leave.date_to.date()))
            leave_dates = sorted(set(leave_dates))  # Get unique sorted dates
            continuous_leave_periods = self._get_continuous_periods(leave_dates)
            struct_id = record.struct_id.id
            for start, end in continuous_leave_periods:
                current_date = start
                while current_date <= end:
                    weekday = current_date.weekday()
                    if struct_id == self.env.ref('hr_payroll.structure_002').id or \
                            struct_id == self.env.ref('hr_payroll_extended.structure_staff_sat001').id:
                        if weekday == 6:  # Sunday
                            holiday_lop += 1
                    elif struct_id == self.env.ref('hr_payroll.structure_worker_001').id:
                        if weekday in (5, 6):
                            holiday_lop += 1
                    current_date += timedelta(days=1)
            record.weekoff_lop = holiday_lop

    def _get_dates_range(self, start_date, end_date):
        """Return a list of all dates between start_date and end_date inclusive."""
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date)
            current_date += timedelta(days=1)
        return date_list

    def _get_continuous_periods(self, dates):
        """Return a list of tuples representing continuous leave periods."""
        if not dates:
            return []

        continuous_periods = []
        start_date = dates[0]
        for i in range(1, len(dates)):
            if (dates[i] - dates[i - 1]).days > 1:
                continuous_periods.append((start_date, dates[i - 1]))
                start_date = dates[i]
        continuous_periods.append((start_date, dates[-1]))
        return continuous_periods

    employee_time_off_days = fields.Float(string='Time off Days', compute='_compute_leaves')

    # PF CALCULATIONS
    # EMPLOYEE
    pf_basic_percentage = fields.Float(compute='pf_type_amount')
    employee_pf_amount = fields.Float()

    # EMPLOYER
    employer_pf_amount = fields.Float()
    pf_basic_percentage_second = fields.Float(compute='pf_type_amount')

    # EMPLOYER PF REGULAR
    pf_second_regular_percent = fields.Float(compute='pf_type_amount')
    pf_second_regular_amt = fields.Float(string='PF Regular Amt  %', compute='pf_type_amount')

    # PENSION
    pf_second_regular_pension_percent = fields.Float(compute='pf_type_amount')
    pf_second_regular_pension_amt = fields.Float(compute='pf_type_amount')

    # ADMIN CHARGES
    pf_admin_percent = fields.Float(string='PF admin %', compute='pf_type_amount')
    pf_admin_amt = fields.Float(string='PF admin Amt  %', compute='pf_type_amount')

    @api.depends('basic_salary')
    def pf_type_amount(self):
        a = 15000
        for i in self:
            if i.basic_salary:
                base_amount = min(i.basic_salary, a)
                i.pf_basic_percentage = 12
                i.pf_basic_percentage_second = 12
                i.employee_pf_amount = base_amount * 0.12
                i.employer_pf_amount = base_amount * 0.12

                i.pf_second_regular_percent = 3.6
                i.pf_second_regular_amt = base_amount * 0.0367

                i.pf_second_regular_pension_percent = 8.33
                i.pf_second_regular_pension_amt = base_amount * 0.0833

                i.pf_admin_percent = 0.50
                i.pf_admin_amt = base_amount * 0.005


            else:
                i.pf_basic_percentage = False
                i.pf_basic_percentage_second = False
                i.employee_pf_amount = False
                i.employer_pf_amount = False
                i.pf_second_regular_percent = False
                i.pf_second_regular_amt = False
                i.pf_second_regular_pension_percent = False
                i.pf_second_regular_pension_amt = False
                i.pf_admin_percent = False
                i.pf_admin_amt = False

    @api.depends('employee_id')
    def _compute_leaves(self):
        leave_types = [('casual_leave', 'hr_payroll_extended.holiday_status_casual_leave'),
                       ('sick_leave', 'hr_holidays.holiday_status_sl'),
                       ('earned_leave', 'hr_payroll_extended.holiday_status_earned_leave')]
        for record in self:
            total_days = 0
            for leave_var, leave_val in leave_types:
                leave_days = sum(self.env['hr.leave'].search([
                    ('date_from', '>=', record.date_from),
                    ('date_to', '<=', record.date_to),
                    ('employee_id', '=', record.employee_id.id),
                    ('holiday_status_id', '=', self.env.ref(leave_val).id)
                ]).mapped('number_of_days_display'))
                setattr(record, leave_var, leave_days)
                total_days += leave_days
            record.employee_time_off_days = total_days

    @api.constrains('date_from', 'employee_id')
    def _check_name(self):
        for record in self:
            if record.employee_id or record.date_from:
                domain = [('date_from', '=', record.date_from),
                          ('employee_id', '=', record.employee_id.id)]
                codes = self.search(domain)
                if len(codes) > 1:
                    for code in codes:
                        if code.id != record.id:
                            raise ValidationError("Alert! The payslip has already been generated for this month.")

    def _compute_remarks(self):
        for rec in self:
            # ALLOWANCE
            other_allowance = 'Other Allowance, ' if rec.other_allowance > 0.00 else ""
            overtime = 'OT Hrs, ' if rec.overtime > 0.00 else ""
            attendance_bonus = 'Attendance Bonus, ' if rec.attendance_bonus > 0.00 else ""
            food_allowance = 'Food Allowance, ' if rec.food_allowance > 0.00 else ""
            incentive = 'Incentive, ' if rec.incentive > 0.00 else ""
            leave_encashment = 'Leave Encashment, ' if rec.leave_encashment > 0.00 else ""
            night_shift_allowance_amount = 'Night Shift, ' if rec.night_shift_allowance_amount > 0.00 else ""
            production_incentive = 'Production Incentive, ' if rec.production_incentive > 0.00 else ""

            # DEDUCTIONS
            allowance_amount_deduction = 'Lop, ' if rec.allowance_amount_deduction > 0.00 else ""
            actual_professional_tax = 'Professional Tax, ' if rec.actual_professional_tax > 0.00 else ""
            other_loan = 'Other Loan, ' if rec.other_loan > 0.00 else ""
            food_deduction = 'Food Deduction, ' if rec.food_deduction > 0.00 else ""
            other_deduction = 'Other Deduction, ' if rec.other_deduction > 0.00 else ""
            room_rent_deduction = 'Room Rent Deduction, ' if rec.room_rent_deduction > 0.00 else ""
            shoe_and_uniform_deduction = 'Shoe and Uniform, ' if rec.shoe_and_uniform_deduction > 0.00 else ""
            income_tax = 'Income Tax, ' if rec.income_tax > 0.00 else ""
            esi = 'ESI. ' if rec.esi > 0.00 else ""

            rec.remarks = str(other_allowance) + str(overtime) + str(attendance_bonus) + str(food_allowance) + str(
                incentive) + str(leave_encashment) + str(night_shift_allowance_amount) + str(
                production_incentive) + str(allowance_amount_deduction) + str(actual_professional_tax) + str(
                other_loan) + str(food_deduction) + str(other_deduction) + str(room_rent_deduction) + str(
                shoe_and_uniform_deduction) + str(income_tax) + str(esi)

    def print_payslip(self):
        return self.env.ref('hr_payroll_extended.action_employee_payslip_report_new').report_action(self)

    def _get_payslip_lines(self):
        line_vals = []
        for payslip in self:
            if not payslip.contract_id:
                raise UserError(
                    _("There's no contract set on payslip %s for %s. Check that there is at least a contract set on the employee form.",
                      payslip.name, payslip.employee_id.name))

            localdict = self.env.context.get('force_payslip_localdict', None)
            if localdict is None:
                localdict = payslip._get_localdict()

            rules_dict = localdict['rules']
            result_rules_dict = localdict['result_rules']

            blacklisted_rule_ids = self.env.context.get('prevent_payslip_computation_line_ids', [])

            result = {}
            for rule in sorted(payslip.struct_id.rule_ids, key=lambda x: x.sequence):
                if rule.id in blacklisted_rule_ids:
                    continue
                localdict.update({
                    'result': None,
                    'result_qty': 1.0,
                    'result_rate': 100,
                    'result_name': False
                })
                if rule._satisfy_condition(localdict):
                    # Retrieve the line name in the employee's lang
                    employee_lang = payslip.employee_id.lang or self.env.lang
                    # This actually has an impact, don't remove this line
                    context = {'lang': employee_lang}
                    if rule.code in localdict['same_type_input_lines']:
                        for multi_line_rule in localdict['same_type_input_lines'][rule.code]:
                            localdict['inputs'][rule.code] = multi_line_rule
                            amount, qty, rate = rule._compute_rule(localdict)
                            if amount > 0:
                                tot_rule = payslip._get_payslip_line_total(amount, qty, rate, rule)
                                localdict = rule.category_id._sum_salary_rule_category(localdict,
                                                                                       tot_rule)
                                rule_name = payslip._get_rule_name(localdict, rule, employee_lang)
                                line_vals.append({
                                    'sequence': rule.sequence,
                                    'code': rule.code,
                                    'name': rule_name,
                                    'salary_rule_id': rule.id,
                                    'contract_id': localdict['contract'].id,
                                    'employee_id': localdict['employee'].id,
                                    'amount': amount,
                                    'quantity': qty,
                                    'rate': rate,
                                    'total': tot_rule,
                                    'slip_id': payslip.id,
                                })
                    else:
                        amount, qty, rate = rule._compute_rule(localdict)
                        if amount > 0:
                            # check if there is already a rule computed with that code
                            previous_amount = localdict.get(rule.code, 0.0)
                            # set/overwrite the amount computed for this rule in the localdict
                            tot_rule = payslip._get_payslip_line_total(amount, qty, rate, rule)
                            localdict[rule.code] = tot_rule
                            result_rules_dict[rule.code] = {'total': tot_rule, 'amount': amount, 'quantity': qty,
                                                            'rate': rate}
                            rules_dict[rule.code] = rule
                            # sum the amount for its salary category
                            localdict = rule.category_id._sum_salary_rule_category(localdict,
                                                                                   tot_rule - previous_amount)
                            rule_name = payslip._get_rule_name(localdict, rule, employee_lang)
                            # create/overwrite the rule in the temporary results
                            result[rule.code] = {
                                'sequence': rule.sequence,
                                'code': rule.code,
                                'name': rule_name,
                                'salary_rule_id': rule.id,
                                'contract_id': localdict['contract'].id,
                                'employee_id': localdict['employee'].id,
                                'amount': amount,
                                'quantity': qty,
                                'rate': rate,
                                'total': tot_rule,
                                'slip_id': payslip.id,
                            }
            line_vals += list(result.values())
        return line_vals

    @api.depends('employee_id')
    def _compute_production_bool(self):
        for rec in self:
            rec.production_bool = True if rec.employee_id.department_id.name == 'PRODUCTION' else False

    @api.depends('contract_id')
    def _compute_night_shift_bool(self):
        for rec in self:
            rec.night_shift_bool = True if rec.contract_id.shift_type == 'night_shift' else False

    # @api.depends('fixed_production_amount', 'number_working_of_days', 'employee_present_days')
    # def _compute_production_incentive(self):
    #     for rec in self:
    #         if rec.fixed_production_amount > 0.00 and rec.number_working_of_days > 0.00:
    #             rec.one_day_production_cost = rec.fixed_production_amount / rec.number_working_of_days
    #             rec.production_incentive = rec.employee_present_days * rec.one_day_production_cost
    #         else:
    #             rec.production_incentive = 0.00
    #             rec.one_day_production_cost = 0.00

    # @api.depends('employee_present_days', 'number_working_of_days')
    # def _compute_attendance_bonus(self):
    #     for rec in self:
    #         rec.attendance_bonus = 750 if rec.employee_present_days == rec.number_working_of_days else 0.00

    @api.onchange('night_shift_allowance', 'total_days_worked')
    def get_night_shift_allowance(self):
        self.night_shift_allowance_amount = self.night_shift_allowance * self.total_days_worked

    @api.onchange('overtime_hours')
    def get_ot_allowance(self):
        for record in self:
            if record.gross_salary and record.overtime_hours:
                one_day_slry = record.contract_id.manual_ctc / 30
                record.overtime = (one_day_slry / 8) * 1.5 * record.overtime_hours
            else:
                record.overtime = 0.0

    # DEDUCTIONS
    other_loan = fields.Float(string='Other Loan')
    food_deduction = fields.Float(string='Food Deduction', default=200.00)
    other_deduction = fields.Float(string='Other Deduction')
    professional_tax = fields.Float(string='Professional Tax', compute='_compute_tax')
    actual_professional_tax = fields.Float(string='Actual Professional Tax')
    # actual_professional_tax = fields.Float(string='Actual Professional Tax', compute='get_actual_professional_tax')
    room_rent_deduction = fields.Float(string='Room Rent Deduction')
    shoe_and_uniform_deduction = fields.Float(string='Shoe & Uniform Deduction')
    income_tax = fields.Float(string='Income Tax')
    esi_basic_percentage = fields.Float(string='ESI Percentage %', store=True)
    esi_basic_percentage_second = fields.Float(string='ESI second', store=True)
    esi = fields.Float(string='ESI', store=True)
    esi_second = fields.Float(string='ESI 2', store=True)
    tds = fields.Float(string='TDS')
    staff_pay_bool = fields.Boolean(string='Staff Pay Bool', compute='get_staff_pay_bool')

    @api.depends('struct_id')
    def get_staff_pay_bool(self):
        for record in self:
            record.staff_pay_bool = True if record.struct_id.id == self.env.ref(
                'hr_payroll.structure_002').id else False

    @api.depends('gross_salary', 'contract_id')
    @api.onchange('gross_salary')
    def _compute_esi(self):
        for rec in self:
            if rec.contract_id.manual_ctc <= 21000:
                rec.esi_basic_percentage = 0.75
                rec.esi_basic_percentage_second = 3.25
                rec.esi = (rec.gross_salary * rec.esi_basic_percentage) / 100.0
                rec.esi_second = (rec.gross_salary * rec.esi_basic_percentage_second) / 100.0
            else:
                rec.esi_basic_percentage = 0
                rec.esi_basic_percentage_second = 0.00
                rec.esi = 0.00
                rec.esi_second = 0.00

    # @api.depends('professional_tax')
    # def get_actual_professional_tax(self):
    #     for rec in self:
    #         rec.actual_professional_tax = rec.professional_tax / 12

    def _compute_number_to_words(self):
        for rec in self:
            rec.amount_in_words = rec.currency_id.amount_to_text(
                rec.total_amount)

    @api.depends('line_ids', 'line_ids.total')
    def _compute_amount_total(self):
        for record in self:
            record.total_amount = sum(rec.total for rec in record.line_ids if rec.code == 'NET')
            record.amount_deduction = sum(
                rec.total for rec in record.line_ids if rec.category_id.name in ['Deduction', 'LOP'])
            record.amount_deduction_only = sum(
                rec.total for rec in record.line_ids if rec.category_id.name in ['Deduction'])
            record.gross_salary = sum(rec.total for rec in record.line_ids if rec.code == 'GROSS')
            record.basic_salary = sum(rec.total for rec in record.line_ids if rec.code == 'BASIC')
            record.hra = sum(rec.total for rec in record.line_ids if rec.code == 'HRA')
            record.conveyance = sum(rec.total for rec in record.line_ids if rec.code == 'CA')
            record.medical = sum(rec.total for rec in record.line_ids if rec.code == 'MA')

    @api.depends('contract_id')
    def _compute_tax(self):
        for rec in self:
            rec.professional_tax = rec.contract_id.professional_tax

    def compute_sheet(self):
        res = super(HrPayslip, self).compute_sheet()
        for record in self:
            record._compute_dates()
            record._compute_leaves()
            record.employee_manual_present_days_onchange()
            record.get_attendance_value()
            record._compute_esi()
            record.get_night_shift_allowance()
            record.get_ot_allowance()
            record.pf_type_amount()
        return res

    @api.depends('select_month', 'select_year', 'employee_id')
    def _compute_name(self):
        for rec in self:
            rec.name = (
                f"Salary Slip for {rec.employee_id.name} of {rec.select_month} - {rec.select_year.name}"
                if rec.employee_id and rec.select_month and rec.select_year
                else ""
            )

    # FOR GETTING 26th TO 25th days
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
                record.date_from = date_from
                record.date_to = date_to

    @api.model
    def _default_year(self):
        current_year = datetime.now().year
        year = self.env['hr.payroll.year'].search([('name', '=', str(current_year))])
        return year and year.id or False

    @api.depends('date_from', 'date_to', 'struct_id')
    def _compute_warning_message(self):
        self.warning_message = ""

    @api.onchange('employee_id')
    def get_contract(self):
        self.contract_id = self.employee_id.contract_id.id if self.employee_id else False
        self.struct_id = self.employee_id.contract_id.struct_id.id if self.employee_id else False

    # IF THE SELECTED MONTH IS NOT IN YEAR CONFIG : FALSE THE VALUES
    @api.onchange('employee_id', 'date_from', 'date_to')
    def employee_number_working_of_days_button(self):
        num_of_days = self.env['hr.payroll.year'].search([('name', '=', self.select_year.name)])
        for record in self:
            for line in num_of_days.day_and_month:
                if int(line.select_month) != record.date_to.month:
                    record.write({
                        'number_working_of_days': 0,
                        'number_of_leave': 0,
                        'total_days_of_month': 0,
                    })

    # FOR MANUAL AND AUTOMATIC ATTENDANCE
    @api.onchange('attendance_type')
    def get_attendance_value(self):
        if self.attendance_type == 'automatic':
            attendance_count = self.sudo().env['hr.attendance'].search([
                ('employee_id', '=', self.employee_id.id)])
            count_val = 0
            for at in attendance_count:
                if self.date_from <= at.check_in.date() <= self.date_to:
                    count_val += 1
            self.employee_present_days = count_val
            self.employee_manual_present_days = count_val
        else:
            self.employee_present_days = self.employee_manual_present_days

    # FOR DAYS CALCULATIONS
    @api.onchange('employee_manual_present_days', 'struct_id')
    def employee_manual_present_days_onchange(self):
        self._compute_leaves()
        if self.select_year:
            month_names = {
                1: 'January', 2: 'February', 3: 'March', 4: 'April',
                5: 'May', 6: 'June', 7: 'July', 8: 'August',
                9: 'September', 10: 'October', 11: 'November', 12: 'December'}
            for year in self.select_year.day_and_month:
                if month_names.get(int(year.select_month)) == self.select_month:
                    if self.employee_manual_present_days <= self.number_working_of_days - (
                            self.employee_time_off_days - self.weekoff_lop):
                        self.employee_present_days = self.employee_manual_present_days
                        self.total_days_of_month = year.total_number_of_days
                        if self.struct_id.id == self.env.ref('hr_payroll.structure_002').id:
                            self.number_of_leave = year.public_holiday_count + year.only_sunday - self.weekoff_lop
                        elif self.struct_id.id == self.env.ref('hr_payroll_extended.structure_staff_sat001').id:
                            self.number_of_leave = year.public_holiday_count + year.only_sunday - self.weekoff_lop
                        elif self.struct_id.id == self.env.ref('hr_payroll.structure_worker_001').id:
                            self.number_of_leave = year.public_holiday_count + year.sunday - self.weekoff_lop - year.staff_saturday
                        else:
                            self.number_of_leave = year.public_holiday_count + year.sunday
                        # STRUCT ID
                        if self.struct_id.id == self.env.ref('hr_payroll.structure_002').id: #worker
                            self.number_working_of_days = year.number_of_days + year.only_saturday - year.public_holiday_count
                        elif self.struct_id.id == self.env.ref('hr_payroll_extended.structure_staff_sat001').id: #staff sat
                            self.number_working_of_days = year.number_of_days + year.only_saturday - year.public_holiday_count
                        elif self.struct_id.id == self.env.ref('hr_payroll.structure_worker_001').id: #staff pay
                            self.number_working_of_days = year.number_of_days + year.staff_saturday - year.public_holiday_count
                        else:
                            self.number_working_of_days = year.number_of_days + year.sunday - year.public_holiday_count
                        val = self.contract_id.manual_ctc
                        self.employee_one_day_salary = round(self.contract_id.manual_ctc / self.total_days_of_month)
                        # self.employee_one_day_salary = round(self.contract_id.manual_ctc / 30)
                        self.employee_loptotal_days = self.number_working_of_days - self.employee_present_days - (
                                self.employee_time_off_days - self.weekoff_lop) if self.employee_time_off_days > 0 else self.number_working_of_days - self.employee_present_days
                        self.employee_final_lop_total_days = self.employee_loptotal_days - self.leave_paid_timeoff
                        self.employee_final_present_days = self.employee_present_days + self.leave_paid_timeoff + self.number_of_leave + self.employee_time_off_days
                        self.allowance_amount_deduction = self.employee_final_lop_total_days * self.employee_one_day_salary
                    else:
                        raise ValidationError(
                            f"The Employee code {self.employee_id.emp_code} has more present days than the number of working days.")

    def employee_days_onchange(self):
        self.get_contract()
        if self.select_year:
            month_names = {
                1: 'January', 2: 'February', 3: 'March', 4: 'April',
                5: 'May', 6: 'June', 7: 'July', 8: 'August',
                9: 'September', 10: 'October', 11: 'November', 12: 'December'}
            for year in self.select_year.day_and_month:
                if month_names.get(int(year.select_month)) == self.select_month:
                    self.employee_present_days = self.employee_manual_present_days
                    self.total_days_of_month = year.total_number_of_days
                    if self.struct_id.id == self.env.ref('hr_payroll.structure_002').id:
                        self.number_of_leave = year.public_holiday_count + year.only_sunday - self.weekoff_lop
                    elif self.struct_id.id == self.env.ref('hr_payroll_extended.structure_staff_sat001').id:
                        self.number_of_leave = year.public_holiday_count + year.only_sunday - self.weekoff_lop
                    elif self.struct_id.id == self.env.ref('hr_payroll.structure_worker_001').id:
                        self.number_of_leave = year.public_holiday_count + year.sunday - self.weekoff_lop - year.staff_saturday
                    else:
                        self.number_of_leave = year.public_holiday_count + year.sunday
                    # STRUCT ID
                    if self.struct_id.id == self.env.ref('hr_payroll.structure_002').id: #worker pay
                        self.number_working_of_days = year.number_of_days + year.only_saturday - year.public_holiday_count
                    elif self.struct_id.id == self.env.ref('hr_payroll_extended.structure_staff_sat001').id: #staff pay sat
                        self.number_working_of_days = year.number_of_days + year.only_saturday - year.public_holiday_count
                    elif self.struct_id.id == self.env.ref('hr_payroll.structure_worker_001').id: #staff pay
                        self.number_working_of_days = year.number_of_days + year.staff_saturday - year.public_holiday_count
                    else:
                        self.number_working_of_days = year.number_of_days + year.sunday - year.public_holiday_count
                    val = self.contract_id.manual_ctc
                    self.employee_one_day_salary = round(self.contract_id.manual_ctc / self.total_days_of_month)
                    self.employee_loptotal_days = self.number_working_of_days - self.employee_present_days - (
                            self.employee_time_off_days - self.weekoff_lop) if self.employee_time_off_days > 0 else self.number_working_of_days - self.employee_present_days
                    self.employee_final_lop_total_days = self.employee_loptotal_days - self.leave_paid_timeoff
                    self.employee_final_present_days = self.employee_present_days + self.leave_paid_timeoff + self.number_of_leave + self.employee_time_off_days
                    self.allowance_amount_deduction = self.employee_final_lop_total_days * self.employee_one_day_salary


class EmployeeSalaryRevision(models.Model):
    _name = 'employee.salary.revision'
    _description = "Employee Salary Revision"

    employee_id = fields.Many2one('hr.employee')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    new_salary_from = fields.Date(string="New Salary From")
    new_salary_amount = fields.Float(string="New Salary Amount")
    old_salary_amount = fields.Float(string="Old Salary Amount")
    salary_hike = fields.Float(string="Salary Hike(%)")
    new_salary_id = fields.Many2one('res.users', default=lambda self: self.env.uid, string="Approved By")
    job_position_id = fields.Many2one('hr.job')
    department_id = fields.Many2one('hr.department')
    level = fields.Char()

    @api.onchange('new_salary_amount', 'old_salary_amount')
    def onchange_hike_percentage(self):
        if self.new_salary_amount > 0 and self.old_salary_amount > 0:

            difference = self.new_salary_amount - self.old_salary_amount

            if difference > 0:
                percentage = difference / self.old_salary_amount
                actual_percenatage = percentage * 100
                percentage_float = "{:.2f}".format(actual_percenatage)
                self.write({
                    'salary_hike': actual_percenatage
                })


from .half_round import half_round


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    @api.model
    def _compute_rule(self, localdict):
        localdict['half_round'] = half_round
        return super(HrSalaryRule, self)._compute_rule(localdict)
