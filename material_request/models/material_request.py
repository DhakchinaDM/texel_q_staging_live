from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MaterialRequestIndent(models.Model):
    _name = 'material.request.indent'
    _description = 'Indent'
    _inherit = ['mail.thread']
    _order = "verified_date desc"

    active = fields.Boolean(string="Active", default=True)

    def action_unarchive(self):
        for rec in self:
            rec.active = not rec.active


    def action_archive(self):
        for rec in self:
            rec.active = not rec.active




    def _get_stock_type_ids(self):
        data = self.env['stock.picking.type'].search([])
        for line in data:
            if line.code == 'internal':
                return line

    def _default_employee(self):
        emp_ids = self.sudo().env['hr.employee'].search([('user_id', '=', self.env.uid)])
        return emp_ids and emp_ids[0] or False

    name = fields.Char(string='Indent Reference', size=256, tracking=True, required=True, copy=False, readonly=True,
                       index=True, default=lambda self: _('/'),
                       help='A unique sequence number for the Indent')
    responsible = fields.Many2one('hr.employee', string='Request Raised By', default=_default_employee, readonly=True,
                                  help="Responsible person for the Material Request Approvers")
    verified_date = fields.Date('Verified Date', readonly=True, tracking=True)
    indent_date = fields.Date('Indent Date', required=True,
                              default=lambda self: fields.Datetime.now())
    required_date = fields.Date('Required Date', required=True)
    indentor_id = fields.Many2one('res.users', 'Indentor', tracking=True)
    department_id = fields.Many2one(string='Department', related='responsible.department_id', required=True,
                                    readonly=True, tracking=True)
    current_job_id = fields.Many2one(related='responsible.job_id', string="Job Position", required=True)
    current_reporting_manager = fields.Many2one(related='responsible.parent_id', string="Reporting Manager",
                                                required=True)
    request_raised_for = fields.Many2one('hr.employee', string='Request Raised For',
                                         help="Request person for the Material")
    requester_department_id = fields.Many2one('hr.department', string='Department Request', required=True,
                                              tracking=True)
    requester_current_job_id = fields.Many2one('hr.job', string="Job Position Request", required=True)
    requester_current_reporting_manager = fields.Many2one('hr.employee', string="Reporting Manager Requester",
                                                          required=True)
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user)
    purpose = fields.Char('Purpose', required=True, tracking=True)
    location_id = fields.Many2one('stock.location', 'Destination Location', required=True,
                                  tracking=True, default=lambda self: self._get_default_location())

    def _get_default_location(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        if warehouse:
            return warehouse.lot_stock_id.id

    analytic_account_id = fields.Many2one('account.analytic.account', 'Project', ondelete="cascade", readonly=True,
                                          tracking=True)
    requirement = fields.Selection([('1', 'Ordinary'), ('2', 'Urgent')], 'Requirement', required=True,
                                   tracking=True)
    type = fields.Selection([('stock', 'Stock')], 'Type', default='stock', required=True,
                            tracking=True, readonly=True)
    product_lines = fields.One2many('material.request.product.lines', 'indent_id', 'Products line')
    request_product_lines = fields.One2many('material.requesting.request.product.lines', 'indent_id', 'Products')
    ribbon_state = fields.Selection(
        [('not_available', 'Stock Not Available'),
         ('mr_stock_available', 'Stock Available'),
         ('store_to_verify', 'Store to Verify'),
         ('store_verified', 'Store Verified'),
         ('partial_stock', 'Partially Stock Available'),
         ('partial_stock_delivered', 'Partially Stock Delivery Created'),
         ('stock_delivered', 'Stock Delivery Created'),
         ('delivery_done', 'Delivery Completed'),
         ('partial_delivery_done', 'Partial Delivery Completed'),
         ('rfq_raise', 'RFQ/PO Raised'),
         ('tender_raise', 'Tender Raised'),
         ('grn_completed', 'GRN Completed'),
         ('draft', 'Draft'),
         ('request_to_approve', 'Request To Approve'),
         ('to_be_approved', 'Waiting For Manager Approval'),
         ('request_approved', 'Approved'),
         ('reject', 'Rejected'),
         ('cancel', 'Cancelled'),
         ], 'Ribbon State',
        default="draft", readonly=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_be_approved', 'Waiting for Approval'),
        ('reject', 'Rejected'),
        ('request_for_store_approval', 'Request for Store Verify'),
        ('request_approved_store', 'Request Verified By Store Team'),
        ('request_approved', 'Approved'),
        ('request_rfq', 'Request For RFQ'),
        ('rfq_create', 'RFQ Created'),
        ('tender_create', 'Tender Created'),
        ('inprogress', 'In Progress'),
        ('received', 'Delivered'),
        ('partially_received', 'Partially Delivered'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default="draft", readonly=True, index=True, copy=False, tracking=True)
    description = fields.Text('Additional Information', readonly=True)
    enable_ribbon = fields.Boolean('Ribbon Active')
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type',
                                      default=_get_stock_type_ids,
                                      help="This will determine picking type of incoming shipment")
    invoice_picking_id = fields.Many2one('stock.picking', string="Picking Id", copy=False)
    picking_count = fields.Integer(string="Count", copy=False, compute='get_picking_count')
    partial_delivery = fields.Boolean('Partial Delivery')
    material_requisition_backorder_count = fields.Integer(compute='_compute_material_requisition_backorder',
                                                          string='Back Order',
                                                          default=0)
    rfq_total = fields.Integer('My RFQ', compute='compute_order')
    purchase_order_count = fields.Integer(compute='_compute_material_requisition_po', string='Purchase Order',
                                          default=0)
    rfq_order_ids = fields.One2many('purchase.order', 'indent_id')
    manager_approve_reason = fields.Text('Manager Approver Approval Remarks')
    store_approver_reason = fields.Text('Store Approver Approval Remarks')
    approver_store = fields.Many2one('res.users', 'Store Approver', tracking=True, domain=lambda self: [
        ('groups_id', 'in', self.env.ref('material_request.group_receptions_report').id)])
    stock_available = fields.Boolean('Stock')
    partial_stock_available = fields.Boolean('Partial Stock')
    store_approval = fields.Boolean('Store Approval')
    store_verified_remark = fields.Text('Store Verified Remarks')
    tender_raised = fields.Boolean('Tender Raised', default=False)
    rfq_raised = fields.Boolean('RFQ Raised', default=False)
    store_request = fields.Boolean('Store Request')
    stock_transferred = fields.Boolean('Stock Transferred')
    partial_stock_transferred = fields.Boolean('Partial Stock Transferred')
    grn_status = fields.Boolean('GRN Status', default=False)
    issued_date = fields.Datetime('Issued Date')
    inward_date = fields.Datetime('Inward Date')
    delevered_qty = fields.Char('Delivered Qty')
    partial_develered_qty = fields.Char('Partial Delivered Qty')

    def return_balance_product(self):
        view = self.env.ref('stock.view_stock_return_picking_form')
        stock_ids = self.env['stock.picking'].sudo().search([('origin', '=', self.name)])

        return {
            'name': _('Stock Return'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.return.picking',
            'views': [(view.id, 'form')],
            'target': 'new',
            'context': {
                'default_mr_delivery_ids': [(6, 0, stock_ids.ids)],
                'default_picking_id': stock_ids and stock_ids[0].id or False,
            },
        }

    def get_picking_count(self):
        for rec in self:
            rec.picking_count = self.env['stock.picking'].sudo().search_count(
                [('origin', '=', rec.name)])

    @api.depends('current_reporting_manager')
    def _compute_current_user(self):
        for record in self:
            record.current_user = record.current_reporting_manager.user_id.id == self.env.user.id

    current_user = fields.Boolean('Current User', compute='_compute_current_user')

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            values['name'] = self.sudo().env['ir.sequence'].next_by_code('material.request.indent') or '/'
        res = super(MaterialRequestIndent, self).create(values_list)
        return res

    def create_material_request(self):
        self.ensure_one()
        if self.automated_sequence:
            name = self.sequence_id.next_by_id()
        else:
            name = self.name
        return {
            "type": "ir.actions.act_window",
            "res_model": "material.requisition.indent",
            "views": [[False, "form"]],
            "context": {
                'form_view_initial_mode': 'edit',
                'default_name': name,
                'default_responsible': self.env.user.id,
                'default_state': 'draft'
            },
        }

    @api.onchange('request_raised_for')
    def requester_details(self):
        if self.request_raised_for:
            self.sudo().write({
                'requester_current_reporting_manager': self.request_raised_for.parent_id.id,
                'requester_department_id': self.request_raised_for.department_id.id,
                'requester_current_job_id': self.request_raised_for.job_id.id,
            })

    def indent_request_for_manager_approval(self):
        user_manager = self.current_reporting_manager.name
        print('User Manager-------------------------', user_manager)
        for indent in self:
            indent.write({
                'state': 'to_be_approved',
                'ribbon_state': 'to_be_approved',
            })

    def indent_request_manager_approved(self):
        for indent in self:
            indent.write({
                'state': 'request_for_store_approval',
                'ribbon_state': 'store_to_verify',
            })

    def indent_request_store_approved(self):
        store_persion = self.env['res.users'].search(
            [('groups_id', 'in', self.env.ref('material_request.group_receptions_report').id)])
        print('Store Person-------------------------', store_persion.id)
        store_persions = store_persion.id
        print('Store Person-------------------------', self._uid)
        if self.state == 'request_for_store_approval':
            if store_persions == self._uid:
                self.write({'state': 'request_approved'})
                view_id = self.env['store.verified.remark']
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Store Verified Remark',
                    'res_model': 'store.verified.remark',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_id': view_id.id,
                    'view_id': self.env.ref('material_request.view_store_verified_remark_form', False).id,
                    'target': 'new',
                }

            else:
                raise UserError(_('Alert! Mr.%s, you are not allowed to approve this %s Material Requisition.') %
                                (self.env.user.name, self.name))

    def get_line_items(self):
        line_vals = []
        for line in self:
            if line.request_product_lines:
                for pro in line.request_product_lines:
                    if pro.short_close:
                        vals = [0, 0, {
                            'product_id': pro.original_product_id.id,
                            'product_uom_qty': pro.approved_product_uom_qty,
                            'product_uom': pro.approved_product_uom.id,
                            'product_available': pro.approved_product_available,
                            'product_category': pro.approved_product_category.id,
                            'product_type': pro.approved_product_type,
                        }]
                        line_vals.append(vals)
                    else:
                        vals = [0, 0, {
                            'product_id': pro.product_id.id,
                            'product_uom_qty': pro.product_uom_qty,
                            'product_uom': pro.product_uom.id,
                            'product_available': pro.product_available,
                            'product_category': pro.product_category.id,
                            'product_type': pro.product_type,
                        }]
                        line_vals.append(vals)
        return line_vals

    def check_product_confirm(self):
        requisition_created = False
        for line in self:
            if line.request_product_lines:
                requisition_created = line.update({
                    'product_lines': line.get_line_items(),
                })

    def request_create_rfq(self):
        for indent in self:
            state = indent.state = 'request_rfq'
            return state

    def material_request_approve_remarks(self):
        view_id = self.env['material.request.approve.remarks']
        return {
            'type': 'ir.actions.act_window',
            'name': 'Material Request Approval Remarks',
            'res_model': 'material.request.approve.remarks',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': view_id.id,
            'view_id': self.env.ref('material_request.material_request_approve_remarks_wizard', False).id,
            'target': 'new',
        }

    def material_request_reject_remarks(self):
        view_id = self.env['material.request.reject.remarks']
        for indent in self:
            indent.write({
                'state': 'reject',
            })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Material request Reject Remarks',
            'res_model': 'material.request.reject.remarks',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': view_id.id,
            'view_id': self.env.ref('material_request.material_request_reject_remarks_wizard', False).id,
            'target': 'new',
        }

    def material_request_cancel_remarks(self):
        view_id = self.env['material.request.cancel.remarks']
        for indent in self:
            indent.write({
                'state': 'cancel',
            })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Material Request Cancel Remarks',
            'res_model': 'material.request.cancel.remarks',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': view_id.id,
            'view_id': self.env.ref('material_request.material_request_cancel_remarks_wizard', False).id,
            'target': 'new',
        }

    def open_rfq_form(self):
        action = self.env.ref('material_request.open_create_rfq_wizard_action')
        result = action.read()[0]
        order_line = []
        for line in self.request_product_lines:
            order_line.append({
                'product_id': line.product_id.id,
                'product_qty': line.product_uom_qty,
                'product_uom_id': line.product_uom.id,
                'on_hand_qty': line.product_available,
            })
            result['context'] = {
                'default_material_requisition_ref': self.name,
                'default_order_lines': order_line,
            }
        return result

    def action_stock_moves(self):

        for order in self:
            product_lines = order.request_product_lines.filtered(lambda r: r.product_id.type in ['product', 'consu'])
            sfg = []
            fg = []
            for k in product_lines:
                for f in k.product_id:
                    if f.categ_id.id == self.env.ref('inventory_extended.category_semi_finished_goods').id:
                        sfg.append(k)
                        print("@@@@@@@@@@@@@", k)
                    if f.categ_id.id != self.env.ref('inventory_extended.category_semi_finished_goods').id:
                        fg.append(k)
                        print("33333333333", k)

            if sfg:
                print("$4444444444444444444444rawrawrawrarw44444444444444444444444444444444444444444444444")
                pick_raw = {
                    'picking_type_id': order.picking_type_id.id,
                    'partner_id': order.responsible.user_id.partner_id.id,
                    'responsible': order.responsible.user_id.partner_id.id,
                    'requested': order.request_raised_for.user_id.partner_id.id,
                    'shipment': True,
                    'origin': order.name,
                    'location_dest_id': order.picking_type_id.default_location_dest_id.id,
                    'location_id': order.picking_type_id.default_location_src_id.id,
                    'move_type': 'direct'
                }
                picking_raw = self.env['stock.picking'].create(pick_raw)
                product_lines_raw = order.request_product_lines.filtered(lambda r: r.product_id.type in ['product', 'consu'])
                for p in sfg:
                    # for pl in product_lines_raw:
                    #     if p.id == pl.product_id.id:
                    #         print("2222222222222222222222222222222222", p.name, "222222222222222222222222",
                    #               pl.product_id.name, "222222222222222222222222222222", p.name == pl.product_id.name)
                        if p.done_qty != 0.00:
                            qty_done = p.done_qty
                        else:
                            qty_done = p.product_uom_qty
                        template = {
                            'name': p.name or '',
                            'product_id': p.product_id.id,
                            'product_uom': p.product_uom.id,
                            'product_uom_qty': p.product_uom_qty,
                            'quantity': qty_done,
                            'location_id': picking_raw.picking_type_id.default_location_src_id.id,
                            'location_dest_id': picking_raw.picking_type_id.default_location_dest_id.id,
                            'picking_id': picking_raw.id,
                            'state': 'draft',
                            'picking_type_id': picking_raw.picking_type_id.id,
                            'route_ids': 1 and [
                                (6, 0, [x.id for x in self.env['stock.route'].search([('id', 'in', (2, 3))])])] or [],
                            'warehouse_id': picking_raw.picking_type_id.warehouse_id.id,
                        }
                        self.env['stock.move'].create(template)
                picking_raw.do_unreserve()
                picking_raw.action_confirm()

            # order.invoice_picking_id = picking.id
            if fg:
                fg_picking_id = self.env.ref('stock.picking_type_out')
                id_value = self.env.ref('stock.stock_location_customers')
                pick_fg = {
                    'picking_type_id': fg_picking_id.id,
                    'partner_id': order.responsible.user_id.partner_id.id,
                    'responsible': order.responsible.user_id.partner_id.id,
                    'requested': order.request_raised_for.user_id.partner_id.id,
                    'shipment': True,
                    'origin': order.name,
                    'location_id': fg_picking_id.default_location_src_id.id,
                    'location_dest_id': id_value.id,
                    'move_type': 'direct'
                }
                picking_fg = self.env['stock.picking'].create(pick_fg)
                product_lines_fg = order.request_product_lines.filtered(
                    lambda r: r.product_id.type in ['product', 'consu'])
                for f in fg:
                    # for pl in product_lines_fg:
                    #     if f.id == pl.product_id.id:
                    #         print("111111111111111111111111111111111111111", f.name, "111111111111111111",
                    #               pl.product_id.name, "111111111111111111111111", f.name == pl.product_id.name)
                            if f.done_qty != 0.00:
                                qty_done = f.done_qty
                            else:
                                qty_done = f.product_uom_qty
                            template = {
                                'name': f.name or '',
                                'product_id': f.product_id.id,
                                'product_uom': f.product_uom.id,
                                'product_uom_qty': f.product_uom_qty,
                                'quantity': qty_done,
                                'location_id': picking_fg.location_id.id,
                                'location_dest_id': picking_fg.location_dest_id.id,
                                'picking_id': picking_fg.id,
                                'state': 'draft',
                                'picking_type_id': picking_fg.picking_type_id.id,
                                'route_ids': 1 and [
                                    (6, 0, [x.id for x in self.env['stock.route'].search([('id', 'in', (2, 3))])])] or [],
                                'warehouse_id': picking_fg.picking_type_id.warehouse_id.id,
                            }
                            self.env['stock.move'].create(template)
                picking_fg.do_unreserve()
                picking_fg.action_confirm()

                # order.invoice_picking_id = picking.id

            # picking.button_validate()

            # for line in order.request_product_lines:
            #     delivered_qty = sum(move.quantity for move in picking.move_ids_without_package if move.product_id == line.product_id)
            #     line.delevered_qtys = str(delivered_qty)
            # diff_quantity = line.product_uom_qty
            # delevarable_qty = line.done_qty
            # template['product_uom_qty'] = diff_quantity
            # template['quantity'] = delevarable_qty

    # def action_stock_moves(self):
    #     if not self.picking_type_id:
    #         raise UserError(_(
    #             " Please select a picking type"))
    #     print('Picking Type1-------------------------', self.picking_type_id.code)
    #     for order in self:
    #         if self.invoice_picking_id:
    #             print("---------------",self.picking_type_id)
    #             print('Picking Type2-------------------------', self.invoice_picking_id)
    #             pick = {}
    #             if self.picking_type_id.code == 'outgoing':
    #                 pick = {
    #                     'picking_type_id': order.picking_type_id.id,
    #                     'partner_id': order.responsible.user_id.partner_id.id,
    #                     'responsible': order.responsible.user_id.partner_id.id,
    #                     'requested': order.request_raised_for.user_id.partner_id.id,
    #                     'shipment': True,
    #                     'origin': order.name,
    #                     'location_dest_id': order.responsible.address_id.property_stock_customer.id,
    #                     'location_id': order.picking_type_id.default_location_src_id.id,
    #                     'move_type': 'direct'
    #                 }
    #             print('Picking Type3-------------------------', pick)
    #             picking = self.env['stock.picking'].create(pick)
    #             self.invoice_picking_id = picking.id
    #             self.picking_count = len(picking)
    #             for line in self.request_product_lines:
    #                 value = line.product_id.name
    #                 print('Picking location-------------------------', value)
    #             product_lines = order.request_product_lines.filtered(lambda r: r.product_id.type in ['product', 'consu'])
    #             if not product_lines:
    #                 print("No Product Lines++++++++++++++++++++++++++++++++")
    #             moves = product_lines._create_stock_moves(picking)
    #             move_ids = moves._action_confirm()
    #             move_ids._action_assign()
    #             print('Move Ids-------------------------', picking)
    #             self.write({'state': 'received', 'ribbon_state': 'stock_delivered'})
    #     for order in self:
    #         if not self.invoice_picking_id:
    #             print('Picking Type2-------------------------', self.invoice_picking_id)
    #             pick = {}
    #             if self.picking_type_id.code == 'outgoing':
    #                 pick = {
    #                     'picking_type_id': order.picking_type_id.id,
    #                     'partner_id': order.responsible.user_id.partner_id.id,
    #                     'responsible': order.responsible.user_id.partner_id.id,
    #                     'requested': order.request_raised_for.user_id.partner_id.id,
    #                     'shipment': True,
    #                     'origin': order.name,
    #                     'location_dest_id': order.responsible.address_id.property_stock_customer.id,
    #                     'location_id': order.picking_type_id.default_location_src_id.id,
    #                     'move_type': 'direct'
    #                 }
    #             print('Picking Type3-------------------------', pick)
    #             picking = self.env['stock.picking'].create(pick)
    #             self.invoice_picking_id = picking.id
    #             self.picking_count = len(picking)
    #             for line in self.request_product_lines:
    #                 value = line.product_id.name
    #                 print('Picking location-------------------------', value)
    #             product_lines = order.request_product_lines.filtered(lambda r: r.product_id.type in ['product', 'consu'])
    #             if not product_lines:
    #                 print("No Product Lines++++++++++++++++++++++++++++++++")
    #             moves = product_lines._create_stock_moves(picking)
    #             move_ids = moves._action_confirm()
    #             move_ids._action_assign()
    #             print('Move Ids-------------------------', picking)
    #             self.write({'state': 'received', 'ribbon_state': 'stock_delivered'})

    # def action_partial_stock_move(self):
    #     if not self.picking_type_id:
    #         raise UserError(_("Please select a picking type"))

    #     for order in self:
    #         if not self.invoice_picking_id:
    #             pick = {}
    #             if self.picking_type_id.code == 'outgoing':
    #                 pick = {
    #                     'picking_type_id': order.picking_type_id.id,
    #                     'partner_id': order.responsible.user_id.partner_id.id,
    #                     'responsible': order.responsible.user_id.partner_id.id,
    #                     'requested': order.request_raised_for.user_id.partner_id.id,
    #                     'shipment': True,
    #                     'origin': order.name,
    #                     'location_dest_id': order.responsible.address_id.property_stock_customer.id,
    #                     'location_id': order.picking_type_id.default_location_src_id.id,
    #                     'move_type': 'direct'
    #                 }
    #             picking = self.env['stock.picking'].create(pick)
    #             self.invoice_picking_id = picking.id
    #             self.picking_count = len(picking)
    #             moves = order.request_product_lines.filtered(lambda r: r.product_id.type in ['product', 'consu'])._create_stock_moves(picking)
    #             move_ids = moves._action_confirm()
    #             move_ids._action_assign()
    #             picking.button_validate()

    #             # Update delivered quantity
    #             for line in order.request_product_lines:
    #                 delivered_qty = sum(move.quantity for move in picking.move_ids_without_package if move.product_id == line.product_id)
    #                 line.delevered_qtys = str(delivered_qty)

    #             # Check if backorder is created
    #             if picking.backorder_id:
    #                 self.write({'state': 'partially_received', 'partial_delivery': True, 'ribbon_state': 'partial_stock_delivered'})
    #             else:
    #                 self.write({'state': 'received', 'ribbon_state': 'stock_delivered'})

    #             self.write({'state': 'partially_received', 'partial_delivery': True,
    #                         'ribbon_state': 'partial_stock_delivered', })

    def create_shipped(self):
        product_onhand = []
        req_product = []
        product_type = []
        res = []
        zero_count = 0.00
        non_zero_count = 0.00
        zero_non_zero_count = 0.00
        req_qun_count = 0.00
        for num in self:
            for l in num.request_product_lines:
                if l.product_type == 'product':
                    product_onhand.append(l.product_available)
                    req_product.append(l.product_uom_qty)
                    product_type.append(l.product_type)
                else:
                    self.write({'stock_available': True,
                                'ribbon_state': 'mr_stock_available'})
                for i in product_onhand:
                    if i not in res:
                        res.append(i)
                for product in res:
                    if product == 0.00:
                        zero_count += 1
                    if product > 0.00:
                        non_zero_count += 1
                for qty in req_product:
                    if qty > product:
                        req_qun_count += 1
                    if non_zero_count and req_qun_count or zero_count and non_zero_count:
                        zero_non_zero_count += 1
                        num.update({
                            'partial_stock_available': True,
                            'ribbon_state': 'partial_stock',
                            'stock_available': False,
                            'tender_raised': False,
                            'rfq_raised': False,
                        })
                        print("--------No Stock")
                    if non_zero_count and zero_non_zero_count == 0.00 or product == qty:
                        if not self.stock_available:
                            num.update({
                                'partial_stock_available': False,
                                'stock_available': True,
                                'partial_delivery': False,
                                'ribbon_state': 'mr_stock_available',
                                'tender_raised': False,
                                'rfq_raised': False,
                            })
                            print("------------stock on")
                        if self.stock_available:
                            num.update({
                                'tender_raised': False,
                            })
            self.write({'enable_ribbon': True})

    def set_draft(self):
        for indent in self:
            indent.state = 'draft'
            for j in indent.product_lines:
                j.unlink()

    def create_RFQ_lines(self):
        return {
            'name': _('Purchase Orders'),
            'domain': [('id', 'in', [x.id for x in self.rfq_order_ids]), ('state', '=', 'draft')],
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'view_id': False,
            'views': [(self.env.ref('purchase.purchase_order_kpis_tree').id, 'tree'),
                      (self.env.ref('purchase.purchase_order_form').id, 'form')],
            'type': 'ir.actions.act_window'
        }

    def material_requisition_back_order(self):
        self.sudo().ensure_one()
        context = dict(self._context or {})
        active_model = context.get('active_model')
        form_view = self.sudo().env.ref('stock.view_picking_form')
        tree_view = self.sudo().env.ref('stock.vpicktree')
        return {
            'name': _('My Back Order'),
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('origin', '=', self.name), ('backorder_id', '!=', False)],
        }

    def _compute_material_requisition_backorder(self):
        self.material_requisition_backorder_count = self.env['stock.picking'].sudo().search_count(
            [('origin', '=', self.name), ('backorder_id', '!=', False)])

    def compute_order(self):
        count = 0
        for employee in self:
            invoices = self.env['purchase.order']
            for record in employee.rfq_order_ids:
                if record.state == 'draft':
                    count += 1
            employee.rfq_total = count
            if employee.rfq_total:
                employee.write({'rfq_raised': True, 'ribbon_state': 'rfq_raise'})

    def button_purchase_order(self):
        self.sudo().ensure_one()
        context = dict(self._context or {})
        active_model = context.get('active_model')
        form_view = self.sudo().env.ref('purchase.purchase_order_form')
        tree_view = self.sudo().env.ref('purchase.purchase_order_view_tree')
        return {
            'name': _('Purchase Order'),
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('origin', '=', self.name), ('state', '=', 'purchase')],
        }

    def _compute_material_requisition_po(self):
        self.purchase_order_count = self.env['purchase.order'].sudo().search_count(
            [('origin', '=', self.name), ('state', '=', 'purchase')])

    def action_view_picking(self):
        self.sudo().ensure_one()
        form_view = self.env.ref('stock.view_picking_form')
        tree_view = self.env.ref('stock.vpicktree')
        return {
            'name': _('Stock Details'),
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('origin', '=', self.name)],
        }

    def apply_approval(self):
        for indent in self:
            indent.button_leader_approval()

    def apply_rejection(self):
        for indent in self:
            indent.button_leader_reject()

    def apply_cancellation(self):
        for indent in self:
            indent.button_leader_cancel()

    def button_leader_approval(self):
        if self.state == 'to_be_approved':
            if self.env.user.id == self._uid:
                self.write({'state': 'request_approved'})
                self.action_stock_moves()
            else:
                raise UserError(_('Alert! Mr.%s, you are not allowed to approve this %s Material Requisition.') %
                                (self.env.user.name, self.name))


