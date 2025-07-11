from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _description = 'Purchase Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    def _default_employee(self):
        emp_ids = self.sudo().env['hr.employee'].search([('user_id', '=', self.env.uid)])
        return emp_ids and emp_ids[0] or False

    @api.model
    def get_current_user_id(self):
        self.user_id = lambda self: self.env.uid

    name = fields.Char(string="Name", default='New')
    req_date = fields.Date(string="Req.Date", default=fields.Date.context_today)
    partner_id = fields.Many2many('res.partner', string="Supplier", required=True)
    user_id = fields.Many2one('res.users', string="Current User", compute='_compute_user_id')
    record_user_id = fields.Many2one('res.users', string="Record Created by", related='create_uid.user_id')
    part_name = fields.Char(string="Part Name")
    req_details = fields.Text(string="Requirement Details:", required=True)
    delivery_date = fields.Date(string="Delivery Date")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'),
    ], string='State', default='draft', tracking=True)
    capital_goods = fields.Boolean(string="Capital Goods")
    raw_material = fields.Boolean(string="Raw Materials")
    tool_gauge = fields.Boolean(string="Tooling & Gauges")
    cons_serv = fields.Boolean(string="Consumables & service")
    pac_mtr = fields.Boolean(string="Packing Materials")
    general_product = fields.Boolean(string="General Product ")
    request_ids = fields.One2many('purchase.request.line', 'request_id', string="Specifications")
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    purchased_product_qty = fields.Integer(compute='_compute_purchased_product_qty', string='Purchased')
    purchase_tender = fields.Char(string='Tender Ref')
    product_category_ids = fields.Many2many('product.category', domain="[('parent_id', '=', False)]", string="product categ check")
    boolean_category = fields.Boolean(string="General Product")
    product_type = fields.Selection([('existing_product', 'Existing Product'), ('new_product', 'New Product')],
                                    string='Product Type', default='existing_product')

    @api.onchange('request_ids', 'product_category_ids')
    def _get_product_category(self):
        for j in self.request_ids:
            test = []
            categ = [i.id for i in self.product_category_ids]
            for k in self.product_category_ids:
                val = [o.id for o in k.child_id]
                categ.extend(val)
                test = tuple(categ)
            j.product_category_ids = [(6, 0, test)]

    def _compute_purchased_product_qty(self):
        for template in self:
            po = self.env['purchase.agreement'].search_count([('sh_source', '=', template.name)])
            template.purchased_product_qty = po

    def action_view_po(self):
        action = self.env["ir.actions.actions"]._for_xml_id("apps_tender_management.sh_purchase_agreement_action")
        action['domain'] = [('sh_source', '=', self.name)]
        action['display_name'] = _("Purchase History for %s", self.name)
        return action

    @api.depends('user_id')
    def _compute_user_id(self):
        for record in self:
            record.user_id = self.env.user

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.sudo().env['ir.sequence'].next_by_code('purchase.request') or '/'
        return super().create(vals_list)

    def button_submit_new(self):
        if not self.request_ids:
            raise ValidationError("Add Products Before Confirming")
        if self.request_ids:
            product_val = []
            for rec in self.request_ids:
                product_val.append((0, 0, {
                    'part_name': rec.part_name,
                    'sh_qty': rec.req_qty,
                    'supplier_part': rec.supplier_part,
                    'description': rec.supplier_part_no}))
            tender = self.env['purchase.agreement'].sudo().create({
                'email_partner_ids': self.partner_id.ids,
                'sh_source': self.name,
                'product_type': self.product_type,
                'sh_purchase_agreement_line_ids': product_val,
                'sh_delivery_date': self.delivery_date,
                'sh_agreement_deadline': self.delivery_date,
                'sh_agreement_type': self.env.ref('apps_tender_management.package_type_07').id,
                'sh_purchase_user_id': self.env.user.id,
            })
            tender.sudo().action_confirm()
            for rec in tender:
                line_ids = []
                current_date = None
                if rec.sh_delivery_date:
                    current_date = rec.sh_delivery_date
                else:
                    current_date = fields.Datetime.now()
                for rec_line in rec.sh_purchase_agreement_line_ids:
                    line_vals = {
                        'name': rec_line.description,
                        'part_name': rec_line.part_name,
                        'supplier_part': rec_line.supplier_part,
                        'date_planned': current_date,
                        'product_qty': rec_line.sh_qty,
                        'status': 'draft',
                        'agreement_id': rec.id,
                        'price_unit': rec_line.sh_price_unit,
                    }
                    line_ids.append((0, 0, line_vals))
                for supplier in rec.email_partner_ids:
                    an_rfq = self.env['analyze.rfq'].sudo().create({
                        'partner_id': supplier.id,
                        'tender_order': True,
                        'agreement_id': rec.id,
                        'user_id': rec.sh_purchase_user_id.id,
                        'origin': self.name,
                        'order_line': line_ids
                    })
            tender.sudo().action_validate()
            self.write({
                'state': 'confirm',
                'purchase_tender': tender.name,
            })

            return {
                'name': _('Purchase Tender'),
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.agreement',
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': tender.id,
                'domain': [('sh_source', '=', self.name)],
                'target': 'current'
            }

    def button_submit(self):
        if not self.request_ids:
            raise ValidationError("Add Products Before Confirming")
        for rec in self.partner_id:
            mail_template = self.env.ref('purchase_request.mail_template_purchase_request_approval')
            current_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            current_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
            content = (
                f"Here is in attachment a request for quotation {self.name} from {self.company_id.name}. "
                f"Check the mentioned item lists and provide us your best quote to support us. "
                f"If you have any questions, please do not hesitate to contact us. "
                f"Best regards,")
            context = {
                'receiver': ' Supplier',
                'content': content,
                'company_name': self.env.company.name,
                'link': current_url,
            }
            email_values = {
                'email_from': self.env.user.email_formatted,
                'email_to': rec.email,
                'subject': 'Request for Quotation',
            }
            mail_template.with_context(**context).send_mail(self.id, force_send=True, email_values=email_values)
        if self.request_ids:
            product_val = []
            for rec in self.request_ids:
                product_val.append((0, 0, {
                    'sh_product_id': rec.part_id.id,
                    'sh_qty': rec.req_qty,
                    'supplier_part': rec.supplier_part,
                    'description': rec.supplier_part_no,
                }))
            tender = self.env['purchase.agreement'].sudo().create({
                'email_partner_ids': self.partner_id.ids,
                'sh_source': self.name,
                'sh_purchase_agreement_line_ids': product_val,
                'sh_delivery_date': self.delivery_date,
                'sh_agreement_deadline': self.delivery_date,
                'sh_agreement_type': self.env.ref('apps_tender_management.package_type_07').id,
                'sh_purchase_user_id': self.env.user.id,
            })
            tender.sudo().action_confirm()
            for rec in tender:
                line_ids = []
                current_date = None
                if rec.sh_delivery_date:
                    current_date = rec.sh_delivery_date
                else:
                    current_date = fields.Datetime.now()
                for rec_line in rec.sh_purchase_agreement_line_ids:
                    line_vals = {
                        'product_id': rec_line.sh_product_id.id,
                        'name': rec_line.description,
                        'supplier_part': rec_line.supplier_part,
                        'date_planned': current_date,
                        'product_qty': rec_line.sh_qty,
                        'status': 'draft',
                        'agreement_id': rec.id,
                        'product_uom': rec_line.sh_product_id.uom_id.id,
                        'price_unit': rec_line.sh_price_unit,
                    }
                    line_ids.append((0, 0, line_vals))
                for supplier in rec.email_partner_ids:
                    proposal = self.env['purchase.order'].sudo().create({
                        'partner_id': supplier.id,
                        'tender_order': True,
                        'agreement_id': rec.id,
                        'user_id': rec.sh_purchase_user_id.id,
                        'origin': self.name,
                        'order_line': line_ids
                    })
            tender.sudo().action_validate()
            self.write({
                'state': 'confirm',
                'purchase_tender': tender.name,
            })

            return {
                'name': _('Purchase Tender'),
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.agreement',
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': tender.id,
                'domain': [('sh_source', '=', self.name)],
                'target': 'current'
            }

    def button_cancel(self):
        self.write({
            'state': 'cancel'
        })

    def set_to_draft(self):
        self.write({
            'state': 'draft'
        })


