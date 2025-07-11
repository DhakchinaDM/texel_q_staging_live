from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import ValidationError


class Request(models.Model):
    _inherit = "maintenance.request"

    @api.returns('self')
    def _default_stage(self):
        return self.env['maintenance.stage'].search([], limit=1)

    completed_date = fields.Datetime(string='Completed Date by')
    production_id = fields.Many2one(
        'mrp.production', string='Manufacturing Order', check_company=True, groups="base.group_no_one")
    image = fields.Image(string="Image")
    machine_id = fields.Char(string="Machine Code")
    subcat_id = fields.Many2one('subcate.details', string=' Sub Category', store=True)
    external_service_order_count = fields.Integer(string='External Service', compute='external_service_count')
        # internal_service_order_count = fields.Integer(string='Internal Service', compute='internal_service_count')
    purchase_order = fields.Many2one('purchase.order', string='Maintenance PO')
    request_code = fields.Char(string=" Request Code", default=lambda self: 'New', readonly=True)
    service_order_generate = fields.Boolean(string="Service Order Generate")
    service_started = fields.Boolean(string="Service Started")
    service_ended = fields.Boolean(string="Service Ended")
    equipment_support = fields.Selection([
        ('service', ' Free Service'), ('paid service', 'Paid Service')], string="Equipment Support")
    machine_service = fields.Many2one('services.details', string="Services")
    service_types = fields.Many2one('services.type.details', string="Services Type")
    external_service_invoice_count = fields.Integer(string='External Invoice',
                                                    compute='external_service_maintenance_invoice_count')
    account_invoice = fields.Many2one('account.move', string='Account Invoice')
    reference = fields.Char(string="Requisition Reference")
    stage_id = fields.Many2one('maintenance.stage', string='Stage', ondelete='restrict', tracking=True,
                               group_expand='_read_group_stage_ids', default=_default_stage, copy=False)
    internal_remarks = fields.Html(string="Start Service Remarks")
    end_remarks = fields.Html(string="End Service Remarks")
    cur_user = fields.Many2one('res.users', "Service Executor")
    end_cur_user = fields.Many2one('res.users', " Service Executor")
    cur_time = fields.Datetime('Service Start Time')
    end_cur_time = fields.Datetime(' Service End Time')
    external_remarks = fields.Html(string="Service Remarks")
    duration = fields.Char("Duration")
    duration_one = fields.Float(" Duration")
    # material_requisition = fields.Many2one('material.requisition.indent', string="Material Requisition Indent")
    # material_state = fields.Selection(related='material_requisition.state')
    submit_for_approval_bool = fields.Boolean(string='Submit')
    approved_bool = fields.Boolean(string='Stage Approved')

    def external_service_maintenance_invoice_count(self):
        self.external_service_invoice_count = self.env['account.move'].sudo().search_count(
            [('invoice_origin', '=', self.request_code), ('move_type', '=', 'in_invoice')])

    def external_service_maintenance_bill_view(self):
        self.sudo().ensure_one()
        form_view = self.sudo().env.ref('account.view_move_form')
        tree_view = self.sudo().env.ref('account.view_in_invoice_bill_tree')
        return {
            'name': _('Maintenance Service Invoice'),
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('invoice_origin', '=', self.request_code), ('move_type', '=', 'in_invoice')],
        }

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['request_code'] = self.sudo().env['ir.sequence'].next_by_code(
                'maintenance_extended.maintenance.request') or '/'
        return super().create(vals_list)

    @api.onchange('equipment_id')
    def equipments_id(self):
        if self.equipment_id:
            self.image = self.equipment_id.image
            # self.machine_id = self.equipment_id.codefor.name

    def external_service_count(self):
        self.external_service_order_count = self.env['service.request'].sudo().search_count(
            [('reference', '=', self.request_code)])

    # def internal_service_count(self):
    #     self.internal_service_order_count = self.env['material.requisition.indent'].sudo().search_count(
    #         [('origin', '=', self.request_code), ('order_type', '=', 'service_order')])

    def parnter_service_bill_view(self):
        self.sudo().ensure_one()
        context = dict(self._context or {})
        active_model = context.get('active_model')
        form_view = self.sudo().env.ref('maintenance_extended.service_request11')
        tree_view = self.sudo().env.ref('maintenance_extended.view_service_tree1')
        return {
            'name': _('External Service Order'),
            'res_model': 'service.request',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('reference', '=', self.request_code)],
        }

    # def maintenance_internal_service_order_req(self):
    #     self.sudo().ensure_one()
    #     context = dict(self._context or {})
    #     active_model = context.get('active_model')
    #     form_view = self.sudo().env.ref('material_requisition.view_stock_indent_indent_form')
    #     tree_view = self.sudo().env.ref('material_requisition.view_indent_indent_tree')
    #     return {
    #         'name': _('Service Requisition'),
    #         'res_model': 'material.requisition.indent',
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'tree,form',
    #         'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
    #         'domain': [('origin', '=', self.request_code), ('order_type', '=', 'service_order')],
    #     }

    # def open_maintenance_service_form(self):
    #     action = self.env.ref('maintenance_extended.open_create_service_order_wizard_action')
    #     result = action.read()[0]
    #     order_line = []
    #     for line in self:
    #         result['context'] = {
    #             'default_maintenance_service_order_ref': line.request_code,
    #             'default_equipment_id': line.equipment_id.id,
    #             # 'default_machine': line.machine_id,
    #             'default_category': line.category_id.id,
    #             'default_requested_by': line.employee_id.id,
    #             'default_requested_for': line.user_id.id,
    #             'default_service_name': line.name,
    #             'default_location_id': self.env.ref('stock.stock_location_stock').id,
    #             'default_order_lines': [(0, 0, {
    #                 'product_id': i.product_id.id,
    #                 'product_qty': i.minimum_stock,
    #                 'product_uom_id': i.product_id.uom_id.id,
    #                 'on_hand_qty': i.product_id.qty_available,
    #             }) for i in line.equipment_id.spare_ids],
    #         }
    #     return result

    # def complete_internal_maintenace_service(self):
    #     if self.material_requisition.state not in ['done', 'received']:
    #         raise ValidationError("Alert, Mr. %s.\nPlease complete the Internal Service Request and try again." \
    #                               % self.env.user.name)
    #     else:
    #         action = self.env.ref('maintenance_extended.internal_service_order_wizard_action')
    #         result = action.read()[0]
    #         order_line = []
    #         for line in self:
    #             result['context'] = {
    #                 'default_maintenance_service_order_ref': line.request_code,
    #                 'default_service_started': line.service_started,
    #                 'default_service_ended': line.service_ended,
    #                 'default_equipment_id': line.equipment_id.id,
    #                 # 'default_machine': line.machine_id,
    #                 'default_category': line.category_id.id,
    #                 'default_service_duration': line.cur_time,
    #             }
    #         return result

    def reset_equipment_request(self):
        """ Reinsert the maintenance request into the maintenance pipe in the first stage"""
        first_stage_obj = self.env['maintenance.stage'].search([], order="sequence asc", limit=1)
        # self.write({'active': True, 'stage_id': first_stage_obj.id})
        self.write({'archive': False, 'stage_id': first_stage_obj.id, 'submit_for_approval_bool': False,
                    'approved_bool': False, 'service_order_generate': False})

    # def get_service_status(self):

#
# class MaterialRequisitionIndent(models.Model):
#     _inherit = 'material.requisition.indent'
#
#     origin = fields.Char(string="Origin")
#     equipment_name = fields.Char(string='Equipment Name')
#     order_type = fields.Selection([
#         ('service_order', 'Service Order')], string='Order Type')
