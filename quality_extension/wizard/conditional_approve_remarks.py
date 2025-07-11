from odoo import api, fields, models, _
from datetime import datetime, date


class ConditionalApproveRemarks(models.TransientModel):
    _name = 'conditional.approve.remarks'
    _description = 'Conditional Approve Remarks'
    _inherit = ['mail.thread']

    remarks = fields.Text('Remarks')
    is_default_remark = fields.Boolean('Enable Default Remark')
    default_remark = fields.Text('Default Remark',
                                 default='Conditional Approve get confirmed Without Remarks')
    record_type = fields.Selection([
        ('inspector', 'Inspector'),
        ('engineer', 'Engineer'),
    ], string='Record Type', default='inspector')

    @api.onchange("is_default_remark")
    def _onchange_is_default_remark(self):
        for val in self:
            if val.is_default_remark:
                val.remarks = val.default_remark
            else:
                val.remarks = ''

    def tick_ok(self):
        applicant_id = self._context.get('active_ids')[0]
        active_id = self.env['incoming.inspection'].search([('id', '=', applicant_id)])
        if self.record_type == 'inspector':
            active_id.write({
                'conditional_approve_remark': self.remarks,
            })
            active_id.inspector_c_approve()
        else:
            active_id.write({
                'state': 'inspector_c_approved',
                'engineer_approve_by': self.env.user.id,
                'engineer_approve_on': fields.Datetime.now(),
                'engineer_approve_type': 'conditional_approve',
                'conditional_approve_remark': self.remarks,
            })
            active_id.complete_receipt()
        return True
