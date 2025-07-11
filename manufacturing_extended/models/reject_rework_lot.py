from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class RejectReworkLot(models.Model):
    _name = "reject.rework.lot"
    _description = "Reject Rework Lot"
    _order = "name desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    doc_num = fields.Char(string='Document Number', tracking=True)
    rev_date = fields.Date(string='Revision Date', tracking=True)
    rev_num = fields.Char(string='Revision Number', tracking=True)


    name = fields.Char(string="Name", required=True, copy=False, tracking=True)
    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lot",
        required=True,
        ondelete="cascade", tracking=True
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Part No",
        related="lot_id.product_id",
        store=True, tracking=True
    )
    part_name = fields.Char(string="Part Name", related="product_id.name", tracking=True)
    quantity = fields.Float(string="Quantity", tracking=True)
    confirm_qty = fields.Float(string="Confirmed Qty", tracking=True)
    state = fields.Selection([
        ("draft", "Draft"),
        ("done", "Done"),
        ("debit_note", "Debit Note"),
        ("scrap", "Scrap"),
        ("ok", "Ok"),
        ("cancel", "Cancelled"),
    ],
        string="Status",
        default="draft", tracking=True
    )
    reason = fields.Text(string="Operator Reason", tracking=True)
    approver_reason = fields.Text(string="Approver Reason", tracking=True)

    lot_type = fields.Selection([('m_reject', 'Material'), ('p_reject', 'Process'), ('rework', 'Rework'), ('ok', 'Ok')],
                                string='Lot Type', store=True, compute='compute_lot_type', readonly=False,
                                tracking=True)
    debit_note_id = fields.Many2one('account.move', string="Debit Note", tracking=True)
    scrap_id = fields.Many2one('stock.scrap', string="Scrap", required=False, tracking=True)

    date = fields.Date(string="Date", default=fields.Date.today, tracking=True)
    customer_id = fields.Many2one('res.partner', string="Customer", tracking=True)
    operation_no = fields.Char(string="Operation No", tracking=True)

    problem = fields.Text(string="Problem", compute='_compute_problem', store=True, tracking=True)

    supplier_id = fields.Many2one('res.partner', string="Supplier", tracking=True)

    workcenter_id = fields.Many2one('mrp.workcenter', string="Work Center", tracking=True)
    process_name = fields.Char(string="Process Name", compute='compute_process_name', store=True, tracking=True)

    batch_no = fields.Char(string="Batch No", tracking=True)
    job_id = fields.Many2one('job.planning', string="Job ID", tracking=True)
    mo_id = fields.Many2one('mrp.production', string="Manufacturing Order", tracking=True)
    part_operation_line_id = fields.Many2one('part.operation.line', string='Part Operation Line', store=True,
                                             related="mo_id.part_operation_line_id", readonly=False, tracking=True)

    reject_entry_type = fields.Selection([
        ('production', 'Production'),
        ('iqc_raw', 'IQC Raw'),
        ('iqc_part', 'IQC Part'),
    ], default='production', string='Reject Entry Type', tracking=True)

    shift = fields.Selection(
        [('shift_I', 'Shift I'), ('shift_II', 'Shift II'), ('shift_III', 'Shift III'), ('shift_G', 'Shift G')],
        string='Shift', tracking=True)
    operator_id = fields.Many2one('hr.employee', string="Operator", tracking=True)

    delivery_id = fields.Many2one('stock.picking', string='Delivery', tracking=True)
    parent_id = fields.Many2one('reject.rework.lot', string='Parent', tracking=True)

    @api.depends('workcenter_id')
    def compute_process_name(self):
        for i in self:
            if i.reject_entry_type == 'production':
                i.process_name = i.workcenter_id.name
            else:
                i.process_name = 'Incoming Inspection'

    @api.depends('reason', 'approver_reason')
    def _compute_problem(self):
        for rec in self:
            rec.problem = rec.approver_reason or rec.reason

    @api.depends('lot_id')
    def compute_lot_type(self):
        for rec in self:
            if rec.lot_id:
                rec.lot_type = rec.lot_id.lot_type
            else:
                rec.lot_type = False

    def confirm_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def confirm_rejection(self):
        for rec in self:
            if rec.approver_reason:
                rec.state = 'done'
            else:
                raise ValidationError(_("You cannot confirm a rejection without an approver reason."))
        # context = dict(self._context or {})
        # reject_rework_ids = self.env['reject.rework.lot'].sudo().search([('id', 'in', context.get('active_ids'))])
        # for rr in reject_rework_ids:
        #     rr.state = 'done'
        # print('Confirming RejectionLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLll', self, reject_rework_ids)
        # return True

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.sudo().env['ir.sequence'].next_by_code('reject.rework.lot') or 'New'
        return super().create(vals_list)


