from odoo import http
from odoo.http import request
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class PartFilter(http.Controller):
    @http.route('/product/filter', auth='public', type='json')
    def project_filter(self):
        product_list = []
        supplier_list = []

        product_ids = request.env['product.template'].search([
            ('categ_id', '=', request.env.ref('inventory_extended.category_finished_goods').id)])
        supplier_ids = request.env['res.partner'].search([])
        for product_id in product_ids:
            product_list.append({'name': product_id.default_code or product_id.name, 'id': product_id.id})
        for supplier_id in supplier_ids:
            supplier_list.append({'name': supplier_id.name, 'id': supplier_id.id})
        return [product_list, supplier_list]

    @http.route('/get_product_inventory', auth='public', type='json')
    def get_product_inventory(self, product_id=None, supplier_id=None, integer_field=0, filter_duration=None):
        inventory_data = []
        today = date.today()
        domain = []
        supplier_name = request.env['res.partner'].browse(
            int(supplier_id)).name if supplier_id and supplier_id != "null" else '-'
        integer_field = int(integer_field) if integer_field and str(integer_field).isdigit() else 0
        if product_id and product_id != "null":
            domain.append(('id', '=', int(product_id)))
            products = request.env['product.template'].search(domain, limit=1)
            product_bom_ids = set(c.product_id.id for b in products.mapped('bom_ids') for c in b.bom_line_ids)
            data_bom_ids = set(c.product_id for b in products.mapped('bom_ids') for c in b.bom_line_ids)
            if supplier_id and supplier_id != "null":
                purchase_lines = request.env['purchase.order.line'].search([
                    ('product_id', 'in', list(product_bom_ids)),
                    ('state', '=', 'purchase'),
                    ('partner_id', '=', supplier_id)])
            else:
                purchase_lines = request.env['purchase.order.line'].search([
                    ('product_id', 'in', list(product_bom_ids)),
                    ('state', '=', 'purchase')])
            customer_releases = request.env['customer.release'].search([
                ('part_no', 'in', products.ids)])
            job_plans = request.env['job.planning'].search([
                ('part_no', 'in', products.ids)])
            date_ranges = []
            if filter_duration == "day":
                date_ranges = [today + timedelta(days=i) for i in range(integer_field)]
            elif filter_duration == "week":
                for i in range(integer_field):
                    start_date = today - timedelta(days=today.weekday()) + timedelta(weeks=i)
                    end_date = start_date + timedelta(days=6)
                    date_ranges.append((start_date, end_date))
            elif filter_duration == "month":
                for i in range(integer_field):
                    start_date = today.replace(day=1) + relativedelta(months=i)
                    end_date = start_date + relativedelta(months=1, days=-1)
                    date_ranges.append((start_date, end_date))
            elif filter_duration == "year":
                for i in range(integer_field):
                    start_date = date(today.year + i, 1, 1)
                    end_date = date(today.year + i, 12, 31)
                    date_ranges.append((start_date, end_date))

            for record in data_bom_ids:
                past_due_qty = 0
                past_due_customer_release = 0
                past_due_job_demand = 0
                upcoming_data = {}
                customer_release_data = {}
                job_demand_data = {}

                if filter_duration == "day":
                    for single_date in date_ranges:
                        upcoming_data[single_date.strftime('%Y-%m-%d')] = 0
                        customer_release_data[single_date.strftime('%Y-%m-%d')] = 0
                        job_demand_data[single_date.strftime('%Y-%m-%d')] = 0
                else:
                    for start_date, end_date in date_ranges:
                        key = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                        upcoming_data[key] = 0
                        customer_release_data[key] = 0
                        job_demand_data[key] = 0

                for line in purchase_lines.filtered(lambda l: l.product_id == record):
                    if line.order_id.date_planned:
                        planned_date = line.order_id.date_planned.date()
                        if planned_date < today:
                            past_due_qty += line.balanced_delivery
                        else:
                            if filter_duration == "day":
                                for single_date in date_ranges:
                                    if planned_date == single_date:
                                        upcoming_data[single_date.strftime('%Y-%m-%d')] += line.balanced_delivery
                            else:
                                for start_date, end_date in date_ranges:
                                    if start_date <= planned_date <= end_date:
                                        key = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                                        upcoming_data[key] += line.balanced_delivery

                for release in customer_releases.filtered(lambda r: r.part_no.id == products.id):
                    if release.due_date:
                        release_date = release.due_date
                        if release_date < today:
                            past_due_customer_release += release.rel_qty
                        else:
                            for date_range in date_ranges:
                                if filter_duration == "day" and release_date == date_range:
                                    customer_release_data[release_date.strftime('%Y-%m-%d')] += release.rel_qty
                                elif filter_duration != "day" and date_range[0] <= release_date <= date_range[1]:
                                    key = f"{date_range[0].strftime('%Y-%m-%d')} to {date_range[1].strftime('%Y-%m-%d')}"
                                    customer_release_data[key] += release.rel_qty

                for plan in job_plans.filtered(lambda p: p.part_no.id == products.id):
                    if plan.job_due:
                        job_date = plan.job_due
                        if job_date < today:
                            past_due_job_demand += plan.job_qty
                        else:
                            for date_range in date_ranges:
                                if filter_duration == "day" and job_date == date_range:
                                    job_demand_data[job_date.strftime('%Y-%m-%d')] += plan.job_qty
                                elif filter_duration != "day" and date_range[0] <= job_date <= date_range[1]:
                                    key = f"{date_range[0].strftime('%Y-%m-%d')} to {date_range[1].strftime('%Y-%m-%d')}"
                                    job_demand_data[key] += plan.job_qty

                inventory_data.append({
                    'product_name': record.display_name,
                    'product_id': products.id,
                    'qty_available': record.qty_available,
                    'partner_id': supplier_name,
                    'past_due': past_due_qty,
                    'past_due_customer_release': past_due_customer_release,
                    'past_due_job_demand': past_due_job_demand,
                    'upcoming': upcoming_data,
                    'customer_release': customer_release_data,
                    'job_demand': job_demand_data,
                })
            return {'inventory_data': inventory_data, 'date_ranges': date_ranges}
