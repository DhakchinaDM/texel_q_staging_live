from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError


class JobOrderTracking(models.Model):
    _name = 'job.order.tracking'
    _description = 'Job Order Tracking'
    _inherit = ['mail.thread.cc', 'mail.thread.main.attachment', 'mail.activity.mixin']
    _order = 'id desc'

    @api.model
    def get_finished_goods(self):
        fg_products = self.env.ref('inventory_extended.category_finished_goods').id
        return [('categ_id', 'in', [fg_products]), ('type', 'in', ['product', 'consu'])]

    # INVISIBLE FIELDS START
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    active = fields.Boolean(default=True)
    # INVISIBLE FIELDS END

    name = fields.Char(string='Name', default='New')
    partner_id = fields.Many2one('res.partner', string='Customer')
    part_no = fields.Many2one('product.template', string='Part No', domain=lambda self: self.get_finished_goods())
    job_qty = fields.Float(string='Job Qty')
    job_prod = fields.Float(string='Job Prod')
    inv_qty = fields.Float(string='Inv Qty')
    job_allocation = fields.Float(string='Job Allocation')
    job_type = fields.Char(string='Job Type', default='Production')
    job_priority = fields.Char(string='Job Priority', default='Medium')
    status_current_operation = fields.Char(string='Status Current Operation')
    schedule_job_complete = fields.Date(string='Schedule Job Complete')
    job_due = fields.Date(string='Job Due')
    order_ref = fields.Char(string='Order Ref')
    order_due = fields.Date(string='Order Due')
    quantity = fields.Float(string='Quantity')
    state = fields.Selection([('new', 'New'), ('progress', 'Progress'), ('close', 'Close'), ('done', 'Done')],
                             default='new')
    process_routing_id = fields.Many2one('process.routing', string='Process Routing')
    operation_ids = fields.One2many('part.operation.line', 'job_order_id', string='Operations')
    job_id = fields.Many2one('job.planning', string='Job ID')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    def action_force_close(self):
        print('-----------------action_force_close-------------------')
        for line in self.operation_ids:
            if line.mo_ids:
                for mo in line.mo_ids:
                    if mo.state != 'done':
                        mo.action_cancel()
            if line.job_work_ids:
                if not line.income_inspection:
                    for job_work in line.job_work_ids:
                        if job_work.state != 'done':
                            job_work.action_cancel()
                # else:
                #     raise UserError(_('You cannot cancel the job work because it is related to income inspection.'))
            self.write({
                'state': 'close',
            })

    def get_operation_status(self):
        for record in self:
            for operation in record.operation_ids:
                mo_states = operation.mapped("mo_ids.state")
                prev_operation = self.env['part.operation.line'].search([
                    ('job_order_id', '=', operation.job_order_id.id),
                    ('sequence', '=', operation.sequence - 1),
                ], limit=1)
                if operation.sequence == 1:
                    print('11111111111111111111111111111111111111111111111111111111111111111')
                    operation.status = 'finish'
                elif operation.operation_qty == operation.done_qty:
                    print('22222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222')

                    operation.status = 'finish'
                else:
                    print('33333333333333333333333333333333333333333333333333333333333333333333333333333333')

                    if operation.sequence == 3 and operation.operation_type == 'internal' and operation.production_op:
                        operation.status = 'ready'
                        operation.mo_ids.filtered(lambda mo: mo.state == 'draft').action_confirm()
                        if mo_states:
                            if all(state == 'done' for state in mo_states):
                                operation.status = 'finish'
                            elif any(state in ['confirmed', 'progress'] for state in mo_states) and any(
                                    state == 'done' for state in mo_states):
                                operation.status = 'progress'

                    elif operation.sequence != 3 and operation.operation_type == 'internal' and operation.production_op:
                        if prev_operation and prev_operation.production_op and prev_operation.status in ['finish',
                                                                                                         'progress']:
                            operation.status = 'ready'
                            operation.mo_ids.filtered(lambda mo: mo.state == 'draft').action_confirm()
                            if mo_states:
                                if all(state == 'done' for state in mo_states):
                                    operation.status = 'finish'
                                elif any(state in ['confirmed', 'progress'] for state in mo_states) and any(
                                        state == 'done' for state in mo_states):
                                    operation.status = 'progress'
                        elif prev_operation and not prev_operation.production_op and prev_operation.status in [
                            'progress',
                            'finish']:
                            operation.status = 'ready'
                            operation.mo_ids.filtered(lambda mo: mo.state == 'draft').action_confirm()
                            if mo_states:
                                if all(state == 'done' for state in mo_states):
                                    operation.status = 'finish'
                                elif any(state in ['confirmed', 'progress'] for state in mo_states) and any(
                                        state == 'done' for state in mo_states):
                                    operation.status = 'progress'
                        else:
                            operation.status = 'draft'
                    elif operation.sequence != 3 and operation.operation_type == 'internal' and not operation.production_op:
                        if operation.final_inspection:
                            if prev_operation and prev_operation.status in ['finish', 'progress']:
                                if not operation.final_inspection_ids:
                                    operation.status = 'ready'
                                else:
                                    if operation.done_qty == operation.operation_qty:
                                        operation.status = 'finish'
                                    elif operation.done_qty > 0:
                                        operation.status = 'progress'
                                    else:
                                        operation.status = 'ready'
                            else:
                                operation.status = 'draft'
                        elif operation.income_inspection:
                            if prev_operation and prev_operation.status in ['finish', 'progress']:
                                if operation.done_qty == operation.operation_qty:
                                    operation.status = 'finish'
                                elif operation.done_qty > 0:
                                    operation.status = 'progress'
                                else:
                                    operation.status = 'ready'
                            else:
                                operation.status = 'draft'
                        elif operation.shippable:
                            if prev_operation and prev_operation.status in ['finish', 'progress']:
                                if operation.done_qty == operation.operation_qty:
                                    operation.status = 'finish'
                                elif operation.done_qty > 0:
                                    operation.status = 'progress'
                                else:
                                    operation.status = 'ready'

                        else:
                            operation.status = 'draft'
                    elif operation.sequence != 3 and operation.operation_type == 'external':
                        next_operation = self.env['part.operation.line'].search([
                            ('job_order_id', '=', operation.job_order_id.id),
                            ('sequence', '=', operation.sequence + 2),
                        ], limit=1)
                        next_operation.status = 'ready'
                        next_operation.mo_ids.filtered(lambda mo: mo.state == 'draft').action_confirm()
                        if prev_operation:
                            operation.status = 'ready'
                            if prev_operation.lot_ids:
                                for lot in prev_operation.lot_ids:
                                    if not lot.job_work_check and lot.lot_type == 'ok':
                                        print(
                                            "!!!!!!!!!!!!!!!!!!!!!!!!!! # operation.create_job_order()!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1")
                                        # operation.create_job_order()
                            if not operation.job_work_ids:
                                operation.status = 'ready'
                            else:
                                if operation.done_qty == operation.operation_qty:
                                    operation.status = 'finish'
                                elif operation.done_qty > 0:
                                    operation.status = 'progress'
                                else:
                                    operation.status = 'ready'
                        else:
                            operation.status = 'draft'
                    elif operation.sequence == 3 and operation.operation_type == 'external':
                        operation.status = 'ready'
                        if not operation.job_work_ids:
                            # operation.create_job_order()
                            operation.create_job_order_four()
                        if not operation.job_work_ids:
                            operation.status = 'ready'
                        else:
                            if operation.done_qty == operation.operation_qty:
                                operation.status = 'finish'
                            elif operation.done_qty > 0:
                                operation.status = 'progress'
                            else:
                                operation.status = 'ready'
                    else:
                        operation.status = 'draft'

    def action_confirm(self):
        print('-----------------')

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.sudo().env['ir.sequence'].next_by_code('job.order.tracking') or '/'
        return super().create(vals_list)


