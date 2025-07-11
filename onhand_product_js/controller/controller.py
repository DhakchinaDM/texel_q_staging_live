from odoo import http
from odoo.http import request

class InventoryOnHandReportController(http.Controller):

    @http.route('/on_hand_product/fg_products', type='json', auth='user')
    def get_fg_products(self):
        category = request.env['product.category'].sudo().search([('name', '=', 'Finished Goods')], limit=1)
        products = request.env['product.product'].sudo().search([('categ_id', '=', category.id)])
        return [{'id': p.id, 'name': p.name, 'default_code': p.default_code} for p in products]

    @http.route('/on_hand_product/operation_codes', type='json', auth='user')
    def get_operation_codes(self, product_id):
        product = request.env['product.product'].sudo().browse(product_id)
        tmpl_id = product.product_tmpl_id.id
        routings = request.env['process.routing'].sudo().search([('product_id', '=', tmpl_id)])

        codes = []
        seen = set()  # To avoid duplicates

        for routing in routings:
            sorted_lines = routing.order_lines.sorted('sequence')
            for line in sorted_lines:
                if line.operation_code and line.operation_code not in seen:
                    codes.append(line.operation_code)
                    seen.add(line.operation_code)
                print(f"Sequence: {line.sequence}, Operation Code: {line.operation_code}")

        print("Final Ordered Operation Codes:", codes)
        return codes

    @http.route('/on_hand_product/get_data', type='json', auth='user')
    def get_data(self, product_id, lot_type=None,op_code=None):
        result = []
        product = request.env['product.product'].sudo().browse(product_id)
        tmpl_id = product.product_tmpl_id.id
        routings = request.env['process.routing'].sudo().search([('product_id', '=', tmpl_id)])
        lot_type_selection = dict(request.env['stock.lot'].fields_get(allfields=['lot_type'])['lot_type']['selection'])

        if op_code:
            for k in op_code:
                routings = routings.filtered(lambda r: any(line.operation_code == k for line in r.order_lines))

        for routing in routings:
            for line in routing.order_lines:
                domain = [('product_id.product_tmpl_id', '=', line.out_product_id.id)]
                if lot_type:
                    domain.append(('lot_type', '=', lot_type))
                lots = request.env['stock.lot'].sudo().search(domain)
                lot_data = []
                for lot in lots:
                    if lot.product_qty > 0:
                        lot_data.append({
                            'id': lot.id,
                            'lot_names': lot.name,
                            'lot_states': lot_type_selection.get(lot.lot_type, ''),
                            'quantity': lot.product_qty,
                        })
                total_qty = sum(l['quantity'] for l in lot_data)
                result.append({
                    'operation_code': line.operation_code,
                    'operation_code_list': line.operation_list_id.name,
                    'operation_product': line.out_product_id.name,
                    'operation_product_id': line.out_product_id.id,
                    'stock_lots': lot_data,
                    'total': total_qty,
                })
        print("Final Result:", result)
        return result
