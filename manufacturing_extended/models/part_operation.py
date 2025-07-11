from odoo.exceptions import ValidationError, UserError
from odoo import api, fields, models, _


class PartOperation(models.Model):
    _name = 'part.operation'
    _description = 'Part Operation'
    _order = "sequence, id"
    _inherit = ['mail.thread.cc', 'mail.thread.main.attachment', 'mail.activity.mixin']

    @api.model
    def get_semi_finished_goods(self):
        fg_products = self.env.ref('inventory_extended.category_finished_goods').id
        sfg_products = self.env.ref('inventory_extended.category_semi_finished_goods').id
        return [('categ_id', 'in', [sfg_products, fg_products]), ('type', 'in', ['product', 'consu'])]

    # INVISIBLE FIELDS START
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    logged_user = fields.Many2one('res.users', string='Logged User', compute='get_logged_user')
    active = fields.Boolean(default=True)
    # INVISIBLE FIELDS END

    sequence = fields.Integer(
        'Sequence', default=1, required=True,
        help="Gives the sequence order when displaying a list of Part Operations.")

    name = fields.Char(string='Name', default='New')
    operation_id = fields.Many2one('mrp.routing.workcenter', string='Operation')
    status = fields.Selection([('draft', 'Draft'), ('progress', 'Progress'), ('finish', 'Finished')], string="State", default='draft')
    operation_code = fields.Char(string='Operation No')
    operation_description = fields.Char(string='Operation Description')
    piece_weight = fields.Float(string='Piece Weight')
    standard_qty = fields.Float(string='Standard Quantity')
    container_type = fields.Many2one('std.container', string='Container Type')
    location = fields.Char(string='Location')
    flowchart_symbol = fields.Selection([
        ('inspection', 'Inspection'),
        ('inspection_with_spc', 'Inspection with SPC'),
        ('operation', 'Operation'),
        ('operation_inspection', 'Operation-Inspection'),
        ('operation_spc', 'Operation-SPC'),
        ('storage', 'Storage'),
        ('sub_operation', 'Sub-Operation'),
        ('transportation', 'Transportation'),
        ('transportation_inspection', 'Transportation-Inspection'),
    ])
    part_workcenter_lines = fields.One2many('part.workcenter.lines', 'part_operation_id')
    user_id = fields.Many2one('res.users', string='User Name', default=lambda self: self.env.user)
    updated_by = fields.Many2one('res.users', string='Updated By', default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', string='Supplier')
    type = fields.Char(string='Type', default='Production')
    workcenters_text = fields.Text(compute='_compute_bom', store=True)
    bom_text = fields.Text(compute='get_workcenters', store=True)
    routing_id = fields.Many2one('process.routing', string='Routing Id')
    product_id = fields.Many2one('product.template', string='Part No', related='routing_id.product_id', store=True)
    operation_type = fields.Selection([('internal', 'Internal'), ('external', 'External')], default='internal',
                                      string='Operation Type')
    shippable = fields.Boolean(string='Shippable')
    production_op = fields.Boolean(string='Production')
    final_production_op = fields.Boolean(string='Final Production')
    income_inspection = fields.Boolean(string='Income Inspection')
    final_inspection = fields.Boolean(string='Final Inspection')
    final_inspection_need = fields.Boolean(string='Final Inspection Need')

    operation_bom_lines = fields.One2many('operation.bom', 'operation_bom_id', string='Operation Bom')
    out_product_id = fields.Many2one('product.template', string='Out Part No')
    bom_lines = fields.One2many('mrp.bom', 'part_operation_id', string='Bom')
    bom_id = fields.Many2one('mrp.bom', string='BOM ID')

    picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type', compute='compute_picking_type', store=True)
    operation_list_id = fields.Many2one('mrp.operation.list', string='Operation List')

    raw_id = fields.Many2one('product.template', string='Raw Material', tracking=True)

    @api.depends('operation_list_id')
    def compute_picking_type(self):
        for part in self:
            part.picking_type_id = part.operation_list_id.picking_type_id.id if part.operation_list_id else False

    def set_semi_finished_product(self):
        for i in self:
            if i.production_op and not i.out_product_id:
                product_id = self.env['product.template'].sudo().create({
                    'name' : i.product_id.name + ' - ' + i.operation_code,
                    'default_code' :str(i.product_id.default_code + ' - ' + i.operation_code),
                    'categ_id': self.env.ref('inventory_extended.category_semi_finished_goods').id,
                })
                product_id.write({
                    'default_code': str(i.product_id.default_code + ' - ' + str(i.operation_code))
                })
                i.write({'out_product_id': product_id.id})
                self.create_mo_setup(product_id)

    def create_mo_setup(self, product_id):
        bom_id = self.env['mrp.bom'].sudo().create({
            'product_tmpl_id': product_id.id,
            'product_qty': 1,
            'bom_line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'product_qty': line.quantity,
            })for line in self.operation_bom_lines],
            'operation_ids': [(0, 0, {
                'name': self.operation_description,
                'workcenter_id': 5,
            })]
        })
        if bom_id.operation_ids:
            self.operation_id = bom_id.operation_ids[0].id  # Store the first operation ID

    @api.depends('operation_bom_lines')
    def _compute_bom(self):
        for record in self:
            record.bom_text = "\n".join(
                filter(None, (line.product_id.default_code or '' for line in
                              record.operation_bom_lines))) if record.operation_bom_lines else False


    @api.depends('part_workcenter_lines')
    def get_workcenters(self):
        for record in self:
            record.workcenters_text = "\n".join(
                filter(None, (line.work_center_id.name or '' for line in
                              record.part_workcenter_lines))) if record.part_workcenter_lines else False

    def get_logged_user(self):
        self.logged_user = self.env.uid

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.sudo().env['ir.sequence'].next_by_code('part.operation') or '/'
        return super().create(vals_list)




class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    part_operation_id = fields.Many2one('part.operation', string='Part Operation')


class OperationBom(models.Model):
    _name = 'operation.bom'
    _description = 'Operation Bom'

    operation_bom_id = fields.Many2one('part.operation', string='Operation ID')
    product_id = fields.Many2one('product.template', string='Part')
    quantity = fields.Float(string='Quantity')


class PartWorkcenterLines(models.Model):
    _name = 'part.workcenter.lines'
    _description = 'Part Workcenter Lines'

    part_operation_id = fields.Many2one('part.operation', string='Part Operation')
    work_center_id = fields.Many2one('mrp.workcenter', string='Workcenter')
    setup = fields.Float(string='Setup (hrs)')
    standard_rate = fields.Float(string='Standard Rate (Pcs / hrs)')
    ideal_rate = fields.Float(string='Ideal Rate (Pcs / hrs)')
    target_rate = fields.Float(string='Target Rate (Pcs / hrs)')
    minimum_performance = fields.Float(string='Minimum Performance')
    expected_performance = fields.Float(string='Expected Performance')
    crew = fields.Float(string='Crew (people)')
    note = fields.Text(string='Note')
