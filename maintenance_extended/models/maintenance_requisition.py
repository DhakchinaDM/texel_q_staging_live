from datetime import date
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError


class MaintenanceRequisition(models.Model):
    _name = 'maintenance.requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Maintenance Requisition'

    def _default_employee(self):
        emp_ids = self.sudo().env['hr.employee'].search([('user_id', '=', self.env.uid)])
        return emp_ids and emp_ids[0] or False

    name = fields.Char('', required=True)
    employee_id = fields.Many2one('hr.employee', string="Responsible")
    equipment_id = fields.Many2one('maintenance.equipment', string="Machine/Equipment")
    machine_id = fields.Char(string="Machine/Equipment Code")
    category_id = fields.Many2one('maintenance.equipment.category', string="Category",
                                  related='equipment_id.category_id')
    subcat_id = fields.Many2one('subcate.details', string="Sub Category")
    request_date = fields.Datetime("Request Date", default=lambda self: fields.Datetime.now(),)
    maintenance_team_id = fields.Many2one('maintenance.team', string='Team',
                                          related='equipment_id.maintenance_team_id')
    maintenance_type = fields.Selection([
        ('corrective', 'BreakDown'),
        ('preventive', 'Preventive'),
    ], string="Maintenance Type", required=True)
    user_id = fields.Many2one('res.users', string=" Responsible", default=lambda self: self.env.user)
    scheduled_date = fields.Datetime(string="Scheduled Date")
    priority = fields.Selection([
        ('0', 'Very Low'),
        ('1', 'Low'),
        ('2', 'Normal'),
        ('3', 'High'),
    ], string="Priority")
    description = fields.Html('Description')
    image = fields.Image(string="Image")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('request_approved', 'Approval Requested'),
        ('to_be_approved', 'Waiting 1st Level Approval'),
        ('leader_approval', 'Waiting 2nd Level Approval'),
        ('manager_approval', 'Waiting 3rd Level Approval'),
        ('director_approval', 'Waiting 4th Level Approval'),
        ('ceo_approval', 'Waiting 5th Level Approval'),
        ('approved', 'Approved'),
        ('maitenance_generated', 'Maintenance Request Generated'),
        ('reject', 'Reject'),
        ('cancel', 'Cancel'),
        ('done', 'Done'),
    ], string='Status', readonly=True, tracking=True, default='draft')
    # type_of_purchase = fields.Many2one('material.approval.config', string="Type Of Maintenance", copy=False,
    #                                    domain="[('approval_type','=', 'material_request')]",
    #                                    tracking=True)
    # approver1 = fields.Many2one('res.users', string="Approver 1", copy=False, tracking=True,
    #                             related='type_of_purchase.first_approval')
    # approver2 = fields.Many2one('res.users', string="Approver 2", copy=False, tracking=True,
    #                             related='type_of_purchase.second_approval')
    # approver3 = fields.Many2one('res.users', string="Approver 3", copy=False, tracking=True,
    #                             related='type_of_purchase.third_approval')
    # approver4 = fields.Many2one('res.users', string="Approver 4", copy=False, tracking=True,
    #                             related='type_of_purchase.fourth_approval')
    # approver5 = fields.Many2one('res.users', string="Approver 5", copy=False, tracking=True,
    #                             related='type_of_purchase.fifth_approval')
    # approval_stages = fields.Selection(string="No.of Approvals", related='type_of_purchase.approval_levels')
    request_code = fields.Char(string=" Request Code", default=lambda self: '/', readonly=True)
    maintenance_service_request_count = fields.Integer(string='Maintenance Request',
                                                       compute='maintenance_requisition_service_request_count')
    responsible = fields.Many2one('hr.employee', string='Request Raised By', default=_default_employee, readonly=True,
                                  help="Responsible person for the Maintenance Request")
    department_id = fields.Many2one(string='Department', related='responsible.department_id', required=True,
                                    readonly=True, tracking=True)
    current_job_id = fields.Many2one(related='responsible.job_id', string="Job Position", required=True)
    current_reporting_manager = fields.Many2one(related='responsible.parent_id', string="Reporting Manager")
    purpose = fields.Char('Purpose', required=True, tracking=True)
    requester_department_id = fields.Many2one('hr.department', string=' Department', required=True, tracking=True)
    requester_current_job_id = fields.Many2one('hr.job', string=" Job Position", required=True)
    requester_current_reporting_manager = fields.Many2one('hr.employee', string=" Reporting Manager",
                                                          required=True)
    approver1_reject_reason = fields.Text('1st Approver Reject Remarks')
    approver2_reject_reason = fields.Text('2nd Approver Reject Remarks')
    approver3_reject_reason = fields.Text('3rd Approver Reject Remarks')
    approver4_reject_reason = fields.Text('4th Approver Reject Remarks')
    approver5_reject_reason = fields.Text('5th Approver Reject Remarks')
    approver1_cancel_reason = fields.Text('1st Approver Cancel Remarks')
    approver2_cancel_reason = fields.Text('2nd Approver Cancel Remarks')
    approver3_cancel_reason = fields.Text('3rd Approver Cancel Remarks')
    approver4_cancel_reason = fields.Text('4th Approver Cancel Remarks')
    approver5_cancel_reason = fields.Text('5th Approver Cancel Remarks')
    approver1_approve_reason = fields.Text('1st Approver Approval Remarks')
    approver2_approve_reason = fields.Text('2nd Approver Approval Remarks')
    approver3_approve_reason = fields.Text('3rd Approver Approval Remarks')
    approver4_approve_reason = fields.Text('4th Approver Approval Remarks')
    approver5_approve_reason = fields.Text('5th Approver Approval Remarks')

    @api.onchange('employee_id')
    def requester_details(self):
        if self.employee_id:
            self.sudo().write({
                'requester_current_reporting_manager': self.employee_id.parent_id.id,
                'requester_department_id': self.employee_id.department_id.id,
                'requester_current_job_id': self.employee_id.job_id.id,
            })

    @api.onchange('equipment_id')
    def equipments_id(self):
        if self.equipment_id:
            self.image = self.equipment_id.image
            self.machine_id = self.equipment_id.codefor
            if self.equipment_id.equipment_assign_to == 'employee':
                self.employee_id = self.equipment_id.employee_id.id

    def maintenance_requisition_service_request_count(self):
        self.maintenance_service_request_count = self.env['maintenance.request'].sudo().search_count(
            [('reference', '=', self.request_code)])

    def maintenance_requisition_service_request_view(self):
        # if self.service_order_count > 0:
        self.sudo().ensure_one()
        context = dict(self._context or {})
        active_model = context.get('active_model')
        form_view = self.sudo().env.ref('maintenance.hr_equipment_request_view_form')
        tree_view = self.sudo().env.ref('maintenance.hr_equipment_request_view_tree')
        return {
            'name': _('Maintenance Requisition'),
            'res_model': 'maintenance.request',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('reference', '=', self.request_code)],
        }

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.sudo().env['ir.sequence'].next_by_code('maintenance.requisition') or '/'
        return super().create(vals_list)

    # @api.onchange('type_of_purchase')
    # def approval_details(self):
    #     if self.type_of_purchase:
    #         self.sudo().write({
    #             'approval_stages': self.type_of_purchase.approval_levels,
    #         })

    @api.depends('state')
    def compute_approver(self):
        for order in self:
            if order.approval_stages == 'first_level':
                order.approval_responsible = order.approver1
            elif order.approval_stages == 'second_level':
                if order.state in ('draft', 'to_be_approved'):
                    order.approval_responsible = order.approver1
                elif order.state == 'leader_approval':
                    order.approval_responsible = order.approver2
            elif order.approval_stages == 'third_level':
                if order.state in ('draft', 'to_be_approved'):
                    order.approval_responsible = order.approver1
                elif order.state == 'leader_approval':
                    order.approval_responsible = order.approver2
                elif order.state == 'manager_approval':
                    order.approval_responsible = order.approver3

    def reject(self):
        for indent in self:
            indent.write({
                'state': 'reject',
            })

    def cancel(self):
        for indent in self:
            indent.write({
                'state': 'cancel',
            })

    def approve(self):
        for indent in self:
            indent.write({
                'state': 'approved',
            })

    def apply_approval(self):
        for indent in self:
            indent.button_leader_approval()

    def indent_confirm(self):
        for indent in self:
            indent.write({
                'state': 'to_be_approved',
            })

    def maintenance_request(self):
        maintenance_create = self.sudo().env['maintenance.request'].sudo().create({
            'name': self.name,
            'employee_id': self.employee_id.id,
            'equipment_id': self.equipment_id.id,
            'machine_id': self.machine_id,
            'category_id': self.category_id.id,
            'subcat_id': self.subcat_id.id,
            'request_date': self.request_date,
            'maintenance_type': self.maintenance_type,
            'description': self.description,
            'maintenance_team_id': self.maintenance_team_id.id,
            'user_id': self.user_id.id,
            'schedule_date': self.scheduled_date,
            'priority': self.priority,
            'reference': self.request_code,
        })
        self.write({'state':'maitenance_generated'})
        return maintenance_create

    def set_approval(self):
        self.write({'state': 'approved'})

    # Maintenance Approve Process based on Num of Approvers to trigger each Process
    def button_approval(self):
        if self.state == 'to_be_approved':
            if self.approval_stages == 'first_level':
                if self.approver1.id == self._uid:
                    self.set_approval()
                else:
                    raise UserError(
                        _('Alert !, Mr.%s You Cannot allowed For the First approval of %s Maintenance Requisition.') %
                        (self.env.user.name, self.name))
        if self.state == 'leader_approval':
            if self.approval_stages == 'second_level':
                if self.approver2.id == self._uid:
                    self.set_approval()
                else:
                    raise UserError(
                        _('Alert !, Mr.%s You Cannot allowed For the Second approval of %s Maintenance Requisition.') %
                        (self.env.user.name, self.name))
        if self.state == 'manager_approval':
            if self.approval_stages == 'third_level':
                if self.approver3.id == self._uid:
                    self.set_approval()
                else:
                    raise UserError(
                        _('Alert !, Mr.%s You Cannot allowed For the Third approval of %s Maintenance Requisition.') %
                        (self.env.user.name, self.name))
        if self.state == 'director_approval':
            if self.approval_stages == 'fourth_level':
                if self.approver4.id == self._uid:
                    self.set_approval()
                else:
                    raise UserError(
                        _('Alert !, Mr.%s You Cannot allowed For the Fourth approval of %s Maintenance Requisition.') %
                        (self.env.user.name, self.name))

    def button_leader_approval(self):
        if self.state == 'to_be_approved':
            if self.approval_stages == 'first_level':
                self.button_approval()
            elif self.approval_stages != ('first_level', 'second_level', 'third_level', 'fourth_level'):
                if self.approver1.id == self._uid or self.approver2.id == self._uid \
                        or self.approver3.id == self._uid or self.approver4.id == self._uid or self.approver5.id == self._uid:
                    if self.approver1.id == self._uid:
                        self.write({'state': 'leader_approval'})
                    elif self.approver2.id == self._uid:
                        self.state = 'manager_approval'
                    elif self.approver3.id == self._uid:
                        self.state = 'director_approval'
                    elif self.approver4.id == self._uid:
                        self.state = 'ceo_approval'
                    elif self.approver5.id == self._uid:
                        self.state = 'approved'
                else:
                    raise UserError(_('Alert !, Mr.%s You Cannot allowed to approve this %s Maintenance Requisition.') %
                                    (self.env.user.name, self.name))
        elif self.state == 'leader_approval':
            if self.approval_stages == 'second_level':
                self.button_approval()
            elif self.approval_stages != ('second_level', 'third_level', 'fourth_level'):
                if self.approver2.id == self._uid or self.approver3.id == self._uid \
                        or self.approver4.id == self._uid or self.approver5.id == self._uid:
                    self.state = 'manager_approval'
                elif self.approver3.id == self._uid:
                    self.state = 'director_approval'
                elif self.approver4.id == self._uid:
                    self.state = 'ceo_approval'
                elif self.approver5.id == self._uid:
                    self.state = 'approved'
                else:
                    raise UserError(_('Alert !, Mr.%s You Cannot allowed to approve this %s Maintenance Requisition.') %
                                    (self.env.user.name, self.name))
        elif self.state == 'manager_approval':
            if self.approval_stages == 'third_level':
                self.button_approval()
            elif self.approval_stages != ('third_level', 'fourth_level'):
                if self.approver3.id == self._uid or self.approver4.id == self._uid or self.approver5.id == self._uid:
                    self.state = 'director_approval'
                elif self.approver4.id == self._uid:
                    self.state = 'ceo_approval'
                elif self.approver5.id == self._uid:
                    self.state = 'approved'
                else:
                    raise UserError(_('Alert !, Mr.%s You Cannot allowed to approve this %s Maintenance Requisition.') %
                                    (self.env.user.name, self.name))
        elif self.state == 'director_approval':
            if self.approval_stages == 'fourth_level':
                self.button_approval()
            elif self.approval_stages != ('fourth_level'):
                if self.approver4.id == self._uid or self.approver5.id == self._uid:
                    if self.approver4.id:
                        self.state = 'ceo_approval'
                    elif self.approver5.id == self._uid:
                        self.state = 'approved'
                else:
                    raise UserError(_('Alert !, Mr.%s You Cannot allowed to approve this %s Maintenance Requisition.') %
                                    (self.env.user.name, self.name))
        elif self.state == 'ceo_approval':
            if self.approver5.id == self._uid:
                self.state = 'approved'
            else:
                raise UserError(_('Alert !, Mr.%s You Cannot allowed to approve this %s Maintenance Requisition.') %
                                (self.env.user.name, self.name))
        return True

    def button_reject(self):
        if self.state == 'to_be_approved':
            if self.approval_stages == 'first_level':
                if self.approver1.id == self._uid:
                    self.indent_reject()
                else:
                    raise UserError(_('Alert !, Mr.%s You Cannot allowed to Reject The %s Maintenance Requisition.') %
                                    (self.env.user.name, self.name))
        if self.state == 'leader_approval':
            if self.approval_stages == 'second_level':
                if self.approver2.id == self._uid:
                    self.indent_reject()
                else:
                    raise UserError(
                        _('Alert !, Mr.%s You Cannot allowed to Reject The %s Maintenance Requisition.') %
                        (self.env.user.name, self.name))
        if self.state == 'manager_approval':
            if self.approval_stages == 'third_level':
                if self.approver3.id == self._uid:
                    self.indent_reject()
                else:
                    raise UserError(
                        _('Alert !, Mr.%s You Cannot allowed to Reject The %s Maintenance Requisition.') %
                        (self.env.user.name, self.name))
        if self.state == 'director_approval':
            if self.approval_stages == 'fourth_level':
                if self.approver4.id == self._uid:
                    self.indent_reject()
                else:
                    raise UserError(
                        _('Alert !, Mr.%s You Cannot allowed to Reject The %s Maintenance Requisition.') %
                        (self.env.user.name, self.name))

    def indent_reject(self):
        for indent in self:
            self.indent({
                'state': 'reject', })

    def indent_cancel(self):
        for indent in self:
            self.indent({
                'state': 'cancel', })

    def button_leader_reject(self):
        if self.state == 'to_be_approved':
            if self.approval_stages == 'first_level':
                self.button_reject()
            elif self.approval_stages != ('first_level', 'second_level', 'third_level', 'fourth_level'):
                if self.approver1.id == self._uid or self.approver2.id == self._uid \
                        or self.approver3.id == self._uid or self.approver4.id == self._uid or self.approver5.id == self._uid:
                    if self.approver1.id == self._uid:
                        self.indent_reject()
                    elif self.approver2.id == self._uid:
                        self.indent_reject()
                    elif self.approver3.id == self._uid:
                        self.indent_reject()
                    elif self.approver4.id == self._uid:
                        self.indent_reject()
                    elif self.approver5.id == self._uid:
                        self.indent_reject()
                else:
                    raise UserError(_('Alert !, Mr.%s You Cannot allowed to Reject The %s Maintenance Requisition.') %
                                    (self.env.user.name, self.name))
        elif self.state == 'leader_approval':
            if self.approval_stages == 'second_level':
                self.button_reject()
            elif self.approval_stages != ('second_level', 'third_level', 'fourth_level'):
                if self.approver2.id == self._uid or self.approver3.id == self._uid \
                        or self.approver4.id == self._uid or self.approver5.id == self._uid:
                    self.indent_reject()
                elif self.approver3.id == self._uid:
                    self.indent_reject()
                elif self.approver4.id == self._uid:
                    self.indent_reject()
                elif self.approver5.id == self._uid:
                    self.indent_reject()
                else:
                    raise UserError(_('Alert !, Mr.%s You Cannot allowed to Reject The %s Maintenance Requisition.') %
                                    (self.env.user.name, self.name))
        elif self.state == 'manager_approval':
            if self.approval_stages == 'third_level':
                self.indent_reject()
            elif self.approval_stages != ('third_level', 'fourth_level'):
                if self.approver3.id == self._uid or self.approver4.id == self._uid or self.approver5.id == self._uid:
                    self.indent_reject()
                elif self.approver4.id == self._uid:
                    self.indent_reject()
                elif self.approver5.id == self._uid:
                    self.indent_reject()
                else:
                    raise UserError(_('Alert !, Mr.%s You Cannot allowed to Reject The %s Maintenance Requisition.') %
                                    (self.env.user.name, self.name))
        elif self.state == 'director_approval':
            if self.approval_stages == 'fourth_level':
                self.button_reject()
            elif self.approval_stages != ('fourth_level'):
                if self.approver4.id == self._uid or self.approver5.id == self._uid:
                    self.indent_reject()
                elif self.approver5.id == self._uid:
                    self.indent_reject()
                else:
                    raise UserError(_('Alert !, Mr.%s You Cannot allowed to Reject The %s Maintenance Requisition.') %
                                    (self.env.user.name, self.name))
        elif self.state == 'ceo_approval':
            if self.approver5.id == self._uid:
                self.button_reject()
            else:
                raise UserError(_('Alert !, Mr.%s You Cannot allowed to Reject The %s Maintenance Requisition.') %
                                (self.env.user.name, self.name))
        return True

    def button_cancels(self):
        if self.state == 'to_be_approved':
            if self.approval_stages == 'first_level':
                if self.approver1.id == self._uid:
                    self.indent_cancel()
                else:
                    raise UserError(_('Alert !, Mr.%s You Cannot allowed to Cancel The %s Maintenance Requisition.') %
                                    (self.env.user.name, self.name))
        if self.state == 'leader_approval':
            if self.approval_stages == 'second_level':
                if self.approver2.id == self._uid:
                    self.indent_cancel()
                else:
                    raise UserError(
                        _('Alert !, Mr.%s You Cannot allowed to Cancel The %s Maintenance Requisition.') %
                        (self.env.user.name, self.name))
        if self.state == 'manager_approval':
            if self.approval_stages == 'third_level':
                if self.approver3.id == self._uid:
                    self.indent_cancel()
                else:
                    raise UserError(
                        _('Alert !, Mr.%s You Cannot allowed to Cancel The %s Maintenance Requisition.') %
                        (self.env.user.name, self.name))
        if self.state == 'director_approval':
            if self.approval_stages == 'fourth_level':
                if self.approver4.id == self._uid:
                    self.indent_cancel()
                else:
                    raise UserError(
                        _('Alert !, Mr.%s You Cannot allowed to Cancel The %s Maintenance Requisition.') %
                        (self.env.user.name, self.name))

    def button_leader_cancel(self):
        if self.state == 'to_be_approved':
            if self.approval_stages == 'first_level':
                self.button_cancels()
            elif self.approval_stages != ('first_level', 'second_level', 'third_level', 'fourth_level'):
                if self.approver1.id == self._uid or self.approver2.id == self._uid \
                        or self.approver3.id == self._uid or self.approver4.id == self._uid or self.approver5.id == self._uid:
                    if self.approver1.id == self._uid:
                        self.indent_cancel()
                    elif self.approver2.id == self._uid:
                        self.indent_cancel()
                    elif self.approver3.id == self._uid:
                        self.indent_cancel()
                    elif self.approver4.id == self._uid:
                        self.indent_cancel()
                    elif self.approver5.id == self._uid:
                        self.indent_cancel()
                else:
                    raise UserError(_('Alert !, Mr.%s You Cannot allowed to Cancel The %s Maintenance Requisition.') %
                                    (self.env.user.name, self.name))
        elif self.state == 'leader_approval':
            if self.approval_stages == 'second_level':
                self.button_cancels()
            elif self.approval_stages != ('second_level', 'third_level', 'fourth_level'):
                if self.approver2.id == self._uid or self.approver3.id == self._uid \
                        or self.approver4.id == self._uid or self.approver5.id == self._uid:
                    self.indent_cancel()
                elif self.approver3.id == self._uid:
                    self.indent_cancel()
                elif self.approver4.id == self._uid:
                    self.indent_cancel()
                elif self.approver5.id == self._uid:
                    self.indent_cancel()
                else:
                    raise UserError(_('Alert !, Mr.%s You Cannot allowed to Cancel The %s Maintenance Requisition.') %
                                    (self.env.user.name, self.name))
        elif self.state == 'manager_approval':
            if self.approval_stages == 'third_level':
                self.indent_cancel()
            elif self.approval_stages != ('third_level', 'fourth_level'):
                if self.approver3.id == self._uid or self.approver4.id == self._uid or self.approver5.id == self._uid:
                    self.indent_cancel()
                elif self.approver4.id == self._uid:
                    self.indent_cancel()
                elif self.approver5.id == self._uid:
                    self.indent_cancel()
                else:
                    raise UserError(_('Alert !, Mr.%s You Cannot allowed to Cancel The %s Maintenance Requisition.') %
                                    (self.env.user.name, self.name))
        elif self.state == 'director_approval':
            if self.approval_stages == 'fourth_level':
                self.button_cancels()
            elif self.approval_stages != ('fourth_level'):
                if self.approver4.id == self._uid or self.approver5.id == self._uid:
                    self.indent_cancel()
                elif self.approver5.id == self._uid:
                    self.indent_cancel()
                else:
                    raise UserError(_('Alert !, Mr.%s You Cannot allowed to Cancel The %s Maintenance Requisition.') %
                                    (self.env.user.name, self.name))
        elif self.state == 'ceo_approval':
            if self.approver5.id == self._uid:
                self.button_cancels()
            else:
                raise UserError(_('Alert !, Mr.%s You Cannot allowed to Cancel The %s Maintenance Requisition.') %
                                (self.env.user.name, self.name))
        return True

    def maintenance_requisition_approve_remarks(self):
        view_id = self.env['maintenance.requisition.approve.remarks']
        return {
            'type': 'ir.actions.act_window',
            'name': 'Maintenance Requisition Approval Remarks',
            'res_model': 'maintenance.requisition.approve.remarks',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': view_id.id,
            'view_id': self.env.ref('maintenance_extended.maintenance_requisition_approve_remarks_wizard', False).id,
            'target': 'new',
        }

    def maintenance_requisition_reject_remarks(self):
        view_id = self.env['maintenance.requisition.reject.remarks']
        return {
            'type': 'ir.actions.act_window',
            'name': 'Maintenance Requisition Reject Remarks',
            'res_model': 'maintenance.requisition.reject.remarks',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': view_id.id,
            'view_id': self.env.ref('maintenance_extended.maintenance_requisition_reject_remarks_wizard', False).id,
            'target': 'new',
        }

    def maintenance_requisition_cancel_remarks(self):
        view_id = self.env['maintenance.requisition.cancel.remarks']
        return {
            'type': 'ir.actions.act_window',
            'name': 'Maintenance Requisition Cancel Remarks',
            'res_model': 'maintenance.requisition.cancel.remarks',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': view_id.id,
            'view_id': self.env.ref('maintenance_extended.maintenance_requisition_cancel_remarks_wizard', False).id,
            'target': 'new',
        }


