from odoo import api, fields, models, _
from datetime import datetime, date


class SpcApproveRemarks(models.TransientModel):
    _name = 'spc.approve.remarks'
    _description = 'SPC Conditional Approve Remarks'
    _inherit = ['mail.thread']

    remarks = fields.Text('Remarks')
    is_default_remark = fields.Boolean('Enable Default Remark')
    default_remark = fields.Text('Default Remark',
                                 default='Conditional Approve get confirmed Without Remarks')

    @api.onchange("is_default_remark")
    def _onchange_is_default_remark(self):
        if self.is_default_remark:
            self.remarks = self.default_remark
        else:
            self.remarks = ''

    def tick_ok(self):
        applicant_id = self._context.get('active_ids')[0]
        active_id = self.env['spc.plan.line'].search([('id', '=', applicant_id)])
        if not active_id.first_approve_done:
            active_id.write({
                'conditional_approve_remark': self.remarks,
                'conditional_approve_remark_time': fields.Datetime.now(),
                'first_approve': self.env.user,
                'state': 'conditionally_approved',
                'first_approve_done': 'True'
            })
        else:
            active_id.write({
                'conditional_approve_remark_two': self.remarks,
                'conditional_approve_remark_two_time': fields.Datetime.now(),
                'second_approve': self.env.user,
                'done_bool': True,
                'state': 'conditionally_approved',
            })


class SpcRejectRemarks(models.TransientModel):
    _name = 'spc.reject.remarks'
    _description = 'SPC Reject Remarks'
    _inherit = ['mail.thread']

    remarks = fields.Text('Remarks')
    is_default_remark = fields.Boolean('Enable Default Remark')
    default_remark = fields.Text('Default Remark',
                                 default='Reject get confirmed Without Remarks')

    @api.onchange("is_default_remark")
    def _onchange_is_default_remark(self):
        if self.is_default_remark:
            self.remarks = self.default_remark
        else:
            self.remarks = ''

    def tick_ok(self):
        applicant_id = self._context.get('active_ids')[0]
        active_id = self.env['spc.plan.line'].search([('id', '=', applicant_id)])
        if not active_id.first_approve_done:
            active_id.write({
                'reject_remark': self.remarks,
                'first_approve_reject': self.env.user,
                'approve_remark_time': fields.Datetime.now(),
                'first_approve_done': 'True',
                'state': 'revisit',
            })
        else:
            active_id.write({
                'reject_remark_2': self.remarks,
                'approve_remark_time_2': fields.Datetime.now(),
                'first_approve_reject_2': self.env.user,
                'done_bool': True,
                'state': 'revisit',
            })
            active_id.action_revision()