class RejectHanding(models.Model):
    _name = 'reject.handling'
    _description = "Reject Handling"

    name = fields.Char(string="Name", required=True, copy=False)
    date = fields.Datetime(string="Date", default=fields.Datetime.now)
    partner_id = fields.Many2one('res.partner', string="Partner")

    lot_type = fields.Selection([('ok', 'Ok'), ('m_reject', 'Material'), ('p_reject', 'Process'), ('rework', 'Rework')],
                                string='Lot Type')
    debit_note_id = fields.Many2one('account.move', string="Debit Note")
    scrap_id = fields.Many2one('stock.scrap', string="Scrap", required=False)
    reject_handling_line_ids = fields.One2many('reject.handling.line', 'reject_handling_id',
                                               string="Reject Handling Lines")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('debit_note', 'Debit Note'),
        ('scrap', 'Scrap'),
        ('ok', 'Ok'),
        ('cancel', 'Cancelled'),
    ], string="Status", default='draft', copy=False)
    partial_done = fields.Boolean(string="Partial Done", compute='compute_partial_done')

    @api.depends('reject_handling_line_ids.confirm_qty')
    def compute_partial_done(self):
        for rec in self:
            if any(line.confirm_qty < line.quantity for line in rec.reject_handling_line_ids):
                rec.partial_done = True
            else:
                rec.partial_done = False

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)

        line_val = []
        lot_type = ''
        context = dict(self._context or {})
        reject_rework_ids = self.env['reject.rework.lot'].sudo().search([('id', 'in', context.get('active_ids'))])
        if reject_rework_ids:
            lot_types = reject_rework_ids.mapped('lot_type')
            if len(set(lot_types)) > 1:
                raise ValidationError(_("All selected Reject Rework Lots must have the same Lot Type."))
            if any(rr.state in ['draft', 'cancel'] for rr in reject_rework_ids):
                raise ValidationError(
                    _("You cannot process Reject Rework Lots that are in 'Draft' or 'Cancelled' state."))

        if not reject_rework_ids:
            return res
        for line in reject_rework_ids:
            lot_type = line.lot_type
            line_data = (0, 0, {
                'reject_rework_lot_id': line.id,
                'lot_id': line.lot_id.id,
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'confirm_qty': line.quantity,
                'state': line.state,
                'lot_type': line.lot_type,
            })
            line_val.append(line_data)
        res["lot_type"] = lot_type
        res["reject_handling_line_ids"] = line_val
        res['name'] = self.sudo().env['ir.sequence'].next_by_code('reject.handling') or 'New'
        return res

    def make_ok(self):
        for record in self:
            StockLot = self.env['stock.lot']
            StockQuant = self.env['stock.quant']
            remaining_qty = False
            print('Making OK')
            for line in record.reject_handling_line_ids:
                if line.quantity == line.confirm_qty:
                    remaining_qty = line.confirm_qty
                    line.reject_rework_lot_id.lot_id.write({
                        'lot_type': 'ok',
                        'job_work_check': False,
                    })
                    line.reject_rework_lot_id.write({
                        'state': 'ok',
                        'lot_type': 'ok',
                    })
                    if line.remark:
                        line.reject_rework_lot_id.write({
                            'approver_reason': line.remark,
                        })
                    line.reject_rework_lot_id.part_operation_line_id.write({
                        'lot_ids': [(4, line.reject_rework_lot_id.lot_id.id)]
                    })
                else:
                    if line.confirm_qty < line.quantity:
                        remaining_qty = line.quantity - line.confirm_qty
                        new_lot = StockLot.create({
                            'product_id': line.product_id.id,
                            'lot_type': 'ok',
                            'job_work_check': False,
                        })
                        # Reduce quantity from original lot
                        original_quant = StockQuant.search([
                            ('product_id', '=', line.product_id.id),
                            ('lot_id', '=', line.lot_id.id),
                            ('location_id', '=', self.env.ref('stock.stock_location_stock').id)
                        ], limit=1)
                        if original_quant:
                            original_quant.quantity = remaining_qty

                        # Add quantity to new lot
                        new_quant = StockQuant.create({
                            'product_id': line.product_id.id,
                            'location_id': self.env.ref('stock.stock_location_stock').id,
                            'lot_id': new_lot.id,
                            'quantity': line.confirm_qty,
                        })
                        new_line = line.reject_rework_lot_id.copy({
                            'quantity': line.confirm_qty,
                            'lot_id': new_lot.id,
                            'lot_type': 'ok',
                            'supplier_id': self.partner_id.id,
                            'state': 'ok',
                            'parent_id': line.reject_rework_lot_id.id,
                            'approver_reason': line.remark,
                            'part_operation_line_id': line.reject_rework_lot_id.part_operation_line_id.id,
                        })

                        line.reject_rework_lot_id.part_operation_line_id.write({
                            'lot_ids': [(4, new_lot.id)]
                        })

                    else:
                        raise UserError('Confirm Qty should be less than quantity')
                    line.reject_rework_lot_id.write({
                        'quantity': remaining_qty,
                    })

    def make_rework(self):
        for record in self:
            StockLot = self.env['stock.lot']
            StockQuant = self.env['stock.quant']
            remaining_qty = False
            print('Making Rework')
            for line in record.reject_handling_line_ids:
                if line.quantity == line.confirm_qty:
                    remaining_qty = line.confirm_qty
                    line.reject_rework_lot_id.lot_id.write({
                        'lot_type': 'rework'
                    })
                    line.reject_rework_lot_id.write({
                        'state': 'done',
                        'lot_type': 'rework'
                    })

                    if line.remark:
                        line.reject_rework_lot_id.write({
                            'approver_reason': line.remark,
                        })
                else:
                    if line.confirm_qty < line.quantity:
                        remaining_qty = line.quantity - line.confirm_qty
                        new_lot = StockLot.create({
                            'product_id': line.product_id.id,
                            'lot_type': 'rework',
                        })
                        # Reduce quantity from original lot
                        original_quant = StockQuant.search([
                            ('product_id', '=', line.product_id.id),
                            ('lot_id', '=', line.lot_id.id),
                            ('location_id', '=', self.env.ref('stock.stock_location_stock').id)
                        ], limit=1)
                        if original_quant:
                            original_quant.quantity = remaining_qty

                        # Add quantity to new lot
                        new_quant = StockQuant.create({
                            'product_id': line.product_id.id,
                            'location_id': self.env.ref('stock.stock_location_stock').id,
                            'lot_id': new_lot.id,
                            'quantity': line.confirm_qty,
                        })
                        new_line = line.reject_rework_lot_id.copy({
                            'quantity': line.confirm_qty,
                            'lot_id': new_lot.id,
                            'lot_type': 'rework',
                            'supplier_id': self.partner_id.id,
                            'state': 'done',
                            'parent_id': line.reject_rework_lot_id.id,
                            'approver_reason': line.remark,
                            'part_operation_line_id': line.reject_rework_lot_id.part_operation_line_id.id,
                        })

                    else:
                        raise UserError('Confirm Qty should be less than quantity')
                    line.reject_rework_lot_id.write({
                        'quantity': remaining_qty,
                    })

    def make_process_reject(self):
        for record in self:
            StockLot = self.env['stock.lot']
            StockQuant = self.env['stock.quant']
            remaining_qty = False
            for line in record.reject_handling_line_ids:
                print('--------------------klnmhkghcugohjhlj', line.quantity, line.confirm_qty)
                if line.quantity == line.confirm_qty:
                    cur_line = line.reject_rework_lot_id
                    remaining_qty = line.confirm_qty
                    self.create_scrap_record(line.product_id, line.confirm_qty, line.lot_id, cur_line)
                    line.reject_rework_lot_id.write({
                        'state': 'scrap',
                        'lot_type': 'p_reject'
                    })
                    if line.remark:
                        line.reject_rework_lot_id.write({
                            'approver_reason': line.remark,
                        })
                else:
                    if line.confirm_qty < line.quantity:
                        remaining_qty = line.quantity - line.confirm_qty
                        new_lot = StockLot.create({
                            'product_id': line.product_id.id,
                            'lot_type': 'p_reject',
                        })
                        # Reduce quantity from original lot
                        original_quant = StockQuant.search([
                            ('product_id', '=', line.product_id.id),
                            ('lot_id', '=', line.lot_id.id),
                            ('location_id', '=', self.env.ref('stock.stock_location_stock').id)
                        ], limit=1)
                        if original_quant:
                            original_quant.quantity = remaining_qty

                        # Add quantity to new lot
                        new_quant = StockQuant.create({
                            'product_id': line.product_id.id,
                            'location_id': self.env.ref('stock.stock_location_stock').id,
                            'lot_id': new_lot.id,
                            'quantity': line.confirm_qty,
                        })
                        new_line = line.reject_rework_lot_id.copy({
                            'quantity': line.confirm_qty,
                            'lot_id': new_lot.id,
                            'lot_type': 'p_reject',
                            'supplier_id': self.partner_id.id,
                            'state': 'scrap',
                            'parent_id': line.reject_rework_lot_id.id,
                            'approver_reason': line.remark,
                            'part_operation_line_id': line.reject_rework_lot_id.part_operation_line_id.id,
                        })
                        cur_line = new_line
                        self.create_scrap_record(line.product_id, line.confirm_qty, new_lot, cur_line)

                    else:
                        raise UserError('Confirm Qty should be less than quantity')
                    line.reject_rework_lot_id.write({
                        'supplier_id': self.partner_id.id,
                        'quantity': remaining_qty,
                    })

    def make_rework_reject(self):
        for record in self:
            StockLot = self.env['stock.lot']
            StockQuant = self.env['stock.quant']
            remaining_qty = False
            for line in record.reject_handling_line_ids:
                print('--------------------klnmhkghcugohjhlj', line.quantity, line.confirm_qty)
                if line.quantity == line.confirm_qty:
                    cur_line = line.reject_rework_lot_id
                    remaining_qty = line.confirm_qty
                    self.create_scrap_record(line.product_id, line.confirm_qty, line.lot_id, cur_line)
                    line.reject_rework_lot_id.write({
                        'state': 'scrap',
                        'lot_type': 'rework'
                    })

                    if line.remark:
                        line.reject_rework_lot_id.write({
                            'approver_reason': line.remark,
                        })
                else:
                    if line.confirm_qty < line.quantity:
                        remaining_qty = line.quantity - line.confirm_qty
                        new_lot = StockLot.create({
                            'product_id': line.product_id.id,
                            'lot_type': 'rework',
                        })
                        # Reduce quantity from original lot
                        original_quant = StockQuant.search([
                            ('product_id', '=', line.product_id.id),
                            ('lot_id', '=', line.lot_id.id),
                            ('location_id', '=', self.env.ref('stock.stock_location_stock').id)
                        ], limit=1)
                        if original_quant:
                            original_quant.quantity = remaining_qty

                        # Add quantity to new lot
                        new_quant = StockQuant.create({
                            'product_id': line.product_id.id,
                            'location_id': self.env.ref('stock.stock_location_stock').id,
                            'lot_id': new_lot.id,
                            'quantity': line.confirm_qty,
                        })
                        new_line = line.reject_rework_lot_id.copy({
                            'quantity': line.confirm_qty,
                            'lot_id': new_lot.id,
                            'lot_type': 'rework',
                            'supplier_id': self.partner_id.id,
                            'state': 'scrap',
                            'parent_id': line.reject_rework_lot_id.id,
                            'approver_reason': line.remark,
                            'part_operation_line_id': line.reject_rework_lot_id.part_operation_line_id.id,
                        })
                        cur_line = new_line
                        self.create_scrap_record(line.product_id, line.confirm_qty, new_lot, cur_line)

                    else:
                        raise UserError('Confirm Qty should be less than quantity')
                    line.reject_rework_lot_id.write({
                        'supplier_id': self.partner_id.id,
                        'quantity': remaining_qty,
                    })

    def create_scrap_record(self, product_id, confirm_qty, lot_id, cur_line):
        StockScrap = self.env['stock.scrap']
        scrap = StockScrap.create({
            'product_id': product_id.id,
            'scrap_qty': confirm_qty,
            'lot_id': lot_id.id,
        })
        scrap.action_validate()

        cur_line.write({
            'scrap_id': scrap.id,
        })

    def make_material_reject(self):
        StockQuant = self.env['stock.quant']
        remaining_qty = False
        for record in self:
            for line in record.reject_handling_line_ids:
                if record.partner_id:
                    if line.quantity == line.confirm_qty:
                        remaining_qty = line.confirm_qty
                        cur_line = line.reject_rework_lot_id
                        self.create_delivery(line.product_id, line.lot_id, line.confirm_qty, cur_line)
                        self.create_debit_note(line.product_id, line.confirm_qty, cur_line)
                        line.reject_rework_lot_id.write({
                            'state': 'debit_note',
                            'lot_type': 'm_reject'
                        })

                        if line.remark:
                            line.reject_rework_lot_id.write({
                                'approver_reason': line.remark,
                            })
                    elif line.quantity > line.confirm_qty:
                        remaining_qty = line.quantity - line.confirm_qty

                        new_lot = self.env['stock.lot'].create({
                            'product_id': line.product_id.id,
                            'lot_type': 'm_reject',
                            'product_qty': line.confirm_qty
                        })
                        original_quant = StockQuant.search([
                            ('product_id', '=', line.product_id.id),
                            ('lot_id', '=', line.lot_id.id),
                            ('location_id', '=', self.env.ref('stock.stock_location_stock').id)
                        ], limit=1)
                        if original_quant:
                            original_quant.quantity = remaining_qty

                        # Add quantity to new lot
                        new_quant = StockQuant.create({
                            'product_id': line.product_id.id,
                            'location_id': self.env.ref('stock.stock_location_stock').id,
                            'lot_id': new_lot.id,
                            'quantity': line.confirm_qty,
                        })

                        new_line = line.reject_rework_lot_id.copy({
                            'quantity': line.confirm_qty,
                            'lot_id': new_lot.id,
                            'lot_type': 'm_reject',
                            'supplier_id': self.partner_id.id,
                            'state': 'debit_note',
                            'parent_id': line.reject_rework_lot_id.id,
                            'approver_reason': line.remark,
                            'part_operation_line_id': line.reject_rework_lot_id.part_operation_line_id.id,
                        })

                        line.write({
                            'quantity': remaining_qty,
                        })
                        cur_line = new_line
                        self.create_delivery(line.product_id, new_lot, line.confirm_qty, cur_line)
                        self.create_debit_note(line.product_id, line.confirm_qty, cur_line)
                    else:
                        raise UserError('Confirm Qty should be less than quantity')
                    line.reject_rework_lot_id.write({
                        'supplier_id': self.partner_id.id,
                        'quantity': remaining_qty,
                    })
                else:
                    raise UserError('Please select Partner name')

    def create_delivery(self, product_id, lot_id, quantity, new_line):
        StockPicking = self.env['stock.picking']

        print('_________________Delivery____________________')
        picking_vals = {
            'partner_id': self.partner_id.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_ids_without_package': [],
        }

        move_vals = {
            'name': product_id.name,
            'product_id': product_id.id,
            'product_uom_qty': quantity,
            'product_uom': product_id.uom_id.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_line_ids': [(0, 0, {
                'product_id': product_id.id,
                'quantity': quantity,
                'lot_id': lot_id.id,
                'location_id': self.env.ref('stock.stock_location_stock').id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'product_uom_id': product_id.uom_id.id,
            })],
        }
        picking_vals['move_ids_without_package'].append((0, 0, move_vals))

        delivery = StockPicking.create(picking_vals)
        delivery.action_confirm()

        new_line.write({
            'delivery_id': delivery.id
        })

        return delivery

    def create_debit_note(self, product_id, quantity, cur_line):
        print('_________________________Debit Note___________________________')
        invoice = self.env['account.move'].create({
            'move_type': 'in_refund',
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product_id.id,
                'quantity': quantity,
                'price_unit': product_id.list_price,
                'name': 'Debit Note for Rejected Material',
            })],
        })

        cur_line.write({
            'debit_note_id': invoice.id
        })
        #     StockPicking = self.env['stock.picking']
        #     AccountMove = self.env['account.move']
        #     StockProductionLot = self.env['stock.lot']
        #     StockQuant = self.env['stock.quant']
        #
        #     for record in self:
        #         # Create Delivery Record
        #         picking_vals = {
        #             'partner_id': self.partner_id.id,
        #             'picking_type_id': self.env.ref('stock.picking_type_out').id,
        #             'location_id': self.env.ref('stock.stock_location_stock').id,
        #             'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        #             'move_ids_without_package': [],
        #         }
        #
        #         for line in record.reject_handling_line_ids:
        #             original_lot = line.lot_id
        #             confirmed_qty = line.confirm_qty
        #             total_qty = line.quantity
        #
        #             if confirmed_qty < total_qty:
        #                 # Calculate remaining quantity
        #                 remaining_qty = total_qty - confirmed_qty
        #
        #                 # Create new lot for the remaining quantity
        #                 new_lot = StockProductionLot.create({
        #                     'product_id': line.product_id.id,
        #                     'lot_type': 'ok',
        #                 })
        #
        #                 # Adjust the quantities in stock quants
        #                 # Reduce quantity from original lot
        #                 original_quant = StockQuant.search([
        #                     ('product_id', '=', line.product_id.id),
        #                     ('lot_id', '=', original_lot.id),
        #                     ('location_id', '=', self.env.ref('stock.stock_location_stock').id)
        #                 ], limit=1)
        #                 if original_quant:
        #                     original_quant.quantity = confirmed_qty
        #
        #                 # Add quantity to new lot
        #                 new_quant = StockQuant.create({
        #                     'product_id': line.product_id.id,
        #                     'location_id': self.env.ref('stock.stock_location_stock').id,
        #                     'lot_id': new_lot.id,
        #                     'quantity': remaining_qty,
        #                 })
        #
        # move_vals = {
        #     'name': line.product_id.name,
        #     'product_id': line.product_id.id,
        #     'product_uom_qty': confirmed_qty,
        #     'product_uom': line.product_id.uom_id.id,
        #     'location_id': self.env.ref('stock.stock_location_stock').id,
        #     'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        #     'move_line_ids': [(0, 0, {
        #         'product_id': line.product_id.id,
        #         'quantity': confirmed_qty,
        #         'lot_id': original_lot.id,
        #         'location_id': self.env.ref('stock.stock_location_stock').id,
        #         'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        #         'product_uom_id': line.product_id.uom_id.id,
        #     })],
        # }
        # picking_vals['move_ids_without_package'].append((0, 0, move_vals))
        #
        # delivery = StockPicking.create(picking_vals)
        # delivery.action_confirm()
        #
        #         # Create Debit Note
        #         move_vals = {
        #             'move_type': 'in_refund',
        #             'partner_id': self.env.user.company_id.partner_id.id,
        #             'invoice_date': fields.Date.today(),
        #             'invoice_line_ids': [],
        #         }
        #         for line in record.reject_handling_line_ids:
        #             line_vals = {
        #                 'name': line.product_id.name,
        #                 'product_id': line.product_id.id,
        #                 'quantity': line.confirm_qty,
        #                 'price_unit': line.product_id.standard_price,
        #             }
        #             move_vals['invoice_line_ids'].append((0, 0, line_vals))
        #         debit_note = AccountMove.create(move_vals)
        #
        #         # Link the created records
        #         record.write({
        #             'debit_note_id': debit_note.id,
        #             'state': 'debit_note',
        #         })
        #         for line in record.reject_handling_line_ids:
        #             line.reject_rework_lot_id.state = 'debit_note'
        #             line.reject_rework_lot_id.debit_note_id = debit_note.id
        #             line.reject_rework_lot_id.confirm_qty = confirmed_qty
        #

    def create_scrap(self):
        print('Creating Scrap')
        #     StockProductionLot = self.env['stock.lot']
        #     StockQuant = self.env['stock.quant']
        #     StockScrap = self.env['stock.scrap']
        #     stock_location = self.env.ref('stock.stock_location_stock')
        #     scrap_location = self.env.ref('stock.stock_location_scrap')
        #
        #     for line in self.reject_handling_line_ids:
        #         original_lot = line.lot_id
        #         confirmed_qty = line.confirm_qty
        #         total_qty = line.quantity
        #
        # if confirmed_qty < total_qty:
        #     # Calculate remaining quantity
        #     remaining_qty = total_qty - confirmed_qty
        #
        #     # Create new lot for the remaining quantity
        #     new_lot = StockProductionLot.create({
        #         'product_id': line.product_id.id,
        #         'lot_type': 'ok',
        #     })
        #
        #     # Adjust the quantities in stock quants
        #     # Reduce quantity from original lot
        #     original_quant = StockQuant.search([
        #         ('product_id', '=', line.product_id.id),
        #         ('lot_id', '=', original_lot.id),
        #         ('location_id', '=', stock_location.id)
        #     ], limit=1)
        #     if original_quant:
        #         original_quant.quantity = confirmed_qty
        #
        #     # Add quantity to new lot
        #     new_quant = StockQuant.create({
        #         'product_id': line.product_id.id,
        #         'location_id': stock_location.id,
        #         'lot_id': new_lot.id,
        #         'quantity': remaining_qty,
        #     })
        #
        #         # Create scrap record
        #         scrap = StockScrap.create({
        #             'product_id': line.product_id.id,
        #             'scrap_qty': confirmed_qty,
        #             'lot_id': original_lot.id,
        #             'location_id': stock_location.id,
        #             'scrap_location_id': scrap_location.id,
        #         })
        #         scrap.action_validate()
        #
        #         # Update related records
        #         line.reject_handling_id.scrap_id = scrap.id
        #         line.reject_handling_id.state = 'scrap'
        #         line.reject_rework_lot_id.state = 'scrap'
        #         line.reject_rework_lot_id.scrap_id = scrap.id
        #         line.reject_rework_lot_id.confirm_qty = confirmed_qty


