from odoo import models, fields, api, _
from datetime import date, timedelta


class Service(models.Model):
    _name = 'services.details'
    _description = 'Service Details'

    name = fields.Char(string="Machine Services")
    equipment_service = fields.Many2one('equipment.support.details', string="Equipment Support", required=True)


class EquipmentServices(models.Model):
    _name = 'equipment.support.details'
    _description = 'Equipment Support Details'

    name = fields.Char(string="Machine Services")
    service_count = fields.Integer(string="Service Count", compute='_compute_maintenance_service_count')
    free_service_limit = fields.Integer(string="Service Limit")
    free_service_limit_used = fields.Integer(string="Service Utilized")
    free_service_remaining_limit = fields.Integer(string="Service Remaining Limit")
    first_service_date = fields.Date(string='1st Service Date')
    first_expire_date = fields.Date(string='1st Expire Date')
    first_service_responsible = fields.Char(string='Responsible Person')
    first_service_enable = fields.Boolean(string="First Service Enable?")
    second_service_date = fields.Date(string='2nd Service Date')
    second_expire_date = fields.Date(string='2nd Expire Date')
    second_service_responsible = fields.Char(string=' Responsible Person')
    second_service_enable = fields.Boolean(string="Second Service Enable?")
    third_service_date = fields.Date(string='3rd Service Date')
    third_expire_date = fields.Date(string='3rd Expire Date')
    third_service_responsible = fields.Char(string='Responsible Person ')
    third_service_enable = fields.Boolean(string="Third Service Enable?")
    responsible_person_company = fields.Char(string="Responsible Person Company")
    responsible_person_company_two = fields.Char(string=" Responsible Person Company")
    responsible_person_company_three = fields.Char(string="Responsible Person Company ")
    maintenance_service_stages = fields.Selection([
        ('first_level', '1'),
        ('second_level', '2'),
        ('third_level', '3')
    ], copy=False, string="No.of Services")
    service_support = fields.Selection([
        ('internal_service', ' Internal Service'), ('external_service', 'External Service')], string="Service Category",
        default='internal_service', readonly=True)
    service_count_new = fields.Integer(string=" Service Count", compute='_compute_maintenance_service_type_count')
    service_period_id = fields.Char(string="Service Name")
    service_period_second = fields.Char(string="Second Service Name")
    service_period_third = fields.Char(string="Third Service Name")
    service_period_code_one = fields.Char(string="1'st Service Period Code", store=True)
    service_period_code_two = fields.Char(string="2'nd Service Period Code", store=True)
    service_period_code_three = fields.Char(string="3'rd Service Period Code", store=True)
    service_period = fields.Float(string="1'st Service Period")
    service_expire_period = fields.Float(string="1'st Expire Period")
    level = fields.Char(string="")
    last_day_of_current_month = date.today()
    registered_date = fields.Date("Registered Date")
    second_service_period = fields.Float(string="2'st Service Period")
    second_service_expire_period = fields.Float(string="2'st Expire Period")
    second_registered_date = fields.Date(" Registered Date")
    third_service_period = fields.Float(string="3'st Service Period")
    third_service_expire_period = fields.Float(string="3'st Expire Period")
    third_registered_date = fields.Date("Registered Date ")
    first_completed_date = fields.Datetime("Completed Date")
    second_completed_date = fields.Datetime(" Completed Date")
    third_completed_date = fields.Datetime("Completed Date ")
    first_service_completed = fields.Boolean(string=" First Service Completed")
    second_service_completed = fields.Boolean(string="First Service Completed ")
    third_service_completed = fields.Boolean(string="First Service Completed")
    service_type = fields.Selection([
        ('paid_service', 'External Paid Service'),
        ('amc_service', 'External AMC Service'),
        ('free_service', 'ExternalFree Service'), ('interal_serivce', 'Internal General Service'),
    ], string="Service Type", default='interal_serivce', readonly=True)
    equipment_id = fields.Many2one('maintenance.equipment', string="Equipment Name")
    complement_service_utilized = fields.Integer(string="Complement Service Utilized")
    complement_service = fields.Boolean(string="Complement Service")
    estimated_service_hours = fields.Float(string="Service")
    first_warranty = fields.Float("Warranty")
    second_warranty = fields.Float(" Warranty")
    third_warranty = fields.Float("Warranty ")
    select_service_period_one = fields.Selection([
        ('days', 'Days'),
        ('months', 'Months'),
    ], string="Service Period")
    select_service_period_two = fields.Selection([
        ('days', 'Days'),
        ('months', 'Months'),
    ], string=" Service Period")
    select_service_period_three = fields.Selection([
        ('days', 'Days'),
        ('months', 'Months'),
    ], string="Service Period ")
    first_service_hours = fields.Float(string="Service Hours")
    second_service_hours = fields.Float(string=" Service Hours")
    third_service_hours = fields.Float(string="Service Hours ")
    first_service_days = fields.Integer(string="Service Days")
    second_service_days = fields.Integer(string=" Service Days")
    third_service_days = fields.Integer(string="Service Days ")
    first_service_month = fields.Integer(string="Service Months")
    second_service_month = fields.Integer(string=" Service Months")
    third_service_month = fields.Integer(string="Service Months ")
    first_service_completion_date = fields.Date(string="First service Completion")
    second_service_completion_date = fields.Date(string="Second service Completion")
    image = fields.Image(string="Image")
    machine_id = fields.Char(string="Equipment Code")

    def tick_ok(self):
        today = date.today()
        current_date = today.strftime("%d/%m/%Y")
        current_user = self.env.user.name
        current_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        current_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
        cc = ''
        ctx = self.env.context.copy()
        ctx.update({
            'name': self.name,
            'indent_date': current_date,
            'url': current_url,
            'current_user': current_user,
            'email_cc': cc,
        })
        if self.free_service_limit == self.free_service_limit_used:
            template = self.env.ref('maintenance_extended.email_template_for_maintenance_request', False)
            template.send_mail(self.id, force_send=True)
        return True

    @api.onchange('equipment_id')
    def equipments_id(self):
        if self.equipment_id:
            self.image = self.equipment_id.image
            self.machine_id = self.equipment_id.codefor

    @api.onchange('first_completed_date')
    def service_completion(self):
        if self.second_service_enable:
            if self.first_completed_date:
                self.first_service_completion_date = self.first_completed_date

    @api.onchange('second_completed_date')
    def service_completion(self):
        if self.third_service_enable:
            if self.second_completed_date:
                self.second_service_completion_date = self.second_completed_date

    @api.onchange('select_service_period_one', 'first_service_month', 'registered_date')
    def find_service_date(self):
        last_day_of_current_month = self.registered_date
        for rec in self:
            if rec.select_service_period_one == 'months' and rec.first_service_month > 0:
                import pandas as pd
                sr = pd.Series(pd.date_range(last_day_of_current_month,
                                             periods=rec.first_service_month, freq='M'))
                domain = []
                for line in sr:
                    domain.append(line)
                current_day = last_day_of_current_month.day
                rec.first_service_date = line + timedelta(days=current_day)
                rec.first_expire_date = line + timedelta(days=current_day)

    @api.onchange('select_service_period_two', 'second_service_month', 'first_service_completion_date')
    def find_second_service_date(self):
        second_last_day_of_current_month = self.first_service_completion_date
        for rec in self:
            if rec.select_service_period_two == 'months' and rec.second_service_month > 0:
                import pandas as pd
                sr = pd.Series(pd.date_range(second_last_day_of_current_month,
                                             periods=rec.second_service_month, freq='M'))
                domain = []
                for line in sr:
                    domain.append(line)
                current_day = second_last_day_of_current_month.day
                rec.second_service_date = line + timedelta(days=current_day)
                rec.second_expire_date = line + timedelta(days=current_day)

    @api.onchange('select_service_period_three', 'third_service_month', 'second_service_completion_date')
    def find_third_service_date(self):
        second_last_day_of_current_month = self.second_service_completion_date
        for rec in self:
            if rec.select_service_period_three == 'months' and rec.third_service_month > 0:
                import pandas as pd
                sr = pd.Series(pd.date_range(second_last_day_of_current_month,
                                             periods=rec.third_service_month, freq='M'))
                domain = []
                for line in sr:
                    domain.append(line)
                current_day = second_last_day_of_current_month.day
                rec.third_service_date = line + timedelta(days=current_day)
                rec.third_expire_date = line + timedelta(days=current_day)

    @api.onchange('first_service_days', 'registered_date', 'first_service_completion_date',
                  'second_service_completion_date')
    def get_service_period(self):
        if self.select_service_period_one == 'days' and self.first_service_days > 0.00:
            self.first_service_date = self.registered_date + timedelta(days=self.first_service_days)
            if self.first_service_date:
                self.first_expire_date = self.first_service_date
        if self.select_service_period_two == 'days' and self.second_service_days > 0.00:
            self.second_service_date = self.first_service_completion_date + timedelta(days=self.second_service_days)
            if self.second_service_date:
                self.second_expire_date = self.second_service_date
        if self.select_service_period_three == 'days' and self.third_service_days > 0.00:
            self.third_service_date = self.first_service_completion_date + timedelta(days=self.third_service_days)
            if self.third_service_date:
                self.third_expire_date = self.third_service_date

    @api.onchange('maintenance_service_stages')
    def booolean_enable(self):
        if self.maintenance_service_stages == 'first_level':
            self.first_service_enable = 'True'
        if self.maintenance_service_stages == 'second_level':
            self.second_service_enable = 'True'
        if self.maintenance_service_stages == 'third_level':
            self.third_service_enable = 'True'

    @api.onchange('service_period', 'registered_date')
    def get_service_period(self):
        if self.service_period and self.registered_date:
            self.first_service_date = self.registered_date + timedelta(days=self.service_period)
            self.first_expire_date = self.registered_date + timedelta(days=self.service_expire_period)
        if self.first_completed_date:
            self.second_service_date = self.first_completed_date + timedelta(days=self.service_period)
            self.second_expire_date = self.first_completed_date + timedelta(days=self.service_expire_period)

            self.third_service_date = self.registered_date + timedelta(days=self.service_period)
            self.third_expire_date = self.registered_date + timedelta(days=self.service_expire_period)

    def service_validation(self):
        current_user = self.env.user.name
        current_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        current_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
        cc = ''
        ctx = self.env.context.copy()
        cur_date = date.today()
        domain = [
            ('service_type', '!=', 'paid_service'),
            ('first_service_enable', '=', True),
            ('first_service_completed', '=', False),
            ('service_period_code', '=', True),
            ('registered_date', '=', True)]
        if self.maintenance_service_stages == 'first_level' and self.first_service_date >= cur_date:
            template = self.env.ref('maintenance_extended.email_template_maintenance_services_notification',
                                    False)
            template.send_mail(self.id, force_send=True)
        first_expire_domain = [
            ('service_type', '!=', 'paid_service'),
            ('first_service_enable', '=', True),
            ('first_service_completed', '=', False),
            ('service_period_code', '=', True),
            ('registered_date', '=', True)]
        if self.maintenance_service_stages == 'first_level' and self.first_expire_date <= cur_date:
            template = self.env.ref('maintenance_extended.email_template_maintenance_services_expire_notification',
                                    False)
            template.send_mail(self.id, force_send=True)
        domain1 = [
            ('service_type', '!=', 'paid_service'),
            ('maintenance_service_stages', '=', 'second_level'),
            ('second_service_enable', '=', True),
            ('second_service_completed', '=', False),
            ('second_service_date', '>=', cur_date),
            ('service_period_code', '=', True),
            ('registered_date', '=', True)]
        if self.maintenance_service_stages != 'first_level':
            template = self.env.ref('maintenance_extended.email_template_maintenance_services_notification',
                                    False)
            template.send_mail(self.id, force_send=True)

    def _cron_generate_service_notification(self):
        self.service_validation()

    def _compute_consumed_value_remaining(self):
        for records in self:
            service_consumed = 0.00
            if records.name:
                lc_process = self.env['service.request'].sudo(). \
                    search([('equipment_service_id', '=', records.name), ('state', '=', 'approved'),
                            ('free_service_boolean', '=', True)])
                for lc in lc_process:
                    count = records.service_count_new
                    service_consumed = count
                records.free_service_limit_used = service_consumed
                records.free_service_remaining_limit = records.free_service_limit - records.free_service_limit_used
                records.tick_ok()

    def _compute_maintenance_service_count(self):
        self.service_count = self.env['services.details'].sudo().search_count([('equipment_service', '=', self.id)])

    def _compute_maintenance_service_type_count(self):
        self.service_count_new = self.env['service.request'].sudo().search_count(
            [('equipment_service_id', '=', self.id)])

    def equipment_service_support_count_view(self):
        self.sudo().ensure_one()
        form_view = self.sudo().env.ref('maintenance_extended.view_services_form')
        tree_view = self.sudo().env.ref('maintenance_extended.view_services_tree')
        return {
            'name': _('Equipment Support Service'),
            'res_model': 'services.details',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('equipment_service', '=', self.id)],
        }

    def equipment_service_request_count_view(self):
        self.sudo().ensure_one()
        form_view = self.sudo().env.ref('maintenance_extended.service_request11')
        tree_view = self.sudo().env.ref('maintenance_extended.view_service_tree1')
        return {
            'name': _('Service Count'),
            'res_model': 'service.request',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('equipment_service_id', '=', self.id)],
        }

    @api.onchange('registered_date')
    def _get_service_sequence(self):
        if self.registered_date:
            registered_date_one = str(self.registered_date).split("-")
            service_code_one = registered_date_one[0] + registered_date_one[1] + registered_date_one[2]
            self.service_period_code_one = service_code_one

    @api.onchange('first_service_enable', 'first_completed_date')
    def _get_second_service_sequence(self):
        if self.first_completed_date:
            registered_date_two = str(self.first_completed_date).split("-")
            service_code_two = registered_date_two[0] + registered_date_two[1] + registered_date_two[2]
            self.service_period_code_two = service_code_two

    @api.onchange('second_completed_date')
    def _get_third_service_sequence(self):
        if self.second_completed_date:
            registered_date_three = str(self.second_completed_date).split("-")
            service_code_three = registered_date_three[0] + registered_date_three[1] + registered_date_three[2]
            self.service_period_code_three = service_code_three


