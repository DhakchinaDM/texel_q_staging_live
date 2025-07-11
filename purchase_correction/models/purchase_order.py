from odoo.exceptions import UserError
from odoo import models, fields, api, _
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    alert_mail_date = fields.Date(string="Deadline")

    @api.depends('date_order')
    def alert_message_to_vendor(self):
        today = fields.Date.today()

        order = self.env['purchase.order'].search([])
        for i in order:
            if i.state == 'purchase':
                current_url = i.env['ir.config_parameter'].sudo().get_param('web.base.url')
                current_url += '/web#id=%d&view_type=form&model=%s' % (i.id, i._name)
                if i.date_order:
                    deadline_date = i.date_order.date() - timedelta(days=1)
                    if today == deadline_date:
                        context = {
                            'company_name': i.env.company.name,
                            'link': current_url,
                            'name': i.name,
                            'creater': i.create_uid.name,

                        }

                        email_values = {
                            'subject': "Urgent: Supplier Delivery Delay (" + i.name + "/24-25)",
                            'email_from': i.env.company.email,
                            'email_to': i.create_uid.email,
                        }

                        template = self.sudo().env.ref('purchase_correction.email_template_purchase_req')
                        template.with_context(**context).send_mail(self.id, force_send=True, email_values=email_values)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    comments = fields.Text(string='Comments')
