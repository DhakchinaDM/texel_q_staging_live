from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from datetime import datetime, date


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_om_hr_payroll_account = fields.Boolean(string='Payroll Accounting')
    portal_allow_api_keys = fields.Boolean(string="Customer API Keys")


class HrPayrollYearList(models.Model):
    _name = 'payroll.year.list'
    _description = 'Payroll Year Master Config'

    name = fields.Char(string='Year')

    _sql_constraints = [('name', "unique(name)", "Name Must Be Unique")]


class HrPayrollMonth(models.Model):
    _name = 'hr.payroll.month'
    _description = 'Payroll Month Master Config'

    name = fields.Char(string='Month')


class HrPayrollYear(models.Model):
    _name = 'hr.payroll.year'
    _description = 'Payroll Year Master Config'

    name = fields.Char(string=' Year', related='year_list_id.name')
    year_list_id = fields.Many2one('payroll.year.list', string='Year')
    day_and_month = fields.One2many('hr.payroll.year.line', 'name_id')
    month = fields.Char(string='month', compute='_compute_month')
    month_number = fields.Char(string='Month Number', compute='_compute_month')
    date_convert = fields.Datetime(string='Date Convert')

    @api.constrains('year_list_id')
    def _check_name(self):
        for record in self:
            if record.year_list_id:
                domain = [('year_list_id', '=', record.year_list_id.id)]
                codes = self.search(domain)
                if len(codes) > 1:
                    for code in codes:
                        if code.id != record.id:
                            raise ValidationError(
                                _('Alert! The Selected Year of %s already exists.') % record.year_list_id.name)

    @api.onchange('month', 'month_number', 'year_list_id', 'day_and_month')
    def _onchange_year_and_month(self):
        import datetime
        import calendar
        try:
            year = int(self.name)
        except ValueError:
            # Handle the case when 'name' cannot be converted to an integer
            return
        for record in self.day_and_month:
            try:
                select_month = int(record.select_month)
                if select_month < 1 or select_month > 12:
                    # Handle the case when 'select_month' is not in the valid range 1-12
                    continue
            except ValueError:
                # Handle the case when 'select_month' cannot be converted to an integer
                continue
            try:
                selection_diff = datetime.datetime(year, select_month, 1)
                record.year_monthnumber_of_days = calendar.monthrange(selection_diff.year, selection_diff.month)[1]
                sundays = len(
                    [1 for i in calendar.monthcalendar(selection_diff.year, selection_diff.month) if i[6] != 0])
                saturdays = len(
                    [1 for i in calendar.monthcalendar(selection_diff.year, selection_diff.month) if i[5] != 0])
                record.sunday = sundays + saturdays
            except (ValueError, TypeError):
                # Handle any other potential exceptions related to invalid date inputs
                continue

    @api.depends('month')
    @api.onchange('month')
    def _compute_month(self):
        import datetime
        import calendar
        date = datetime.datetime.now()
        daten = datetime.datetime(1, int(date.month), 1).strftime("%B")
        self.month = daten
        self.month_number = date.month

    # @api.onchange('day_and_month')
    # def _public_holiday(self):
    #     print('========_public_holiday===========')
    #     for record in self.day_and_month:
    #         public_leave_count = 0.00
    #         current_year = datetime.now().year  # Get the current year
    #
    #         # Assuming 'select_month' contains the month number
    #         employee_public_leave = record.env['hr.public.holidays.line'].sudo().search([
    #             ('month_number', '=', record.select_month),
    #             ('holiday_id.year_list_id', '=', record.name_id.year_list_id.id)
    #         ])
    #
    #         for line in employee_public_leave:
    #             if record.select_month == line.month_number:
    #                 public_leave_count += 1
    #
    #         record.public_holiday_count = public_leave_count
    #
    #         # Create a list to store the names of public holidays
    #         holiday_names = []
    #         for rec in employee_public_leave:
    #             if record.select_month == rec.month_number:
    #                 if rec.name:
    #                     holiday_names.append(rec.name)
    #
    #         # Join the holiday names into a single string
    #         record.holiday_public = ', '.join(holiday_names)

    @api.depends('day_and_month.select_month', 'day_and_month.public_holiday_count')
    def _compute_days(self):
        import datetime
        import calendar

        today = datetime.date.today()
        current_year = today.year

        for record in self.day_and_month:
            if record.select_month:
                try:
                    selected_month = int(record.select_month)
                    if 1 <= selected_month <= 12:
                        if selected_month == 1:
                            prev_month_year = current_year - 1
                            prev_month = 12
                        else:
                            prev_month_year = current_year
                            prev_month = selected_month - 1

                        start_date = datetime.date(prev_month_year, prev_month, 26)
                        end_date = datetime.date(current_year, selected_month, 25)

                        sundays = 0
                        saturdays = 0
                        total_days = 0

                        current_date = start_date
                        while current_date <= end_date:
                            if current_date.weekday() == 5:
                                saturdays += 1
                            elif current_date.weekday() == 6:
                                sundays += 1
                            total_days += 1
                            current_date += datetime.timedelta(days=1)

                        record.number_of_days = total_days - (sundays + saturdays)
                        record.total_number_of_days = total_days
                        record.sunday = sundays + saturdays
                        record.only_saturday = saturdays
                        record.only_sunday = sundays
                except ValueError:
                    continue

    def get_number_of_working_days(self):
        hr_payslips = self.env['hr.payslip'].search([('date_year', '=', self.name)])
        for payslip in hr_payslips:
            for record in self.day_and_month:
                convert_select_month = datetime(1, int(record.select_month), 1).strftime("%B")
                if payslip.date_months == convert_select_month:
                    payslip.write({
                        'number_working_of_days': record.number_of_days,
                        'number_of_leave': record.public_holiday_count + record.sunday,
                        'total_days_of_month': record.total_number_of_days,

                    })