class IndentRequestProductLines(models.Model):
    _name = 'material.request.product.lines'
    _description = 'Indent Product Lines'

    indent_id = fields.Many2one('material.request.indent', 'Indent', required=True)
    indent_type = fields.Selection([('new', 'Purchase Indent'), ('existing', 'Repairing Indent')], 'Type')
    product_id = fields.Many2one('product.product', 'Product')
    original_product_id = fields.Many2one('product.product', 'Product to be Repaired')
    product_uom_qty = fields.Float('Quantity Required', digits='Product UoS', default=1)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure request', compute='_compute_product_details')
    product_uos_qty = fields.Float('Quantity (UoS)', digits='Product UoS')
    product_uos = fields.Many2one('uom.uom', 'Product UoS')
    qty_available = fields.Float('In Stock')
    product_available = fields.Float(string='OnHand Qty', related='product_id.qty_available')
    delay = fields.Float('Lead Time')
    qty_shipped = fields.Float('QTY Shipped')
    name = fields.Text('Purpose', required=False)
    specification = fields.Text('Specification')
    product_category = fields.Many2one('product.category', string='Product Category',
                                       compute='_compute_product_details')
    product_type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product'),
    ], string='Product Type', compute='_compute_product_details')

    @api.depends('product_id')
    def _compute_product_details(self):
        for val in self:
            if val.product_id:
                val.product_uom = val.product_id.uom_id.id
                val.product_category = val.product_id.categ_id.id
                val.product_type = val.product_id.type
            else:
                val.product_uom = False
                val.product_category = False
                val.product_type = False

    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        print("partial_delevery------------------------")
        for line in self:
            if picking.picking_type_id.code == 'outgoing':
                template = {
                    'name': line.name or '',
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom.id,
                    'location_id': picking.picking_type_id.default_location_src_id.id,
                    'location_dest_id': line.indent_id.responsible.address_id.property_stock_customer.id,
                    'picking_id': picking.id,
                    'state': 'draft',
                    'picking_type_id': picking.picking_type_id.id,
                    'route_ids': 1 and [
                        (6, 0, [x.id for x in self.env['stock.route'].search([('id', 'in', (2, 3))])])] or [],
                    'warehouse_id': picking.picking_type_id.warehouse_id.id,
                }
            diff_quantity = line.product_uom_qty
            tmp = template.copy()
            tmp.update({
                'product_uom_qty': diff_quantity,
            })
            template['product_uom_qty'] = diff_quantity
            done += moves.create(template)
        return done


