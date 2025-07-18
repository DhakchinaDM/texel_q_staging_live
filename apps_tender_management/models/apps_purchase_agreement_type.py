# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PurchaseAgreementType(models.Model):
    _name = 'purchase.agreement.type'
    _description = 'Purchase Agreement Type'
    _rec_name = 'name'

    name = fields.Char("Name", required=True)
