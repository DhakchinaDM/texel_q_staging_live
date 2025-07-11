from odoo import fields, models, api, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    _description = 'Purchase Order'

    current_revision_id = fields.Many2one('purchase.order', 'Current revision', readonly=True, copy=True)
    old_revision_ids = fields.One2many('purchase.order', 'current_revision_id', 'Old revisions', readonly=True,
                                       context={'active_test': False})
    revision_number = fields.Integer('Revision', copy=False)
    unrevisioned_name = fields.Char('Purchase Order Reference', copy=False, readonly=True)
    active = fields.Boolean('Active', default=True, copy=True)
    created_date = fields.Datetime('Quotation Date', required=True,
                                   default=lambda self: fields.Datetime.now())
    revised = fields.Boolean('Revised Quotation')

    @api.model_create_multi
    def create(self, vals_list):
        orders = self.browse()
        partner_vals_list = []
        for vals in vals_list:
            company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
            # Ensures default picking type and currency are taken from the right company.
            self_comp = self.with_company(company_id)
            if vals.get('name', 'New') == 'New':
                seq_date = None
                if 'date_order' in vals:
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
                vals['name'] = self_comp.env['ir.sequence'].next_by_code('purchase.order', sequence_date=seq_date) or '/'
                vals['unrevisioned_name'] = vals['name']
            vals, partner_vals = self._write_partner_values(vals)
            partner_vals_list.append(partner_vals)
            orders |= super(PurchaseOrder, self_comp).create(vals)
        for order, partner_vals in zip(orders, partner_vals_list):
            if partner_vals:
                order.sudo().write(partner_vals)  # Because the purchase user doesn't have write on `res.partner`
        return orders

    def action_revision(self):
        self.ensure_one()
        view_ref = self.env['ir.model.data'].check_object_reference('purchase', 'purchase_order_form')
        view_id = view_ref and view_ref[1] or False,
        self.with_context(purchase_revision_history=True).copy()
        self.write({'state': 'draft',
                    'created_date': fields.Datetime.now(),
                    'date_order': fields.Datetime.now()})
        self.order_line.write({
            'state': 'draft'
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Order'),
            'res_model': 'purchase.order',
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }

    @api.returns('self', lambda value: value.id)
    def copy(self, defaults=None):
        if not defaults:
            defaults = {}
        if not self.unrevisioned_name:
            self.unrevisioned_name = self.name
        if self.env.context.get('purchase_revision_history'):
            prev_name = self.name
            revno = self.revision_number
            self.write({'revision_number': revno + 1,
                        'name': '%s-A%d' % (self.unrevisioned_name, revno + 1),
                        'remark_one': False,
                        'remark_two': False,
                        'remark_three': False,
                        })
            defaults.update(
                {'name': prev_name, 'revision_number': revno, 'revised': True, 'active': True, 'state': 'cancel',
                 'current_revision_id': self.id, 'unrevisioned_name': self.unrevisioned_name, })
        return super(PurchaseOrder, self).copy(defaults)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    revision = fields.Integer(string="Purchase Revision", compute='purchase_revision_count')

    def purchase_revision_count(self):
        for rec in self:
            rec.revision = self.env['purchase.order'].sudo().search_count([('origin', '=', rec.name)])

    def action_revision(self):
        return {
            'name': _('Purchase amendment'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': self.id,
            'domain': [('origin', '=', self.name)],
            'target': 'current'
        }

    def purchase_revision(self):
        line_ids = []
        line_vals = {}
        for rec_line in self.move_ids_without_package:
            line_vals = {
                'product_id': rec_line.product_id.id,
                'name': rec_line.product_id.name,
                'date_planned': fields.Datetime.now(),
                'product_qty': rec_line.product_uom_qty,
                'status': 'draft',
            }
            line_ids.append((0, 0, line_vals))
        if line_vals:
            proposal = self.env['purchase.order'].sudo().create({
                'partner_id': self.partner_id.id,
                'name': self.origin + '-' + "A1",
                'origin': self.name,
                'user_id': self.env.user.id,
                'order_line': line_ids
            })
            po = self.env['purchase.order'].sudo().search([('name', '=', self.origin)])
            self.write({
                'state': 'cancel',
            })
            po.write({
                'state': 'cancel',
                'remark_cancel': 'Canceled Due to Revision by %s' % self.env.user.name,
            })
