from odoo import models, fields, api, _


class SupplierPerformCategory(models.Model):
    _name = 'supplier.perform.category'
    _description = 'Supplier Performance Category'

    name = fields.Char(string='Category Name')


class SupplierEvaluationLine(models.Model):
    _name = 'supplier.evaluation.line'
    _description = 'Supplier evaluation Line'

    evaluation_category = fields.Many2one('supplier.perform.category', string='Evaluation Category')
    picking_id = fields.Many2one('stock.picking', string='picking')
    value = fields.Selection([('1', 'Very Low'), ('2', "Low"), ('3', 'Medium'), ('4', 'Good'), ('5', 'very Good')],
                             string="Value", )
    note = fields.Char(string='Note')
    val = fields.Integer(string=' Value', compute='_compute_value')

    @api.depends('value')
    def _compute_value(self):
        for record in self:
            if record.value == '2':
                record.val = 25
            elif record.value == '3':
                record.val = 50
            elif record.value == '4':
                record.val = 75
            elif record.value == '5':
                record.val = 100
            else:
                record.val = 0


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    evaluation_line = fields.One2many('supplier.evaluation.line', 'picking_id')
    pick_type = fields.Selection([('in', 'In'), ('out', 'Out')], compute='_compute_pick_type')

    def _compute_pick_type(self):
        for rec in self:
            rec.pick_type = 'out' if rec.picking_type_id.id == self.env.ref('stock.picking_type_out').id else False

    def print_grn_label(self):
        return self.env.ref('supplier_perfomance.report_grn_label_pdf').report_action(self)

    def render_report(self, docids, data=None):
        doc = self.env['stock.picking'].browse(docids[0])
        context = {
            'doc': doc,
            'line': doc.line_id,
        }
        return self.env['ir.qweb']._render('supplier_performance.grn_label_template', context)

    def button_validate(self):
        lines = []
        for j in self.move_ids_without_package:
            sequence_code = 'stock.barcode.sequence'
            order_date = self.create_date
            order_date = str(order_date)[0:10]
            j.barcode = self.env['ir.sequence'] \
                .with_context(ir_sequence_date=order_date).next_by_code(sequence_code)
        for i in self.env['supplier.perform.category'].search([]):
            vals = (0, 0, {
                'evaluation_category': i.id,
            })
            lines.append(vals)
        self.write({'evaluation_line': lines})
        return super(StockPicking, self).button_validate()


class StockMove(models.Model):
    _inherit = 'stock.move'

    barcode = fields.Char(string='Barcode')
    mfg_date = fields.Date(string='MFG Date')
    supplier_reference = fields.Char(string='Supplier Reference', compute='_compute_reference', readonly=False,
                                     store=True)
    inv_date = fields.Date(string="Invoice Date", compute='_compute_reference', readonly=False, store=True)

    @api.depends('picking_id')
    def _compute_reference(self):
        for record in self:
            if record.picking_id:
                record.supplier_reference = record.supplier_reference or record.picking_id.supplier_reference
                record.inv_date = record.inv_date or record.picking_id.inv_date
            else:
                record.supplier_reference = False
                record.inv_date = False


class ResPartner(models.Model):
    _inherit = 'res.partner'
