from odoo import models, fields, api, _
from datetime import timedelta
from datetime import date, datetime
import xlwt
from io import BytesIO
from xlwt import easyxf, Borders
import io
import base64
from odoo.tools import base64_to_image
from PIL import Image


class SupplierPerformance(models.TransientModel):
    _name = 'supplier.performance'
    _description = 'Supplier Performance Report'

    partner_id = fields.Many2one('res.partner', string="Supplier")
    months_selection = fields.Selection([('month', 'Last Month'), ('3_month', ' 3 Months'), ('6_month', '6 Months'),
                                         ('year', 'Last Year')],
                                        string='Months', default='6_month')
    summary_file = fields.Binary('Product Report')
    file_name = fields.Char('File Name')
    report_printed = fields.Boolean(' Report')
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    select_month = fields.Selection([
        ('January', 'January'),
        ('February', 'February'),
        ('March', 'March'),
        ('April', 'April'),
        ('May', 'May'),
        ('June', 'June'),
        ('July', 'July'),
        ('August', 'August'),
        ('September', 'September'),
        ('October', 'October'),
        ('November', 'November'),
        ('December', 'December'),
    ], string="Month", default=lambda self: datetime.now().strftime('%B'))
    year_master = fields.Many2one('hr.payroll.year', string='Year',
                                  default=lambda self: self._default_year())

    @api.model
    def _default_year(self):
        current_year = datetime.now().year
        year = self.env['hr.payroll.year'].search([('name', '=', str(current_year))])
        return year and year.id or False

    @api.onchange('select_month', 'year_master')
    def _compute_dates(self):
        for record in self:
            if record.select_month:
                current_year = datetime.now().year
                year = int(self.year_master.name) if self.year_master.name else current_year
                month = datetime.strptime(record.select_month, '%B').month
                first_day = date(year, month, 1)
                if month == 12:
                    last_day = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    last_day = date(year, month + 1, 1) - timedelta(days=1)
                record.start_date = first_day
                record.end_date = last_day

    def tick_ok(self):
        today = fields.Datetime.now()
        domain = []
        pat_domain = []
        if self.select_month and self.year_master:
            domain.append(('date_done', '>=', self.start_date))
            domain.append(('date_done', '<=', self.end_date))
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
            pat_domain.append(('id', '=', self.partner_id.id))
        stock_picking = self.env['stock.picking'].search(domain)
        partner = [{'name': i.name, 'id': i.id, 'data': []} for i in self.env['res.partner'].search(pat_domain)]
        for stock in stock_picking:
            for pat in partner:
                if stock.partner_id.id == pat['id']:
                    for line in stock.move_ids:
                        pat['data'].append({
                            'product': line.product_id.name,
                            'part_no': line.product_id.default_code,
                            'order_date': stock.scheduled_date,
                            'delivery_date': stock.date_done,
                            'deadline': stock.date_deadline,
                            'order_qty': line.product_uom_qty,
                            'delivery_qty': line.quantity,
                            'state': stock.state,
                            'name': stock.name,
                            'origin': stock.origin,
                        })
        workbook = xlwt.Workbook()
        worksheet1 = workbook.add_sheet('Supplier Performance Report')

        design_9 = easyxf('align: horiz right;')
        design_12 = easyxf(
            'align: horiz right; pattern: pattern solid, fore_colour gray25; font: bold 1;')
        design_13 = easyxf(
            'align: horiz center; font: bold 1; pattern: pattern solid, fore_colour gray25;')
        design_14 = easyxf(
            'align: horiz left; font: bold 1; pattern: pattern solid, fore_colour gray25;')

        # BORDER TOP,BOTTOM,RIGHT & LEFT [THIN]
        design_7 = easyxf(
            'align: horiz center;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_8 = easyxf(
            'align: horiz left;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_15 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 320; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_16 = easyxf(
            'align: horiz left, vert center; font: bold 1, height 250; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_17 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 250; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_18 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 200; pattern: pattern solid, fore_colour 0x2B;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_19 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 200; pattern: pattern solid, fore_colour 0x2B;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;'
            'align: wrap on, vert center, horiz center;')

        # BORDER TOP,BOTTOM,RIGHT & LEFT [MEDIUM]
        design_20 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 200; pattern: pattern solid, fore_colour white;'
            'borders: left medium, right medium, top medium, bottom medium, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        # BORDER TOP,LEFT & BOTTOM
        design_21 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 150;'
            'borders: left medium, top medium, bottom medium, left_colour black, top_colour black, bottom_colour black;')
        # BORDER TOP & BOTTOM
        design_22 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 150;'
            'borders: top medium, bottom medium, top_colour black, bottom_colour black;')
        # BORDER TOP,BOTTOM & RIGHT
        design_23 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 150;'
            'borders: right medium, top medium, bottom medium, right_colour black, top_colour black, bottom_colour black;')
        # BORDER TOP & LEFT
        design_24 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 150;'
            'borders: left medium, top medium, left_colour black, top_colour black;')
        # BORDER LEFT
        design_25 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 150;'
            'borders: left medium, left_colour black;')
        # BORDER LEFT & BOTTOM
        design_26 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 150;'
            'borders: left medium, bottom medium, left_colour black, bottom_colour black;')
        # BORDER TOP
        design_27 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 150;'
            'borders: top medium, top_colour black;')
        # NO BORDER APPLIED FOR design_28
        design_28 = easyxf('align: horiz center, vert center;''font: bold 1,height 150;')
        # BORDER BOTTOM
        design_29 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 150;'
            'borders: bottom medium, bottom_colour black;')
        # BORDER TOP & RIGHT
        design_30 = easyxf(
            'align: horiz left, vert center; font: bold 1, height 150;'
            'borders: top medium, right medium, top_colour black, right_colour black;')
        # BORDER RIGHT
        design_31 = easyxf(
            'align: horiz left, vert center; font: bold 1, height 150;'
            'borders: right medium, right_colour black;')
        # BORDER BOTTOM & RIGHT
        design_32 = easyxf(
            'align: horiz left, vert center; font: bold 1, height 150;'
            'borders: bottom medium, right medium, bottom_colour black, right_colour black;')
        # BORDER TOP,RIGHT & LEFT
        design_33 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 150, underline on;'
            'borders: top medium, right medium, left medium, left_colour black, right_colour black, top_colour black;')
        # BORDER RIGHT & LEFT
        design_34 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 150;'
            'borders: right medium, left medium, left_colour black, right_colour black;')
        # BOTTOM RIGHT & LEFT
        design_35 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 150;'
            'borders: bottom medium, right medium, left medium, left_colour black, right_colour black, bottom_colour black;')
        # BORDER RIGHT
        design_36 = easyxf(
            'align: horiz left, vert center; font: bold 1, height 150;'
            'borders: right thin, right_colour black;')

        for i in range(2, 14):
            worksheet1.col(0).width = 1600
            worksheet1.col(1).width = 6000
            worksheet1.col(i).width = 3000
            worksheet1.col(14).width = 3500
            worksheet1.col(15).width = 3500
            worksheet1.col(16).width = 3500
            worksheet1.col(17).width = 4000
            worksheet1.col(18).width = 3500

        worksheet1.row(0).height_mismatch = True
        worksheet1.row(0).height = 1000
        worksheet1.row(1).height = 600
        worksheet1.row(2).height = 450
        worksheet1.row(3).height = 750
        rows = 0
        serial_no = 1

        # TO SET THE 1ST 4 ROW FREEZE
        worksheet1.set_panes_frozen(True)
        worksheet1.set_horz_split_pos(rows + 4)

        # COMPANY LOGO
        if self.company_id.logo:
            pil_image = base64_to_image(self.company_id.logo)
            pil_image = pil_image.resize((140, 15))
            im = pil_image
            image_parts = im.split()
            r = image_parts[0]
            g = image_parts[1]
            b = image_parts[2]
            img = Image.merge("RGB", (r, g, b))
            fo = io.BytesIO()
            img.save(fo, format='bmp')

            worksheet1.insert_bitmap_data(fo.getvalue(), rows, 0)
        cell_style_logo = easyxf(
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;'
        )
        worksheet1.write_merge(rows, rows, 0, 2, '', cell_style_logo)
        worksheet1.write_merge(rows, rows, 3, 15, 'EXTERNAL PROVIDERS PERFORMANCE MONITORING REGISTER', design_15)
        worksheet1.write_merge(rows, rows, 16, 18, 'PUR/DI/R/07', design_15)
        rows += 1
        for i in partner:
            epn = "EXTERNAL PROVIDER NAME : " + str(i['name'])
            worksheet1.write_merge(rows, rows, 0, 12, epn, design_16)
            period = str(self.select_month) + "-", str(self.year_master.name)
            worksheet1.write_merge(rows, rows, 13, 18, period, design_17)
            rows += 1
            worksheet1.write_merge(rows, rows + 1, 0, 0, 'S No', design_18)
            worksheet1.write_merge(rows, rows + 1, 1, 1, 'Part Name', design_18)
            worksheet1.write_merge(rows, rows + 1, 2, 2, 'Part No', design_18)
            worksheet1.write_merge(rows, rows, 3, 5, 'DELIVERY RATING', design_18)
            worksheet1.write_merge(rows, rows, 6, 9, 'QUALITY RATING - INCOMING', design_18)
            worksheet1.write_merge(rows, rows, 10, 13, 'QUALITY RATING - PROCESS', design_18)
            worksheet1.write_merge(rows, rows + 1, 14, 14, 'INCIDENT OF EXCESS FRIEGHT', design_19)
            worksheet1.write_merge(rows, rows + 1, 15, 15, 'CUSTOMER COMPLAINTS', design_19)
            worksheet1.write_merge(rows, rows + 1, 16, 16, 'OVERALL RATING', design_19)
            worksheet1.write_merge(rows, rows + 1, 17, 17, 'PERFORMANCE STATUS', design_19)
            worksheet1.write_merge(rows, rows + 1, 18, 18, 'FIRST TIME THROUGH', design_19)

            rows += 1
            worksheet1.write(rows, 3, 'Schedule Qty', design_19)
            worksheet1.write(rows, 4, 'Received Qty', design_19)
            worksheet1.write(rows, 5, 'Percentage %', design_19)

            worksheet1.write(rows, 6, 'Received Qty', design_19)
            worksheet1.write(rows, 7, 'Accepted Qty', design_19)
            worksheet1.write(rows, 8, 'Rejected Qty', design_19)
            worksheet1.write(rows, 9, 'QUALITY RATING', design_19)

            worksheet1.write(rows, 10, 'Prod Qty', design_19)
            worksheet1.write(rows, 11, 'OK  Qty', design_19)
            worksheet1.write(rows, 12, 'Rejected Qty', design_19)
            worksheet1.write(rows, 13, 'QUALITY RATING', design_19)
            rows += 1
            for j in i['data']:
                worksheet1.write(rows, 0, serial_no, design_7)
                worksheet1.write(rows, 1, j['product'], design_8)
                worksheet1.write(rows, 2, j['part_no'], design_8)
                # worksheet1.write(rows, 3, j['product'], design_8)
                # worksheet1.write(rows, 4, j['name'], design_8)
                # worksheet1.write(rows, 5, j['origin'], design_8)
                # worksheet1.write(rows, 6, j['order_date'].strftime('%d-%m-%Y') if j['order_date'] else "-", design_7)
                # worksheet1.write(rows, 7, j['deadline'].strftime('%d-%m-%Y') if j['deadline'] else "-", design_7)
                # worksheet1.write(rows, 8, j['delivery_date'].strftime('%d-%m-%Y') if j['delivery_date'] else "-",
                #                  design_7)
                # worksheet1.write(rows, 9, j['order_qty'], design_9)
                # worksheet1.write(rows, 10, j['delivery_qty'], design_9)
                rows += 1
                serial_no += 1
            worksheet1.write_merge(rows, rows + 0, 0, 18, '', design_36)
            rows += 1
            worksheet1.write_merge(rows, rows, 0, 2, 'TOTAL', design_18)
            worksheet1.write(rows, 3, '1000', design_18)
            worksheet1.write(rows, 4, '10601', design_18)
            worksheet1.write(rows, 5, '106.01', design_18)
            worksheet1.write(rows, 6, '10,601', design_18)
            worksheet1.write(rows, 7, '0', design_18)
            worksheet1.write(rows, 8, '100', design_18)
            worksheet1.write(rows, 9, '9220', design_18)
            worksheet1.write(rows, 10, '9,127', design_18)
            worksheet1.write(rows, 11, '93', design_18)
            worksheet1.write(rows, 12, '98.99', design_18)
            worksheet1.write(rows, 13, '100', design_18)
            worksheet1.write(rows, 14, '100', design_18)
            worksheet1.write(rows, 15, '101', design_18)
            worksheet1.write(rows, 16, '94.00', design_18)
            worksheet1.write(rows, 17, '', design_18)
            worksheet1.write(rows, 18, '', design_18)
            rows += 1
            worksheet1.write_merge(rows, rows + 1, 0, 18, '', design_20)
            rows += 2
            worksheet1.write_merge(rows, rows + 1, 0, 18, '', design_31)
            rows += 2
            # BOX 1
            worksheet1.write_merge(rows, rows + 3, 1, 2, 'QUALITY RATING', design_21)
            worksheet1.write_merge(rows, rows + 1, 3, 4, 'ACCEPTED QTY', design_22)
            worksheet1.write_merge(rows + 2, rows + 3, 3, 4, 'RECEIVED QTY / PROD QTY', design_22)
            worksheet1.write_merge(rows, rows + 3, 5, 6, 'x  100', design_23)

            # BOX 2 & 3
            worksheet1.write_merge(rows, rows, 8, 9, 'GRADE : A', design_24)
            worksheet1.write_merge(rows, rows, 10, 11, '91-100', design_27)
            worksheet1.write_merge(rows, rows, 12, 13, 'EXCELLENT', design_30)
            worksheet1.write_merge(rows, rows, 15, 18, 'CUSTOMER COMPLAINTS', design_33)
            rows += 1
            worksheet1.write_merge(rows, rows, 8, 9, 'GRADE : B', design_25)
            worksheet1.write_merge(rows, rows, 10, 11, '81-90', design_28)
            worksheet1.write_merge(rows, rows, 12, 13, 'GOOD', design_31)
            worksheet1.write_merge(rows, rows, 15, 18, '100 %  ZERO COMPLAINTS', design_34)
            rows += 1
            worksheet1.write_merge(rows, rows, 8, 9, 'GRADE : C', design_25)
            worksheet1.write_merge(rows, rows, 10, 11, '71-80', design_28)
            worksheet1.write_merge(rows, rows, 12, 13, 'AVERAGE', design_31)
            worksheet1.write_merge(rows, rows, 15, 18, '0-99%	REDUCE 25 % FOR EACH COMPLAINT', design_34)

            rows += 1
            worksheet1.write_merge(rows, rows, 8, 9, 'GRADE : D', design_25)
            worksheet1.write_merge(rows, rows, 10, 11, '60-70', design_28)
            worksheet1.write_merge(rows, rows, 12, 13, 'POOR', design_31)
            worksheet1.write_merge(rows, rows, 15, 18, '', design_34)

            rows += 1
            worksheet1.write_merge(rows, rows, 8, 9, 'GRADE : E', design_26)
            worksheet1.write_merge(rows, rows, 10, 11, '< 59', design_29)
            worksheet1.write_merge(rows, rows, 12, 13, 'CANNOT BE CONSIDER', design_32)
            worksheet1.write_merge(rows, rows, 15, 18, '', design_35)

            rows += 1
            worksheet1.write_merge(rows, rows + 0, 0, 18, '', design_31)
            rows += 1

            # BOX 1
            worksheet1.write_merge(rows, rows + 3, 1, 2, 'DELIVERY RATING', design_21)
            worksheet1.write_merge(rows, rows + 1, 3, 4, 'RECEIVED QTY', design_22)
            worksheet1.write_merge(rows + 2, rows + 3, 3, 4, 'SCHEDULE QTY', design_22)
            worksheet1.write_merge(rows, rows + 3, 5, 6, 'x  100', design_23)
            worksheet1.write_merge(rows, rows, 15, 18, 'NO OF INCIDENTS OF EXCESS FREIGHT', design_33)
            rows += 1
            worksheet1.write_merge(rows, rows, 15, 18, '100 % No Incident', design_34)
            rows += 1
            worksheet1.write_merge(rows, rows, 15, 18, '0-99 % REDUCE 10% FOR EACH Incident', design_34)
            rows += 1
            worksheet1.write_merge(rows, rows, 15, 18, '', design_34)
            rows += 1
            worksheet1.write_merge(rows, rows, 15, 18, '', design_34)
            rows += 1
            worksheet1.write_merge(rows, rows, 0, 18, '', design_27)

        fp = BytesIO()
        o = workbook.save(fp)
        fp.read()
        excel_file = base64.b64encode(fp.getvalue())
        self.write({'summary_file': excel_file, 'file_name': f'Supplier Performance Report.xls',
                    'report_printed': True})
        fp.close()
        return {
            'view_mode': 'form',
            'name': 'Supplier Performance',
            'res_id': self.id,
            'res_model': 'supplier.performance',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'target': 'new',
        }