class PurchaseRequestLine(models.Model):
    _name = 'purchase.request.line'
    _description = "Purchase Request Line"

    part_id = fields.Many2one('product.product', string="Part No", domain="[('categ_id', 'in', product_category_ids)]")
    part_ids = fields.Many2many('product.product', string="Part Nos Many2many")
    request_id = fields.Many2one("purchase.request", string="Part Name ")
    number = fields.Integer(string="No", compute='_compute_serial_number')
    supplier_part = fields.Char(string='Supplier Part No')
    supplier_part_no = fields.Char(string="Specification")
    req_qty = fields.Integer(string="Required Quantity")
    on_hand_qty = fields.Float(string="On Hand Quantity", related='part_id.qty_available')
    product_category_ids = fields.Many2many('product.category')
    part_name = fields.Char(string='Part Name')

    @api.onchange('part_id')
    def onchange_part_id(self):
        if self.part_id:
            self.supplier_part_no = self.part_id.name
            self.supplier_part = self.part_id.supplier_part
        else:
            self.supplier_part_no = False
            self.supplier_part = False

    # FUNCTION FOR GENERATING SERIAL NUMBER
    @api.depends('request_id.request_ids')
    def _compute_serial_number(self):
        for record in self:
            record.number = 0
        for i in self.mapped('request_id'):
            serial_number = 1
            for line in i.request_ids:
                line.number = serial_number
                serial_number += 1


class ProductProduct(models.Model):
    _inherit = "product.product"

    supplier_part = fields.Char(string='Supplier Part No', compute='get_product_supplier_part', readonly=False)
    print_grn_label = fields.Boolean(string='Print Label', compute='_compute_label')

    def _compute_label(self):
        for rec in self:
            rec.print_grn_label = True if rec.categ_id.id in [37, 38, 9] else False

    @api.depends('product_tmpl_id')
    def get_product_supplier_part(self):
        for product in self:
            if product.product_tmpl_id:
                product.supplier_part = product.product_tmpl_id.supplier_part
            else:
                product.supplier_part = False


class ProductTemplate(models.Model):
    _inherit = "product.template"

    supplier_part = fields.Char(string='Supplier Part No')
