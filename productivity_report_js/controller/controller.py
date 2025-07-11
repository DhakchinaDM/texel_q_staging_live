from odoo import http
from odoo.http import request
from datetime import datetime

class ProductivityReportController(http.Controller):

    @http.route('/productivity_report/fg_products', type='json', auth='user')
    def get_fg_products(self):
        category = request.env['product.category'].sudo().search([('name', '=', 'Finished Goods')], limit=1)
        products = request.env['product.product'].sudo().search([('categ_id', '=', category.id)])
        return [{
            'id': p.id,
            'name': p.name,
            'default_code': p.default_code
        } for p in products]

    @http.route('/productivity_report/get_data', type='json', auth='user')
    def get_data(self, product_id, from_date=None, to_date=None):
        result = []

        product = request.env['product.product'].sudo().browse(product_id)
        tmpl_id = product.product_tmpl_id.id
        routings = request.env['process.routing'].sudo().search([('product_id', '=', tmpl_id)])

        for routing in routings:

            for line in routing.order_lines:
                domain = [
                    ('op_no', '=', line.operation_code),
                    ('picking_type_id', '=', line.picking_type_id.id),
                    ('product_id.product_tmpl_id', '=', line.out_product_id.id),
                    ('state', '=', 'done'),
                ]
                if from_date:
                    domain.append(('date', '>=', from_date))
                if to_date:
                    domain.append(('date', '<=', to_date))

                moves = request.env['stock.move'].sudo().search(domain)


                move_data = []
                for move in moves:
                    print("1111111111111111111111111111111111111111111111",move)
                    lot_names = move.lot_ids.mapped('name')
                    lot_states = [dict(request.env['stock.lot'].fields_get(allfields=['lot_type'])['lot_type']['selection']).get(lot.lot_type, '') for lot in move.lot_ids]
                    move_data.append({
                        'id': move.id,
                        'lot_names': lot_names,
                        'lot_states': lot_states,
                        'operation_list_id': move.operation_list_id.name,
                        'op_no': move.op_no,
                        'date': move.date.strftime('%d/%m/%Y') if move.date else '',
                        'quantity': move.quantity,
                    })

                # print("1111111111111111111111111111111111111111111111",move_data)

                result.append({
                    'operation_code': line.operation_code,
                    'stock_moves': move_data,
                })

        return result