class ServicesType(models.Model):
    _name = 'services.type.details'
    _description = 'Service Type Details'

    name = fields.Char(string="Machine Services")
    code = fields.Char(string="Code")


class ExternalDeliveryOrder(models.Model):
    _name = 'external.delivery.order'
    _description = 'External Delivery Order'

    def _get_stock_type_ids(self):
        data = self.env['stock.picking.type'].search([])
        for line in data:
            if line.code == 'outgoing':
                return line

    def name_get(self):
        result = []
        for rec in self:
            if rec.request_code:
                name = '[' + str(rec.request_code) + ']' + rec.name
                result.append((rec.id, name))
            else:
                name = rec.name
                result.append((rec.id, name))
        return result

    request_code = fields.Char(string="External Delivery Code", default=lambda self: '/', readonly=True)
    name = fields.Char(string="Service Name")
    reference = fields.Char("External Service Reference")
    machine_id = fields.Many2one('maintenance.equipment', string="Equipment ID ")
    equip_name = fields.Char(string="Item For Service ", related='machine_id.name')
    category_name = fields.Char(string='Category', related='machine_id.category_id.name')
    subcategory_id = fields.Many2one('subcate.details', string=' Sub Category')
    assigned_by = fields.Many2one('hr.employee', string='Assigned By', help="Service executer")
    service_takeover_incharge = fields.Many2one('hr.employee', string="Service Takeover Incharge")
    reference_code = fields.Char(string="External Maintenance Reference")
    service_type = fields.Selection([('repair', 'Repair'),
                                     ('replace', 'Replace'),
                                     ('updation', 'Updation'),
                                     ('checking', 'Checking'),
                                     ('adjust', 'Adjustment'),
                                     ('other', 'Other')],
                                    string='Type Of Service', help="Type for the service request")
    request_by = fields.Char(string='Requested By', help="Service executer")
    remarks = fields.Char(string="Remarks")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('delivery_sent', 'Waiting Delivery Approval'),
        ('under_service', 'Delivery Sent'),
        ('completed', 'Completed'),
    ], string="Status", default='draft')
    picking_type_id = fields.Many2one('stock.picking.type', 'Warehouse',
                                      default=_get_stock_type_ids,
                                      help="This will determine picking type of incoming shipment")
    # out_gate_entry_id = fields.Many2one('gate.entry', string='Gate Entry Out')
    # in_gate_entry_id = fields.Many2one('gate.entry', string='Gate Entry In')
    supplier_name = fields.Many2one('res.partner', string="Supplier name")
    external_delivery_status = fields.Selection([
        ('in', 'IN'),
        ('out', 'OUT'),
    ], string="Delivery Status")

    def delivery_complete(self):
        self.sudo().write({
            'state': 'completed'
        })

    def external_delivery_validate(self):
        self.sudo().write({
            'state': 'under_service'
        })

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['request_code'] = self.sudo().env['ir.sequence'].next_by_code('external.delivery.order') or '/'
        return super().create(vals_list)


class CostActualEstimation(models.Model):
    _name = 'cost.actual.estimation'
    _description = 'Cost Actual Estimation'

    actual_service_request_id = fields.Many2one('service.request', string="Service Request")
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
