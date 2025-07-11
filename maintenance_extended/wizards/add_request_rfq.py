from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError


class HrEmployeeCreate(models.TransientModel):
    _name = "hr.employee.request.create"
    _description = 'Hr Employee Create'

    def _default_employee(self):
        emp_ids = self.sudo().env['hr.employee'].search([('user_id', '=', self.env.uid)])
        return emp_ids and emp_ids[0] or False

    partner_ids = fields.Many2many('res.partner', string="Supplier name")
    service_name = fields.Char(string="Reason For Service", help="Service name")
    maintenance_service_order_ref = fields.Char(string="Reference")
    order_lines = fields.One2many('hr.employee.create.request.line', 'line_order_id', string='Order Lines')
    purchase_order_type = fields.Selection([
        ('create_rfq', 'Create Service Order')
    ], copy=False, string="Order Type", default='create_rfq')
    equipment_service_id = fields.Many2one('equipment.support.details', string=" Service Type")
    equipment_service_category = fields.Selection([
        ('internal_service', ' Internal Service'),
        ('external_service', 'External Service')], string="Service Category", default='internal_service')
    equipment_id = fields.Many2one('maintenance.equipment', string='Equipment id')
    machine = fields.Char(string="Equipment Name", related='equipment_id.name')
    category = fields.Many2one('maintenance.equipment.category', string="Category",
                               related='equipment_id.category_id', store=True)
    sub_category = fields.Many2one('subcate.details', string="Subcategory", related='equipment_id.subcategory_id',
                                   store=True)
    service_limit = fields.Integer("Service Limit")
    wiz_service_period = fields.Char(string="Service Name")
    first_service_wiz = fields.Integer(string="1'st Service Period")
    first_expire_period_wiz = fields.Integer(string="1'st Expire Period")
    registered_wiz = fields.Char(string="Registered Date")
    comppleted_wiz = fields.Char(string="Completed Date")
    first_service_date_wiz = fields.Char(string="Service Date")
    first_service_expire_wiz = fields.Char(string="Expire Date")
    responsible_wiz = fields.Char(string="Responsible Person")
    responsible_wiz_company = fields.Char(string="Responsible Person Company")
    service_code_wiz = fields.Char(string="Service Period Code")
    service_limit_wiz = fields.Integer(string=" Service Limit")
    service_utilised_wiz = fields.Integer(string="Service Utilized")
    service_remaining_wiz = fields.Integer(string="Service Remaining")
    period_type = fields.Selection([
        ('day', '/Days')
    ], default="day")
    requested_for = fields.Many2one('res.users', string="Requested For")
    requested_by = fields.Many2one('hr.employee', string="Requested By")
    responsible = fields.Many2one('hr.employee', string='Request Raised By', default=_default_employee, readonly=True,
                                  help="Responsible person for the Material Request")
    department_id = fields.Many2one('hr.department', string='Department', readonly=True,
                                    compute='_compute_responsible_details')
    current_job_id = fields.Many2one('hr.job', string="Job Position", compute='_compute_responsible_details')
    current_reporting_manager = fields.Many2one('hr.employee', string="Reporting Manager",
                                                compute='_compute_responsible_details')
    request_raised_for = fields.Many2one('hr.employee', string='Request Raised For',
                                         help="Request person for the Material")
    requester_department_id = fields.Many2one('hr.department', string=' Department')
    requester_current_job_id = fields.Many2one('hr.job', string=" Job Position")
    requester_current_reporting_manager = fields.Many2one('hr.employee', string=" Reporting Manager")
    purpose = fields.Char('Purpose')
    location_id = fields.Many2one('stock.location', 'Destination Location')
    requirement = fields.Selection([('1', 'Ordinary'), ('2', 'Urgent')], 'Requirement')
    required_date = fields.Datetime('Required Date')
    no_of_days_after = fields.Integer(string='No-of-Days After', default=1)
    indent_date = fields.Datetime('Indent Date', readonly=True,
                                  default=lambda self: fields.Datetime.now())
    cost_estimation_ids = fields.One2many('hr.employee.create.estimate.line', 'service_request_id',
                                          string='Cost Estimation Lines')
    complement_service = fields.Boolean(string="Complement Service")
    service_type = fields.Selection(related='equipment_service_id.service_type', string="Service Type")

    @api.depends('responsible')
    def _compute_responsible_details(self):
        for i in self:
            if i.responsible:
                i.write({
                    'department_id': i.responsible.department_id.id,
                    'current_job_id': i.responsible.job_id.id,
                    'current_reporting_manager': i.responsible.parent_id.id,
                })
            else:
                i.write({
                    'department_id': False,
                    'current_job_id': False,
                    'current_reporting_manager': False,
                })

    @api.onchange('required_date', 'indent_date', 'no_of_days_after')
    def get_required_date(self):
        if self.indent_date and self.no_of_days_after:
            self.required_date = self.indent_date + timedelta(days=self.no_of_days_after)
        if self.required_date:
            if self.required_date <= self.indent_date or self.no_of_days_after == 0:
                raise ValidationError(("Alert!,Mr. %s. The Num of Days should be greaterthan Zero and,"
                                       " \n The Required Date should be Graterthan than Current Date.") \
                                      % (self.env.user.name))

    @api.onchange('request_raised_for')
    def requester_details(self):
        if self.request_raised_for:
            self.sudo().write({
                'requester_current_reporting_manager': self.request_raised_for.parent_id.id,
                'requester_department_id': self.request_raised_for.department_id.id,
                'requester_current_job_id': self.request_raised_for.job_id.id,
            })

    @api.onchange("equipment_service_id")
    def service_details_wizard(self):
        equipment_support = self.env['equipment.support.details'].sudo().search(
            [('name', '=', self.equipment_service_id.name)])
        first_check = self.equipment_service_id.first_service_completed
        second_check = self.equipment_service_id.second_service_completed
        third_check = self.equipment_service_id.third_service_completed
        first_date = self.equipment_service_id.first_expire_date
        second_date = self.equipment_service_id.second_expire_date
        third_date = self.equipment_service_id.third_expire_date
        # first_service_date = self.equipment_service_id.first_service_date
        cur_dateandtime = datetime.now()
        cur_date = cur_dateandtime.date()
        first_seq_code = self.equipment_service_id.service_period_code_one
        second_seq_code = self.equipment_service_id.service_period_code_two
        third_seq_code = self.equipment_service_id.service_period_code_three
        service_count = self.equipment_service_id.maintenance_service_stages
        if self.equipment_service_id:
            if first_check == False and first_seq_code and first_date >= cur_date:
                self.wiz_service_period = self.equipment_service_id.service_period_id
                self.first_service_wiz = self.equipment_service_id.service_period
                self.registered_wiz = self.equipment_service_id.registered_date
                self.first_service_date_wiz = self.equipment_service_id.first_service_date
                self.first_service_expire_wiz = self.equipment_service_id.first_expire_date
                self.responsible_wiz = self.equipment_service_id.first_service_responsible
                self.responsible_wiz_company = self.equipment_service_id.responsible_person_company
                self.service_code_wiz = self.equipment_service_id.service_period_code_one
                self.service_limit_wiz = self.equipment_service_id.free_service_limit
                self.service_utilised_wiz = self.equipment_service_id.free_service_limit_used
                self.service_remaining_wiz = self.equipment_service_id.free_service_remaining_limit
            if first_check == True and second_check == False and second_date >= cur_date and second_seq_code:
                self.wiz_service_period = self.equipment_service_id.service_period_second
                self.first_service_wiz = self.equipment_service_id.second_service_period
                self.registered_wiz = self.equipment_service_id.second_registered_date
                self.comppleted_wiz = self.equipment_service_id.second_completed_date
                self.first_service_date_wiz = self.equipment_service_id.second_service_date
                self.first_service_expire_wiz = self.equipment_service_id.second_expire_date
                self.responsible_wiz = self.equipment_service_id.second_service_responsible
                self.responsible_wiz_company = self.equipment_service_id.responsible_person_company_two
                self.service_code_wiz = self.equipment_service_id.service_period_code_two
                self.service_limit_wiz = self.equipment_service_id.free_service_limit
                self.service_utilised_wiz = self.equipment_service_id.free_service_limit_used
                self.service_remaining_wiz = self.equipment_service_id.free_service_remaining_limit
            if first_check == True and second_check == True and third_check == False and third_date >= cur_date and third_seq_code:
                self.wiz_service_period = self.equipment_service_id.service_period_third
                self.first_service_wiz = self.equipment_service_id.third_service_period
                self.registered_wiz = self.equipment_service_id.third_registered_date
                self.first_service_date_wiz = self.equipment_service_id.third_service_date
                self.first_service_expire_wiz = self.equipment_service_id.third_expire_date
                self.responsible_wiz = self.equipment_service_id.third_service_responsible
                self.responsible_wiz_company = self.equipment_service_id.responsible_person_company_three
                self.service_code_wiz = self.equipment_service_id.service_period_code_three
                self.service_limit_wiz = self.equipment_service_id.free_service_limit
                self.service_utilised_wiz = self.equipment_service_id.free_service_limit_used
                self.service_remaining_wiz = self.equipment_service_id.free_service_remaining_limit
            if first_check == True and second_check == True and third_check == True and \
                    equipment_support.complement_service == False:
                raise ValidationError(("The External Service of %s, has no Service Limit to Use, \n"
                                       "Service Limits are  Utilized %s services.") \
                                      % (self.equipment_service_id.name, service_count))

    def get_service_order_line_items(self):
        line_vals = []
        for line in self.order_lines:
            if line:
                vals = [0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_qty,
                    'product_uom': line.product_uom_id.id,
                    'product_available': line.on_hand_qty,
                    'short_close': False,
                    'approved_product_uom_qty': False,
                }]
                line_vals.append(vals)
        return line_vals

    def get_service_estimation_order_line_items(self):
        line_vals = []
        for line in self.cost_estimation_ids:
            if line:
                vals = [0, 0, {
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'cost_estimation_type': line.cost_estimation_type,
                    'unit_price': line.unit_price,
                    'product_uom': line.product_uom.id,
                    'sub_total': line.sub_total,
                    'description': line.description,
                }]
                line_vals.append(vals)
        return line_vals

    # def create_new_transfer_contract(self):
    #     active_id = self.env.context.get('active_id', False)
    #     indent_id = self.env['maintenance.request'].search([('id', '=', active_id)])
    #     for line_value in self.order_lines:
    #         if line_value.product_qty == 0:
    #             raise ValidationError('Alert!!,  Mr.%s ,  '
    #                                   '\n Please Enter the Unit Price For the Product %s .' % (
    #                                       self.env.user.name, line_value.product_id.name))
    #     contract = self.env['material.requisition.indent'].create({
    #         'origin': self.maintenance_service_order_ref,
    #         'equipment_name': self.machine,
    #         'responsible': self.responsible.id,
    #         'department_id': self.department_id.id,
    #         'current_job_id': self.current_job_id.id,
    #         'current_reporting_manager': self.current_reporting_manager.id,
    #         'purpose': self.purpose,
    #         'location_id': self.location_id.id,
    #         'request_raised_for': self.request_raised_for.id,
    #         'requester_department_id': self.requester_department_id.id,
    #         'requester_current_job_id': self.requester_current_job_id.id,
    #         'requester_current_reporting_manager': self.requester_current_reporting_manager.id,
    #         'indent_date': self.indent_date,
    #         'required_date': self.required_date,
    #         'requirement': self.requirement,
    #         'order_type': 'service_order',
    #         'state': 'draft',
    #         'cron_Boolean': True,
    #         'store_request': True,
    #         'ribbon_state': 'store_to_verify',
    #         'request_product_lines': self.get_service_order_line_items(),
    #     })
    #     contract.write({
    #         'state': 'request_approved_store',
    #         'store_approval': True,
    #         'ribbon_state': 'store_verified',
    #     })
    #     indent_id.write({
    #         'service_order_generate': True,
    #         'material_requisition': contract.id,
    #     })
    #     return contract

    @api.onchange('equipment_service_id')
    def onchange_equipment_service_id(self):
        if self.equipment_service_id and self.equipment_service_id.first_service_enable:
            self.sudo().write({
                'wiz_service_period': self.equipment_service_id.service_period_id,
                'complement_service': self.equipment_service_id.complement_service,
                'first_service_wiz': self.equipment_service_id.service_period,
                'registered_wiz': self.equipment_service_id.registered_date,
                'first_service_date_wiz': self.equipment_service_id.first_service_date,
                'first_service_expire_wiz': self.equipment_service_id.first_expire_date,
                'responsible_wiz': self.equipment_service_id.first_service_responsible,
                'responsible_wiz_company': self.equipment_service_id.responsible_person_company,
                'service_code_wiz': self.equipment_service_id.service_period_code_one,
            })

    # def open_equipment_service_form(self):
    #     service_request = self.env['service.request']
    #     obj_purchase_order = self.env['maintenance.request']
    #     if self.env.context.get('active_model') == 'maintenance.request':
    #         active_id = self.env.context.get('active_id', False)
    #         indent_id = self.env['maintenance.request'].search([('id', '=', active_id)])
    #
    #         purchase_order_dict = {'origin': indent_id.name,
    #                                'indent_id': active_id, 'service_order_generate': True}
    #         support_id = self.env['equipment.support.details'].sudo().search(
    #             [('name', '=', self.equipment_service_id.name)])
    #     for line in self:
    #         for line_value in line.cost_estimation_ids:
    #             if line_value.product_qty == 0 and line_value.unit_price == 0:
    #                 raise ValidationError('Alert!!,  Mr.%s ,  '
    #                                       '\n Please Enter the Unit Price and Product Qty For the Product %s .' % (
    #                                           self.env.user.name, line_value.product_id.name))
    #             if line_value.unit_price == 0:
    #                 raise ValidationError('Alert!!,  Mr.%s ,  '
    #                                       '\n Please Enter the Unit Price For the Product %s .' % (
    #                                           self.env.user.name, line_value.product_id.name))
    #             if line_value.product_qty == 0:
    #                 raise ValidationError('Alert!!,  Mr.%s ,  '
    #                                       '\n Please Enter the Product Qty For the Product %s .' % (
    #                                           self.env.user.name, line_value.product_id.name))
    #         new_requisition_id = service_request.create({
    #             'reference': line.maintenance_service_order_ref and line.maintenance_service_order_ref or '',
    #             'machine_id': line.equipment_id.id and line.equipment_id.id or '',
    #             'equip_name': line.machine and line.machine or '',
    #             'category_name': line.category.id and line.category.id or '',
    #             'subcategory_id': line.sub_category.id and line.sub_category.id or '',
    #             'service_date': datetime.now(),
    #             'equipment_service_id': line.equipment_service_id.id and line.equipment_service_id.id or '',
    #             'service_executer_id': line.requested_for.employee_id.id and line.requested_for.employee_id.id or '',
    #             'request_by': line.requested_by.name and line.requested_by.name or '',
    #             'cost_estimation_ids': line.get_service_estimation_order_line_items(),
    #         })
    #         indent_id.write({
    #             'service_order_generate': True,
    #         })
    #         return True


