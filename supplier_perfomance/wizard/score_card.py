from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from datetime import date, datetime
import xlwt
from io import BytesIO
import base64
from base64 import b64decode, b64encode
from xlwt import easyxf, Borders
import io
import base64
from odoo.tools import base64_to_image
from PIL import Image


class SupplierMonthlyScoreCard(models.TransientModel):
    _name = 'supplier.monthly.score.card'
    _description = 'Vendor Monthly Score Card'

    partner_id = fields.Many2one('res.partner', string='Supplier')
    part_no = fields.Many2many('product.product', string='Part No')
    summary_file = fields.Binary('Product Report')
    file_name = fields.Char('File Name')
    report_printed = fields.Boolean('Report')
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

    def print_score_card(self):
        workbook = xlwt.Workbook()
        worksheet1 = workbook.add_sheet('Supplier Monthly Score Card Report')
        custom_color_1 = 0x21
        workbook.set_colour_RGB(custom_color_1, 224, 228, 244)
        design_1 = easyxf(
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;'
            'align: horiz left, vert center; font: height 220; pattern: pattern solid, fore_colour white;')

        design_2 = easyxf(
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;'
            'align: horiz left, vert center; font: bold 1, height 220; pattern: pattern solid, fore_colour white;')

        design_3 = easyxf(
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;'
            'align: horiz center, vert center; font: bold 1, height 220; pattern: pattern solid, fore_colour white;')

        design_4 = easyxf(
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;'
            'align: horiz center, vert center; font: bold 1, height 225; pattern: pattern solid, fore_colour 0x2B;')

        design_5 = easyxf(
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;'
            f'align: horiz left, vert center; font: bold 1, height 250; pattern: pattern solid, fore_colour {custom_color_1};')
        design_6 = easyxf(
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;'
            f'align: horiz center, vert center; font: bold 1, height 250; pattern: pattern solid, fore_colour {custom_color_1};')
        design_15 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 320; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        for i in range(2, 14):
            worksheet1.col(0).width = 1600
            worksheet1.col(1).width = 5000
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
        worksheet1.row(3).height = 450
        worksheet1.row(4).height = 400
        worksheet1.row(5).height = 400
        worksheet1.row(6).height = 400
        worksheet1.row(7).height = 400
        worksheet1.row(8).height = 400
        worksheet1.row(9).height = 400
        worksheet1.row(10).height = 400
        worksheet1.row(11).height = 400
        worksheet1.row(12).height = 400
        worksheet1.row(13).height = 400
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
        worksheet1.write_merge(rows, rows, 3, 12, 'Vendor Monthly Score Card', design_15)
        worksheet1.write_merge(rows, rows, 13, 16, 'PUR/DI/R/07', design_15)
        rows += 1
        worksheet1.write_merge(rows, rows, 0, 2, 'Vendor Code', design_6)
        supplier_code = self.partner_id.supplier_code if self.partner_id.supplier_code else "-"
        worksheet1.write_merge(rows, rows, 3, 4, supplier_code, design_6)
        supplier = "Supplier:- " + str(self.partner_id.name)
        worksheet1.write_merge(rows, rows, 5, 12, supplier, design_5)
        period = str(self.select_month) + "-", str(self.year_master.name)
        worksheet1.write_merge(rows, rows, 13, 16, period, design_5)
        rows += 1
        worksheet1.write_merge(rows, rows, 0, 2, 'Process', design_6)
        worksheet1.write_merge(rows, rows, 3, 4, 'Casting', design_6)
        part_no = "Part No. : " + ", ".join([i.name for i in self.part_no])
        worksheet1.write_merge(rows, rows, 5, 12, part_no, design_5)
        worksheet1.write_merge(rows, rows, 13, 16, "", design_5)
        rows += 1
        worksheet1.write(rows, 0, 'S.No', design_4)
        worksheet1.write_merge(rows, rows, 1, 2, "Description", design_4)
        worksheet1.write(rows, 3, "Unit", design_4)
        worksheet1.write(rows, 4, "", design_4)
        worksheet1.write_merge(rows, rows, 5, 12, "Measurements", design_4)
        worksheet1.write_merge(rows, rows, 13, 16, "Remarks", design_4)
        rows += 1
        worksheet1.write(rows, 0, '1', design_3)
        worksheet1.write_merge(rows, rows, 1, 2, 'Quality Rating', design_2)
        worksheet1.write(rows, 3, '99.84%', design_3)
        worksheet1.write(rows, 4, '100%', design_3)
        worksheet1.write_merge(rows, rows, 5, 12,
                               '((No.of parts Received or Produced - No.of Part Reject) / No.of part received)*100%',
                               design_1)
        worksheet1.write_merge(rows, rows, 13, 16, '', design_1)
        rows += 1
        worksheet1.write(rows, 0, '2', design_3)
        worksheet1.write_merge(rows, rows, 1, 2, 'Delivery Rating', design_2)
        worksheet1.write(rows, 3, '106.17%', design_3)
        worksheet1.write(rows, 4, '100%', design_3)
        worksheet1.write_merge(rows, rows, 5, 12,
                               '((No.of parts Received/No.of parts scheduled)*100)',
                               design_1)
        worksheet1.write_merge(rows, rows, 13, 16, '', design_1)
        rows += 1
        worksheet1.write(rows, 0, '3', design_3)
        worksheet1.write_merge(rows, rows, 1, 2, 'Excess Freight', design_2)
        worksheet1.write(rows, 3, '100%', design_3)
        worksheet1.write(rows, 4, '100%', design_3)
        worksheet1.write_merge(rows, rows, 5, 12,
                               '100 - (No.of Lots delayed X 5)',
                               design_1)
        worksheet1.write_merge(rows, rows, 13, 16, 'No.dispatch overdue from scheduled date', design_1)
        rows += 1
        worksheet1.write(rows, 0, '4', design_3)
        worksheet1.write_merge(rows, rows, 1, 2, 'Customer complaint', design_2)
        worksheet1.write(rows, 3, '100%', design_3)
        worksheet1.write(rows, 4, '100%', design_3)
        worksheet1.write_merge(rows, rows, 5, 12, '100 - (No.of complaints X 5)', design_1)
        worksheet1.write_merge(rows, rows, 13, 16, 'No.of incidents happened at this month', design_1)
        rows += 1
        worksheet1.write(rows, 0, '5', design_3)
        worksheet1.write_merge(rows, rows, 1, 2, 'Overall Rating', design_2)
        worksheet1.write(rows, 3, '101.50%', design_3)
        worksheet1.write(rows, 4, '100%', design_3)
        worksheet1.write_merge(rows, rows, 5, 12, 'Average of the above Points (1 to 4)', design_1)
        worksheet1.write_merge(rows, rows, 13, 16, '', design_1)
        rows += 1
        worksheet1.write_merge(rows, rows, 0, 16, '', design_1)
        rows += 1
        worksheet1.write(rows, 0, '1', design_3)
        worksheet1.write_merge(rows, rows, 1, 2, 'Customer complaint', design_2)
        worksheet1.write(rows, 3, "No's", design_3)
        worksheet1.write(rows, 4, '100%', design_3)
        worksheet1.write_merge(rows, rows, 5, 12, 'No.of incidents happened at this month', design_1)
        worksheet1.write_merge(rows, rows, 13, 16, '', design_1)
        rows += 1
        worksheet1.write(rows, 0, '2', design_3)
        worksheet1.write_merge(rows, rows, 1, 2, 'Customer complaint', design_2)
        worksheet1.write(rows, 3, "No's", design_3)
        worksheet1.write(rows, 4, '100%', design_3)
        worksheet1.write_merge(rows, rows, 5, 12, 'No.of complaint current month + total complaint of this year',
                               design_1)
        worksheet1.write_merge(rows, rows, 13, 16, 'Rolling this year', design_1)
        rows += 1
        worksheet1.write(rows, 0, '3', design_3)
        worksheet1.write_merge(rows, rows, 1, 2, 'CAR', design_2)
        worksheet1.write(rows, 3, "Days", design_3)
        worksheet1.write(rows, 4, 'Days', design_3)
        worksheet1.write_merge(rows, rows, 5, 12, 'Submission date - Target date',
                               design_1)
        worksheet1.write_merge(rows, rows, 13, 16, 'No.of days overdue', design_1)
        rows += 1
        worksheet1.write(rows, 0, '3', design_3)
        worksheet1.write_merge(rows, rows, 1, 2, 'PPAP', design_2)
        worksheet1.write(rows, 3, "Days", design_3)
        worksheet1.write(rows, 4, 'Days', design_3)
        worksheet1.write_merge(rows, rows, 5, 12, 'Submission date - Target date',
                               design_1)
        worksheet1.write_merge(rows, rows, 13, 16, 'No.of days overdue', design_1)

        fp = BytesIO()
        o = workbook.save(fp)
        fp.read()
        excel_file = base64.b64encode(fp.getvalue())
        self.write({'summary_file': excel_file, 'file_name': f'Supplier Score Card Report.xls',
                    'report_printed': True})
        fp.close()
        return {
            'view_mode': 'form',
            'name': 'Supplier Monthly Score Card',
            'res_id': self.id,
            'res_model': 'supplier.monthly.score.card',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'target': 'new',
        }
