from odoo import api, fields, models, _
from odoo.tools import float_compare
from odoo.tools.misc import format_date
from datetime import date



class MrpProduction(models.Model):
    _inherit = "mrp.production"

    load_component = fields.Boolean(string='Load Component', default=False)
    job_id = fields.Many2one('job.planning', string='Job ID')
    tracking_id = fields.Many2one('job.order.tracking', string='Tracking ID', related='job_id.tracking_id', store=True)
    components_availability_state = fields.Selection(
        selection_add=[('partial', 'Partially Available')], compute='_compute_components_availability'
    )
    operation_state = fields.Selection([('waiting', 'Waiting'), ('progress', 'Progress'), ('done', 'Done')])
    part_operation_line_id = fields.Many2one('part.operation.line', string='Part Operation Line', store=True)
    status = fields.Selection(string="Status", related='part_operation_line_id.status', store=True)
    notes = fields.Text(string='Notes')
    qty_type = fields.Selection([('ok', 'Ok'), ('m_reject', 'Material'), ('p_reject', 'Process'), ('rework', 'Rework')],
                                string='Quantity Type')
    productivity_tracking_id = fields.Many2one('productivity.line', string='Productivity Tracking')
    lot_ids = fields.Many2many('stock.lot', string='Lot')

    def confirm_next_operation_mo(self):
        for rec in self:
            if rec.part_operation_line_id:
                next_operation = self.env['part.operation.line'].search([
                    ('job_id', '=', rec.job_id.id),
                    ('sequence', '>', rec.part_operation_line_id.sequence)], order="sequence asc", limit=1)

                if next_operation:
                    for mo in next_operation.mo_ids:
                        if mo.state == 'draft':
                            mo.action_confirm()

    @api.depends('tracking_id.operation_ids')
    def get_part_operation_line(self):
        for rec in self:
            rec.part_operation_line_id = self.env['part.operation.line'].search(
                [('job_id', '=', rec.job_id.id)]).filtered(lambda r: rec.id in r.mo_ids.ids)

    @api.depends('state', 'reservation_state', 'date_start', 'move_raw_ids.forecast_availability',
                 'move_raw_ids.product_qty')
    def _compute_components_availability(self):
        productions = self.filtered(lambda mo: mo.state not in ('cancel', 'done', 'draft'))
        other_productions = self - productions

        # Default values
        productions.components_availability_state = 'available'
        productions.components_availability = _('Available')
        other_productions.components_availability = False
        other_productions.components_availability_state = False

        for production in productions:
            total_moves = len(production.move_raw_ids)
            fully_available_moves = 0
            partially_available_moves = 0
            unavailable_moves = 0

            for move in production.move_raw_ids:
                required_qty = move.product_qty
                available_qty = move.forecast_availability
                precision = move.product_id.uom_id.rounding

                # If no stock at all
                if float_compare(available_qty, 0, precision_rounding=precision) == 0:
                    unavailable_moves += 1
                # If partial stock available
                elif float_compare(available_qty, required_qty, precision_rounding=precision) == -1:
                    partially_available_moves += 1
                # If fully available
                else:
                    fully_available_moves += 1

            # Assign availability status
            if unavailable_moves == total_moves:
                production.components_availability = _('Not Available')
                production.components_availability_state = 'unavailable'
            elif partially_available_moves > 0 or (fully_available_moves > 0 and unavailable_moves > 0):
                production.components_availability = _('Partially Available')
                production.components_availability_state = 'partial'
            else:
                forecast_date = max(
                    production.move_raw_ids.filtered('forecast_expected_date').mapped('forecast_expected_date'),
                    default=False)
                if forecast_date:
                    production.components_availability = _('Exp %s', format_date(self.env, forecast_date))
                    production.components_availability_state = 'late' if forecast_date > production.date_start else 'expected'

    def _split_productions(self):

        backorder = super()._split_productions()

        # Get first and last backorders
        first_backorder = backorder[0]
        last_backorder = backorder[-1]
        remaining_qty = False

        # Copy job-related details to the last backorder
        last_backorder.job_id = first_backorder.job_id
        last_backorder.load_component = first_backorder.load_component
        last_backorder.part_operation_line_id = first_backorder.part_operation_line_id

        # Link the new backorder to the part operation line
        first_backorder.part_operation_line_id.mo_ids = [(4, last_backorder.id)]

        # Track total available quantity from selected lots
        total_available_qty = 0

        if backorder:
            for move in self.move_raw_ids:
                # Retrieve stored lot numbers before they were removed
                move.store_lot_numbers()
                stored_lots = move.stored_lot_ids

                # Find the corresponding move in the backorder
                backorder_move = backorder.move_raw_ids.filtered(
                    lambda m: m.product_id == move.product_id and m.state == 'confirmed'
                )
                if backorder_move and stored_lots:
                    for lot in stored_lots:

                        # Accumulate total available quantity from selected lots
                        total_available_qty += lot.product_qty

                    # Deduct the produced quantity from the total available quantity
                    remaining_qty = total_available_qty - first_backorder.product_qty

                    # If the remaining quantity is negative, set it to 0
                    if remaining_qty < 0:
                        remaining_qty = 0
                    # Create stock move lines
                    for lot in stored_lots:
                        if lot.product_qty > 0:
                            final_qty = min(backorder_move.product_uom_qty, lot.product_qty)
                            self.env['stock.move.line'].create({
                                'move_id': backorder_move.id,
                                'product_id': move.product_id.id,
                                'lot_id': lot.id,
                                'quantity': final_qty,
                                'location_id': move.location_id.id,
                                'location_dest_id': move.location_dest_id.id,
                            })
            last_backorder.load_component = first_backorder.load_component if remaining_qty > 0 else False

        return backorder

    def button_mark_done(self):
        res = super().button_mark_done()
        if self.product_id.part_operation:
            next_operation = self.env['part.operation'].search([
                ('routing_id', '=', self.product_id.part_operation.routing_id.id),
                ('sequence', '=', self.product_id.part_operation.sequence + 1)
            ], limit=1)
            #
            # prev_operation_recs = []
            # prev_operation = self.env['part.operation'].search([])
            # for j in prev_operation:
            #     if j.product_id.id == self.product_id.product_tmpl_id.part_operation.product_id.id:
            #         print("11111111111111111111111111111111111111111111111111", j.name)
            #         if j.sequence == next_operation.sequence-1:
            #             prev_operation_recs.append(j)
            #             break
            #         print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@,", j.name)
            #         prev_operation_recs.append(j)
            # print("Previous Operation Records:", prev_operation_recs)
            # bool = False
            # for y in prev_operation_recs:
            #     if y.operation_type == 'external':
            #         bool= True
            # # print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", next_operation.supplier)
            if next_operation.operation_type == 'external':
                if next_operation.sequence != 3:
                    self.env['stock.picking'].create({
                        'partner_id': next_operation.partner_id.id,
                        'dc_entry_type': 'jw',
                        'ins_type': 'incoming_part',
                        'picking_type_code': 'incoming',
                        'quality': True,
                        'picking_dc_type': 'standard',
                        'picking_type_id': self.env.ref('delivery_challan.jw_operation').id,
                        'move_ids_without_package': [(0, 0, {
                            'product_id': self.product_id.id,
                            'product_uom_qty': self.product_qty,
                            'product_uom': self.product_id.uom_id.id,
                            'name': self.product_id.name,
                            'location_id': self.env.ref('delivery_challan.jw_operation').default_location_src_id.id,
                            'location_dest_id': self.env.ref('delivery_challan.jw_operation').default_location_dest_id.id,
                        })],
                    })


        if self.part_operation_line_id:
            self.part_operation_line_id.write({
                'lot_ids': [(4, self.lot_producing_id.id)],
            })


        return res

    def create_productivity_line(self, productivity_records):
        part_operation = self.product_id.product_tmpl_id.part_operation
        vals = {
            'part_operation_id': self.part_operation_line_id.id if self.part_operation_line_id else False,
            'job_id': self.job_id.id if self.job_id else False,
            'mo_id': self.id,
            'remarks': self.notes,
            'op_code': part_operation.operation_code,
            'operation_id': part_operation.operation_id.id,
            'lot_id': self.lot_producing_id.id,
            'produced_qty': self.qty_produced,
            'product_id': part_operation.routing_id.product_id.product_variant_id.id,
            'out_product_id': self.product_id.id,
            'qty_type': self.qty_type,
            'workcenter_productivity_id': productivity_records.id if productivity_records else False,
        }
        productivity_id = self.env['productivity.line'].create(vals)
        self.write({'productivity_tracking_id': productivity_id.id})

    def create_final_inspection(self):
        inspection_vals = {
            'customer': self.part_operation_line_id.job_id.partner_id.id,
            'product_id': self.part_operation_line_id.job_id.part_no.id,
            'lot_ids': [(4, self.lot_producing_id.id)],
            'part_operation_line_id': self.part_operation_line_id.id,
            'tc_no': '-',
            'tc_date': date.today(),
            'inspect_date': date.today(),
            'qty': self.lot_producing_id.product_qty,  # Use lot-specific qty
        }

        final_inspection = self.env['final.inspection'].create(inspection_vals)
        final_inspection.get_final_parameter_details()
        self.part_operation_line_id.final_inspection_ids = [(4, final_inspection.id)]

