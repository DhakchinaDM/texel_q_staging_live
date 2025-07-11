from odoo import http
from odoo.http import request
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


class PartFilter(http.Controller):

    @http.route('/customer/filter', auth='public', type='json')
    def project_filter(self):
        product_list = []
        customer_list = []

        product_ids = request.env['product.template'].search([
            ('categ_id', '=', request.env.ref('inventory_extended.category_finished_goods').id)])
        customer_ids = request.env['res.partner'].search([('customer_rank', '=', 1)])
        for product_id in product_ids:
            product_list.append({'name': product_id.default_code or product_id.name, 'id': product_id.id})
        for supplier_id in customer_ids:
            customer_list.append({'name': supplier_id.name, 'id': supplier_id.id})
        return [product_list, customer_list]

    @http.route('/get_customer_release', auth='public', type='json')
    def get_customer_release(self, product_id=None, supplier_id=None):
        inventory_data = []
        domain = [('state', 'not in', ['done'])]

        if product_id and product_id != "null":
            products = request.env['product.template'].search([('id', '=', int(product_id))])
            if products:
                domain.append(('part_no', 'in', products.ids))
        if supplier_id and supplier_id != "null":
            suppliers = request.env['res.partner'].search([('id', '=', int(supplier_id))])
            if suppliers:
                domain.append(('partner_id', 'in', suppliers.ids))
        customer_releases = request.env['customer.release'].search(domain)
        inventory_data.extend([{
            'part_no': cr.part_no.default_code,
            'product_id': cr.part_no.id,
            'customer': cr.partner_id.name,
            'ship_to': cr.ship_to,
            'po_ref': cr.po_ref,
            'qty_ready': cr.qty_ready,
            'qty_loaded': cr.qty_loaded,
            'due_date': cr.due_date,
            'rel_qty': cr.rel_qty,
        } for cr in customer_releases])
        return {'inventory_data': inventory_data}
