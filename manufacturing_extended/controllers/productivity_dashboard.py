from odoo import http
from odoo.http import request
from datetime import datetime

class ProductivityDashboardController(http.Controller):
    @http.route('/get_finished_goods', type='json', auth='user')
    def get_finished_goods(self):
        """Fetch all products under the Finished Goods category"""
        category = request.env.ref('inventory_extended.category_finished_goods', raise_if_not_found=False)
        if not category:
            return []

        products = request.env['product.product'].search_read(
            [('categ_id', '=', category.id)], ['id', 'name', 'default_code']
        )
        return products

    @http.route('/get_productivity_data', type='json', auth='user')
    def get_productivity_data(self, product_id=None, start_date=None, end_date=None):
        if not product_id:
            return []

        domain = [('product_id', '=', product_id)]

        if start_date:
            domain.append(('date', '>=', start_date))
        if end_date:
            domain.append(('date', '<=', end_date))

        records = request.env['productivity.line'].sudo().search_read(
            domain,
            ['product_id', 'op_code', 'lot_id', 'job_id', 'produced_qty', 'qty_type', 'remarks', 'date','total_produced_qty']
        )

        # Convert the date field to dd/mm/yyyy format
        for record in records:
            if record.get('date'):
                record['date'] = datetime.strptime(str(record['date']), '%Y-%m-%d').strftime('%d/%m/%Y')

        grouped_data = []
        op_code_dict = {}
        for record in records:
            op_code = record['op_code']
            if op_code not in op_code_dict:
                op_code_dict[op_code] = []
            op_code_dict[op_code].append(record)

        for op_code, records in op_code_dict.items():
            grouped_data.append({'op_code': op_code, 'records': records})

        return grouped_data
