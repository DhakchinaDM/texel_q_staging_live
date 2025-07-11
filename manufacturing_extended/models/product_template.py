from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    raw_id = fields.Many2one('product.template', string='Raw Material', tracking=True)
    operation_list_id = fields.Many2one('mrp.operation.list', string='Operation List', tracking=True)
    part_operation = fields.Many2one('part.operation', string='Part Operation', tracking=True)

class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string='Status', default='active', compute='_compute_status', store=True)

    @api.depends('product_tmpl_id.seller_ids')
    def _compute_status(self):
        for record in self:
            record.status = 'inactive'  # default
            if record.product_tmpl_id:
                # Filter seller_infos by same partner_id
                seller_infos = record.product_tmpl_id.seller_ids.filtered(lambda s: s.partner_id == record.partner_id)
                if seller_infos:
                    # Get the most recent one
                    most_recent = seller_infos.sorted(
                        key=lambda r: r.create_date or fields.Datetime.now(), reverse=True
                    )[0]
                    if record == most_recent:
                        record.status = 'active'

