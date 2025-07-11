from odoo.exceptions import ValidationError, UserError
from odoo import api, fields, models, _


class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    struct_id = fields.Many2one('hr.payroll.structure', string='Salary Structure')
    resource_calendar_id = fields.Many2one(required=True, help="Employee's working schedule.")
    type_id = fields.Many2one('hr.contract.type', string="Employee Category",
                              required=True, help="Employee category",
                              default=lambda self: self.env['hr.contract.type'].search([], limit=1))
    shift_type = fields.Selection([('day_shift', 'Day Shift'), ('night_shift', "Night Shift")],
                                  string="Shift Type")
    night_shift_allowance = fields.Float(string='Night Shift Allowance')

    def _get_default_notice_days(self):
        if self.env['ir.config_parameter'].get_param(
                'hr_resignation.notice_period'):
            return self.env['ir.config_parameter'].get_param(
                'hr_resignation.no_of_days')
        else:
            return 0

    journal_id = fields.Many2one('account.journal', 'Journal', required=False)

    analytic_account_id = fields.Many2one('account.analytic.account',
                                          'Analytic Account')
    notice_days = fields.Integer(string="Notice Period",
                                 default=_get_default_notice_days)
    da_percentage = fields.Float(string='Dearness %')
    dearness_allowance = fields.Float(string='Dearness Allowance')
    hra_percentage = fields.Float(string='HRA %', default=20)
    house_rent_allowance = fields.Float(string='House Rent Allowance')
    conveyance_percentage = fields.Float(string='Conveyance %', default=10)
    convenyance_allowance = fields.Float(string='Conveyance Allowance')
    special_percentage = fields.Float(string='Medical %', default=10)
    special_allowance = fields.Float(string='Special Allowance')
    leave_incentives = fields.Float(string='Leave Allowance')
    travel_incentives = fields.Float(string='Travel Allowance')
    health_insurance = fields.Float(string='Health Insurance')
    notice_period_pay = fields.Float(string='Notice Period Pay')

    tds = fields.Float(string='TDS')
    professional_tax = fields.Float(string='Professional Tax')
    pf_type = fields.Selection([
        ('dynamic', 'Dynamic'),
        ('fix', 'Fixed'), ('form_level', 'Form 11'),
    ], string="PF Type", default="fix")
    contract_amount_settlement = fields.Float(string='Contract Allowance Amount')
    esi_basic_percentage = fields.Float(string='ESI Percentage %', compute='_onchange_esi_pf_calculations')
    esi_basic_percentage_second = fields.Float(string='ESI Percentage  %', compute='_onchange_esi_pf_calculations')
    esi = fields.Float(string='ESI', compute='_onchange_esi_pf_calculations')
    esi_second = fields.Float(compute='_onchange_esi_pf_calculations')
    start_date_doj = fields.Date(string="Joining Date", related='employee_id.date_of_joining', readonly=False)
    date_start = fields.Date('Start Date', compute='_compute_emp_doj', tracking=True,
                             index=True)

    def _compute_emp_doj(self):
        for rec in self:
            rec.date_start = rec.employee_id.date_of_joining if rec.employee_id.date_of_joining else False

    manual_ctc = fields.Float(string='CTC', store=True)
    salary_hike_effective_date = fields.Date(string="Salary Hike Effective Date")

    basic_percentage = fields.Float(string='Basic Percentage %', default=60)
    amount_settlement_diff = fields.Float(string='CTC Difference')
    basic_allowance = fields.Float(string="Basic Allowance")
    wage = fields.Float(string='Basic')
    salary_hike_enabled = fields.Boolean(string='Salary Hike?')
    ctc = fields.Float(string='Master Salary', store=True)

    employee_pf_amount = fields.Float(string="Employee PF", compute='pf_type_amount')
    employer_pf_amount = fields.Float(string="Employer PF", compute='pf_type_amount')
    approved_by = fields.Many2one('res.users', default=lambda self: self.env.user, string='Current User')
    compute_contract_validate = fields.Boolean(string="")
    contract_deduction_settlement = fields.Float(string='Contract Deduction Amount')
    pf_basic_percentage = fields.Float(string='PF Percentage %', compute='pf_type_amount')
    pf_basic_percentage_second = fields.Float(string='PF Percentage  %', compute='pf_type_amount')
    pf_deduction = fields.Float(string="PF Deductions")
    pf_deduction_second = fields.Float(string="PF  Deductions")
    weekly_incentive = fields.Float(string="Weekly Incentive")
    monthly_incentive = fields.Float(string="Monthly Incentive")
    special_incentive = fields.Float(string="Special Incentive")

    pf_second_regular_percent = fields.Float(string='PF Regular  %', compute='pf_type_amount')
    pf_second_regular_amt = fields.Float(compute='pf_type_amount')

    pf_second_regular_pension_percent = fields.Float(string='PF Pension  %', compute='pf_type_amount')
    pf_second_regular_pension_amt = fields.Float(string='PF Pension Amt  %', compute='pf_type_amount')

    pf_admin_percent = fields.Float(string='PF admin %', compute='pf_type_amount')
    pf_admin_amt = fields.Float(string='PF admin Amt  %', compute='pf_type_amount')

    @api.depends('manual_ctc')
    def _onchange_esi_pf_calculations(self):
        for rec in self:
            if rec.manual_ctc <= 21000:
                rec.esi_basic_percentage = 0.75
                rec.esi_basic_percentage_second = 3.25
                rec.esi = (rec.manual_ctc * rec.esi_basic_percentage) / 100.0
                rec.esi_second = (rec.manual_ctc * rec.esi_basic_percentage_second) / 100.0
            else:
                rec.esi_basic_percentage = 0
                rec.esi_basic_percentage_second = 0.00
                rec.esi = 0.00
                rec.esi_second = 0.00

    # @api.onchange('pf_basic_percentage', 'pf_basic_percentage_second')
    # def pf_basic_percentage_onchange(self):
    #     self.employee_pf_amount = (self.ctc / 100) * self.pf_basic_percentage
    #     self.employer_pf_amount = (self.ctc / 100) * self.pf_basic_percentage_second

    @api.depends('pf_type', 'wage')
    def pf_type_amount(self):
        a = 15000
        for i in self:
            if i.wage and i.pf_type == 'fix':
                base_amount = min(i.wage, a)
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

    # CLEAR THE EMPLOYEE CONTRACT CTC COMPUTATION AND CTC DIFFERENCE TO IDENTIFY AND UPDATE STATUS AS 'RUNNING.
    def employee_contract_validate(self):
        if self.employee_id and self.amount_settlement_diff != 0.00:
            raise ValidationError(
                _("Alert!, Contract cannot be Validated for Mr.%s, "
                  "as The Contract Salary Allocation is Not Matching with CTC - %s. "
                  "The Payment Difference is %s.") % (
                    self.employee_id.name, self.ctc,
                    self.amount_settlement_diff))
        else:
            self.write({'compute_contract_validate': True})
            self.write({
                'state': 'open',
            })

    # CLEAR THE EMPLOYEE CONTRACT AMOUNT TO RE-CALCULATE OR RESET.
    def clear_contract_amount_setup(self):
        for contract in self:
            if contract.ctc:
                contract.amount_settlement_diff = contract.ctc
                contract.wage = 0.00
                contract.basic_percentage = 0.00
                contract.house_rent_allowance = 0.00
                contract.dearness_allowance = 0.00
                contract.convenyance_allowance = 0.00
                contract.special_allowance = 0.00
                contract.health_insurance = 0.00
                contract.hra_percentage = 0.00
                contract.conveyance_percentage = 0.00
                contract.special_percentage = 0.00
                contract.da_percentage = 0.00
                contract.travel_incentives = 0.00
                contract.pf_type = 'form_level'

    @api.onchange('ctc', 'manual_ctc')
    def _onchange_employee_ctc_to_manual_ctc(self):
        if self.employee_id:
            self.ctc = self.manual_ctc

    # ALLOCATE THE EMPLOYEE CONTRACT AMOUNT TO PERCENTAGE WISE TO SEPARATE IT.
    @api.onchange('wage', 'dearness_allowance', 'house_rent_allowance', 'convenyance_allowance', 'special_allowance')
    def hra_allowance_value(self):
        if self.ctc:
            self.basic_percentage = (self.wage * 100) / self.ctc
            self.da_percentage = (self.dearness_allowance * 100) / self.ctc
            self.hra_percentage = (self.house_rent_allowance * 100) / self.ctc
            self.conveyance_percentage = (self.convenyance_allowance * 100) / self.ctc
            self.special_percentage = (self.special_allowance * 100) / self.ctc

    # ALLOCATE THE EMPLOYEE CONTRACT AMOUNT TO PERCENTAGE WISE TO SEPARATE IT.
    @api.onchange('wage', 'hra_percentage', 'basic_percentage', 'da_percentage', 'conveyance_percentage',
                  'ctc', 'esi', 'esi_basic_percentage',
                  'esi_second',
                  'special_percentage',
                  'esi_basic_percentage_second')
    def hra_allowance(self):
        for record in self:
            record.wage = False
            record.house_rent_allowance = False
            record.dearness_allowance = False
            record.convenyance_allowance = False
            record.special_allowance = False
            record.esi = False
            record.esi_second = False
            if record.ctc:
                if record.basic_percentage:
                    total_basic = record.ctc * (1 - (record.basic_percentage or 0.0) / 100.0)
                    record.write({
                        'basic_allowance': total_basic})
                    record.wage = record.ctc - record.basic_allowance
            if record.wage > 0.00:
                if record.hra_percentage:
                    per_val = (record.ctc / 100) * record.hra_percentage
                    record.house_rent_allowance = per_val
                if record.da_percentage:
                    per_val = (record.ctc / 100) * record.da_percentage
                    record.dearness_allowance = per_val
                if record.conveyance_percentage:
                    per_val = (record.ctc / 100) * record.conveyance_percentage
                    record.convenyance_allowance = per_val
                if record.special_percentage:
                    per_val = (record.ctc / 100) * record.special_percentage
                    record.special_allowance = per_val
            if record.ctc <= 21100.00:
                if record.ctc:
                    total_esi = (record.ctc * record.esi_basic_percentage) / 100.0
                    total_esi_second = (record.ctc * record.esi_basic_percentage_second) / 100.0
                    record.esi = total_esi
                    record.esi_second = total_esi_second
                else:
                    record.write({'esi': 0.00, 'esi_second': 0.00})

    # APPLY THE EMPLOYEE CONTRACT AMOUNT TO WITH PERCENTAGE WISE
    @api.depends('amount_settlement_diff')
    @api.onchange('amount_settlement_diff', 'wage', 'house_rent_allowance', 'dearness_allowance',
                  'convenyance_allowance',
                  'special_allowance',
                  'professional_tax',
                  'esi',
                  'travel_incentives', 'health_insurance', 'contract_amount_settlement',
                  'tds', 'employee_pf_amount', 'employer_pf_amount')
    def _onchange_amount_settlement_diff(self):
        total_calculation = 0.00
        if self.ctc:
            self.contract_amount_settlement = self.wage + \
                                              self.house_rent_allowance + \
                                              self.dearness_allowance + \
                                              self.special_allowance + \
                                              self.travel_incentives + \
                                              self.convenyance_allowance + \
                                              self.health_insurance
            # self.contract_deduction_settlement = (self.tds + self.employee_pf_amount + self.employer_pf_amount + self.esi + self.professional_tax)
            total_calculation = (self.contract_amount_settlement) + self.contract_deduction_settlement
            self.amount_settlement_diff = self.ctc - total_calculation

    # CHECK AND UPDATE THE EMPLOYEE SALARY REVISIONS AND RE-CONFIGURE THE CTC.
    def employee_salary_update(self):
        for salary in self:
            employee_hike_date = ''
            employee_hike_salary = []
            if salary.employee_id:
                if salary.employee_id.salary_revision_ids:
                    for hike in salary.employee_id.salary_revision_ids:
                        employee_hike_salary = hike.new_salary_amount
                        employee_hike_date = hike.new_salary_from
                    salary.write({
                        'manual_ctc': employee_hike_salary,
                        'ctc': employee_hike_salary,
                        'salary_hike_effective_date': employee_hike_date,
                        'salary_hike_enabled': True
                    })
                    salary.hra_allowance()
                else:
                    raise ValidationError(
                        _("Alert!, The Selected Employee of 'Mr.%s ', "
                          "Doesn't have any Salary Revisions or not mentioned,"
                          "System will Accept only the mentioned The CTC Amount %s INR.") % (
                            self.employee_id.name, self.ctc))

    # NEW END ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def get_all_structures(self):
        """
        @return: the structures linked to the given contracts, ordered by hierachy (parent=False first,
                 then first level children and so on) and without duplicata
        """
        structures = self.mapped('struct_id')
        if not structures:
            return []
        # YTI TODO return browse records
        return list(set(structures._get_parent_structure().ids))

    def get_attribute(self, code, attribute):
        return self.env['hr.contract.advantage.template'].search([('code', '=', code)], limit=1)[attribute]

    def set_attribute_value(self, code, active):
        for contract in self:
            if active:
                value = self.env['hr.contract.advantage.template'].search([('code', '=', code)], limit=1).default_value
                contract[code] = value
            else:
                contract[code] = 0.0


class HrContractAdvantageTemplate(models.Model):
    _name = 'hr.contract.advantage.template'
    _description = "Employee's Advantage on Contract"

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    code = fields.Char('Code', required=True)
    lower_bound = fields.Float('Lower Bound', help="Lower bound authorized by the employer for this advantage")
    upper_bound = fields.Float('Upper Bound', help="Upper bound authorized by the employer for this advantage")
    default_value = fields.Float('Default value for this advantage')
