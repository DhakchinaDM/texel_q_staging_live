from odoo import fields, models, api
import xlwt
import base64
from odoo import http
from odoo.http import request
from xlwt import easyxf
import io
from odoo.addons.web.controllers.main import content_disposition


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    data = fields.Binary('Report')
    responsible = fields.Many2one('res.partner', string='Request Raised By')
    requested = fields.Many2one('res.partner', string='Request Raised For')
    shipment = fields.Boolean('Shipment', copy=False)

    def company_address(self, val):
        output = ""
        if not val:
            if self.user_id.company_id.street:
                output += self.user_id.company_id.street
                output += ","
            if self.user_id.company_id.street2:
                output += self.user_id.company_id.street2
                output += ","
            if self.user_id.company_id.city:
                output += self.user_id.company_id.city
                output += ","
            if self.user_id.company_id.state_id:
                output += self.user_id.company_id.state_id.name
            if self.user_id.company_id.zip:
                output += "-"
                output += self.user_id.company_id.zip
                output += "."
        else:
            if val.name:
                output += val.name
                output += ", \n"
            if val.street:
                output += val.street
                output += ", \n"
            if val.street2:
                output += val.street2
                output += ", \n"
            if val.city:
                output += val.city
                output += ", \n"
            if val.state_id:
                output += val.state_id.name
            if val.zip:
                output += "-"
                output += val.zip
                output += "."
        return output

    def delivery_chalan(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet1 = workbook.add_sheet('Attendance Sheet')

        # Define cell styles
        style_empty_bold_center = easyxf('align: horiz center;font: bold 1;')
        style_empty_bold_left = easyxf('align: horiz left;font: bold 1;')
        style_empty_bold_right = easyxf('align: horiz right;font: bold 1;')
        style_empty_center = easyxf('align: horiz center;')
        style_empty_left = easyxf('align: horiz left;')
        style_empty_right = easyxf('align: horiz right;')
        style_title = easyxf('align: horiz center;font: bold 1;pattern: pattern solid, fore_colour grey25;')
        style_bold = easyxf('align: horiz left;font: bold 1;pattern: pattern solid, fore_colour gray25;')

        # Set column widths
        for col in range(8):
            if col == 2:
                worksheet1.col(col).width = 10000
            elif col == 7:
                worksheet1.col(col).width = 8000
            else:
                worksheet1.col(col).width = 5000

        # Write headers and data
        rows = 0
        cols = 0
        worksheet1.set_panes_frozen(True)
        worksheet1.set_horz_split_pos(rows + 1)
        rows += 1
        worksheet1.write_merge(rows, rows, 0, 7, self.user_id.company_id.name, style_title)
        rows += 1
        worksheet1.write_merge(rows, rows, 0, 7, self.company_address(False), style_title)
        rows += 1
        worksheet1.write_merge(rows, rows, 0, 7, "Delivery Challan", style_empty_bold_center)
        rows += 1
        worksheet1.write(rows, 0, 'GST', style_empty_bold_left)
        worksheet1.write(rows, 1, self.user_id.company_id.vat, style_empty_bold_right)
        worksheet1.write(rows, 6, 'D.C', style_empty_bold_left)
        worksheet1.write(rows, 7, self.name, style_empty_bold_right)
        rows += 1
        worksheet1.write(rows, 0, 'Phone', style_empty_bold_left)
        worksheet1.write(rows, 1, self.user_id.company_id.phone, style_empty_bold_right)
        worksheet1.write(rows, 6, 'Date', style_empty_bold_left)
        worksheet1.write(rows, 7, self.scheduled_date.strftime("%d-%m-%Y"), style_empty_bold_right)
        rows += 1
        worksheet1.write(rows, 6, 'Transport Name', style_empty_bold_left)
        worksheet1.write(rows, 7, self.origin, style_empty_bold_right)
        rows += 2

        worksheet1.write(rows, 0, 'TO ADDRESS', style_empty_bold_left)
        worksheet1.write_merge(rows, rows + 5, 1, 7, self.company_address(self.partner_id), style_empty_bold_left)
        rows += 6

        worksheet1.write_merge(rows, rows, 0, 1, 'Mode of Transport', style_title)
        worksheet1.write(rows, 2, 'Contact Person Name & Phone No', style_title)
        worksheet1.write_merge(rows, rows, 3, 5, 'Supplier Reference', style_title)
        worksheet1.write_merge(rows, rows, 6, 7, 'Place of Supply', style_title)
        rows += 1

        worksheet1.write_merge(rows, rows, 0, 1, '-', style_empty_center)
        worksheet1.write(rows, 2, '', style_empty_center)
        worksheet1.write_merge(rows, rows, 3, 5, '', style_empty_center)
        worksheet1.write_merge(rows, rows, 6, 7, '-', style_empty_center)
        rows += 1
        header_table = ["SL.NO", "PART NO", "PART DESCRIPTION", "SERVICE", "UOM", "QTY", "UNIT PRICE", "TOTAL VALUE"]
        col_val = 0
        for i in header_table:
            worksheet1.write(rows, col_val, i, style_title)
            col_val += 1
        rows += 1
        col_val = 0
        qty = 0.0
        unit_price = 0.0
        total_value = 0.0
        for line in self.move_ids_without_package:
            col_val += 1
            qty += line.quantity
            unit_price += line.product_id.list_price
            total_value += line.quantity * line.product_id.list_price
            worksheet1.write(rows, 0, col_val, style_empty_right)
            worksheet1.write(rows, 1, line.product_id.default_code, style_empty_center)
            worksheet1.write(rows, 2, line.product_id.name, style_empty_left)
            worksheet1.write(rows, 3, line.product_id.categ_id.name, style_empty_left)
            # worksheet1.write(rows, 4, line.kkkkk, style_empty_left)
            worksheet1.write(rows, 4, "NO'S", style_empty_center)
            worksheet1.write(rows, 5, line.quantity, style_empty_right)
            worksheet1.write(rows, 6, line.product_id.list_price, style_empty_right)
            worksheet1.write(rows, 7, line.quantity * line.product_id.list_price, style_empty_right)
        rows += 1

        worksheet1.write_merge(rows, rows, 0, 4, 'Grand Total', style_empty_bold_right)
        worksheet1.write(rows, 5, qty, style_empty_right)
        worksheet1.write(rows, 6, unit_price, style_empty_right)
        worksheet1.write(rows, 7, total_value, style_empty_right)
        rows += 1

        worksheet1.write(rows, 0, 'Rupees', style_empty_bold_left)
        worksheet1.write_merge(rows, rows, 1, 7, self.company_id.currency_id.amount_to_text(int(total_value)),
                               style_empty_bold_left)
        rows += 1

        worksheet1.write_merge(rows, rows, 0, 7, 'Declaration :-',
                               style_empty_bold_left)
        rows += 1

        worksheet1.write_merge(rows, rows+5, 0, 7, 'Declaration :-',
                               style_empty_bold_left)
        rows += 1
        # Save workbook to BytesIO
        fp = io.BytesIO()
        o = workbook.save(fp)
        out = base64.b64encode(fp.getvalue())
        self.write({'data': out})
        cc = {
            'type': 'ir.actions.act_url',
            'url': '/report_module/stock_picking?model=stock.picking&id=%s' % self.id,
            'target': 'new',
        }
        return cc

    class return_xls_download(http.Controller):
        _cp_path = '/report_module'

        @http.route('/report_module/stock_picking', type='http', auth="public")
        def harvest_report_xls_download(self, **data):
            harvest_search = http.request.env['stock.picking'].search([('id', '=', data.get('id'))])
            if harvest_search:
                filecontent = base64.b64decode(harvest_search.data)
                filename = harvest_search.name + " " + 'Delivery Chalan.xls'
                if filecontent and filename:
                    return request.make_response(filecontent,
                                                 headers=[('Content-Type', 'application/octet-stream'),
                                                          ('Content-Disposition', content_disposition(filename))])
            else:
                return request.not_found()
