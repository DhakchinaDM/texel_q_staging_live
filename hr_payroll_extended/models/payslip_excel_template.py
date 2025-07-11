from odoo import api, fields, models, _


class PayslipExcelTemplate(models.Model):
    _name = 'payslip.excel.template'
    _description = 'Excel Payslip Template'
    _rec_name = 'ref'

    name = fields.Binary(string='Excel Template')
    ref = fields.Text(string='Reference')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payroll_excel_template_id = fields.Many2one('payslip.excel.template', string='Payroll Excel Template',
                                                default=lambda self: self.env.ref(
                                                    'hr_payroll_extended.payslip_template_1').id)
