from odoo.exceptions import ValidationError, UserError
from odoo import api, fields, models, _


class ProductionOrder(models.Model):
    _name = 'production.order'
    _description = 'Production Order'
    _inherit = ['mail.thread.cc', 'mail.thread.main.attachment', 'mail.activity.mixin']

    name = fields.Char(string='Name', default='New')
    product_id = fields.Many2one('product.product', string='Part No', domain="[('part_type', '=', 'fg')]")
    quantity = fields.Float(string='Quantity')
    user_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    logged_user = fields.Many2one('res.users', string='Logged User', compute='get_logged_user')
    active = fields.Boolean(default=True)
    status = fields.Selection([('draft', 'Draft'), ('to_approve', 'To Approve'), ('confirm', 'Confirm')],
                              string="State",
                              default='draft', tracking=True, )
    delivery_reference_id = fields.Many2one('stock.picking', string='Delivery Reference')
    manufacturing_reference_id = fields.Many2one('mrp.production', string='Manufacturing Reference')
    partner_id = fields.Many2one('res.partner', string='Customer')
    bom_id = fields.Many2one('mrp.bom', string='BOM', domain="""[
        '&',
            '|',
                ('company_id', '=', False),
                ('company_id', '=', company_id),
            '&',
                '|',
                    ('product_id','=',product_id),
                    '&',
                        ('product_tmpl_id.product_variant_ids','=',product_id),
                        ('product_id','=',False),
        ('type', '=', 'normal')]""")

    manufacturing_count = fields.Integer(string='Manufacturing Count', compute='_compute_manufacturing_count')
    delivery_count = fields.Integer(string='Delivery Count', compute='_compute_delivery_count')

    def _compute_manufacturing_count(self):
        self.manufacturing_count = self.env['mrp.production'].search_count(
            [('name', '=', self.manufacturing_reference_id.name)])

    def get_manufacturing_views(self):
        self.sudo().ensure_one()
        form_view = self.sudo().env.ref('mrp.mrp_production_form_view')
        tree_view = self.sudo().env.ref('mrp.mrp_production_tree_view')
        return {
            'name': _('Manufacturing'),
            'res_model': 'mrp.production',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('name', '=', self.manufacturing_reference_id.name)],
        }

    def _compute_delivery_count(self):
        self.delivery_count = self.env['stock.picking'].search_count([('name', '=', self.delivery_reference_id.name)])

    def get_delivery_views(self):
        self.sudo().ensure_one()
        form_view = self.sudo().env.ref('stock.view_picking_form')
        tree_view = self.sudo().env.ref('stock.vpicktree')
        return {
            'name': _('Delivery'),
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('name', '=', self.delivery_reference_id.name)],
        }

    @api.onchange('product_id')
    def get_product_id_bom(self):
        self.bom_id = self.product_id.variant_bom_ids[0].id if self.product_id.variant_bom_ids else False

    def _get_stock_type_ids(self):
        data = self.env['stock.picking.type'].search([])
        for line in data:
            if line.code == 'outgoing':
                return line

    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type',
                                      default=_get_stock_type_ids,
                                      help="This will determine picking type of incoming shipment")

    def submit_to_approve(self):
        if self.quantity <= 0.00:
            raise ValidationError(_("Please enter the quantity before submitting !"))
        self.write({'status': 'to_approve'})

    def button_confirm(self):
        for record in self:
            manufacturing = self.env['mrp.production'].create({
                'product_id': record.product_id.id,
                'product_qty': record.quantity,
                'bom_id': record.bom_id.id,
            })
            manufacturing.action_confirm()
            manufacturing.button_mark_done()
            record.manufacturing_reference_id = manufacturing.id
            delivery = self.env['stock.picking'].create({
                'partner_id': record.partner_id.id,
                'picking_type_id': record.picking_type_id.id,
                'origin': record.name,
                'move_ids_without_package': [(0, 0, {
                    'product_id': record.product_id.id,
                    'name': record.product_id.name,
                    'quantity': record.quantity,
                    'location_id': self.env.ref('stock.stock_location_stock').id,
                    'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                })],
            })
            delivery.button_validate()
            record.delivery_reference_id = delivery.id
            self.write({'status': 'confirm'})

    def get_logged_user(self):
        self.logged_user = self.env.uid

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.sudo().env['ir.sequence'].next_by_code('production.order') or '/'
        return super().create(vals_list)
