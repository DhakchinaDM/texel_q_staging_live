from odoo import fields, models, api, _
from dateutil.relativedelta import relativedelta
from datetime import date
from odoo.addons.phone_validation.tools import phone_validation
from odoo.exceptions import AccessError, UserError, ValidationError

GENDER_SELECTION = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other')
]
CERTIFICATE_SELECTION = [
    ('elementary School', 'Elementary School'),
    ('junior high school', 'Junior High School'),
    ('graduate', 'Senior High School'),
    ('bachelor', 'Bachelor'),
    ('master', 'Master'),
    ('doctor', 'Doctor'),
    ('other', 'Other'),
]


class HrEmployee(models.Model):
    _inherit = "hr.employee"
    _description = 'Employee'
    _order = 'emp_code asc'

    slip_ids = fields.One2many('hr.payslip', 'employee_id', string='Payslips', readonly=True)
    payslip_count = fields.Integer(compute='_compute_payslip_count', string='Payslip Count',
                                   groups="om_om_hr_payroll.group_hr_payroll_user")

    date_of_joining = fields.Date(string="Date Of Joining", groups="hr.group_hr_user",
                                  default=lambda self: fields.Date.to_string(date.today()))
    months = fields.Integer(string="Months", default="6", groups="hr.group_hr_user")
    eligible_leave_period = fields.Date(string="Eligible Leave Period Months", compute="months_onchange")
    name_emergency = fields.Char(string="Contact  Name", groups="hr.group_hr_user")
    number_emergency = fields.Char(string="Contact Number", groups="hr.group_hr_user")
    allocation_bool = fields.Boolean(string="Allocation Boolean", compute="allocation_bool_compute")
    emp_code = fields.Integer(string="Employee Code", groups="hr.group_hr_user")
    salary_revision_ids = fields.One2many('employee.salary.revision', 'employee_id')
    uan_number = fields.Char(string="UAN Number", groups="hr.group_hr_user")
    provident_fund_number = fields.Char(string="Provident Fund Number", groups="hr.group_hr_user")
    aadhar_number = fields.Char(string="Aadhar Number", groups="hr.group_hr_user")
    pan_number = fields.Char(string="Pan Number", groups="hr.group_hr_user")
    blood_type = fields.Selection([('A+', 'A+'), ('A-', 'A-'), ('A1+', 'A1+'), ('A1-', 'A1-'), ('B+', 'B+'),
                                   ('B-', 'B-'), ('B1-', 'B1-'), ('B1+', 'B1+'), ('O+', 'O+'), ('O-', 'O-'),
                                   ('AB+', 'AB+'), ('AB-', 'AB- '), ('A1B+', 'A1B+')], string="Blood Type",
                                  groups="hr.group_hr_user")
    barcode = fields.Char('Employee Id (badge)', help="ID Used for Employee Identification")
    age = fields.Integer(string="Age")
    religion = fields.Char(string="Religion")
    language = fields.Char(string="Language")
    employee_wrk_hist_ids = fields.One2many('employee.education.history', 'employee_id_employee')

    spouse_identification_id = fields.Char('Identification Id')
    family_ids = fields.One2many('hr.family.info', 'employee_id', string='Family', help='Family Information')
    esi_number = fields.Char(string='ESI Number')
    # equipment_ids = fields.One2many('maintenance.equipment', 'employee_id')
    shift_id = fields.Many2one('shift.master')

    @api.constrains('emp_code')
    def restrict_emp_code(self):
        for record in self:
            if record.emp_code:
                domain = [('emp_code', '=', record.emp_code)]
                codes = self.search(domain)
                if len(codes) > 1:
                    for code in codes:
                        if code.id != record.id:
                            raise ValidationError(
                                _('Alert! The Employee code already exists!.'))

    @api.depends('eligible_leave_period')
    def allocation_bool_compute(self):
        for k in self:
            if k.eligible_leave_period:
                to_date = fields.Date.today()
                if k.eligible_leave_period <= to_date:
                    k.allocation_bool = True
                else:
                    k.allocation_bool = False
            else:
                k.allocation_bool = False

    def _compute_payslip_count(self):
        for employee in self:
            employee.payslip_count = len(employee.slip_ids)

    @api.onchange('months', 'date_of_joining')
    @api.depends('months', 'date_of_joining')
    def months_onchange(self):
        if self.months and self.date_of_joining:
            self.eligible_leave_period = self.date_of_joining + relativedelta(months=self.months)
        else:
            self.eligible_leave_period = self.date_of_joining


