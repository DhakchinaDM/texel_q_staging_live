from odoo import models, fields, api, _
from datetime import date, datetime, timedelta


class PurchaseInherit(models.Model):
    _inherit = 'purchase.order'

    five_days = fields.Char(string='Five Days', compute='_compute_five_days', store=True)
    red = fields.Boolean(string='Red', compute='_compute_five_days', store=True)
    orange = fields.Boolean(string='Orange', compute='_compute_five_days', store=True)
    green = fields.Boolean(string='Green', compute='_compute_five_days', store=True)
    current_date = fields.Datetime(string='Current Date', compute='_compute_current_date',
                                   default=lambda self: fields.Date.today())
    purchase_attachment = fields.Binary(string='Attachment')
    purchase_attachment_ids = fields.Many2many('ir.attachment', string="Attachment ")

    @api.depends('current_date')
    def _compute_current_date(self):
        for record in self:
            record.current_date = date.today()

    @api.depends('date_planned')
    def _compute_five_days(self):
        for record in self:
            if record.current_date and record.date_planned:
                delta = record.date_planned - record.current_date
                record.five_days = delta.days
                if '5' >= record.five_days >= '1':
                    record.red = False
                    record.orange = True
                    record.green = False
                elif record.five_days <= '0':
                    record.red = True
                    record.orange = False
                    record.green = False
                else:
                    record.red = False
                    record.orange = False
                    record.green = True
            else:
                record.five_days = '0'
