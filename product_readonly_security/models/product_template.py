from odoo import models


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "product.readonly.security.mixin",'mail.thread', 'mail.activity.mixin']