class MaintenanceRequisitionApproveRemarks(models.TransientModel):
    _name = 'maintenance.requisition.approve.remarks'
    _description = 'Maintenance Requisition Approve Remarks'
    _inherit = ['mail.thread']

    remarks = fields.Text('Remarks')
    is_default_remark = fields.Boolean('Enable Default Remark')
    default_remark = fields.Text('Default Remark',
                                 default='Maintenance Requisition Approval get confirmed Without Remarks.')

    @api.onchange("is_default_remark")
    def _onchange_is_default_remark(self):
        for val in self:
            if val.is_default_remark == True:
                val.remarks = val.default_remark
            else:
                val.remarks = ''

    def tick_ok(self):
        applicant_id = self._context.get('active_ids')[0]
        active_id = self.env['maintenance.requisition'].search([('id', '=', applicant_id)])
        today = date.today()
        current_date = today.strftime("%d/%m/%Y")
        current_user = self.env.user.name

        if active_id.state == 'to_be_approved':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_approval()
            active_id.write({'approver1_approve_reason': text})
        elif active_id.state == 'leader_approval':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_approval()
            active_id.write({'approver2_approve_reason': text})
        elif active_id.state == 'manager_approval':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_approval()
            active_id.write({'approver3_approve_reason': text})
        elif active_id.state == 'director_approval':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_approval()
            active_id.write({'approver4_approve_reason': text})
        elif active_id.state == 'ceo_approval':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_approval()
            active_id.write({'approver5_approve_reason': text})
        return True