class EmployeeEducationHistory(models.Model):
    _name = 'employee.education.history'
    _description = 'Employee Education History'

    employee_id_employee = fields.Many2one('hr.employee')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    department_id = fields.Many2one('employee.department', string="Department")
    degree_id = fields.Many2one('employee.degree', string="Degree")
    # level_id = fields.Many2one('employee.level', string="Level")
    level_id = fields.Char(string="Level")
    institute_id = fields.Many2one('employee.level', string="Institute")
    from_date = fields.Date(string="From")
    to_date = fields.Date(string="To")
    attachment = fields.Many2many('ir.attachment', string="Attachments")
    detail = fields.Char(string="Specialization")
    attachment_name = fields.Char(string="Education Details")


class HrFamilyInfo(models.Model):
    _name = 'hr.family.info'
    _description = 'Employee Family Information'

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    gender = fields.Selection(GENDER_SELECTION, 'gender')
    birthday = fields.Date('Date Of Birth')
    relation_id = fields.Many2one('hr.employee.relation', 'Relation')
    mobile = fields.Char('Mobile')
    certificate = fields.Selection(CERTIFICATE_SELECTION, 'Certificate Level',
                                   default='other', groups="hr.group_hr_user")
    employee_id = fields.Many2one('hr.employee', string="Employee", help='Select corresponding Employee', )
    country_id = fields.Many2one(
        'res.country', 'Nationality (Country)', related='employee_id.country_id')

    @api.onchange('mobile', 'country_id')
    def _onchange_mobile_validation(self):
        if self.mobile:
            self.mobile = self._phone_format(self.mobile)

    def _phone_format(self, number, country=None, company=None):
        country = country or self.country_id or self.env.company.country_id
        if not country:
            return number
        return phone_validation.phone_format(
            number,
            country.code if country else None,
            country.phone_code if country else None,
            force_format='INTERNATIONAL',
            raise_exception=False
        )


class HrEmployeeRelation(models.Model):
    _name = 'hr.employee.relation'
    _description = 'Relation'

    name = fields.Char('Name')
    abbreviation = fields.Char('Abbreviation')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)


class EmployeeDepartment(models.Model):
    _name = 'employee.department'
    _description = 'Department'

    name = fields.Char(string="Department")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)


class EmployeeDegree(models.Model):
    _name = 'employee.degree'
    _description = 'Employee Degree'

    name = fields.Char(string="Degree")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)


class EmployeeLevel(models.Model):
    _name = 'employee.level'
    _description = 'Employee Level'

    name = fields.Char(string="Level")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)


class HrAttendance(models.Model):
    _inherit = "hr.attendance"
    _description = 'Hr Attendance'

    emp_code = fields.Integer(string="Employee Code")

    employee_id = fields.Many2one('hr.employee', string="Employee", compute='_compute_from_emp_code', store=True,
                                  required=True, readonly=False,
                                  ondelete='cascade', index=True)

    @api.onchange('employee_id')
    def get_emp_code(self):
        for rec in self:
            if rec.employee_id:
                rec.emp_code = rec.employee_id.emp_code

    @api.depends('emp_code')
    def _compute_from_emp_code(self):
        for record in self:
            if record.emp_code != 0:
                record.employee_id = self.env['hr.employee'].sudo().search([('emp_code', '=', record.emp_code)],
                                                                           limit=1)
            else:
                record.employee_id = False