class MonthYear(models.Model):
    _name = 'hr.payroll.year.line'
    _description = 'Payroll Year line'

    name_id = fields.Many2one('hr.payroll.year', string=' Year')
    year_list_id = fields.Many2one('payroll.year.list', string='Year', related='name_id.year_list_id')
    number_of_days = fields.Float(string='Number Of Days', compute='_compute_days', store=True)
    week_off = fields.Selection([('weekoff', 'All Saturdays & Sundays')], default='weekoff',
                                string='Week Off')
    sunday = fields.Integer(string='Saturday & Sunday', compute='_compute_days', store=True)
    only_saturday = fields.Integer(string='Saturday', compute='_compute_days', store=True)
    only_sunday = fields.Integer(string='Sunday', compute='_compute_days', store=True)
    boolen_leave = fields.Boolean(string='Approved')
    select_month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string="Month")
    public_holiday_count = fields.Integer(string='Public Holiday', compute='_public_holiday')
    holiday_public = fields.Char(string='Leave Type', compute='_public_holiday')
    staff_saturday = fields.Integer(string='Staff Saturday Holiday', compute='_public_holiday')
    total_number_of_days = fields.Float(string='Total Number Of Days', compute='_compute_days', store=True)
    year_monthnumber_of_days = fields.Float(string='year month Number Of Days')

    # @api.depends('select_month', 'year_list_id')
    # def _public_holiday(self):
    #     for record in self:
    #         public_leave_count = 0.00
    #         current_year = datetime.now().year
    #         employee_public_leave = record.env['hr.public.holidays.line'].sudo().search([
    #             ('month_number', '=', record.select_month),
    #             ('holiday_id.year_list_id', '=', record.name_id.year_list_id.id)
    #         ])
    #         for line in employee_public_leave:
    #             if record.select_month == line.month_number:
    #                 public_leave_count += 1
    #         record.public_holiday_count = public_leave_count
    #         holiday_names = []
    #         for rec in employee_public_leave:
    #             if record.select_month == rec.month_number:
    #                 if rec.name:
    #                     holiday_names.append(rec.name)
    #         record.holiday_public = ', '.join(holiday_names)

    @api.depends('select_month')
    def _public_holiday(self):
        for record in self:
            staff_sat = 0.00
            public_leave_count = 0.00
            today = date.today()
            current_year = today.year
            holiday_names = []
            if record.select_month:
                try:
                    selected_month = int(record.select_month)
                    if 1 <= selected_month <= 12:
                        if selected_month == 1:
                            prev_month_year = current_year - 1
                            prev_month = 12
                        else:
                            prev_month_year = current_year
                            prev_month = selected_month - 1
                        start_date = date(prev_month_year, prev_month, 26)
                        end_date = date(current_year, selected_month, 25)
                        public_holiday_lines = record.env['hr.public.holidays.line'].sudo().search([
                            ('date', '>=', start_date),
                            ('date', '<=', end_date),
                        ])
                        staff_saturday_lines = record.env['hr.public.holidays.line'].sudo().search([
                            ('date', '>=', start_date),
                            ('date', '<=', end_date),
                            ('week_day', '=', 5)
                        ])
                        for sat in staff_saturday_lines:
                            staff_sat += 1
                        for line in public_holiday_lines:
                            public_leave_count += 1
                            if line.name:
                                holiday_names.append(line.name)

                except ValueError:
                    public_leave_count = 0.00
                    staff_sat = 0.00
                    holiday_names = []

            record.public_holiday_count = public_leave_count
            record.staff_saturday = staff_sat
            record.holiday_public = ', '.join(holiday_names)

    @api.depends('select_month', 'public_holiday_count')
    def _compute_days(self):
        self.name_id._compute_days()

    def action_approve(self):
        for rec in self:
            if rec.select_month:
                rec.write({'boolen_leave': True})
                rec.name_id._compute_days()
                rec.name_id.get_number_of_working_days()

    @api.constrains('select_month')
    def _check_name(self):
        for record in self:
            if record.select_month:
                current_year = fields.Date.today().year
                domain = [
                    ('select_month', '=', record.select_month),
                    ('name_id', '=', str(current_year))
                ]
                codes = self.search(domain)
                if len(codes) > 1:
                    for code in codes:
                        if code.id != record.id:
                            convert_select_month_val = datetime(1, int(record.select_month), 1).strftime("%B")
                            raise ValidationError(
                                _('Alert! The Selected Month and Year of %s-%s already exists.') % (
                                    convert_select_month_val, record.name_id.name))
