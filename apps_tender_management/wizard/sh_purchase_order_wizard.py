from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError


class ShPurchaseOrderWizard(models.TransientModel):
    _name = 'purchase.order.wizard'
    _description = 'Purchase Order Wizard'

    sh_group_by_partner = fields.Boolean("Group By")

    def action_create_po(self):

        context = dict(self._context or {})
        purchase_order_line = self.env['purchase.order.line'].sudo().search([('id', 'in', context.get('active_ids'))])

        if purchase_order_line:
            if not self.sh_group_by_partner:
                order_ids = []
                for order_line in purchase_order_line:
                    if order_line.price_unit == 0:
                        raise ValidationError("Please Check the Unit Price")

                    purchase_order_id = self.env['purchase.order'].sudo().create({
                        'partner_id': order_line.partner_id.id,
                        'date_order': fields.Datetime.now(),
                        'agreement_id': order_line.agreement_id.id,
                        'user_id': self.env.user.id,
                        'date_planned': order_line.date_planned,
                        'selected_order': True,
                        'payment_term_id': order_line.order_id.payment_term_id.id,
                        'attachment': order_line.order_id.attachment,
                        'notes_col': order_line.order_id.notes_col,
                        'partner_ref': order_line.order_id.partner_ref,
                        'alert_mail_date': order_line.order_id.alert_mail_date,
                        'purchase_delivery_type': order_line.order_id.purchase_delivery_type,
                    })
                    order_ids.append(purchase_order_id.id)
                    line_vals = {
                        'order_id': purchase_order_id.id,
                        'product_id': order_line.product_id.id,
                        'name': order_line.name,
                        'supplier_part': order_line.supplier_part,
                        'date_planned': order_line.date_planned,
                        'status': 'draft',
                        'product_uom': order_line.product_id.uom_id.id,
                        'product_qty': order_line.product_qty,
                        'price_unit': order_line.price_unit,
                        'date': order_line.date,
                        'taxes_id': [(6, 0, order_line.taxes_id.ids)]
                    }
                    purchase_order_line = self.env['purchase.order.line'].sudo().create(line_vals)
                return {
                    'name': _("Purchase Orders/RFQ's"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'domain': [('id', 'in', order_ids), ('selected_order', '=', True)],
                    'target': 'current'
                }
            else:
                partner_list = []
                agreement_id = None
                attachment = None
                payment_term_id = None
                notes_col = None
                order_ids = []
                for order_line in purchase_order_line:
                    if order_line.price_unit == 0:
                        raise ValidationError("Please Check the Unit Price")
                    if order_line.partner_id and order_line.partner_id not in partner_list:
                        partner_list.append(order_line.order_id)
                    agreement_id = order_line.agreement_id.id
                for partner in partner_list:
                    order_vals = {
                        'partner_id': partner.partner_id.id,
                        'user_id': self.env.user.id,
                        'date_order': fields.Datetime.now(),
                        'agreement_id': agreement_id,
                        'selected_order': True,
                        'payment_term_id': partner.payment_term_id.id,
                        'attachment': partner.attachment,
                        'notes_col': partner.notes_col,
                        'partner_ref': partner.partner_ref,
                        'alert_mail_date': partner.alert_mail_date,
                        'purchase_delivery_type': partner.purchase_delivery_type,
                        # 'date': partner.date,
                    }
                    order_id = self.env['purchase.order'].create(order_vals)
                    order_ids.append(order_id.id)
                    line_ids = []
                    for order_line in purchase_order_line:
                        if order_line.partner_id.id == partner.partner_id.id:
                            order_line_vals = {
                                'order_id': order_id.id,
                                'product_id': order_line.product_id.id,
                                'name': order_line.product_id.name,
                                'date_planned': order_line.date_planned,
                                'status': 'draft',
                                'product_uom': order_line.product_id.uom_id.id,
                                'product_qty': order_line.product_qty,
                                'price_unit': order_line.price_unit,
                                'date': order_line.date,
                                'taxes_id': [(6, 0, order_line.taxes_id.ids)]
                            }
                            line_ids.append((0, 0, order_line_vals))
                    order_id.order_line = line_ids
                return {
                    'name': _("Purchase Orders/RFQ's"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'domain': [('id', 'in', order_ids), ('selected_order', '=', True)],
                    'target': 'current'
                }
