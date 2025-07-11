from odoo import fields, models, api, _
from odoo.exceptions import AccessError, UserError, ValidationError


class ForceClose(models.TransientModel):
    _name = 'force.close'
    _description = 'Force Close Wizard'

    remarks = fields.Char(string='Remarks', required=True)

    def tick_ok(self):
        active_id = self.env.context.get('active_id', False)
        pre_close = self.env['purchase.order'].search([('id', '=', active_id)])
        pre_close.write({
            'force_close_remarks': self.remarks,
            'cancel_bool': False
        })
        pre_close.action_force_close()
