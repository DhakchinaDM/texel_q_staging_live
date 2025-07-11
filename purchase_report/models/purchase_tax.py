from odoo import models, fields, api, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def over_all_tax_val(self):
        sale_order_line = self.env['purchase.order.line'].search([("order_id", "=", self.id)])
        ll = []
        bbbb = 1
        for j in sale_order_line:
            if j.taxes_id not in ll:
                ll.append(j.taxes_id)
        for n in ll:
            bb = n.name
            oo = bb.split(" ")
            gg = oo[0]
            if str(gg) == "GST":
                bbbb = 2
            if str(gg) == "IGST":
                bbbb = 3
        return bbbb

    def over_all_tax(self):
        sale_order_line = self.env['purchase.order.line'].search([('order_line', '=', self.id)])
        ll = []
        for j in sale_order_line:
            if j.taxes_id not in ll:
                ll.append(j.taxes_id)
        all_val = []
        for n in ll:
            bb = n.name
            oo = bb.split(" ")
            gg = oo[-1]
            ff = oo[0]
            hh = gg[0:-1]
            try:
                hh_float = float(hh)
            except ValueError:
                # Handle the case where hh cannot be converted to a float
                # You might want to log a warning or skip this entry
                continue

            cc = 0
            for k in sale_order_line:
                if n.id == k.taxes_id.id:
                    cc += k.price_subtotal

            if str(ff) == "GST":
                vals = {
                    'tax_name': n.name,
                    'st': gg,
                    'taxes_id': n.id,
                    'subtotal': cc,
                    'gst': hh_float,
                    'sgst': (cc / 100) * (hh_float / 2),
                    'cgst': (cc / 100) * (hh_float / 2),
                }
                all_val.append(vals)
            elif str(ff) == "IGST":
                vals = {
                    'tax_name': n.name,
                    'st': gg,
                    'taxes_id': n.id,
                    'subtotal': cc,
                    'gst': hh_float,
                    'igst': (cc / 100) * hh_float,
                }
                all_val.append(vals)

        return all_val
