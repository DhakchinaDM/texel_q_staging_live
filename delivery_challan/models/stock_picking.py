from asyncio import exceptions
from xml.dom import ValidationErr
from odoo import models, fields, api, _
from odoo.tests.common import Form, tagged
from odoo.exceptions import AccessError, UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _description = 'Delivery Order'
    _order = 'create_date desc'

    products_ids = fields.Many2many('product.product', string='Products', compute='_compute_products_ids', store=True)

    @api.depends('move_ids_without_package.product_id')
    def _compute_products_ids(self):
        for rec in self:
            product_ids = rec.move_ids_without_package.mapped('product_id').ids
            if product_ids:
                rec.products_ids = [(6, 0, product_ids)]
            else:
                rec.products_ids = [(5, 0, 0)]

    @api.model
    def _default_note(self):
        return (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("delivery_challan.use_picking_terms")
                and self.env.company.picking_terms
                or ""
        )

    def _default_picking_type_id(self):
        picking_type_code = self.env.context.get('restricted_picking_type_code')
        picking_dc_entry = self.env.context.get('restricted_dc_entry')
        if picking_type_code:
            picking_types = self.env['stock.picking.type'].search([
                ('code', '=', picking_type_code),
                ('dc_entry_type', '=', picking_dc_entry),
                ('company_id', '=', self.env.company.id),
            ])
            return picking_types[:1].id

    note = fields.Html("Terms and conditions", default=_default_note)
    transport_mode = fields.Selection([
        ('by_road', 'By Road'),
        ('by_hand', 'By Hand'),
        ('by_courier', 'By Courier'),
    ], default='by_road', string='Mode of Transport')

    contact_person = fields.Many2one('res.partner', string='Contact Person', domain="[('parent_id', '=', partner_id)]")
    contact_person_str = fields.Char(string='Contact Person ')
    place_of_supply = fields.Char(string='Place of supply', related='partner_id.city')
    vehicle_no = fields.Char(string='Vehicle No')
    vehicle = fields.Char(string='Velicle')

    dc_records = fields.Boolean(string='DC Records', compute='_compute_show_dc_records')
    dc_entry_type = fields.Selection([
        ('dc', 'Delivery Challan'),
        ('r_dc', 'Return Delivery Challan'),
        ('jw', 'Job Work'),
        ('r_jw', 'Return Job Work'),
        ('sjw', 'Service Job Work'),
        ('r_sjw', 'Return Service Job Work'),
    ], string="DC Entry Type", compute='_compute_dc_entry_type', store=True)

    stock_return_type = fields.Selection([
        ('return', 'Returnable'),
        ('non-return', 'Non - Returnable'),
    ], default='return', string='Return Type')
    picking_dc_type = fields.Selection([
        ('standard', 'Standard'),
        ('non-standard', 'Non - Standard'),
    ], default='standard', string='DC Type')

    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        required=True, readonly=True, index=True,
        default=_default_picking_type_id)

    quality = fields.Boolean(string='Quality Check')
    quality_checked = fields.Boolean(string="Quality cleared")
    remarks = fields.Text(string='Remark')

    @api.onchange('picking_dc_type')
    def _onchange_std_non_std(self):
        """ Automatically add the product when 'non-std' is selected """
        product = self.env.ref('delivery_challan.product_dc_general')

        if self.picking_dc_type == 'non-standard':
            existing_product = self.move_ids_without_package.filtered(
                lambda m: m.product_id == product.product_variant_id)
            if not existing_product:
                self.move_ids_without_package = [(0, 0, {
                    'product_id': product.product_variant_id.id,
                    'name': product.name,
                    'picking_dc_type': 'non-standard',
                    'product_uom_qty': 1.0,
                    'product_uom': product.uom_id.id,
                    'location_id': self.location_id.id,
                    'location_dest_id': self.location_dest_id.id,
                })]
        else:
            self.move_ids_without_package = False

    @api.depends('picking_type_id')
    def _compute_dc_entry_type(self):
        for s in self:
            if s.picking_type_id:
                s.dc_entry_type = s.picking_type_id.dc_entry_type
            else:
                s.dc_entry_type = False

    @api.depends('picking_type_code', 'picking_type_id')
    def _compute_show_dc_records(self):
        for rec in self:
            rec.dc_records = rec.picking_type_id.id == self.env.ref('delivery_challan.dc_operation').id

    def action_dc_report(self):
        self.write({'printed': True})
        return self.env.ref('delivery_challan.report_dc_report').report_action(self)

    def action_jobdc_report(self):
        self.write({'printed': True})
        return self.env.ref('delivery_challan.report_jobdc_report').report_action(self)

    def quality_check(self):
        self.create_quality_check()
        self.quality_checked = True

    def button_validate(self):
        print("--------------------------------------------------")
        res = super(StockPicking, self).button_validate()

        if self.picking_type_code == 'outgoing' and self.dc_entry_type in ['dc', 'jw']:
            print("-----------------111111111111111111111111111111 != 'incoming'-------------")
            # super().button_validate()
            # self.set_job_status()
            self.create_return_job_work()
            return res

            # self.action_create_return_order()
        elif self.picking_type_code == 'incoming':
            print("-----------------22222222222222222222222222222222 != 'incoming'-------------")

            # super().button_validate()
            if self.quality:
                print("-----------------333333333333333333333333333333333 != 'incoming'-------------")

                self.quality_check()
                # self.set_job_status()
            return res

            # if self.quality:
            #     print("+++++++++++++++++++++")
            #     if self.quality_checked:
            #         super().button_validate()
            #         self.set_job_status()
            #
            #     else:
            #         raise ValidationError("Quality Check is required before validation.")
            # elif not self.quality:
            #     print("----------")
            #     super().button_validate()
        else:
            print(
                "###########################eleleleleleslelslelslelslelelselslelslelslels##########################################")
            # self.set_job_status()
            # super().button_validate()
            return res

    def set_job_status(self):
        if self.picking_type_code == 'incoming':
            jw_ids = self.env['stock.picking'].search([('return_job_work_id', '=', self.id)])
            if jw_ids:
                for pick in jw_ids:
                    pick.write({
                        'job_work_status': 'completed',
                    })
                    next_operation = self.env['part.operation.line'].search([
                        ('job_order_id', '=', pick.part_operation_line_id.job_order_id.id),
                        ('sequence', '=', pick.part_operation_line_id.sequence + 1)
                    ])
                    pick.part_operation_line_id.lot_ids = [(4, self.lot_id.id)]
                    next_operation.lot_ids = [(4, self.lot_id.id)]
            else:
                self.write({
                    'job_work_status': 'completed',
                })
                self.part_operation_line_id.lot_ids = [(4, self.lot_id.id)]
        else:
            jw_ids = self.env['stock.picking'].search([('job_work_id', '=', self.id)])
            if jw_ids:
                for pick in jw_ids:
                    pick.write({
                        'job_work_status': 'send',
                    })
            else:
                self.write({
                    'job_work_status': 'send',
                })

    def create_return_job_work(self):
        for picking in self:
            print('------------------picking------------------', picking, picking.name)
            if picking.picking_type_id.code != 'outgoing':
                continue  # Only proceed for outgoing pickings

            # Get Incoming Picking Type (you might want to filter it better based on warehouse)
            incoming_picking_type_dc = self.env.ref('delivery_challan.return_dc_operation')
            incoming_picking_type = self.env.ref('delivery_challan.return_jw_operation')

            if not incoming_picking_type_dc:
                raise UserError("Incoming picking type not found for the warehouse.")
            if not incoming_picking_type:
                raise UserError("Incoming picking type not found for the warehouse.")

            next_operation = self.env['part.operation.line'].search([
                ('job_order_id', '=', picking.part_operation_line_id.job_order_id.id),
                ('sequence', '=', picking.part_operation_line_id.sequence + 1)
            ])

            # Create a new picking (incoming)
            if self.dc_entry_type == 'dc':
                new_picking = self.env['stock.picking'].create({
                    'partner_id': picking.partner_id.id,
                    'picking_type_id': incoming_picking_type_dc.id,
                    'origin': f"Return of {picking.name}",
                    'location_id': incoming_picking_type_dc.location_dest_id.id,  # reverse of outgoing
                    'location_dest_id': incoming_picking_type_dc.location_id.id,
                    'quality': picking.quality,
                    # 'part_operation_line_id': next_operation.id,
                    'return_id': picking.id,
                    'move_ids_without_package': [],
                })
            if self.dc_entry_type == 'jw':
                new_picking = self.env['stock.picking'].create({
                    'partner_id': picking.partner_id.id,
                    'picking_type_id': incoming_picking_type.id,
                    'origin': f"Return of {picking.name}",
                    'location_id': incoming_picking_type.location_dest_id.id,  # reverse of outgoing
                    'location_dest_id': incoming_picking_type.location_id.id,
                    'quality': picking.quality,
                    # 'part_operation_line_id': next_operation.id,
                    'return_id': picking.id,
                    'move_ids_without_package': [],
                })

            # Create move lines
            for move in picking.move_ids_without_package:
                self.env['stock.move'].create({
                    'name': move.name,
                    'product_id': move.product_id.id,
                    'product_uom_qty': move.product_uom_qty,
                    'product_uom': move.product_uom.id,
                    'picking_id': new_picking.id,
                    'location_id': new_picking.picking_type_id.default_location_src_id.id,
                    'location_dest_id': new_picking.picking_type_id.default_location_dest_id.id,
                })
            new_picking.action_confirm()
            next_operation.write({
                'job_work_ids': [(4, new_picking.id)],
            })
            jw_ids = self.env['stock.picking'].search([('job_work_id', '=', picking.id)])
            print('------------------new_picking------------------', jw_ids)
            if jw_ids:
                for pick in jw_ids:
                    print('----------PICK--------', pick, pick.name)
                    pick.write({
                        'return_job_work_id': new_picking.id
                    })
            else:
                picking.write({
                    'return_job_work_id': new_picking.id
                })
        return new_picking

    def create_quality_check(self):
        print('++++++++_______QUALITY____---=-=-=-=-=-=')
        for move in self.move_ids_without_package:
            income = self.env['incoming.inspection'].create({
                'material_grade': move.product_tmpl_id.material_grade,
                'product_id': move.product_tmpl_id.id,
                'partner_id': move.partner_id.id,
                # 'picking_id': vals.id,
                # 'purchase_id': purchase.id if purchase else False,
                # 'po_date': purchase.confirm_date if purchase else False,
                'draw_rev_no': move.product_tmpl_id.draw_rev_no,
                'draw_rev_date': move.product_tmpl_id.draw_rev_date,
                'lot_qty': move.quantity,
                'lot_id': move.lot_ids[0].id if move.lot_ids else False,
                'dc_invoice_no': move.supplier_reference,
                # 'grn_date': vals.create_date,
                'stock_move_id': move.id,
                'inspection_incoming_type': 'incoming_part',
                'type': 'sub_cont',
                'parameters_ids': self._prepare_parameters_vals(move)
            })
            self.income_inspection_ids = [(4, income.id)]

    def action_create_return_order(self):
        stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(
            active_ids=self.ids, active_id=self.id, active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.create_returns()


class StockMove(models.Model):
    _inherit = 'stock.move'

    total_amount = fields.Float(string='Total', compute='get_total_amount')
    job_work_service = fields.Char(string='Job work Service')
    job_work_id = fields.Many2one('job.work.type', string='Purpose')
    dc_description = fields.Char(string='Description ')

    picking_dc_type = fields.Selection([
        ('standard', 'Standard'),
        ('non-standard', 'Non - Standard'),
    ], default='standard', string='DC Type')

    hsn_code = fields.Char(string='HSN/SAC Code', related='product_id.l10n_in_hsn_code', readonly=False, store=True)
    supplier_part_no = fields.Char(string='Supplier Part No', readonly=False, store=True,
                                   compute='_compute_supplier_part_no')

    taxes = fields.Many2one('account.tax', string="Tax")
    taxe_value = fields.Char(string="Tax Value", compute="_compute_tax_values", store=True)

    @api.depends('product_id')
    def _compute_supplier_part_no(self):
        for rec in self:
            if rec.product_id:
                rec.supplier_part_no = rec.product_id.supplier_part
            else:
                rec.supplier_part_no = False

    @api.depends('taxe_value', 'taxes')
    def _compute_tax_values(self):
        for rec in self:
            if rec.taxes:
                tax_percentage = rec.taxes.amount / 100
                taxe_value = rec.total_amount * tax_percentage
                rec.taxe_value = round(taxe_value, 2)
                rec.total_amount = float(rec.total_amount) + float(rec.taxe_value)
            else:
                rec.taxe_value = 0.0

    @api.depends('product_uom_qty', 'price_unit')
    def get_total_amount(self):
        for product in self:
            if product.product_uom_qty != 0.00 and product.price_unit != 0.00:
                product.total_amount = product.product_uom_qty * product.price_unit
            else:
                product.total_amount = False

    @api.model
    def default_get(self, fields_list):
        """ Ensure the correct product is set when adding a new line manually """
        defaults = super().default_get(fields_list)
        picking_id = self._context.get('default_picking_id')
        if picking_id:
            picking = self.env['stock.picking'].browse(picking_id)
            if picking.picking_dc_type == 'non-standard' and picking.dc_entry_type in ['dc', 'jw']:
                product = self.env.ref('delivery_challan.product_dc_general')
                defaults.update({
                    'product_id': product.product_variant_id.id,
                    'picking_dc_type': 'non-standard'
                })
            elif picking.dc_entry_type in ['sjw']:
                product = self.env.ref('delivery_challan.product_dc_general_sjw')
                defaults.update({
                    'product_id': product.product_variant_id.id,
                    'picking_dc_type': 'standard'
                })
        return defaults


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    def update_a_sequence_prefix(self):
        stock = self.env['stock.picking.type'].sudo().search([])
        for i in stock:
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!1111", i.sequence_code)

    dc_entry_type = fields.Selection([
        ('dc', 'Delivery Challan'),
        ('r_dc', 'Return Delivery Challan'),
        ('jw', 'Job Work'),
        ('r_jw', 'Return Job Work'),
        ('sjw', 'Service Job Work'),
        ('r_sjw', 'Return Service Job Work'),
    ], string="DC Entry Type")

    # prefix = fields.Char("Prefix")
    # year = fields.Char("Year")


class JobWorkType(models.Model):
    _name = 'job.work.type'
    _description = "Job Work Type"

    name = fields.Char(string='Name', required=True)