class RejectHandingLine(models.Model):
    _name = 'reject.handling.line'
    _description = "Reject Handling Line"

    reject_handling_id = fields.Many2one('reject.handling', string="Reject Handling", required=True, ondelete='cascade')
    reject_rework_lot_id = fields.Many2one('reject.rework.lot', string="Reject Rework Lot", required=True,
                                           ondelete='cascade')
    lot_id = fields.Many2one('stock.lot', string="Lot", related='reject_rework_lot_id.lot_id', store=True)
    product_id = fields.Many2one('product.product', string="Product", related='reject_rework_lot_id.product_id',
                                 store=True)
    quantity = fields.Float(string="Quantity", related='reject_rework_lot_id.quantity', store=True)
    confirm_qty = fields.Float(string="Confirmed Quantity")
    state = fields.Selection(string="Status", related='reject_rework_lot_id.state', store=True)
    lot_type = fields.Selection(string='Lot Type', related='reject_rework_lot_id.lot_type', store=True)
    remark = fields.Text(string="Remark")


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        reject_id = self.env['reject.rework.lot'].search([('debit_note_id', '=', self.id)])

        print('============================================', reject_id)
        print('==========================666==================', reject_id.delivery_id)

        # if reject_id:
        #     if reject_id.delivery_id.state != 'done':
        #         raise ValidationError('Please Confirm Delivery item before Post the Debit Note')
        # print('==========================77777777777777==================', reject_id.delivery_id)
        return res
