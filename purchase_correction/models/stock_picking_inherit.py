from odoo import models, fields, api, _
from datetime import date, datetime, timedelta


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    po_date_time = fields.Datetime(string='Po Date')
