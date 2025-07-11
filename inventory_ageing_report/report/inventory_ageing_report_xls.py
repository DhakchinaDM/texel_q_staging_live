# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import datetime
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError,ValidationError
import pytz
from odoo import models
import pdb


class InvReportXls(models.AbstractModel):
    _name = 'report.inventory_ageing_report.inventory_report_xls'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wizard):
        if self._context.get('xls_ageing_export'):
            bold = workbook.add_format({'bold': True})
            middle = workbook.add_format({'align': 'center', 'fg_color': 'e0efd4', 'border': True})
            middle_1 = workbook.add_format({'align': 'left', 'fg_color': 'e0efd4', 'border': True})
            middle_2 = workbook.add_format({'align': 'right', 'fg_color': 'e0efd4', 'border': True})
            center = workbook.add_format({'align': 'center'})
            left = workbook.add_format({'align': 'left', 'bold': True})
            left1 = workbook.add_format({'align': 'left'})
            right = workbook.add_format({'align': 'right'})
            top = workbook.add_format({'top': 1})
            report_format = workbook.add_format({'font_size': 24})
            rounding = self.env.user.company_id.currency_id.decimal_places or 2
            lang_code = self.env.user.lang or 'en_US'
            date_format = workbook.add_format({'num_format': 'dd/mm/yy hh:mm:ss', 'align': 'left'})
            dt_format = workbook.add_format({'num_format': 'dd/mm/yy', 'align': 'left'})
            dt_format1 = workbook.add_format({'num_format': 'dd/mm/yy', 'align': 'center'})
            format4 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True})
            heading_format = workbook.add_format({'align': 'center',
                                                  'valign': 'vcenter',
                                                  'bold': True,
                                                  'size': 14,
                                                  'fg_color': '#AAA4A3'
                                                  })
            heading_format_1 = workbook.add_format({'align': 'center'})
            sheet = workbook.add_worksheet('Inventory Ageing Report')
            sheet.set_column('A4:A4', 15)
            sheet.set_column('B4:B4', 30)
            sheet.set_column('C4:C4', 20)
            sheet.set_column('D4:D4', 35)
            sheet.set_column('E4:E4', 20)
            sheet.set_column('F4:G4', 20)
            sheet.set_column('H4:H4', 18)
            sheet.set_column('I4:I4', 15)
            sheet.set_column('J4:K4', 16)
            sheet.set_column('L4:M4', 20)
            sheet.set_column('N4:O4', 20)

            c = 0
            sheet.merge_range('A1:M1', 'Inventory Ageing Report', heading_format_1)

            tdy_dt = date.today()
            year = 365
            sheet.write(1, 0, _('Date'), left1)
            user = self.env['res.users'].browse(self.env.uid)
            tz = pytz.timezone(user.tz)
            time = pytz.utc.localize(datetime.now()).astimezone(tz)
            sheet.write(1, 1, wizard.start_dt, dt_format)
            sheet.write(1, 2, _('Interval(Days)'), left1)
            sheet.write(1, 3, wizard.interval_days, left1)

            sheet.merge_range(3, 0, 4, 0, _('Warehouse'), middle)
            sheet.merge_range(3, 1, 4, 1, _('Location'), middle)
            sheet.merge_range(3, 2, 4, 2, _('Part Code'), middle)
            sheet.merge_range(3, 3, 4, 3, _('Description'), middle)
            # sheet.merge_range(3, 4, 4, 4, _('Product Type (M/P)'), middle)
            sheet.merge_range(3, 5, 4, 4, _('Cost Price'), middle)
            sheet.merge_range(3, 6, 3, 12, _('Quantity'), middle)
            sheet.write(4, 5, _('<=' + str(wizard.interval_days) + 'Days'), middle)
            sheet.write(4, 6, _(str(wizard.interval_days) + '-' + str(wizard.interval_days * 2) + ' Days'), middle)
            sheet.write(4, 7, _(str(wizard.interval_days * 2) + '-' + str(wizard.interval_days * 3) + ' Days'), middle)
            sheet.write(4, 8, _(str(wizard.interval_days * 3) + '-' + str(wizard.interval_days * 4) + ' Days'), middle)
            sheet.write(4, 9, _(str(wizard.interval_days * 4) + '-' + str(year) + ' Days'), middle)
            sheet.write(4, 10, _('>1 year'), middle)
            sheet.write(4, 11, _('>2 Years'), middle)
            sheet.write(4, 12, _('>3 Years'), middle)
            sheet.merge_range(3, 14, 4, 13, _('Total Value'), middle)
            quant_obj = self.env['stock.quant']
            move_obj = self.env['stock.move']
            inv_data = []
            tt_qty = 0

            if not wizard.interval_days > 0:
                raise UserError(_("Interval Days should not be zero"))
            if not wizard.location_ids:
                raise UserError(_("Atleast one location is required"))

            quant_list = []
            t11 = (datetime.strptime(str(wizard.start_dt), "%Y-%m-%d"))
            t12 = wizard.start_dt - relativedelta(days=wizard.interval_days)

            t21 = wizard.start_dt - relativedelta(days=(wizard.interval_days))
            t22 = wizard.start_dt - relativedelta(days=(wizard.interval_days * 2))

            t31 = wizard.start_dt - relativedelta(days=(wizard.interval_days * 2))
            t32 = wizard.start_dt - relativedelta(days=(wizard.interval_days * 3))

            t41 = wizard.start_dt - relativedelta(days=(wizard.interval_days * 3))
            t42 = wizard.start_dt - relativedelta(days=(wizard.interval_days * 4))

            t51 = wizard.start_dt - relativedelta(days=(wizard.interval_days * 4))
            t52 = wizard.start_dt - relativedelta(days=year)

            t61 = wizard.start_dt - relativedelta(days=year)
            t71 = wizard.start_dt - relativedelta(days=(year * 2))
            t81 = wizard.start_dt - relativedelta(days=(year * 3))
            t82 = wizard.start_dt - relativedelta(days=(year * 5))

            prod_sr = self.env['product.product'].search([('type', '=', 'product'), ('generic_product', '=', False)])
            for loc in wizard.location_ids:
                prod_list = []
                for pr in prod_sr:
                    for dt in range(0, 8):
                        if dt == 0:
                            start_date = t11
                            end_date = t12
                        elif dt == 1:
                            start_date = t21
                            end_date = t22
                        elif dt == 2:
                            start_date = t31
                            end_date = t32
                        elif dt == 3:
                            start_date = t41
                            end_date = t42
                        elif dt == 4:
                            start_date = t51
                            end_date = t52
                        elif dt == 5:
                            start_date = t61
                            end_date = t71
                        elif dt == 6:
                            start_date = t71
                            end_date = t81
                        elif dt == 7:
                            start_date = t81
                            end_date = t82
                        else:
                            start_date = False
                            end_date = False

                        if wizard.location_ids and start_date and end_date:
                            quant_sr = quant_obj.search([
                                ('location_id', '=', loc.id),
                                ('in_date', '<=', start_date),
                                ('in_date', '>=', end_date),
                                ('quantity', '>', 0),
                                ('product_id', '=', pr.id)
                            ])

                        if quant_sr:
                            prod_qty = 0
                            qty_0_30 = 0
                            qty_30_60 = 0
                            qty_60_90 = 0
                            qty_90_120 = 0
                            qty_120_365 = 0
                            qty_1_365 = 0
                            qty_2_365 = 0
                            qty_3_365 = 0
                            tt_qty = 0
                            for qt in quant_sr:
                                prod_qty = qt.quantity
                                if dt == 0:
                                    qty_0_30 += prod_qty
                                elif dt == 1:
                                    qty_30_60 += prod_qty
                                elif dt == 2:
                                    qty_60_90 += prod_qty
                                elif dt == 3:
                                    qty_90_120 += prod_qty
                                elif dt == 4:
                                    qty_120_365 += prod_qty
                                elif dt == 5:
                                    qty_1_365 += prod_qty
                                elif dt == 6:
                                    qty_2_365 += prod_qty
                                elif dt == 7:
                                    qty_3_365 += prod_qty
                            proc_method = ''
                            if pr.procurement_method:
                                for mp in pr.procurement_method:
                                    if mp.name in ('Purchase to Order', 'Purchase to Stock'):
                                        proc_method = 'Purchase'
                                    elif mp.name in ('Manufacture to Order', 'Manufacture to Stock'):
                                        proc_method = 'Manufacture'

                            tt_qty = qty_0_30 + qty_30_60 + qty_60_90 + qty_90_120 + qty_120_365 + qty_1_365 + qty_2_365 + qty_3_365
                            if pr.id not in prod_list:
                                prod_list.append(pr.id)
                                inv_data.append({
                                    'product_id': pr.id,
                                    'warehouse_id': wizard.warehouse_id.id,
                                    'warehouse': wizard.warehouse_id.name,
                                    'location': loc.location_id.name + '/' + loc.name,
                                    'part_code': pr.old_product_code,
                                    'desc': pr.name,
                                    'prod_type': proc_method,
                                    'avg_cost': round(pr.avg_cost_total, 2) or 0,
                                    'qty_0_30': round(qty_0_30, 2) or 0,
                                    'qty_30_60': round(qty_30_60, 2) or 0,
                                    'qty_60_90': round(qty_60_90, 2) or 0,
                                    'qty_90_120': round(qty_90_120, 2) or 0,
                                    'qty_120_365': round(qty_120_365, 2) or 0,
                                    'qty_1_365': round(qty_1_365, 2) or 0,
                                    'qty_2_365': round(qty_2_365, 2) or 0,
                                    'qty_3_365': round(qty_3_365, 2) or 0,
                                    'tt_val': round(tt_qty, 2) * round(pr.avg_cost_total, 2) or 0,
                                })
                            else:
                                for each in inv_data:
                                    total_qty = 0
                                    if each['product_id'] == pr.id:
                                        if not each['qty_0_30'] > 0:
                                            each.update({'qty_0_30': qty_0_30})
                                        if not each['qty_30_60'] > 0:
                                            each.update({'qty_30_60': qty_30_60})
                                        if not each['qty_60_90'] > 0:
                                            each.update({'qty_60_90': qty_60_90})
                                        if not each['qty_90_120'] > 0:
                                            each.update({'qty_90_120': qty_90_120})
                                        if not each['qty_120_365'] > 0:
                                            each.update({'qty_120_365': qty_120_365})
                                        if not each['qty_1_365'] > 0:
                                            each.update({'qty_1_365': qty_1_365})
                                        if not each['qty_2_365'] > 0:
                                            each.update({'qty_2_365': qty_2_365})
                                        if not each['qty_3_365'] > 0:
                                            each.update({'qty_3_365': qty_3_365})
                                        total_qty = each['qty_0_30'] + each['qty_30_60'] + each['qty_60_90'] + each[
                                            'qty_90_120'] + each['qty_120_365'] + each['qty_1_365'] + each[
                                                        'qty_2_365'] + each['qty_3_365']
                                        each.update({'tt_val': total_qty * each['avg_cost']})
            seq = 1
            i = 5
            if not inv_data:
                raise UserError(_("No Records Found"))
            tt_0_30 = 0
            tt_30_60 = 0
            tt_60_90 = 0
            tt_90_120 = 0
            tt_120_365 = 0
            tt_1_365 = 0
            tt_2_365 = 0
            tt_3_365 = 0
            grand_tt_val = 0
            for l in inv_data:
                sheet.write(i, 0, l.get('warehouse'), center)
                sheet.write(i, 1, l.get('location'))
                sheet.write(i, 2, l.get('part_code'))
                sheet.write(i, 3, l.get('desc'))
                # sheet.write(i, 4, l.get('prod_type'), center)
                sheet.write(i, 4, l.get('avg_cost'), right)
                sheet.write(i, 5, l.get('qty_0_30'), right)
                sheet.write(i, 6, l.get('qty_30_60'), right)
                sheet.write(i, 7, l.get('qty_60_90'), right)
                sheet.write(i, 8, l.get('qty_90_120'), right)
                sheet.write(i, 9, l.get('qty_120_365'), right)
                sheet.write(i, 10, l.get('qty_1_365'), right)
                sheet.write(i, 11, l.get('qty_2_365'), right)
                sheet.write(i, 12, l.get('qty_3_365'), right)
                sheet.write(i, 13, l.get('tt_val'), right)
                i += 1
                tt_0_30 += l.get('qty_0_30')
                tt_30_60 += l.get('qty_30_60')
                tt_60_90 += l.get('qty_60_90')
                tt_90_120 += l.get('qty_90_120')
                tt_120_365 += l.get('qty_120_365')
                tt_1_365 += l.get('qty_1_365')
                tt_2_365 += l.get('qty_2_365')
                tt_3_365 += l.get('qty_3_365')
                grand_tt_val += l.get('tt_val')
            sheet.write(i, 5, 'Total', middle)
            sheet.write(i, 6, round(tt_0_30), middle_2)
            sheet.write(i, 7, round(tt_30_60), middle_2)
            sheet.write(i, 8, round(tt_60_90), middle_2)
            sheet.write(i, 9, round(tt_90_120), middle_2)
            sheet.write(i, 10, round(tt_120_365), middle_2)
            sheet.write(i, 11, round(tt_1_365), middle_2)
            sheet.write(i, 12, round(tt_2_365), middle_2)
            sheet.write(i, 13, round(tt_3_365), middle_2)
            sheet.write(i, 14, round(grand_tt_val), middle_2)
