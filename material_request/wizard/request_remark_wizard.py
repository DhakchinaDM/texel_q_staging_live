from odoo import api, fields, models, _
from datetime import datetime, date


class MaterialRequestApproveRemarks(models.TransientModel):
    _name = 'material.request.approve.remarks'
    _description = 'Material Request Approve Remarks'
    _inherit = ['mail.thread']

    remarks = fields.Text('Remarks')
    is_default_remark = fields.Boolean('Enable Default Remark')
    default_remark = fields.Text('Default Remark',
                                 default='request Approval get confirmed Without Remarks')

    @api.onchange("is_default_remark")
    def _onchange_is_default_remark(self):
        for val in self:
            if val.is_default_remark:
                val.remarks = val.default_remark
            else:
                val.remarks = ''

    def tick_ok(self):
        applicant_id = self._context.get('active_ids')[0]
        active_id = self.env['material.request.indent'].search([('id', '=', applicant_id)])
        today = date.today()
        current_date = today.strftime("%d/%m/%Y")
        current_user = self.env.user.name

        if active_id.state == 'to_be_approved':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_approval()
            active_id.message_post(body=text)
        return True


class MaterialRequestRejectRemarks(models.TransientModel):
    _name = 'material.request.reject.remarks'
    _description = 'Material Request Reject Remarks'
    _inherit = ['mail.thread']

    remarks = fields.Text('Remarks')

    def tick_ok(self):
        applicant_id = self._context.get('active_ids')[0]
        active_id = self.env['material.request.indent'].search([('id', '=', applicant_id)])
        today = date.today()
        current_date = today.strftime("%d/%m/%Y")
        current_user = self.env.user.name

        if active_id.state == 'to_be_approved':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_rejection()
            active_id.write({'manager_approve_reason': text})
        elif active_id.state == 'leader_approval':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_rejection()
            active_id.write({'store_approver_reason': text})
        


class MaterialRequestCancelRemarks(models.TransientModel):
    _name = 'material.request.cancel.remarks'
    _description = 'Material Request Cancel Remarks'
    _inherit = ['mail.thread']

    remarks = fields.Text('Remarks')

    def tick_ok(self):
        applicant_id = self._context.get('active_ids')[0]
        active_id = self.env['material.request.indent'].search([('id', '=', applicant_id)])
        today = date.today()
        current_date = today.strftime("%d/%m/%Y")
        current_user = self.env.user.name

        if active_id.state == 'to_be_approved':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_cancellation()
            # active_id.write({'approver1_cancel_reason': text})
        elif active_id.state == 'leader_approval':
            text = '[ ' + current_user + ' ]' + '[ ' + current_date + ' ]' + ' - ' + self.remarks + '\n'
            active_id.apply_cancellation()
            # active_id.write({'approver2_cancel_reason': text})
        return True

