from odoo import fields, models, api, _
from odoo.exceptions import AccessError, UserError, ValidationError
from datetime import date
import logging

class ApprovalRemark(models.TransientModel):
    _name = 'approval.remark'
    _description = 'Description'

    name = fields.Char(string="Remarks", required=True)
    remark_type = fields.Selection([
        ('approve', 'Approve Remark'),
        ('reject', 'Reject Remark'),
        ('cancel', 'Cancel Remark'),
    ], string="Remark Type")
    model = fields.Selection([
        ('pur', 'Purchase'),
        ('pur_req', 'Purchase Request'),
    ], string="Approval Class")
    done_approvals = fields.Selection(
        [('first', 'First Approver'), ('second', 'Second Approver'), ('third', 'Third Approver'),
         ('approved', 'Approved'),
         ], string="Done Approvals")
    approval_remark = fields.Boolean(string="Default Remark")
    reject_remark = fields.Boolean(string="Default Remark ")
    cancel_remark = fields.Boolean(string="Default Remark  ")

    @api.onchange('approval_remark')
    def default_remark_approve(self):
        if self.approval_remark:
            self.name = "The Approval will proceed without remark"
        if not self.approval_remark:
            self.name = False

    @api.onchange('reject_remark')
    def default_remark_reject(self):
        if self.reject_remark:
            self.name = "The Rejection will proceed without remark"
        if not self.reject_remark:
            self.name = False

    @api.onchange('cancel_remark')
    def default_remark_cancel(self):
        if self.cancel_remark:
            self.name = "The Cancellation will proceed without remark"
        if not self.cancel_remark:
            self.name = False

    def request_cancel(self):
        active_ids = self.env.context.get('active_ids')
        active_id = self.env['purchase.request'].search([('id', 'in', active_ids)])
        today = date.today()
        current_date = today.strftime("%d/%m/%Y")
        current_user = self.env.user.name
        active_id.write({
            'state': 'cancel',
            'remark_cancel': '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.name + '\n',
        })

    def request_reject(self):
        active_ids = self.env.context.get('active_ids')
        active_id = self.env['purchase.request'].search([('id', 'in', active_ids)])
        today = date.today()
        current_date = today.strftime("%d/%m/%Y")
        current_user = self.env.user.name
        active_id.write({
            'state': 'reject',
            'remark_reject': '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.name + '\n',
        })

    def approve(self):
        active_ids = self.env.context.get('active_ids')
        active_id = self.env['purchase.request'].search([('id', 'in', active_ids)])
        if self.remark_type == 'approve':
            if self.model == 'pur_req':
                if active_id.request_ids:
                    product_val = []
                    for rec in active_id.request_ids:
                        product_val.append((0, 0, {
                            'product_id': rec.part_id.id,
                            'product_qty': rec.req_qty,
                            'product_uom': rec.part_id.uom_id.id,
                            'price_unit': 1,
                        }))
                    self.env['purchase.order'].sudo().create({
                        'partner_id': active_id.partner_id.id,
                        'origin': active_id.name,
                        'order_line': product_val,
                    })
                    active_id.write({
                        'state': 'approved',
                        'remark': self.name,
                    })
                if not active_id.request_ids:
                    raise ValidationError(_("Please add the part number before proceeding"))
        elif self.remark_type == 'reject':
            active_id.write({
                'state': 'reject',
                'remark': self.name,
            })
        elif self.remark_type == 'cancel':
            active_id.write({
                'state': 'cancel',
                'remark': self.name,
            })

    def approve_one(self):
        active_ids = self.env.context.get('active_ids')
        purchase_id = self.env['purchase.order'].search([('id', 'in', active_ids)])
        today = date.today()
        current_date = today.strftime("%d/%m/%Y")
        current_user = self.env.user.name
        user_id =purchase_id.is_user_admin
        # if purchase_id.approval_id.purchase_limit_one > purchase_id.amount_total:
        #     mail_template = self.env.ref('purchase_approval.mail_template_purchase_indent_approval')
        #     current_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        #     current_url += '/web#id=%d&view_type=form&model=%s' % (purchase_id.id, purchase_id._name)
        #     content = (
        #         f"The Purchase Indent {purchase_id.name} has been Approved and the Purchase Order has been Created"
        #     )
        #     context = {
        #         'receiver': str(purchase_id.create_uid.name),
        #         'content': content,
        #         'company_name': purchase_id.env.company.name,
        #     }
        #     email_values = {
        #         'email_from': purchase_id.env.user.email_formatted,
        #         'email_to': purchase_id.create_uid.login,
        #         'subject': 'Purchase Indent Approved',
        #     }
        #     mail_template.with_context(**context).send_mail(purchase_id.id, force_send=True, email_values=email_values)
        #     purchase_id.write({
        #         'state': 'approved',
        #         'done_approvals': 'first',
        #         'remark_one': '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.name + '\n',
        #     })
        # elif purchase_id.approval_id.purchase_limit_one < purchase_id.amount_total:
        mail_template = self.env.ref('purchase_approval.mail_template_purchase_indent_approval')
        current_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        current_url += '/web#id=%d&view_type=form&model=%s' % (purchase_id.id, purchase_id._name)
        content = (
            f"The Purchase Indent {purchase_id.name}, first approval has been completed and waiting for second Level of Approval"
        )
        context = {
            'receiver': str(purchase_id.approver_two.name),
            'content': content,
            'company_name': purchase_id.env.company.name,
            'link': current_url,
        }
        email_values = {
            'email_from': purchase_id.env.user.email_formatted,
            'email_to': purchase_id.approver_two.login,
            'subject': 'Purchase Indent Approval',
        }
        mail_template.with_context(**context).send_mail(purchase_id.id, force_send=True, email_values=email_values)
        if user_id == 1:
            purchase_id.write({
                'state': 'approved',
                'done_approvals': 'first',
                'remark_one': '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.name + '\n',
            })
        else:
            purchase_id.write({
                'state': 'second',
                'done_approvals': 'first',
                'remark_one': '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.name + '\n',
            })

    def approve_second(self):
        active_ids = self.env.context.get('active_ids')
        purchase_id = self.env['purchase.order'].search([('id', 'in', active_ids)])
        today = date.today()
        current_date = today.strftime("%d/%m/%Y")
        current_user = self.env.user.name
        if purchase_id.state == 'second':
            # if purchase_id.approval_id.purchase_limit_one < purchase_id.amount_total and purchase_id.approval_id.purchase_limit_two > purchase_id.amount_total:
            #     mail_template = self.env.ref('purchase_approval.mail_template_purchase_indent_approval')
            #     current_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            #     current_url += '/web#id=%d&view_type=form&model=%s' % (purchase_id.id, purchase_id._name)
            #     content = (
            #         f"The Purchase Indent {purchase_id.name} has been Approved"
            #     )
            #     context = {
            #         'receiver': str(purchase_id.create_uid.name),
            #         'content': content,
            #         'company_name': purchase_id.env.company.name,
            #         'link': current_url,
            #     }
            #     email_values = {
            #         'email_from': purchase_id.env.user.email_formatted,
            #         'email_to': purchase_id.create_uid.login,
            #         'subject': 'Purchase Indent Approved',
            #     }
            #     mail_template.with_context(**context).send_mail(purchase_id.id, force_send=True,
            #                                                     email_values=email_values)
            #     purchase_id.write({
            #         'state': 'approved',
            #         'done_approvals': 'second',
            #         'remark_two': '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.name + '\n',
            #     })
            # elif purchase_id.approval_id.purchase_limit_one < purchase_id.amount_total and purchase_id.approval_id.purchase_limit_two < purchase_id.amount_total:
            mail_template = self.env.ref('purchase_approval.mail_template_purchase_indent_approval')
            current_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            current_url += '/web#id=%d&view_type=form&model=%s' % (purchase_id.id, purchase_id._name)
            content = (
                f"The Purchase Indent {purchase_id.name} second approval has been completed and waiting for third Level of Approval"
            )
            context = {
                'receiver': str(purchase_id.approver_three.name),
                'content': content,
                'company_name': purchase_id.env.company.name,
                'link': current_url,
            }
            email_values = {
                'email_from': purchase_id.env.user.email_formatted,
                'email_to': purchase_id.approver_three.login,
                'subject': 'Purchase Indent Approved',
            }
            email_valuess = {
                'email_from': purchase_id.env.user.email_formatted,
                'email_to': purchase_id.create_uid.login,
                'subject': 'Purchase Indent Approved',
            }
            mail_template.with_context(**context).send_mail(purchase_id.id, force_send=True,
                                                            email_values=email_values)
            purchase_id.write({
                'state': 'approved',
                'done_approvals': 'second',
                'remark_two': '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.name + '\n',
            })

    def approve_third(self):
        active_ids = self.env.context.get('active_ids')
        purchase_id = self.env['purchase.order'].search([('id', 'in', active_ids)])
        today = date.today()
        current_date = today.strftime("%d/%m/%Y")
        current_user = self.env.user.name
        if purchase_id.state == 'third':
            mail_template = self.env.ref('purchase_approval.mail_template_purchase_indent_approval')
            current_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            current_url += '/web#id=%d&view_type=form&model=%s' % (purchase_id.id, purchase_id._name)
            content = (
                f"The Purchase Indent {purchase_id.name} has been Approved"
            )
            context = {
                'receiver': str(purchase_id.create_uid.name),
                'content': content,
                'company_name': purchase_id.env.company.name,
                'link': current_url,
            }
            email_values = {
                'email_from': purchase_id.env.user.email_formatted,
                'email_to': purchase_id.create_uid.login,
                'subject': 'Purchase Indent Approved',
            }
            mail_template.with_context(**context).send_mail(purchase_id.id, force_send=True,
                                                            email_values=email_values)
        purchase_id.write({
            'state': 'approved',
            'done_approvals': 'third',
            'remark_three': '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.name + '\n',
        })

    def cancel_approve(self):
        active_ids = self.env.context.get('active_ids')
        purchase_id = self.env['purchase.order'].search([('id', 'in', active_ids)])
        current_user = self.env.user.name
        remarks_text = self.name or "No remarks provided."
        today = date.today().strftime("%d/%m/%Y")
        
        message = _("Purchase request cancelled by %s on %s with remarks: %s") % (current_user, today, remarks_text)
        
        for purchase in purchase_id:
            purchase.message_post(body=message)
        
        purchase_id.write({
            'state': 'cancel',
            'done_approvals': 'third',
            'remark_cancel': self.name,
        })

    def reject(self):
        active_ids = self.env.context.get('active_ids')
        
        if not active_ids:
            return  

        purchase_orders = self.env['purchase.order'].browse(active_ids)  
        current_user = self.env.user.name
        remarks_text = self.name or "No remarks provided."
        today = date.today().strftime("%d/%m/%Y")
        
        message = _("Purchase request rejected by %s on %s with remarks: %s") % (current_user, today, remarks_text)

        for purchase in purchase_orders:
            purchase.message_post(body=message)

        purchase_orders.write({
            'state': 'reject',
            'done_approvals': 'third',
            'remark_reject': self.name,
        })
