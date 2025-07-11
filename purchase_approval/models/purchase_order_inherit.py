from odoo import fields, models, api, _
from odoo.exceptions import AccessError, UserError, ValidationError
from datetime import date, datetime, timedelta


class ResPartner(models.Model):
    _inherit = ['res.partner']

    # _name = 'res.partner'
    # _inherit = ['mail.thread']


    ref_no = fields.Char(string="Vendor Reference Code")


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    grn_created = fields.Boolean(string="Grn Created", store=True)
    grn = fields.Integer(string="Grn Count", compute='created_grn')
    quotation_no = fields.Char(string='Quotation', related='order_id.quotation_no')
    date = fields.Date(string="Lead Time")
    stock_done = fields.Float(string='Done', store=True)
    balance = fields.Float(string='BaLance')
    balanced_delivery = fields.Float(string=' Quantity', store=True, related='product_qty')
    supplier_part = fields.Char(string='Supplier Part No')
    status = fields.Selection(selection_add=[('progress', 'In Progress')])
    purchase_type = fields.Selection(string="Purchase Type", related='order_id.purchase_type',store=True)
    supplier_reference = fields.Char(string='Supplier Reference')
    inv_date = fields.Date(string="Invoice Date")
    product_category_ids = fields.Many2many('product.category')
    mfg_date = fields.Date(string='MFG Date')


    @api.onchange('purchase_type', 'name')
    def get_non_standard_po(self):
        for i in self:
            if i.purchase_type == 'ser':
                i.write({
                    'product_id': self.env.ref('purchase_approval.product_product_service').id,
                    'product_uom': self.env.ref('uom.product_uom_dozen').id,
                })

    @api.onchange('product_category_ids')
    def get_product_category_ids(self):
        for rec in self:
            rec.order_id._get_product_category()

    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity', 'qty_received', 'product_uom_qty',
                 'order_id.state')
    def _compute_qty_invoiced(self):
        for line in self:
            # compute qty_invoiced
            qty = line.qty_invoiced
            for inv_line in line._get_invoice_lines():
                if inv_line.move_id.state not in ['cancel'] or inv_line.move_id.payment_state == 'invoicing_legacy':
                    if inv_line.move_id.move_type == 'in_invoice':
                        qty += inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom)
                    elif inv_line.move_id.move_type == 'in_refund':
                        qty -= inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom)
            line.qty_invoiced = qty

            # compute qty_to_invoice
            if line.order_id.state in ['purchase', 'done']:
                if line.product_id.purchase_method == 'purchase':
                    line.qty_to_invoice = line.product_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_received - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    @api.onchange('product_id')
    def compute_supplier_part(self):
        for i in self:
            if i.product_id:
                i.supplier_part = i.product_id.supplier_part
            else:
                i.supplier_part = False

    # @api.depends('product_qty', 'qty_received')
    # def _compute_balanced_delivery(self):
    #     for line in self:
    #         # Calculate the balanced delivery value
    #         line.balanced_delivery = line.product_qty - line.qty_received

    def created_grn(self):
        for rec in self:
            rec.grn = self.env['stock.picking'].sudo().search_count(
                [('origin', '=', rec.order_id.name)])

    def action_view_grn(self):
        picking = self.env['stock.move'].search(
            [('origin', '=', self.order_id.name), ('purchase_line_id', '=', self.id)])
        return {
            'name': _('GRN'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': picking.id,
            'domain': [('name', '=', picking.name)],
            'target': 'current'
        }

    def generate_grn(self):
        picking = self.env.ref('stock.picking_type_in')
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!11", picking)
        if self.stock_done == 0.00:
            raise ValidationError("Done quantity cannot be zero.")
        elif self.stock_done > self.balanced_delivery:
            raise ValidationError("Done value must be greater than Quantity.")
        stock_location = self.env.ref('stock.stock_location_stock')
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        grn = self.env['stock.picking'].sudo().create({
            'partner_id': self.partner_id.id,
            'origin': self.order_id.name,
            'pick_type': 'in',
            'purchase_id': self.order_id.id,
            'location_id': supplier_location.id,
            'location_dest_id': stock_location.id,
            'supplier_reference': self.supplier_reference,
            'inv_date': self.inv_date,
            'state': 'assigned',
            'picking_type_id': picking.id,
            'move_ids_without_package': [(0, 0, {
                'name': self.product_id.name,
                'product_id': self.product_id.id,
                'product_uom': self.product_id.uom_id.id,
                'product_uom_qty': self.stock_done,
                'quantity': 0,
                'location_id': picking.default_location_src_id.id,
                'location_dest_id': picking.default_location_dest_id.id,
                'purchase_line_id': self.id,
                'price_unit': self.price_unit,
                'mfg_date': self.mfg_date,
            })],
        })
        self.order_id.grn_reference = grn.id
        self.order_id.picking_ids = [(4, grn.id)]
        self.balance = self.balanced_delivery - self.stock_done
        self.stock_done = 0.00
        self.balanced_delivery = self.balance
        if self.balanced_delivery != 0.00:
            self.write({
                # 'grn_created': True,
                'status': 'progress',
            })
        else:
            self.write({
                'grn_created': True,
                'status': 'confirm',
            })
        grn.action_confirm()
        stock = self.env['stock.picking'].search([('origin', '=', self.order_id.name), ('state', '=', 'assigned')])
        stock.write({
            'po_date_time': self.order_id.confirm_date
        })
        stock.button_validate()
        stock.print_grn_label()
        stock.create_bill()
        if self.product_id.print_grn_label:
            val = self.env.ref('supplier_perfomance.report_grn_label_pdf').report_action(stock)
        else:
            val = False
        return val

    def generate_grn_po(self):
        stock_location = self.env.ref('stock.stock_location_stock')
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        context = dict(self._context or {})
        purchase_order_line = self.env['purchase.order.line'].sudo().search([('id', 'in', context.get('active_ids'))])
        po_list = []

        for rec in purchase_order_line:
            if rec.state != 'confirm':
                if rec.order_id and rec.order_id not in po_list:
                    po_list.append(rec.order_id)

        for po in po_list:
            move_lines = []

            for pol in purchase_order_line:
                if po.partner_id.id == pol.partner_id.id:
                    move_line_vals = {
                        'product_id': pol.product_id.id,
                        'name': pol.product_id.name,
                        'product_uom': pol.product_id.uom_id.id,
                        'product_uom_qty': pol.stock_done,
                        'quantity': 0,
                        'location_id': supplier_location.id,
                        'location_dest_id': stock_location.id,
                        'purchase_line_id': pol.id,
                    }
                    move_lines.append((0, 0, move_line_vals))

                    pol.balance = pol.balanced_delivery - pol.stock_done
                    pol.stock_done = 0.00
                    pol.balanced_delivery = pol.balance

                    if pol.balanced_delivery != 0.00:
                        pol.write({'status': 'progress'})
                    else:
                        pol.write({'grn_created': True, 'status': 'confirm'})

            picking_vals = {
                'partner_id': po.partner_id.id,
                'origin': po.name,
                'purchase_id': po.id,
                'user_id': self.env.user.id,
                'scheduled_date': fields.Datetime.now(),
                'picking_type_id': self.env.ref('stock.picking_type_in').id,
                'location_id': supplier_location.id,
                'location_dest_id': stock_location.id,
                'state': 'assigned',
                'move_ids_without_package': move_lines,
            }

            picking = self.env['stock.picking'].create(picking_vals)

            po.picking_ids = [(4, picking.id)]

            self.order_id.grn_reference = picking.id

            picking.action_confirm()
            picking.print_grn_label()
            picking.create_bill()

            for r in purchase_order_line:
                if r.product_id.print_grn_label:
                    return self.env.ref('supplier_perfomance.report_grn_label_pdf').report_action(picking)
            else:
                return False


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    _order = 'name desc'

    product_category_ids = fields.Many2many('product.category', domain="[('parent_id', '=', False)]")
    shipping_terms = fields.Selection([
        ('to_your_account', ' To your Account'),
        ('our_scope', 'Our scope'),
    ], string="Shipping Terms")
    shipping_method = fields.Selection([
        ('road', 'Road'),
        ('by_hand', 'By hand'),
        ('by_courier', 'By courier'),
    ], string="Shipping Method")

    created_by_id = fields.Many2one('res.users', string='Create by', related='create_uid', store=True)


    @api.model_create_multi
    def create(self, vals):
        purchase_order = super(PurchaseOrder, self).create(vals)
        if purchase_order.state == 'draft':
            body = 'Purchase Request Created'
        else:
            body = 'Purchase Order Created'
        existing_message = self.env['mail.message'].search([
            ('model', '=', 'purchase.order'),
            ('res_id', '=', purchase_order.id),
        ], limit=1)
        if existing_message:
            existing_message.write({'body': body})
        return purchase_order

    def get_product_category_ids(self):
        product_category_ids_test = [i.name for i in self.env['product.category'].search([('parent_id', '=', False)])]
        data = [{'name': i, 'ticked': False} for i in product_category_ids_test]
        for category in self.product_category_ids:
            for item in data:
                if category.name == item['name']:
                    item['ticked'] = True
        return data

    @api.onchange('order_line', 'product_category_ids')
    def _get_product_category(self):
        for j in self.order_line:
            test = []
            categ = [i.id for i in self.product_category_ids]
            for k in self.product_category_ids:
                val = [o.id for o in k.child_id]
                categ.extend(val)
                test = tuple(categ)
            j.product_category_ids = [(6, 0, test)]

    def get_employee_manager(self):
        emp_ids = self.sudo().env['hr.employee'].search([('user_id', '=', self.env.uid)])
        user_id = self.env['res.users'].search(
            [('employee_id', '=', emp_ids.coach_id.id and emp_ids[0].coach_id.id or False)])
        return user_id

    purchase_type = fields.Selection([
        ('goods', 'Standard'), ('ser', 'Non-Standard'), ], string="Purchase Type", default='goods')
    force_close_remarks = fields.Char(string='Pre Close Remarks')
    cancel_bool = fields.Boolean(string='Cancel', default=True)

    approval_id = fields.Many2one('category.approval', string="Approval Type",
                                  default=lambda self: self.env.ref('approval.category_approval_default',
                                                                    raise_if_not_found=False))
    no_of_approvers = fields.Selection(string='No of Approvers', related='approval_id.no_of_approvers')
    approver_one = fields.Many2one('res.users', string="First Approver", default=get_employee_manager)
    approver_two = fields.Many2one('res.users', string="Second Approver", related='approval_id.approver_two')
    approver_three = fields.Many2one('res.users', string="Third Approver", related='approval_id.approver_three')
    approver_four = fields.Many2one('res.users', string="Fourth Approver", related='approval_id.approver_four')
    approver_five = fields.Many2one('res.users', string="Fifth Approver", related='approval_id.approver_five')
    # remark fields
    remark_one = fields.Char(string="First Approval Remark")
    remark_cancel = fields.Char(string="Cancel Remark")
    remark_reject = fields.Char(string="Reject Remark")
    remark_two = fields.Char(string="Second Approval Remark")
    remark_three = fields.Char(string="Third Approval Remark")
    state = fields.Selection(selection_add=[
        ('draft', 'Request'),
        ('first', 'Waiting for First Approval'),
        ('second', 'Waiting for Second Approval'),
        ('third', 'Waiting for Third Approval'),
        ('to approve', 'To Approve'),
        ('approved', 'Approved'),
        ('sent', 'RFQ Sent'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    done_approvals = fields.Selection([('first', 'First Approver'), ('second', 'Second Approver'),
                                       ('third', 'Third Approver'), ('approved', 'Approved')])
    curr_user = fields.Many2one('res.users', string="User", compute='_compute_user_id')
    attachment = fields.Binary('PDF')
    grn_reference = fields.Many2one('stock.picking', string='Grn Ref')

    purchase_order_create = fields.Boolean(string='Create', copy=False)
    quotation_no = fields.Char(string='Quotation')
    order_seq_no = fields.Char(string='Order', copy=False)
    force_close_bool = fields.Boolean('Force Close')
    notes_col = fields.Text(string='Notes')
    purchase_delivery_type = fields.Selection([
        ('supplier', 'Supplier'),
        ('texelq', 'Texel Q'),
    ], string="Delivery Type", default='supplier')
    confirm_date = fields.Datetime(string='Confirmation Date ')

    current_date = fields.Datetime(string='Current Date', compute='_compute_confirm_date')

    shipped_to = fields.Many2one('res.partner', string='Shipped To')

    is_user_admin = fields.Boolean(compute="_compute_is_user_admin", store=False)

    @api.depends()
    def _compute_is_user_admin(self):
        """Check if the current user is user ID 2."""
        current_user_id = self.env.user.id
        for record in self:
            record.is_user_admin = current_user_id == 2
            


    @api.depends('current_date')
    def _compute_confirm_date(self):
        for record in self:
            record.current_date = datetime.now()

    @api.onchange('purchase_type')
    def get_non_standard_po(self):
        line_ids = [(5, 0, 0)]
        for i in self:
            if i.purchase_type == 'ser':
                line_vals = {
                    'product_id': self.env.ref('purchase_approval.product_product_service').id,
                    'name': self.env.ref('purchase_approval.product_product_service').name,
                    'product_uom': self.env.ref('uom.product_uom_dozen').id,
                }
                line_ids.append((0, 0, line_vals))
            i.order_line = line_ids

    def action_force_close(self):
        view_id = self.env['force.close']
        force = False
        if not self.cancel_bool:
            for i in self.order_line:
                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@2",i)
                if i.product_qty != i.qty_received:
                    print("111111111111111111111111111111111111111111111111",i.product_id.name)
                    self.force_close_bool = True
                    i.status = 'confirm'
                    force = True
                    stock = self.env['stock.picking'].search([('origin', '=', self.name), ('state', '=', 'assigned')])
                    if self.force_close_bool:
                        for picking in stock:
                            picking.state = 'done'

            if not force:
                raise UserError(
                    _(F"Dear{self.env.user.name} All Part Quantity And Received Quantity Are Same So You Didn't "
                      F"Force Close"))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Remarks',
            'res_model': 'force.close',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': view_id.id,
            'view_id': self.env.ref('purchase_approval.force_close_view_form',
                                    False).id,
            'target': 'new',
        }

    def _compute_user_id(self):
        for record in self:
            record.curr_user = self.env.user.id

    def generate_grn(self):
        list_id = self.env.ref('purchase_approval.po_order_line_tree_view').id
        form_id = self.env.ref('purchase_approval.po_order_line_form_view').id
        return {
            'name': _('Generate GRN'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.line',
            'view_type': 'tree',
            'view_mode': 'tree',
            'views': [(list_id, 'tree')],
            'domain': [('state', 'not in', ['cancel']), ('order_id', '=', self.name)],
            'target': 'current'
        }

    def submit_for_approval(self):
        if self.order_line:
            for rec in self.order_line:
                if rec.product_id:
                    
                    if rec.price_unit > 0.00:
                        mail_template = self.env.ref('purchase_approval.mail_template_purchase_indent_approval')
                        current_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        current_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
                        content = (
                            f"The Purchase Indent {self.name} is awaiting for your approval "
                        )
                        context = {
                            'receiver': str(self.approver_one.name),
                            'content': content,
                            'company_name': self.env.company.name,
                            'link': current_url,
                        }
                        email_values = {
                            'email_from': self.env.user.email_formatted,
                            'email_to': self.approver_one.login,
                            'subject': 'Purchase Indent Approval',
                        }
                        mail_template.with_context(**context).send_mail(self.id, force_send=True,
                                                                        email_values=email_values)
                        # if self.is_user_admin == 1:
                        #     self.write({'state': 'third'})
                        # else:
                        self.write({'state': 'first'})
                    else:
                        raise ValidationError(_(
                            "The Product Line items, product price is %s, "
                            "price should be greater than %s, kindly check it", rec.price_unit, rec.price_unit))
        if not self.order_line:
            raise ValidationError("Add Part No and Other Details to Proceed Further")

    def confirm_po_order(self):
        self.state = 'purchase'
        if not self.purchase_order_create:
            self.quotation_no = self.name
            if self.purchase_type == 'goods':
                self.name = self.sudo().env['ir.sequence'].next_by_code('purchase.order.confirm') or '/'
            else:
                self.name = self.sudo().env['ir.sequence'].next_by_code('service.purchase.order.confirm') or '/'
            self.order_seq_no = self.name
            self.purchase_order_create = True
            self.confirm_date = fields.Datetime.now()
        else:
            self.name = self.order_seq_no

    def button_draft(self):
        res = super().button_draft()
        if self.quotation_no:
            self.name = self.quotation_no
        return res

    def button_approved_one(self):
        view = self.env.ref('approval.approval_remark_form_view')
        return {
            'name': _('Purchase Approve Remarks'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.remark',
            'views': [(view.id, 'form')],
            'target': 'new',
            'context': {
                'default_ref_id': self.id,
                'default_remark_type': 'approve',
                'default_done_approvals': 'first',
                'default_model': 'pur',
            },
        }

    def button_approved_two(self):
        view = self.env.ref('approval.approval_remark_form_view')
        return {
            'name': _('Purchase Approve Remarks'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.remark',
            'views': [(view.id, 'form')],
            'target': 'new',
            'context': {
                'default_ref_id': self.id,
                'default_remark_type': 'approve',
                'default_done_approvals': 'second',
                'default_model': 'pur',
            },
        }

    def button_approved_three(self):
        view = self.env.ref('approval.approval_remark_form_view')
        return {
            'name': _('Purchase Approve Remarks'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.remark',
            'views': [(view.id, 'form')],
            'target': 'new',
            'context': {
                'default_ref_id': self.id,
                'default_remark_type': 'approve',
                'default_done_approvals': 'third',
                'default_model': 'pur',
            },
        }

    def button_reject(self):
        view = self.env.ref('approval.approval_remark_form_view')
        return {
            'name': _('Reject Remarks'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.remark',
            'views': [(view.id, 'form')],
            'target': 'new',
            'context': {
                'default_ref_id': self.id,
                'default_remark_type': 'reject',
                'default_model': 'pur',
            },
        }
    
    def button_cancel(self):
        view = self.env.ref('approval.approval_remark_form_view')
        return {
            'name': _('Cancel Remarks'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.remark',
            'views': [(view.id, 'form')],
            'target': 'new',
            'context': {
                'default_ref_id': self.id,
                'default_remark_type': 'cancel',
                'default_model': 'pur',
            },
        }


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    supplier_reference = fields.Char(string='Supplier Reference')
    inv_date = fields.Date(string="Invoice Date")