class PartOperationLine(models.Model):
    _name = 'part.operation.line'
    _description = 'Part Operation Line'
    _order = 'id asc'

    job_order_id = fields.Many2one('job.order.tracking', string='Job Order')
    name = fields.Char(string='Name')
    part_operation_id = fields.Many2one('part.operation', string='Part Operation')
    job_id = fields.Many2one('job.planning', string='Job ID')
    status = fields.Selection(
        [('draft', 'Draft'), ('ready', 'Ready'), ('progress', 'Progress'), ('finish', 'Finished')], string="State",
        compute='_compute_production_status', store=True)
    operation_code = fields.Char(string='Operation No')
    workcenter_id = fields.Many2one('mrp.workcenter', string='Workcenter')
    workorder_id = fields.Many2one('mrp.workorder', string='Workorder')
    sequence = fields.Integer('Sequence', required=True,
                              help="Gives the sequence order when displaying a list of Part Operations.")
    operation_qty = fields.Float(string='Operation Quantity')
    balance_qty = fields.Float(string='Balance Quantity', compute="_compute_balance_qty", store=True)
    done_qty = fields.Float(string='Done Quantity', compute="_compute_done_qty", store=True)
    mo_ids = fields.Many2many('mrp.production', string='Manufacture Orders', store=True)
    operation_id = fields.Many2one('mrp.routing.workcenter', string='Operation')
    operation_type = fields.Selection([('internal', 'Internal'), ('external', 'External')], default='internal',
                                      string='Operation Type')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    bom_id = fields.Many2one('mrp.bom', string='BOM ID')
    production_op = fields.Boolean(string='Production')
    productivity_line_ids = fields.One2many('productivity.line', 'part_operation_id', string='Productivity Lines')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    out_product_id = fields.Many2one('product.template', string='Out Part No',
                                     related='part_operation_id.out_product_id', store=True)

    lot_ids = fields.Many2many('stock.lot', string='Lot IDs')
    job_work_id = fields.Many2one('stock.picking', string='Job Work ID')
    job_work_ids = fields.Many2many('stock.picking', string='Job Work IDs', store=True)
    # job_work_status = fields.Char(string='Job Work Status', compute='_compute_job_work_status')
    job_work_status = fields.Char(string='Job Work Status')

    final_inspection_id = fields.Many2one('final.inspection', string='Final Inspection ID ')
    final_inspection_ids = fields.Many2many('final.inspection', string='Final Inspection ID', store=True)

    quality_ids = fields.Many2many('incoming.inspection', string='Quality IDs', compute='_compute_quality_ids',
                                   store=True)
    final_inspection = fields.Boolean(string='Final Inspection', related='part_operation_id.final_inspection',
                                      store=True)
    final_inspection_need = fields.Boolean(string='Final Inspection Need',
                                           related='part_operation_id.final_inspection_need',
                                           store=True)
    income_inspection = fields.Boolean(string='Income Inspection', related='part_operation_id.income_inspection',
                                       store=True)
    shippable = fields.Boolean(string='Shippable')
    customer_release_ids = fields.Many2many('customer.release', string='Customer Release IDs', store=True)

    @api.depends('mo_ids.qty_produced', 'lot_ids')
    def _compute_done_qty(self):
        machining = self.env.ref("manufacturing_extended.op_machining")
        packing = self.env.ref("manufacturing_extended.op_packing")
        final_inspection = self.env.ref("manufacturing_extended.op_final_inspection")
        tracked_ops = [machining.id, packing.id, final_inspection.id]

        for record in self:
            print('--- Computing done_qty ---', record.done_qty, record.operation_qty, record.balance_qty,
                  record.sequence, record.production_op, record.status)

            if record.sequence in [1, 2]:
                record.done_qty = record.operation_qty
                print(">>> Direct operation: done_qty =", record.done_qty)
            elif record.production_op and record.part_operation_id:
                op_id = record.part_operation_id.operation_list_id.id
                if op_id in tracked_ops:
                    produced_qty = sum(
                        mo.lot_producing_id.product_qty
                        for mo in record.mo_ids
                        if mo.lot_producing_id and mo.lot_producing_id.lot_type == 'ok'
                    )
                    print("1111111111111111111111111111111111111111111111111",produced_qty)

                    # scrapped_qty = sum(record.mo_ids.mapped('scrap_ids.scrap_qty'))
                    record.done_qty = produced_qty
                    print(f">>> Computed done_qty for {record.part_operation_id.operation_list_id.name}:",
                          record.done_qty)

                # elif record.production_op:
                # # record.done_qty = record.operation_qty - record.balance_qty
                # produced_qty = sum(record.mo_ids.mapped('qty_produced'))
                # scrapped_qty = sum(record.mo_ids.mapped('scrap_ids.scrap_qty'))  # Get total scrapped quantity
                #
                # usable_qty = produced_qty - scrapped_qty  # Only the usable quantity should be deducted
                # record.done_qty = usable_qty
            else:
                record.done_qty = 0
                print("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                      record.done_qty)

            # elif record.operation_type == 'external':
            #     record.done_qty = sum(
            #         move.product_uom_qty
            #         for jw in record.job_work_ids.filtered(lambda j: j.job_work_status != 'new')
            #         for move in jw.move_ids_without_package
            #     )
            #     # record.done_qty = total_qty
            # elif record.income_inspection:
            #     record.done_qty = sum(
            #         income.lot_qty
            #         for income in record.quality_ids.filtered(lambda j: j.state == 'done')
            #     )
            # previous_operation = self.env['part.operation.line'].search([
            #     ('job_order_id', '=', record.job_order_id.id),
            #     ('sequence', '=', record.sequence - 1),
            # ], limit=1)
            # print('------------------income_inspection-------------------', previous_operation.sequence,
            #       previous_operation.job_work_ids)
            # record.done_qty = sum(
            #     move.product_uom_qty
            #     for jw in previous_operation.job_work_ids.filtered(lambda j: j.job_work_status == 'completed')
            #     for move in jw.move_ids_without_package
            # )
            # record.done_qty = total_qty
            #     print('------------------total_qty-------------------', record.done_qty)
            # elif record.final_inspection:
            #     record.done_qty = sum(
            #         final.qty
            #         for final in record.final_inspection_ids.filtered(lambda j: j.state == 'approve')
            #     )
            #     # record.done_qty = total_qty
            # elif record.shippable:
            #     record.done_qty = sum(
            #         release.rel_qty
            #         for release in record.customer_release_ids.filtered(lambda j: j.state == 'complete')
            #     )
            #
            # else:
            #     previous_operation = self.search([
            #         ('job_order_id', '=', record.job_order_id.id),
            #         ('sequence', '=', record.sequence - 1),
            #     ], limit=1)
            #     if previous_operation:
            #         record.done_qty = previous_operation.done_qty
            #     else:
            #         record.done_qty = record.operation_qty
            # else:
            #     record.done_qty = record.operation_qty

    def create_customer_release(self):
        print('************** create_customer_release *********************')
        print('************** create_customer_release *********************')
        for record in self:
            previous_production_op = self.search([
                ('job_order_id', '=', record.job_order_id.id),
                ('sequence', '=', record.sequence - 1),
            ], order='sequence desc', limit=1)

            if not previous_production_op:
                continue

            # Filter lots that have not been customer-released yet
            unreleased_lots = previous_production_op.lot_ids.filtered(lambda l: not l.customer_release_check)

            for lot in unreleased_lots:
                release_vals = {
                    'partner_id': record.job_id.partner_id.id,
                    'part_no': record.job_id.part_no.id,
                    'lot_ids': [(6, 0, [lot.id])],
                    'part_operation_line_id': record.id,
                    'due_date': date.today(),
                    'rel_qty': lot.product_qty,  # Use lot-specific qty
                }

                customer_release = self.env['customer.release'].create(release_vals)
                lot.customer_release_check = True  # Mark as released
                record.customer_release_ids = [(4, customer_release.id)]

    def create_final_inspection(self):
        print('************** create_final_inspection *********************')
        for record in self:
            previous_production_op = self.search([
                ('job_order_id', '=', record.job_order_id.id),
                ('sequence', '=', record.sequence - 1),
            ], order='sequence desc', limit=1)

            if not previous_production_op:
                continue

            # Filter lots that have not been inspected yet
            uninspected_lots = previous_production_op.lot_ids.filtered(lambda l: not l.final_inspection_check)

            for lot in uninspected_lots:
                inspection_vals = {
                    'customer': previous_production_op.job_id.partner_id.id,
                    'product_id': previous_production_op.job_id.part_no.id,
                    'lot_ids': [(6, 0, [lot.id])],
                    'part_operation_line_id': record.id,
                    'tc_no': '-',
                    'tc_date': date.today(),
                    'inspect_date': date.today(),
                    'qty': lot.product_qty,  # Use lot-specific qty
                }

                final_inspection = self.env['final.inspection'].create(inspection_vals)
                lot.final_inspection_check = True  # Mark as inspected
                record.final_inspection_id = final_inspection.id
                record.final_inspection_ids = [(4, final_inspection.id)]

    @api.depends('job_work_id', 'job_work_id.income_inspection_ids',
                 'job_work_id.income_inspection_ids.state', 'lot_ids')
    def _compute_quality_ids(self):
        print('------------------_compute_quality_ids-------------------')
        for record in self:
            print('------------------record.job_work_ids-------------------', record.job_work_ids)
            if record.job_work_ids:
                quality_ids = []
                for job_work in record.job_work_ids:
                    quality_ids.extend(job_work.income_inspection_ids.ids)
                record.quality_ids = [(6, 0, quality_ids)]
            else:
                record.quality_ids = [(5, 0, 0)]

    # @api.depends('job_work_id', 'job_work_id.state', 'job_work_id.return_id.state', 'job_work_id.return_id',
    #              'job_work_id.return_id.quality_checked')
    # def _compute_job_work_status(self):
    #     for i in self:
    #         if i.job_work_id:
    #             return_id = self.env['stock.picking'].search([
    #                 ('return_id', '=', i.job_work_id.id),
    #             ])
    #             if return_id.quality_checked:
    #                 i.job_work_status = 'received'
    #                 i.status = 'finish'
    #             else:
    #                 if i.job_work_id.state == 'done':
    #                     i.job_work_status = 'send'
    #                     i.status = 'progress'
    #                 else:
    #                     i.job_work_status = 'draft'
    #         else:
    #             i.job_work_status = False

    def create_job_order_four(self):
        print('************** create_job_order_four *********************')
        # valid_lots = self.lot_ids.filtered(lambda l: not l.job_work_check)
        # total_assignable_qty = sum(lot.product_qty for lot in valid_lots)
        #
        # if total_assignable_qty <= 0:
        #     raise UserError(_("No available lots for assignment. All lots are already assigned to job work."))
        #
        # picking_qty = min(total_assignable_qty, self.operation_qty)

        # print('-AA-----------------picking_qty-------------------', picking_qty,
        #       total_assignable_qty)

        # if picking_qty > 0:
        job_work = self.env['stock.picking'].create({
            'partner_id': self.supplier_id.id,
            'dc_entry_type': 'jw',
            'ins_type': 'incoming_part',
            'picking_type_code': 'outgoing',
            'quality': True,
            'part_operation_line_id': self.id,
            'picking_dc_type': 'standard',
            'picking_type_id': self.env.ref('delivery_challan.jw_operation').id,
            'move_ids_without_package': [(0, 0, {
                'product_id': self.out_product_id.product_variant_id.id,
                'product_uom_qty': self.operation_qty,
                'product_uom': self.out_product_id.uom_id.id,
                'name': self.out_product_id.name,
                'location_id': self.env.ref('delivery_challan.jw_operation').default_location_src_id.id,
                'location_dest_id': self.env.ref('delivery_challan.jw_operation').default_location_dest_id.id,
            })],
        })

        # StockMoveLine = self.env['stock.move.line']
        #
        # for move in job_work.move_ids_without_package:
        #     product = move.product_id
        #
        #     # 🧼 Step 1: Remove invalid or already assigned lots from move lines
        #     move.move_line_ids.filtered(lambda line: not line.lot_id or line.lot_id not in valid_lots).unlink()
        #
        #     # 🔁 Step 2: Reassign fresh from valid_lots
        #     assigned_qty = sum(move.move_line_ids.mapped('quantity'))
        #     existing_lot_ids = move.move_line_ids.mapped('lot_id.id')
        #     print('------------------existing_lot_ids-------------------', existing_lot_ids, valid_lots)
        #     for lot in valid_lots:
        #         if assigned_qty >= picking_qty:
        #             break
        #
        #         if lot.id in existing_lot_ids:
        #             continue  # Already assigned in earlier loop
        #
        #         lot_available_qty = lot.product_qty
        #         qty_to_assign = min(picking_qty - assigned_qty, lot_available_qty)
        #
        #         if qty_to_assign <= 0:
        #             continue
        #
        #         StockMoveLine.create({
        #             'move_id': move.id,
        #             'product_id': product.id,
        #             'product_uom_id': move.product_uom.id,
        #             'quantity': qty_to_assign,
        #             'location_id': move.location_id.id,
        #             'location_dest_id': move.location_dest_id.id,
        #             'lot_id': lot.id,
        #         })
        #
        #         lot.job_work_check = True
        #         print('------------------lot.job_work_check-------------------', lot.name, lot.job_work_check)
        #         assigned_qty += qty_to_assign

        job_work.action_confirm()

        self.write({
            'job_work_id': job_work.id,
            'status': 'progress',
            'job_work_ids': [(4, job_work.id)],
        })

    def create_job_order(self):
        print('************** create_job_order *********************')
        max_operation = self.env['part.operation.line'].search([
            ('job_order_id', '=', self.job_order_id.id),
            ('production_op', '=', True),
            ('operation_type', '=', 'internal'),
            ('sequence', '=', self.sequence - 1),
        ], order='sequence desc', limit=1)
        print('------------------max_operation-------------------', max_operation, max_operation.sequence,
              max_operation.lot_ids)

        if not max_operation:
            print('⚠ No previous operation found where production_op is True.')
            return

        print('🛠 Previous Operation:', max_operation, max_operation.out_product_id)

        valid_lots = max_operation.lot_ids.filtered(lambda l: not l.job_work_check)
        print("qwertyuioplkjhgfdsaxzccdbvcbvmnvmcfldpwiwuyqwtetefdghdjskahdsgfgbcfnjdxcnjd", valid_lots)
        total_assignable_qty = sum(lot.product_qty for lot in valid_lots if lot.lot_type == 'ok')
        print("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
              total_assignable_qty)

        if total_assignable_qty <= 0:
            raise UserError(_("No available lots for assignment. All lots are already assigned to job work."))

        picking_qty = total_assignable_qty

        print('-AA-----------------picking_qty-------------------', picking_qty, max_operation.done_qty,
              total_assignable_qty)

        # if picking_qty > 0:
        job_work = self.env['stock.picking'].create({
            'partner_id': self.supplier_id.id,
            'dc_entry_type': 'jw',
            'ins_type': 'incoming_part',
            'picking_type_code': 'outgoing',
            'quality': True,
            'part_operation_line_id': self.id,
            'picking_dc_type': 'standard',
            'picking_type_id': self.env.ref('delivery_challan.jw_operation').id,
            'move_ids_without_package': [(0, 0, {
                'product_id': max_operation.out_product_id.product_variant_id.id,
                'product_uom_qty': picking_qty,
                'product_uom': max_operation.out_product_id.uom_id.id,
                'name': max_operation.out_product_id.name,
                'location_id': self.env.ref('delivery_challan.jw_operation').default_location_src_id.id,
                'location_dest_id': self.env.ref('delivery_challan.jw_operation').default_location_dest_id.id,
            })],
        })

        StockMoveLine = self.env['stock.move.line']

        for move in job_work.move_ids_without_package:
            product = move.product_id

            # 🧼 Step 1: Remove invalid or already assigned lots from move lines
            move.move_line_ids.filtered(lambda line: not line.lot_id or line.lot_id not in valid_lots).unlink()

            # 🔁 Step 2: Reassign fresh from valid_lots
            assigned_qty = sum(move.move_line_ids.mapped('quantity'))
            existing_lot_ids = move.move_line_ids.mapped('lot_id.id')
            print('------------------existing_lot_ids-------------------', existing_lot_ids, valid_lots)
            for lot in valid_lots:
                if assigned_qty >= picking_qty:
                    break

                if lot.id in existing_lot_ids:
                    continue  # Already assigned in earlier loop

                lot_available_qty = lot.product_qty
                qty_to_assign = min(picking_qty - assigned_qty, lot_available_qty)

                if qty_to_assign <= 0:
                    continue

                StockMoveLine.create({
                    'move_id': move.id,
                    'product_id': product.id,
                    'product_uom_id': move.product_uom.id,
                    'quantity': qty_to_assign,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'lot_id': lot.id,
                })

                lot.job_work_check = True
                print('------------------lot.job_work_check-------------------', lot.name, lot.job_work_check)
                assigned_qty += qty_to_assign

            job_work.action_confirm()

            self.write({
                'job_work_id': job_work.id,
                'status': 'progress',
                'job_work_ids': [(4, job_work.id)],
            })

            print(f'✅ Job Work Created: {job_work.name}')

    def create_mo_order(self):
        mo_order = self.env['mrp.production'].create({
            'product_tmpl_id': self.part_operation_id.out_product_id.id,
            'product_id': self.part_operation_id.out_product_id.product_variant_id.id,
            'product_qty': self.operation_qty,
            'bom_id': self.bom_id.id,
            'job_id': self.job_id.id,
            'date_finished': self.job_order_id.schedule_job_complete,
            'part_operation_line_id': self.id,
            'tracking_id': self.job_order_id.id,
            'picking_type_id': self.part_operation_id.picking_type_id.id,
        })
        print('------------------part_operation_line_id-------------------', mo_order.part_operation_line_id)
        mo_order.action_confirm()
        return mo_order

    @api.depends('job_id')
    def _compute_mo_ids(self):
        for record in self:
            mo_ids = self.env['mrp.production'].search([('job_id', '=', record.job_id.id)])

    def complete_operation(self):
        for record in self:
            if record.status in ['ready', 'progress']:
                record.write({
                    'status': 'finish'
                })
            else:
                raise UserError(_("Operation is not ready to be completed."))

    @api.depends(
        'production_op', 'operation_type', 'mo_ids.state', 'sequence', 'mo_ids', 'status',
        'job_order_id', 'job_work_ids.state', 'job_work_status', 'job_work_ids.job_work_status', 'lot_ids',
        'lot_ids.lot_type',
        'quality_ids', 'quality_ids.state', 'final_inspection_ids.state', 'final_inspection_ids',
        'customer_release_ids', 'customer_release_ids.state'
    )
    def _compute_production_status(self):
        print('======== COMPUTING PRODUCTION STATUS ========')
        for record in self:
            if record.job_order_id:
                record.job_order_id.get_operation_status()

    @api.depends('operation_qty', 'done_qty', 'final_inspection_ids.state', 'mo_ids.state', 'job_work_ids.state')
    def _compute_balance_qty(self):
        """ Computes balance quantity as Total Job Qty - Usable Produced Qty """
        print('------------------_compute_balance_qty-------------------')
        for record in self:
            record.balance_qty = record.operation_qty - record.done_qty

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.sudo().env['ir.sequence'].next_by_code('part.operation.line') or '/'
        return super().create(vals_list)


class ProductivityLine(models.Model):
    _name = 'productivity.line'
    _description = 'Productivity Line'

    part_operation_id = fields.Many2one('part.operation.line', string='Part Operation')
    part_operation_raw_id = fields.Many2one('part.operation', string='Part Operation Raw',compute='_compute_production_product')
    name = fields.Char(string='Name')
    job_id = fields.Many2one('job.planning', string='Job ID')
    mo_id = fields.Many2one('mrp.production', string='MO ID')
    remarks = fields.Text(string='Remarks')
    date = fields.Date(string='Date', default=fields.Date.today())
    op_code = fields.Char(string='Operation Code')
    operation_id = fields.Many2one('mrp.routing.workcenter', string='Operation')
    lot_id = fields.Many2one('stock.lot', string='Lot')
    produced_qty = fields.Float(string='Produced Quantity', related='mo_id.product_uom_qty', store=True)
    product_id = fields.Many2one('product.product', string='Product')
    out_product_id = fields.Many2one('product.product', string='Out Product')
    qty_type = fields.Selection(
        [('ok', 'Ok Qty'), ('m_reject', 'Material Rej Qty'), ('p_reject', 'Process Rej Qty'), ('rework', 'Rework Qty')],
        string='Quantity Type')
    next_op_code = fields.Char(string='Next Operation Code', compute='get_next_op_code')
    workcenter_productivity_id = fields.Many2one('mrp.workcenter.productivity', string='Workcenter Productivity',
                                                 store=True)

    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    total_produced_qty = fields.Float(string='Total Produced Quantity', compute='_compute_total_produced_qty',
                                      store=True)

    @api.depends('out_product_id')
    def _compute_production_product(self):
        for record in self:
            if record.out_product_id:
                record.part_operation_raw_id = record.out_product_id.part_operation.id
            else:
                record.part_operation_raw_id = False


    @api.depends('produced_qty', 'qty_type', 'workcenter_productivity_id')
    def _compute_total_produced_qty(self):
        for record in self:
            if record.workcenter_productivity_id:
                record.total_produced_qty = record.workcenter_productivity_id.produced_qty
            else:
                record.total_produced_qty = 0.0

    @api.depends('part_operation_raw_id')
    def get_next_op_code(self):
        for record in self:
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!",record.part_operation_raw_id)
            next_operation = self.env['part.operation'].search([
                ('routing_id', '=', record.part_operation_raw_id.routing_id.id),
                ('sequence', '=', record.part_operation_raw_id.sequence + 1)
            ], limit=1)
            print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@",next_operation)
            record.next_op_code = next_operation.operation_code if next_operation else ''

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.sudo().env['ir.sequence'].next_by_code('productivity.line') or '/'
        return super().create(vals_list)
