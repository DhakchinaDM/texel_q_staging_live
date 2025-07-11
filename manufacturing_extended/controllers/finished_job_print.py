import base64
import io
import qrcode
from odoo import http
from odoo.http import request
from odoo.tools.safe_eval import safe_eval

class WorkorderReportController(http.Controller):

    def generate_qr_code(self, data):
        """Generate a QR code image from the given data."""
        qr = qrcode.make(data)
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def generate_pdf(self, workorder, report_type):
        """Generate a PDF for the given workorder and type."""
        qr_data = f"Workorder: {workorder.name}\nEmployee: {workorder.employee_id.name}\nStart Time: {workorder.date_start}\nEnd Time: {workorder.date_end}"
        qr_code = self.generate_qr_code(qr_data)

        pdf_content = request.env.ref('manufacturing_extended.report_production_job')._render_qweb_pdf(
            workorder.id, data={'qr_code': qr_code, 'report_type': report_type}
        )
        return pdf_content[0]

    @http.route('/workorder/download_report', type='http', auth='user', methods=['POST'])
    def download_report(self, **kwargs):
        workorder_id = int(kwargs.get("workorder_id"))
        report_type = kwargs.get("report_type")

        workorder = request.env['mrp.workorder'].browse(workorder_id)

        if workorder.exists():
            pdf_content = self.generate_pdf(workorder, report_type)
            pdf_name = f"workorder_{report_type}.pdf"

            headers = [
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename="{pdf_name}"')
            ]

            return request.make_response(pdf_content, headers)
        return request.not_found()
