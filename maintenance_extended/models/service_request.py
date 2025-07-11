from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class Service(models.Model):
    _name = 'service.request'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "service_name"

    def _get_employee_id(self):
        employee_rec = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        return employee_rec.id

    service_name = fields.Char(string="Reason For Service", help="Service name")
    equipment_service_id = fields.Many2one('equipment.support.details', string=" Service Type")
    supplier_name = fields.Many2one('res.partner', string="Supplier name")
    reference = fields.Char("Reference")
    employee_id = fields.Many2one('hr.employee', string="Employee", default=_get_employee_id, readonly=True,
                                  required=True, help="Employee")
    service_date = fields.Datetime(string="date", help="Service date")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('assign', 'Assigned'),
        ('check', 'Checked'),
        ('canceled', 'Cancelled'),
        ('reject', 'Rejected'),
        ('approved', 'Approved'),
        ('delivered', 'Delivered'),
        ('completed', 'Completed'),
        ('invoiced', 'Invoiced'),
        ('wait', 'Waiting For Payment Approval'),
        ('payment_approved', 'Payment Approved'),
        ('payment_rejected', 'Payment Rejected'),
    ], default='draft', tracking=True, help="State")
    service_executer_id = fields.Many2one('hr.employee', string='Manager', help="Service executer")
    service_executer = fields.Char(string='Manager ', help="Service executer")
    request_by = fields.Char(string='Requested By', help="Service executer")
    assigned_by = fields.Many2one('hr.employee', string='Assigned By', help="Service executer")
    service_takeover_incharge = fields.Many2one('hr.employee', string="Service Takeover Incharge")
    read_only = fields.Boolean(string="check field", compute='get_user')
    tester = fields.One2many('service.execute', 'test', string='tester', help="Tester")
    internal_note = fields.Text(string="internal notes", help="Internal Notes")
    service_type = fields.Selection([('repair', 'Repair'),
                                     ('replace', 'Replace'),
                                     ('updation', 'Updation'),
                                     ('checking', 'Checking'),
                                     ('adjust', 'Adjustment'),
                                     ('other', 'Other')],
                                    string='Type Of Service', help="Type for the service request")
    remarks = fields.Char(string="Remarks")
    name = fields.Char(string=" Service Code", default=lambda self: '/', readonly=True)
    machine_id = fields.Many2one('maintenance.equipment', string="Equipment ID ")
    equip_name = fields.Char(string="Item For Service ", related='machine_id.name')
    category_name = fields.Char(string='Category', related='machine_id.category_id.name')
    subcategory_id = fields.Many2one('subcate.details', string=' Sub Category')
    cost_estimation_ids = fields.One2many('cost.estimation', 'service_request_id', string="Cost Estimation")
    cost_estimation_actual_ids = fields.One2many('cost.actual.estimation', 'actual_service_request_id',
                                                 string="Actual Cost Estimation")
    amount_total = fields.Monetary('Total Other Estimation')
    total_labour_estimate = fields.Monetary('Total Labour Estimation', compute='_amount_all')
    total_overhead_estimate = fields.Monetary('Total Overhead Estimation')
    total_material_estimate = fields.Monetary('Total Material Estimation', compute='_amount_all')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', string="Currency")
    total_cost_estimation = fields.Float(string="Overall Cost Estimation")
    service_support = fields.Selection(related='equipment_service_id.service_support')
    external_service_order_count = fields.Integer(string='Invoice', compute='external_service_count')
    external_delivery_service_order_count = fields.Integer(string='Delivery', compute='external_delivery_count')
    account_invoice = fields.Many2one('account.move', string='Account Invoice')
    actual_total_cost_estimation = fields.Monetary(string="Actual Overall Cost Estimation")
    cost_estimation_difference_amount = fields.Monetary(string="Cost Estimation Difference",
                                                        compute='_cost_estimation_diff')
    free_service_boolean = fields.Boolean(string="Free Service Boolean")

    def button_escalate(self):
        self.write({
            'state': 'wait'
        })

    def button_approve(self):
        self.write({
            'state': 'payment_approved'
        })

    def button_reject(self):
        self.write({
            'state': 'payment_rejected'
        })

    @api.depends('total_cost_estimation', 'actual_total_cost_estimation')
    def _cost_estimation_diff(self):
        self.cost_estimation_difference_amount = 0.00
        for cost in self:
            if cost.total_cost_estimation or cost.actual_total_cost_estimation:
                cost.cost_estimation_difference_amount = cost.actual_total_cost_estimation - cost.total_cost_estimation

    def external_service_count(self):
        self.external_service_order_count = self.env['account.move'].sudo().search_count(
            [('invoice_origin', '=', self.reference), ('move_type', '=', 'in_invoice')])

    def external_service_bill_view(self):
        self.sudo().ensure_one()
        context = dict(self._context or {})
        active_model = context.get('active_model')
        form_view = self.sudo().env.ref('account.view_move_form')
        tree_view = self.sudo().env.ref('account.view_in_invoice_bill_tree')
        return {
            'name': _('Maintenance Service Invoice'),
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('invoice_origin', '=', self.reference), ('move_type', '=', 'in_invoice')],
        }

    def external_delivery_count(self):
        self.external_delivery_service_order_count = self.env['external.delivery.order'].sudo().search_count(
            [('reference', '=', self.name), ('reference_code', '=', self.reference)])

    def external_delivery_view(self):
        self.sudo().ensure_one()
        context = dict(self._context or {})
        active_model = context.get('active_model')
        form_view = self.sudo().env.ref('maintenance_extended.external_delivery_order')
        tree_view = self.sudo().env.ref('maintenance_extended.external_delivery_order_tree')
        return {
            'name': _('External Delivery Order'),
            'res_model': 'external.delivery.order',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('reference', '=', self.name), ('reference_code', '=', self.reference)],
        }

    def generate_invoice(self):
        external_delivery = self.env['external.delivery.order'].search(
            [('reference', '=', self.name), ('reference_code', '=', self.reference)])
        rfq = self.env['account.move']
        order_line = []
        if external_delivery.state == 'completed':
            for line in self.cost_estimation_ids:
                pass
                order_line.append({
                    'product_id': line.product_id.id,
                    'name': line.description,
                    'quantity': line.product_qty,
                    'product_uom_id': line.product_uom,
                    'price_unit': line.unit_price,
                })
            for service in self:
                if service:
                    res = rfq.create({
                        'partner_id': service.supplier_name.id,
                        'invoice_origin': service.reference,
                        'invoice_date': fields.Datetime.now(),
                        'ref': service.reference,
                        'invoice_line_ids': order_line,
                        'move_type': 'in_invoice',
                    })
        else:
            raise ValidationError("Alert!,The Service Delivery for %s is not yet completed.It is in Under "
                                  "Service.So Please Complete the Delivery Process."
                                  % self.name)
        self.sudo().write({
            'state': 'invoiced'
        })
        return

    @api.depends('cost_estimation_ids.sub_total', 'cost_estimation_ids.cost_estimation_type', 'total_cost_estimation')
    def _amount_all(self):
        for order in self:
            amount_material_sum = 0.0
            amount_labour_sum = 0.0
            amount_overhead_sum = 0.0
            amount_other_sum = 0.0
            for line in order.cost_estimation_ids:
                if line.cost_estimation_type == 'material':
                    amount_material_sum += line.sub_total
                    order.update({
                        'total_material_estimate': amount_material_sum,
                    })
                else:
                    amount_material_sum = 0.00
                if line.cost_estimation_type == 'labour':
                    amount_labour_sum += line.sub_total
                    order.update({
                        'total_labour_estimate': amount_labour_sum,
                    })
                else:
                    amount_labour_sum = 0.00
                if line.cost_estimation_type == 'overhead':
                    amount_overhead_sum += line.sub_total
                    order.update({
                        'total_overhead_estimate': amount_overhead_sum,
                    })
                else:
                    amount_overhead_sum = 0.00
                if line.cost_estimation_type == 'others':
                    amount_other_sum += line.sub_total
                    order.update({
                        'amount_total': amount_other_sum,
                    })
                else:
                    amount_other_sum = 0.00
            overall_total = order.total_material_estimate + order.total_labour_estimate + order.total_overhead_estimate + order.amount_total
            order.update({
                'total_cost_estimation': overall_total,
            })

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.sudo().env['ir.sequence'].next_by_code('service.request') or '/'
        return super().create(vals_list)

    @api.depends('read_only')
    def get_user(self):
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        if res_user.has_group('project.group_project_manager'):
            self.read_only = True
        else:
            self.read_only = False

    def submit_reg(self):
        self.ensure_one()
        self.sudo().write({
            'state': 'requested'
        })
        return

    def service_completed(self):
        line_vals = []
        vals = {
            'maintenance_request_name': self.service_name,
            'maintenance_request_code': self.id,
            'maintenance_request_ref': self.reference,
            'request_by': self.request_by,
            'request_assigned_by': self.assigned_by.id,
            'request_incharge': self.service_takeover_incharge.id,
            'request_manager': self.service_executer_id.id,
            'request_supplier_id': self.supplier_name.id,
            'maintenance_type': self.equipment_service_id.id,
            'maintenance_end_date': self.service_date,
        }
        line_vals.append((0, 0, vals))
        self.machine_id.external_equipment_history_ids = line_vals
        self.sudo().write({
            'state': 'completed'
        })

    def service_cancel(self):
        self.sudo().write({
            'state': 'canceled'
        })
        return

    def assign_executer(self):
        self.ensure_one()
        if not self.service_executer_id:
            raise ValidationError(_("Select Executer For the Requested Service"))
        self.write({
            'state': 'assign'
        })
        return

    def service_approval(self):
        for record in self:
            record.tester.sudo().state_execute = 'approved'
            record.write({
                'state': 'approved'
            })
        return

    def service_approved(self):
        equipment_support = self.env['equipment.support.details']. \
            search([('name', '=', self.equipment_service_id.name)])
        first_check = equipment_support.first_service_completed
        second_check = equipment_support.second_service_completed
        third_check = equipment_support.third_service_completed
        if first_check == False:
            equipment_support.write({
                'first_completed_date': fields.Datetime.now(),
                'first_service_completed': True,
            })
        elif first_check == True and second_check == False:
            equipment_support.write({
                'second_completed_date': fields.Datetime.now(),
                'second_service_completed': True,
            })
        elif first_check == True and second_check == True and third_check == False:
            equipment_support.write({
                'third_completed_date': fields.Datetime.now(),
                'third_service_completed': True,
            })
        self.write({
            'state': 'approved',
            'free_service_boolean': True,
        })
        return

    def service_rejection(self):
        self.write({
            'state': 'reject'
        })
        return

    def external_delivery_for_maintenance(self):
        self.write({
            'state': 'delivered'
        })
        external_delivery_order_create = self.sudo().env['external.delivery.order'].sudo().create({
            'name': self.service_name,
            'equip_name': self.equip_name,
            'machine_id': self.machine_id.id,
            'subcategory_id': self.subcategory_id.id,
            'category_name': self.category_name,
            'assigned_by': self.assigned_by.id,
            'service_takeover_incharge': self.service_takeover_incharge.id,
            'service_type': self.service_type,
            'request_by': self.request_by,
            'remarks': self.remarks,
            'reference': self.name,
            'reference_code': self.reference,
            'supplier_name': self.supplier_name.id,
            'state': 'delivery_sent',
        })
        return external_delivery_order_create


