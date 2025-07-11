from odoo import api, fields, models, tools, _
from PyPDF2 import PdfFileWriter, PdfFileReader
import io
import base64


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    _description = 'Pay Slip'

    def send_payslip_via_mail(self):
        for rec in self:
            report = self.env.ref('hr_payroll_extended.action_employee_payslip_report_new')
            pdf_content, _ = report.with_context({})._render_qweb_pdf(
                'hr_payroll_extended.action_employee_payslip_report_new', [rec.id])
            password = rec.employee_id.work_phone
            if password:
                encrypted_pdf = self._encrypt_pdf(pdf_content, password)
            else:
                encrypted_pdf = pdf_content
            data_record = base64.b64encode(encrypted_pdf)
            ir_values = {
                'name': "Payslip Report",
                'type': 'binary',
                'datas': data_record,
                'store_fname': 'payslip_report.pdf',
                'mimetype': 'application/pdf',
            }
            data_id = self.env['ir.attachment'].create(ir_values)
            template = self.sudo().env.ref('send_payslip_via_mail.email_template_payslip_via_mail', False)
            template.attachment_ids = [(6, 0, [data_id.id])]
            email_values = {
                'email_to': rec.employee_id.work_email,
                'email_from': self.env.user.email, }
            template.send_mail(rec.id, email_values=email_values, force_send=True)
            template.attachment_ids = [(3, data_id.id)]
            print('=================MAIL SENT==========================')
        return True

    def _encrypt_pdf(self, pdf_content, password):
        """Helper method to encrypt PDF"""

        pdf_writer = PdfFileWriter()
        pdf_reader = PdfFileReader(io.BytesIO(pdf_content))
        for page_num in range(pdf_reader.getNumPages()):
            pdf_writer.addPage(pdf_reader.getPage(page_num))
        pdf_writer.encrypt(user_pwd=password, owner_pwd=None, use_128bit=True)
        output = io.BytesIO()
        pdf_writer.write(output)
        return output.getvalue()

# without encryption
    # def send_payslip_via_mail(self):
    #     for rec in self:
    #         print('===============')
    #         report_template_id =  self.env['ir.actions.report'].sudo()._render_qweb_pdf('hr_payroll_extended.action_employee_payslip_report_new', [self.id])[0]
    #         data_record = base64.b64encode(report_template_id)
    #         ir_values = {
    #             'name': "Payslip Report",
    #             'type': 'binary',
    #             'datas': data_record,
    #             'store_fname': data_record,
    #             'mimetype': 'application/x-pdf',
    #         }
    #         data_id = self.env['ir.attachment'].create(ir_values)
    #         template = self.sudo().env.ref('hr_payroll_extended.email_template_payslip_via_mail', False)
    #         template.attachment_ids = [(6, 0, [data_id.id])]
    #         email_values = {'email_to': self.employee_id.work_email,
    #                         'email_from': self.env.user.email}
    #         template.send_mail(self.id, email_values=email_values, force_send=True)
    #         print('===========================================')
    #         template.attachment_ids = [(3, data_id.id)]
    #         return True