class MaintenanceRequisitionRejectRemarks(models.TransientModel):
    _name = 'maintenance.requisition.reject.remarks'
    _description = 'Maintenance Requisition Reject Remarks'
    _inherit = ['mail.thread']

    remarks = fields.Text('Remarks')

    def tick_ok(self):
        applicant_id = self._context.get('active_ids')[0]
        active_id = self.env['maintenance.requisition'].search([('id', '=', applicant_id)])
        today = date.today()
        current_date = today.strftime("%d/%m/%Y")
        current_user = self.env.user.name

        if active_id.state == 'to_be_approved':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_rejection()
            active_id.write({'approver1_reject_reason': text})
        elif active_id.state == 'leader_approval':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_rejection()
            active_id.write({'approver2_reject_reason': text})
        elif active_id.state == 'manager_approval':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_rejection()
            active_id.write({'approver3_reject_reason': text})
        elif active_id.state == 'director_approval':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_rejection()
            active_id.write({'approver4_reject_reason': text})
        elif active_id.state == 'ceo_approval':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_rejection()
            active_id.write({'approver5_reject_reason': text})
        return True


class MaintenanceRequisitionCancelRemarks(models.TransientModel):
    _name = 'maintenance.requisition.cancel.remarks'
    _description = 'Maintenance Requisition Cancel Remarks'
    _inherit = ['mail.thread']

    remarks = fields.Text('Remarks')

    def tick_ok(self):
        applicant_id = self._context.get('active_ids')[0]
        active_id = self.env['maintenance.requisition'].search([('id', '=', applicant_id)])
        today = date.today()
        current_date = today.strftime("%d/%m/%Y")
        current_user = self.env.user.name

        if active_id.state == 'to_be_approved':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_cancellation()
            active_id.write({'approver1_cancel_reason': text})
        elif active_id.state == 'leader_approval':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_cancellation()
            active_id.write({'approver2_cancel_reason': text})
        elif active_id.state == 'manager_approval':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_cancellation()
            active_id.write({'approver3_cancel_reason': text})
        elif active_id.state == 'director_approval':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_cancellation()
            active_id.write({'approver4_cancel_reason': text})
        elif active_id.state == 'ceo_approval':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_cancellation()
            active_id.write({'approver5_cancel_reason': text})
        return True
