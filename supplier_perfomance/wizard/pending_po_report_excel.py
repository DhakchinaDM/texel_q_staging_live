from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from datetime import date, datetime
import xlwt
from io import BytesIO
import base64
from base64 import b64decode, b64encode
from xlwt import easyxf


class PendingPoExcel(models.TransientModel):
    _name = 'pending.purchase.order.excel'
    _description = 'Pending Purchase Order Excel'

    start_date = fields.Datetime(string="Start Date")
    end_date = fields.Datetime(string="End Date")
    purchase_orders = fields.Many2many('purchase.order', string='Orders')
    order_type = fields.Selection([('completed', 'Completed'), ('pending', 'Pending')],
                                  string='Type')
    summary_file = fields.Binary('Purchase Report')
    file_name = fields.Char('File Name')
    report_printed = fields.Boolean('Report')
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def tick_ok(self):
        domain = [('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date),
                  ('state', '=', 'draft')]
        orders = self.env['purchase.order'].search(domain)
        data = []
        for val in orders:
            for i in val.order_line:
                var = {
                    'date': val.create_date,
                    'po_num': val.name,
                    'vendor_name': val.partner_id.name,
                    'texelq': i.product_id.default_code,
                    'description': i.product_id.name,
                    'qty_received': i.qty_received,
                    'qty_pending': i.product_qty - i.qty_received
                }
                data.append(var)

        address = str(
            self.company_id.street + self.company_id.street2 + ' ' + self.company_id.city + ' ' + self.company_id.state_id.name + '-' + self.company_id.zip)
        workbook = xlwt.Workbook()

        worksheet1 = workbook.add_sheet('Pending Purchase Order Report')
        design_1 = easyxf('align: horiz center;')
        design_2 = easyxf('align: horiz left;')
        design_3 = easyxf('align: horiz right;')
        design_4 = easyxf('align: horiz right; pattern: pattern solid, fore_colour gray25;font: bold 1;')
        design_5 = easyxf('align: horiz center;font: bold 1;pattern: pattern solid, fore_colour gray25;')
        design_6 = easyxf('align: horiz left;font: bold 1;pattern: pattern solid, fore_colour gray25;')
        design_8 = easyxf('align: horiz left;font: bold 1;')
        heading_format = xlwt.easyxf(
            'font: bold 1;align: horiz center; borders: left thin, right thin, top thin, bottom thin;')

        rows = 0
        worksheet1.set_panes_frozen(True)
        worksheet1.set_horz_split_pos(rows + 1)

        rows += 1
        worksheet1.write_merge(rows, rows, 0, 13, self.company_id.name, design_5)
        rows += 1
        worksheet1.write_merge(rows, rows, 0, 13, address, design_5)
        rows += 2
        worksheet1.write_merge(rows, rows, 0, 13, 'Pending Purchase Order Report', design_5)
        rows += 2
        worksheet1.write_merge(rows, rows, 0, 3, 'Generated By:', design_8)
        worksheet1.write_merge(rows, rows, 4, 6, self.user_id.name, design_2)
        worksheet1.write_merge(rows, rows, 7, 9, 'Date:', design_8)
        worksheet1.write_merge(rows, rows, 10, 13, fields.Datetime.now().strftime('%d-%m-%Y'), design_2)
        rows += 1
        worksheet1.write_merge(rows, rows, 0, 3, 'Start Date:', design_8)
        worksheet1.write_merge(rows, rows, 4, 6, self.start_date.strftime('%d-%m-%Y'), design_2)
        worksheet1.write_merge(rows, rows, 7, 9, 'End Date:', design_8)
        worksheet1.write_merge(rows, rows, 10, 13, self.end_date.strftime('%d-%m-%Y'), design_2)

        rows += 2
        worksheet1.write_merge(rows, rows, 0, 0, 'Date', design_5)
        worksheet1.write_merge(rows, rows, 1, 2, 'P.O.No', design_5)
        worksheet1.write_merge(rows, rows, 3, 4, 'Vendor Name', design_5)
        worksheet1.write_merge(rows, rows, 5, 6, 'Texelq Part No', design_5)
        worksheet1.write_merge(rows, rows, 7, 9, 'Part Description', design_5)
        worksheet1.write_merge(rows, rows, 10, 11, 'Qty Received', design_5)
        worksheet1.write_merge(rows, rows, 12, 13, 'Qty Pending', design_5)
        rows += 1
        cnt = 0
        for datas in data:
            if datas['po_num']:
                worksheet1.write_merge(rows, rows, 1, 2, datas['po_num'], design_2)
            else:
                worksheet1.write_merge(rows, rows, 0, 0, '-', design_1)
            if datas['date']:
                worksheet1.write(rows, cnt, datas['date'].strftime('%d-%m-%Y'), design_2)
            else:
                worksheet1.write(rows, cnt, '-', design_1)
            if datas['vendor_name']:
                worksheet1.write_merge(rows, rows, 3, 4, datas['vendor_name'], design_2)
            else:
                worksheet1.write_merge(rows, rows, 3, 4, '-', design_1)
            if datas['texelq']:
                worksheet1.write_merge(rows, rows, 5, 6, datas['texelq'], design_2)
            else:
                worksheet1.write_merge(rows, rows, 5, 6, '-', design_1)
            if datas['description']:
                worksheet1.write_merge(rows, rows, 7, 9, datas['description'], design_2)
            else:
                worksheet1.write_merge(rows, rows, 7, 9, '-', design_1)
            if datas['qty_received']:
                worksheet1.write_merge(rows, rows, 10, 11, datas['qty_received'], design_3)
            else:
                worksheet1.write_merge(rows, rows, 10, 11, '-', design_1)
            if datas['qty_pending']:
                worksheet1.write_merge(rows, rows, 12, 13, datas['qty_pending'], design_3)
            else:
                worksheet1.write_merge(rows, rows, 12, 13, '-', design_1)
            rows += 1

        fp = BytesIO()
        o = workbook.save(fp)
        fp.read()
        excel_file = base64.b64encode(fp.getvalue())
        self.write(
            {'summary_file': excel_file,
             'file_name': 'Pending PO Report  - [ %s ].xls' % self.start_date.strftime('%d/%m/%Y'),
             'report_printed': True})
        fp.close()
        return {
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'pending.purchase.order.excel',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'target': 'new',
        }
