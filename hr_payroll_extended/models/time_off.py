from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'
    _description = 'Hr Leave Allocation'

    emp_code = fields.Integer(string="Employee Code")

    def refresh(self):
        for allocation in self:
            emp = self.env['hr.employee'].search([('emp_code', '=', allocation.emp_code)], limit=1)
            if allocation.holiday_type == 'employee':
                if allocation.emp_code == 0:
                    allocation.employee_ids = self.env.user.employee_id
                    allocation.employee_id = self.env.user.employee_id
                else:
                    allocation.employee_ids = [(6, 0, [emp.id])]
                    allocation.employee_id = emp.id
                allocation.mode_company_id = False
                allocation.category_id = False

    @api.depends('holiday_type', 'emp_code')
    def _compute_from_holiday_type(self):
        default_employee_ids = self.env['hr.employee'].browse(
            self.env.context.get('default_employee_id')) or self.env.user.employee_id
        emp = self.env['hr.employee'].search([('emp_code', '=', self.emp_code)], limit=1)
        for allocation in self:
            if allocation.holiday_type == 'employee':
                if allocation.emp_code == 0:
                    allocation.employee_ids = self.env.user.employee_id
                    allocation.employee_id = self.env.user.employee_id
                else:
                    allocation.employee_ids = [(6, 0, [emp.id])]
                    allocation.employee_id = emp.id
                allocation.mode_company_id = False
                allocation.category_id = False
            elif allocation.holiday_type == 'company':
                allocation.employee_ids = False
                if not allocation.mode_company_id:
                    allocation.mode_company_id = self.env.company
                allocation.category_id = False
            elif allocation.holiday_type == 'department':
                allocation.employee_ids = False
                allocation.mode_company_id = False
                allocation.category_id = False
            elif allocation.holiday_type == 'category':
                allocation.employee_ids = False
                allocation.mode_company_id = False
            else:
                allocation.employee_ids = default_employee_ids


#
class HrLeave(models.Model):
    _inherit = 'hr.leave'
    _description = 'Hr Leave Allocation'

    emp_code = fields.Integer(string="Employee Code")
    payslip_id = fields.Many2one('hr.payslip', ondelete='cascade', string='Payslip')
    request_unit_half = fields.Boolean('Half Day')
    request_unit_hours = fields.Boolean('Custom Hours', )

    @api.depends('holiday_status_id', 'request_unit_hours')
    def _compute_request_unit_half(self):
        pass

    @api.depends('holiday_status_id', 'request_unit_half')
    def _compute_request_unit_hours(self):
        pass

    @api.depends('holiday_type', 'emp_code', 'payslip_id')
    def _compute_from_holiday_type(self):
        for rec in self:
            allocation_from_domain = self.env['hr.leave.allocation']
            if (self._context.get('active_model') == 'hr.leave.allocation' and
                    self._context.get('active_id')):
                allocation_from_domain = allocation_from_domain.browse(self._context['active_id'])
            emp = self.env['hr.employee'].search([('emp_code', '=', rec.emp_code)], limit=1)
            for holiday in rec:
                if holiday.holiday_type == 'employee':
                    if holiday.payslip_id:
                        holiday.emp_code = holiday.payslip_id.emp_code
                        holiday.employee_ids = [(6, 0, [holiday.payslip_id.employee_id.id])]
                        holiday.employee_id = holiday.payslip_id.employee_id.id
                    elif holiday.emp_code == 0:
                        holiday.employee_ids = rec.env.user.employee_id
                        holiday.employee_id = rec.env.user.employee_id
                    else:
                        holiday.employee_ids = [(6, 0, [emp.id])]
                        holiday.employee_id = emp.id
                    if not holiday.employee_ids:
                        if allocation_from_domain:
                            holiday.employee_ids = allocation_from_domain.employee_id
                            holiday.holiday_status_id = allocation_from_domain.holiday_status_id
                        else:
                            # This handles the case where a request is made with only the employee_id
                            # but does not need to be recomputed on employee_id changes
                            holiday.employee_ids = holiday.employee_id or rec.env.user.employee_id
                    holiday.mode_company_id = False
                    holiday.category_id = False
                elif holiday.holiday_type == 'company':
                    holiday.employee_ids = False
                    if not holiday.mode_company_id:
                        holiday.mode_company_id = rec.env.company.id
                    holiday.category_id = False
                elif holiday.holiday_type == 'department':
                    holiday.employee_ids = False
                    holiday.mode_company_id = False
                    holiday.category_id = False
                elif holiday.holiday_type == 'category':
                    holiday.employee_ids = False
                    holiday.mode_company_id = False
                else:
                    holiday.employee_ids = rec.env.context.get(
                        'default_employee_id') or holiday.employee_id or rec.env.user.employee_id


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'
    _description = 'Hr Leave Type'

    @api.depends('requires_allocation', 'virtual_remaining_leaves', 'max_leaves', 'request_unit')
    @api.depends_context('holiday_status_display_name', 'employee_id', 'from_manager_leave_form')
    def _compute_display_name(self):
        if not self.requested_display_name():
            # leave counts is based on employee_id, would be inaccurate if not based on correct employee
            return super()._compute_display_name()
        for record in self:
            name = record.name
            if record.requires_allocation == "yes" and not self._context.get('from_manager_leave_form'):
                group = self.env.ref('hr_payroll_extended.group_leave_type_access')
                if record.env.uid in group.users.ids:
                    name = "{name} ({count})".format(
                        name=name,
                        count=_('%g remaining out of %g') % (
                            float_round(record.virtual_remaining_leaves, precision_digits=2) or 0.0,
                            float_round(record.max_leaves, precision_digits=2) or 0.0,
                        ) + (_(' hours') if record.request_unit == 'hour' else _(' days')),
                    )
                else:
                    name = "{name}".format(
                        name=name)
            record.display_name = name