class IndentMeterialRequestProductLines(models.Model):
    _name = 'material.requesting.request.product.lines'
    _description = 'Indent Request Product Lines'

    indent_id = fields.Many2one('material.request.indent', 'Indent', required=True)
    indent_type = fields.Selection([('new', 'Purchase Indent'), ('existing', 'Repairing Indent')], 'Type')
    product_id = fields.Many2one('product.product', 'Part')
    product_name = fields.Char('Product Name', related='product_id.name')
    original_product_id = fields.Many2one('product.product', 'Approved Product')
    product_uom_qty = fields.Float('Quantity Required', digits='Product UoS', default=1)
    approved_product_uom_qty = fields.Float('Quantity Approved', digits='Product UoS')
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure Requested', compute='_compute_product_details')
    approved_product_uom = fields.Many2one('uom.uom', 'Unit of Measure Approved',
                                           compute='_compute_original_product_id_details')
    product_uos_qty = fields.Float('Quantity (UoS)', digits='Product UoS')
    product_uos = fields.Many2one('uom.uom', 'Product UoS')
    qty_available = fields.Float('In Stock')
    product_available = fields.Float(string='OnHand Qty',compute='_compute_product_avilable')

    @api.depends('product_id')
    def _compute_product_avilable(self):
        for i in self:
            qty = 0.0
            if i.product_id:
                stock = self.env['stock.lot'].sudo().search([
                    ('product_id', '=', i.product_id.id),
                    ('lot_type', '=', 'ok')
                ])
                qty = sum(stock.mapped('product_qty'))
            i.product_available = qty

    approved_product_available = fields.Float(string='Approved OnHand Qty',
                                              related='original_product_id.qty_available', )
    delay = fields.Float('Lead Time')
    name = fields.Text('Purpose')
    specification = fields.Text('Specification')
    product_category = fields.Many2one('product.category', string='Product Category',
                                       compute='_compute_product_details')
    approved_product_category = fields.Many2one('product.category', string='Approved Product Category',
                                                compute='_compute_original_product_id_details')
    product_type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product'),
    ], string='Product Type', compute='_compute_product_details')
    approved_product_type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product'),
    ], string='Approved Product Type', compute='_compute_original_product_id_details')
    short_close = fields.Boolean('Short Close')
    delevered_qtys = fields.Char('Delivered Qty')
    done_qty = fields.Float('Done Qty')

    # @api.depends('product_uom_qty')
    # def _compute_done_qty(self):
    #     print("+++++++++DONE QTY+++++++++++")
    #     for record in self:
    #         if record.product_uom_qty != 0.00:
    #             record.done_qty = record.product_uom_qty
    #         else:
    #             record.done_qty = 0.00

    @api.constrains('product_uom_qty', 'product_available')
    def _check_product_uom_qty(self):
        for record in self:
            if record.product_uom_qty > record.product_available:
                print("++++++++++++++++++++", record.product_uom_qty)
                raise UserError(_('The quantity required cannot be more than the available quantity.'))

    @api.depends('product_id')
    def _compute_product_details(self):
        for val in self:
            if val.product_id:
                val.product_uom = val.product_id.uom_id.id
                val.product_category = val.product_id.categ_id.id
                val.product_type = val.product_id.type
            else:
                val.product_uom = False
                val.product_category = False
                val.product_type = False

    @api.depends('original_product_id')
    def _compute_original_product_id_details(self):
        for val in self:
            if val.product_id:
                val.approved_product_uom = val.original_product_id.uom_id.id
                val.approved_product_category = val.original_product_id.categ_id.id
                val.approved_product_type = val.original_product_id.type
            else:
                val.approved_product_uom = False
                val.approved_product_category = False
                val.approved_product_type = False

    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            if picking.picking_type_id.code == 'outgoing':
                template = {
                    'name': line.name or '',
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom.id,
                    'location_id': picking.picking_type_id.default_location_src_id.id,
                    'location_dest_id': line.indent_id.responsible.address_id.property_stock_customer.id,
                    'picking_id': picking.id,
                    'state': 'draft',
                    'picking_type_id': picking.picking_type_id.id,
                    'route_ids': 1 and [
                        (6, 0, [x.id for x in self.env['stock.route'].search([('id', 'in', (2, 3))])])] or [],
                    'warehouse_id': picking.picking_type_id.warehouse_id.id,
                }
            diff_quantity = line.product_uom_qty
            delevarable_qty = line.done_qty
            print("++++++++++++++++++++", line.done_qty)
            tmp = template.copy()
            tmp.update({
                'product_uom_qty': diff_quantity, 'quantity': delevarable_qty,
            })
            template['product_uom_qty'] = diff_quantity
            template['quantity'] = delevarable_qty
            done += moves.create(template)
            print("++++++++++++++++++++", picking)

        picking.action_confirm()
        picking.action_assign()
        picking.button_validate()

        # Update delivered quantity
        for line in self:
            delivered_qty = sum(
                move.quantity for move in picking.move_ids_without_package if move.product_id == line.product_id)
            line.delevered_qtys = str(delivered_qty)

        return done


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for move in self.move_ids_without_package:
            print(f'Product: {move.product_id.name}, Quantity: {move.quantity}')
            product_line = self.env['material.requesting.request.product.lines'].search([
                ('product_id', '=', move.product_id.id),
                ('indent_id', '=', self.origin)
            ], limit=1)
            if product_line:
                delivered_qty = float(product_line.delevered_qtys or 0.00) + move.quantity
                print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>.', delivered_qty)
                product_line.delevered_qtys = str(delivered_qty)
        return res
