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


class CurrentStockReport(models.Model):
    _name = 'current.stock.report'
    _description = 'Current Stock Report'

    summary_file = fields.Binary('Current Stock Report')
    file_name = fields.Char('File Name')
    report_printed = fields.Boolean('Report')
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    def get_current_stock_data(self, start_date, data=None):
        value = {'filter': {}, 'data': {}}
        product_category = self.env['product.category']
        product = self.env['product.product']
        category = [{'name': i.name, 'id': i.id, } for i in product_category.search([])]
        products_list = [{'name': i.display_name, 'id': i.id, 'templ_id': i.product_tmpl_id, 'category': i.categ_id.id}
                         for i in
                         product.search([])]

        stock_picking_in = self.env['stock.picking'].search(
            [('picking_type_code', '=', 'incoming'), ('date_done', '>=', start_date), ('date_done', '<=', start_date),
             ('state', '=', 'done')])

        stock_picking_out = self.env['stock.picking'].search(
            [('picking_type_code', '=', 'outgoing'), ('date_done', '>=', start_date), ('date_done', '<=', start_date),
             ('state', '=', 'done')])

        val = []
        cat_domain = []

        if data:
            if data['category']:
                cat_ids = [i['id'] for i in data['category']]
                cat_domain.append(('id', 'in', cat_ids))
            if data['product']:
                filter_product_ids = [i['id'] for i in data['product']]
                filter_product = product.search([('id', 'in', filter_product_ids)])
                cat_ids = [i.categ_id.id for i in filter_product]
                cat_domain.append(('id', 'in', cat_ids))

        pro_category = product_category.search(cat_domain)

        for cat in pro_category:
            cat_data = {'name': cat.name, 'id': cat.id, }
            pro_data = []
            product_cat = [('categ_id', '=', cat.id)]
            if data:
                if data['product']:
                    filter_product_ids = [i['id'] for i in data['product']]
                    product_cat.append(('id', 'in', filter_product_ids))

            for pro in product.search(product_cat):
                product_data = {
                    'code': pro.default_code if pro.default_code else "None",
                    'name': pro.display_name,
                    'categ': pro.categ_id.name,
                }
                inn = 0
                for m in stock_picking_in:
                    for k in m.move_ids:
                        if k.product_id.id == pro.id:
                            inn += k.product_uom_qty

                out = 0
                for m in stock_picking_out:
                    for k in m.move_ids:
                        if k.product_id.id == pro.id:
                            out += k.product_uom_qty

                product_data['opening'] = pro.qty_available - inn + out
                product_data['opening_val'] = pro.lst_price * product_data['opening']
                product_data['received_tdy'] = inn
                product_data['received_total'] = inn * pro.standard_price
                product_data['sale_tdy'] = out
                product_data['sale_total'] = out * pro.lst_price
                product_data['on_hand'] = pro.qty_available
                product_data['cost_price'] = pro.standard_price
                product_data['value'] = pro.standard_price * pro.qty_available

                pro_data.append(product_data)
            cat_data['products'] = pro_data
            cat_data['no_of_products'] = len(pro_data)
            val.append(cat_data)

        value['filter']['category'] = category
        value['filter']['products_list'] = products_list
        value['data'] = val

        return value

    def print_current_stock_report(self, data=None):
        workbook = xlwt.Workbook()
        worksheet1 = workbook.add_sheet('Current Stock Report')
        design_15 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 320; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_16 = easyxf(
            'align: horiz center, vert center; font: height 200; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_17 = easyxf(
            'align: horiz left, vert center; font: bold 1, height 230; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_18 = easyxf(
            'align: horiz center, vert center; font:  bold 1, height 200; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_19 = easyxf(
            'align: horiz right, vert center; font:  bold 1, height 200;')
        design_20 = easyxf(
            'align: horiz left, vert center; font: height 200; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_21 = easyxf(
            'align: horiz right, vert center; font: height 200; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')

        worksheet1.col(0).width = 1600
        worksheet1.col(1).width = 4000
        worksheet1.col(2).width = 6000
        worksheet1.col(3).width = 3500
        worksheet1.col(4).width = 3500
        worksheet1.col(5).width = 3500
        worksheet1.col(6).width = 4500
        worksheet1.col(7).width = 4500
        worksheet1.col(8).width = 5000
        worksheet1.row(0).height_mismatch = True
        worksheet1.row(0).height = 800
        worksheet1.row(2).height = 450
        worksheet1.row(3).height = 450

        start_date = self.start_date
        stock_data = self.get_current_stock_data(start_date, data)

        rows = 0
        cols = 0
        serial_no = 1
        #
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
            #
            worksheet1.insert_bitmap_data(fo.getvalue(), rows, 0)
        cell_style_logo = easyxf(
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;'
        )
        worksheet1.write_merge(rows, rows, 0, 1, '', cell_style_logo)
        worksheet1.write_merge(rows, rows, 2, 8, str(self.company_id.name), design_15)
        rows += 1
        address = str(self.company_id.street) + str(self.company_id.street2) + str(self.company_id.state_id.name) + str(
            self.company_id.zip)
        worksheet1.write_merge(rows, rows, 0, 8, address, design_16)
        rows += 1
        title = "Current Stock Report "
        worksheet1.write_merge(rows, rows, 0, 8, title, design_15)
        cols_head = ['S.No', 'Code', 'Name', 'Opening', 'Purchase', 'Sale',
                     "On Hand", "Cost", 'On Hand Value']
        rows += 1
        for i in cols_head:
            worksheet1.write(rows, cols, _(i), design_18)
            cols += 1

        rows += 1
        for category in stock_data['data']:
            worksheet1.write_merge(rows, rows, 0, 8, category['name'], design_17)
            rows += 1
            for product in category['products']:
                worksheet1.write(rows, 0, serial_no, design_20)
                worksheet1.write(rows, 1, product['code'], design_20)
                worksheet1.write(rows, 2, product['name'], design_20)
                worksheet1.write(rows, 3, product['opening'], design_21)
                worksheet1.write(rows, 4, product['received_tdy'], design_21)
                worksheet1.write(rows, 5, product['sale_tdy'], design_21)
                worksheet1.write(rows, 6, product['on_hand'], design_21)
                worksheet1.write(rows, 7, product['cost_price'], design_21)
                worksheet1.write(rows, 8, product['value'], design_21)
                rows += 1
                serial_no += 1

        rows += 1

        fp = BytesIO()
        o = workbook.save(fp)
        fp.read()
        excel_file = base64.b64encode(fp.getvalue())
        self.write({
            'summary_file': excel_file,
            'file_name': f'Current Stock Report.xls',
            'report_printed': True
        })

        fp.close()
        return {
            'view_mode': 'form',
            'name': 'Current Stock Report',
            'res_id': self.id,
            'res_model': 'current.stock.report',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'target': 'new',
        }
