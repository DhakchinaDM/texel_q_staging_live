from odoo import api, fields, models,_
import datetime
from odoo.exceptions import UserError, ValidationError

week_list = [('0', 'Monday'),
             ('1', 'Tuesday'),
             ('2', 'Wednesday'),
             ('3', 'Thursday'),
             ('4', 'Friday'),
             ('5', 'Saturday'),
             ('6', 'Sunday')]


class HRPublicHolidays(models.Model):
    _name = 'hr.public.holidays'
    _description = 'Public Holidays'

    name = fields.Char(string='Description', related='year_list_id.name')
    year_list_id = fields.Many2one('payroll.year.list', string='Year')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    holidays_ids = fields.One2many(
        'hr.public.holidays.line', 'holiday_id', 'Holidays')
    department_ids = fields.Many2many('hr.department', string='Department')

    def public_holiday_mail(self):
        '''
        This method is used to send an email of Public Holidays to all employees.
        ------------------------------------------------------------------------
        '''
        active_user = self.env['res.users'].browse(self._uid)
        try:
            email_to = []
            template_id = self.env.ref(
                'hr_payroll_extended.public_holidays_email_template')
            emp_rec = self.env['hr.employee'].search([('work_email', '!=', '')])
            for emp in emp_rec:
                email_to.append(str(emp.work_email))
            join_emails = ','.join(email_to)
            template_id.write(
                {'email_from': active_user.partner_id.email,
                 'email_to': join_emails})
            template_id.send_mail(self.id, force_send=True)
        except ValueError:
            template_id = False

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



class HRPublicHolidaysLine(models.Model):
    _name = 'hr.public.holidays.line'
    _description = 'Public Holidays Line'

    date = fields.Date('Date')
    week_day = fields.Selection([('0', 'Monday'),
                                 ('1', 'Tuesday'),
                                 ('2', 'Wednesday'),
                                 ('3', 'Thursday'),
                                 ('4', 'Friday'),
                                 ('5', 'Saturday'),
                                 ('6', 'Sunday')], 'Weekday')
    name = fields.Char('Description')
    holiday_id = fields.Many2one(
        'hr.public.holidays', 'Public Holiday List')
    month = fields.Char("Month", compute='onchange_date')
    month_number = fields.Char("Month ")

    @api.depends('date')
    def onchange_date(self):
        """
        Auto select the weekday based on the date selected.
        ---------------------------------------------------
        @param self: object pointer
        """
        for line in self:
            if line.date:
                line.week_day = str(line.date.weekday())
                daten = datetime.datetime(1, int(line.date.month), 1).strftime("%B")
                line.month = daten
                line.month_number = line.date.month
            else:
                line.month = False
                line.month_number = False
