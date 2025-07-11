from odoo import api, fields, models, _
from datetime import datetime, date


class LayoutRemarks(models.TransientModel):
    _name = 'layout.remarks'
    _description = 'Layout Remarks'
    _inherit = ['mail.thread']

    remarks = fields.Text('Remarks')
    remarks_id = fields.Many2one('layout.request',"Relation")


    def tick_ok(self):
        for i in self:
            if i.remarks_id:
                i.remarks_id.remarks_boolean = True
                i.remarks_id.remarks = i.remarks
                i.remarks_id.layout_state = 're_inspect'