class HrEmployeeCreateLine(models.TransientModel):
    _name = "hr.employee.create.request.line"
    _description = 'Hr Employee Create Line'

    product_id = fields.Many2one('product.product', string='Product')
    line_order_id = fields.Many2one('hr.employee.request.create')
    on_hand_qty = fields.Integer('On Hand Qty')
    product_qty = fields.Float('Quantity')
    product_uom = fields.Char(string="UoM")
    product_uom_id = fields.Many2one('uom.uom', 'UOM')

    @api.onchange('product_id')
    def onchange_product_id(self):
        for val in self:
            if val.product_id:
                val.product_uom_id = val.product_id.uom_id and val.product_id.uom_id.id
                val.on_hand_qty = val.product_id.qty_available and val.product_id.qty_available


class HrEmployeeCreateEstimateLine(models.TransientModel):
    _name = "hr.employee.create.estimate.line"
    _description = 'Hr Employee Estimate Line'

    service_request_id = fields.Many2one('hr.employee.request.create', string="Service Request")
    cost_estimation_type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('overhead', 'Overhead'),
        ('others', 'Others'),
    ], string="Type")
    product_id = fields.Many2one('product.product', string='Product')
    product_uom = fields.Many2one('uom.uom', "Unit of Measure")
    product_qty = fields.Float("Quantity")
    unit_price = fields.Float("Unit Price")
    sub_total = fields.Float(compute='_compute_amount', string="Sub Total")
    description = fields.Char(string="Description")

    @api.onchange('product_id')
    def onchange_product_id(self):
        for val in self:
            if val.product_id:
                val.product_uom = val.product_id.uom_id and val.product_id.uom_id.id
                val.description = val.product_id.name and val.product_id.name

    @api.depends('product_qty', 'unit_price')
    def _compute_amount(self):
        for line in self:
            sub_total = 0.0
            if line.product_qty > 0 and line.unit_price > 0:
                sub_total = line.product_qty * line.unit_price
            else:
                sub_total = 0
            line.update({
                'sub_total': sub_total
            })