class ServiceExecute(models.Model):
    _name = 'service.execute'
    _rec_name = 'issue'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'issue'

    client = fields.Many2one('hr.employee', string="Client", help="Client")
    executer = fields.Many2one('hr.employee', string='Executer', help="Executer")
    execute_date = fields.Datetime(string="Date Of Reporting", help="Date of reporting")
    state_execute = fields.Selection([('draft', 'Draft'), ('requested', 'Requested'), ('assign', 'Assigned')
                                         , ('check', 'Checked'), ('reject', 'Rejected'),
                                      ('approved', 'Approved')], tracking=True, )
    test = fields.Many2one('service.request', string='test', help="Test")
    notes = fields.Text(string="Internal notes", help="Internal Notes")
    executer_product = fields.Char(string='Service Item', help="service item")
    type_service = fields.Char(string='Service Type', help="Service type")
    service_execute = fields.Char(string=" Service Code", default=lambda self: '/', readonly=True)
    machine_execute = fields.Many2one('maintenance.equipment', string="Equipment ID ")
    equip_name_execute = fields.Char(string="Item For Service ", related='machine_execute.name')
    category_execute = fields.Char(string='Category', related='machine_execute.category_id.name')
    subcategory_execute = fields.Many2one('subcate.details', string=' Sub Category')
    issue = fields.Char(string="Issue", help="Issue")

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['service_execute'] = self.sudo().env['ir.sequence'].next_by_code('service.execute') or '/'
        return super().create(vals_list)

    def service_check(self):
        self.test.sudo().state = 'check'
        self.write({
            'state_execute': 'check'
        })
        return


class CostEstimation(models.Model):
    _name = 'cost.estimation'
    _description = 'Cost Estimation'

    service_request_id = fields.Many2one('service.request', string="Service Request")
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
