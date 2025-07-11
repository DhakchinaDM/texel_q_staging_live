from odoo import Command, api, fields, models, _
from dateutil.relativedelta import relativedelta
from odoo.tools import float_round
from odoo.exceptions import UserError


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    job_started = fields.Boolean(string='Job Started', default=False)
    partial_stock = fields.Boolean(string="Partial Stock", compute="get_partial_stock", store=True)
    load_component = fields.Boolean(string='Load Component', related='production_id.load_component', store=True)
    available_qty_fg = fields.Float(string="Available Quantity for FG", compute="_compute_available_qty_fg",
                                    store=True)
    component_availability_state = fields.Selection(string="Component Availability",
                                                    related='production_id.components_availability_state', store=True)
    job_id = fields.Many2one('job.planning', string='Job ID', related='production_id.job_id', store=True)

    @api.depends('production_id.move_raw_ids.product_id', 'production_id.move_raw_ids.product_uom_qty',
                 'production_id.state', 'production_id.product_qty', 'production_id.location_src_id.quant_ids.quantity',
                 'production_id.location_src_id.quant_ids.reserved_quantity',
                 'production_id.move_finished_ids.product_id',  # Track produced components
                 'production_id.move_finished_ids.state',  # Track stock move status
                 'production_id.move_finished_ids.quantity')
    def _compute_available_qty_fg(self):
        for wo in self:
            if wo.production_id:
                fg_qty = wo.production_id.product_qty  # Planned FG quantity
                min_available_qty = float('inf')  # Track the minimum available component quantity
                has_stock = False  # Flag to check if any stock is available

                for move in wo.production_id.move_raw_ids:
                    product = move.product_id
                    required_qty = move.product_uom_qty

                    if required_qty > 0:
                        # Get all quants for the product in the source location (consider only lot-tracked stock)
                        if move.product_id.tracking == 'lot':
                            quants = self.env['stock.quant'].search([
                                ('product_id', '=', product.id),
                                ('lot_id', '!=', False),
                                ('location_id', '=', wo.production_id.location_src_id.id or False),
                                ('lot_id.lot_type', 'in', ['ok', False])
                            ])

                            available_qty = 0  # Total available qty for this work order

                            for quant in quants:
                                # Find move lines for this lot and this work order
                                reserved_move_lines = self.env['stock.move.line'].search([
                                    ('lot_id', '=', quant.lot_id.id),
                                    ('move_id', 'in', move.ids),  # Check if the move belongs to this work order
                                ])

                                reserved_qty = sum(
                                    reserved_move_lines.mapped('quantity'))  # Total reserved for this WO
                                actual_available_qty = quant.quantity - max(quant.reserved_quantity - reserved_qty, 0)

                                available_qty += max(actual_available_qty, 0)  # Ensure it's never negative

                            if available_qty > 0:
                                has_stock = True  # At least some stock is available

                            # The maximum FG that can be produced based on this component's availability
                            possible_fg_qty = (available_qty / required_qty) * fg_qty if required_qty else 0

                            # Track the lowest possible FG quantity based on component availability
                            min_available_qty = min(min_available_qty, possible_fg_qty)
                        else:
                            # For non-lot-tracked products, check the available quantity directly
                            available_qty = self.env['stock.quant']._get_available_quantity(product,
                                                                                            wo.production_id.location_src_id)

                            if available_qty > 0:
                                has_stock = True

                # Update FG quantity based on stock availability and planned quantity
                if has_stock:
                    wo.available_qty_fg = min(min_available_qty, fg_qty)  # Ensure it does not exceed planned FG qty
                else:
                    wo.available_qty_fg = 0.0  # No stock available for any component
            else:
                wo.available_qty_fg = 0.0


    @api.depends('production_id.state', 'production_id.product_qty', 'state',
                 'production_id.mrp_production_child_count', 'production_id.move_raw_ids.quantity',
                 'production_id.move_raw_ids.product_uom_qty')
    def get_partial_stock(self):
        for i in self:
            if i.production_id.mrp_production_child_count == 0:
                # No child MO exists, so partial_stock must be True
                i.partial_stock = True
            else:
                # Check if any move has available stock in quant
                has_partial_component = any(
                    self.env['stock.quant']._get_available_quantity(move.product_id, move.location_id) > 0
                    for move in i.production_id.move_raw_ids
                )

                # If state is 'waiting', 'ready', or 'progress' and a lot has available quantity
                if i.state in ['waiting', 'ready', 'progress'] and has_partial_component:
                    i.partial_stock = True
                else:
                    i.partial_stock = False

    def button_start(self, bypass=False, emp_id=None):

        if emp_id:
            emp_id = self.env['hr.employee'].search([('emp_code', '=', emp_id)], limit=1)

        skip_employee_check = bypass or (not self.env.user.employee_id)
        main_employee = None

        if not skip_employee_check:
            if not self.env.context.get('mrp_display'):
                main_employee = emp_id.id if emp_id else self.env.user.employee_id.id

                if not main_employee:
                    raise UserError(
                        _("You need to link this user to an employee of this company to process the work order."))

            else:
                connected_employees = self.env['hr.employee'].get_employees_connected()
                if not connected_employees:
                    raise UserError(_("You need to log in to process this work order."))

                main_employee = self.env['hr.employee'].get_session_owner()
                if not main_employee:
                    raise UserError(_("There is no session chief. Please log in."))

            if any(main_employee not in [emp.id for emp in wo.allowed_employees] and not wo.all_employees_allowed for wo
                   in self):
                raise UserError(_("You are not allowed to work on this work order."))

        for wo in self:
            if any(not time.date_end for time in wo.time_ids.filtered(lambda t: t.user_id.id == self.env.user.id)):
                continue

            if wo.state in ('done', 'cancel'):
                continue

            if wo.product_tracking == 'serial' and wo.qty_producing == 0:
                wo.qty_producing = 1.0
            elif wo.qty_producing == 0:
                wo.qty_producing = wo.qty_remaining

            if wo._should_start_timer():
                self.env['mrp.workcenter.productivity'].create(
                    wo._prepare_timeline_vals(wo.duration, fields.Datetime.now())
                )

            if wo.production_id.state != 'progress':
                wo.production_id.write({'date_start': fields.Datetime.now()})

            if wo.state != 'progress':
                date_start = fields.Datetime.now()
                vals = {
                    'state': 'progress',
                    'date_start': date_start,
                }

                if not wo.leave_id:
                    leave = self.env['resource.calendar.leaves'].create({
                        'name': wo.display_name,
                        'calendar_id': wo.workcenter_id.resource_calendar_id.id,
                        'date_from': date_start,
                        'date_to': date_start + relativedelta(minutes=wo.duration_expected),
                        'resource_id': wo.workcenter_id.resource_id.id,
                        'time_type': 'other'
                    })
                    vals['date_finished'] = leave.date_to
                    vals['leave_id'] = leave.id
                else:
                    if not wo.date_start or wo.date_start > date_start:
                        vals['date_start'] = date_start
                        vals['date_finished'] = wo._calculate_date_finished(date_start)
                    if wo.date_finished and wo.date_finished < date_start:
                        vals['date_finished'] = date_start

                wo.with_context(bypass_duration_calculation=True).write(vals)

            if len(wo.time_ids) == 1 or all(wo.time_ids.mapped('date_end')):
                for check in wo.check_ids:
                    if check.component_id:
                        check._update_component_quantity()

            if main_employee:
                if len(wo.allowed_employees) == 0 or main_employee in [emp.id for emp in wo.allowed_employees]:
                    wo.start_employee(self.env['hr.employee'].browse(main_employee).id)
                    wo.employee_ids |= self.env['hr.employee'].browse(main_employee)
            wo.job_started = True
            wo.workcenter_id.job_started = True

        return True

    def button_pending(self, pause_data=None):
        """
        Handles pausing the work order, creates a backorder MO only if any reject quantity exists,
        marks it as done, and scraps it.
        """
        print("=================Pause Data==================", pause_data)
        global process_reject_qty, process_reject_reason, rework_qty, rework_reason, material_reject_reason, material_reject_qty
        pause_data = pause_data or {}  # Ensure it's a dictionary
        productivity_records = self.env['mrp.workcenter.productivity']
        ok_qty = 0

        for wo in self:
            # Get production details from pause_data
            produced_qty = pause_data.get('produced_qty', 0)
            ok_qty = pause_data.get('ok_qty', 0)
            rework_qty = pause_data.get('rework_qty', 0)
            material_reject_qty = pause_data.get('material_reject_qty', 0)
            process_reject_qty = pause_data.get('process_reject_qty', 0)
            pause_reason = pause_data.get('pause_reason', 'Nil')
            process_reject_reason = pause_data.get('process_reject_reason', 'Nil')
            material_reject_reason = pause_data.get('material_reject_reason', 'Nil')
            rework_reason = pause_data.get('rework_reason', 'Nil')
            shift = pause_data.get('shift', 'Nil')
            emp_id = pause_data.get('emp_id', 'Nil')
            ok_qty_remark = pause_data.get('ok_qty_remark', 'Nil')

            # Find the active workcenter productivity record(s)
            productivity_records = self.env['mrp.workcenter.productivity'].search([
                ('workorder_id', '=', wo.id),
                ('date_end', '=', False)
            ])
            print("=================Productivity Records==================", productivity_records)
            # Update the productivity record with the pause data
            wo.job_started = False
            wo.workcenter_id.job_started = False

            if ok_qty > 0:
                # Process OK quantity in the current production
                wo.production_id.write({'qty_producing': max(ok_qty, 0), 'notes': ok_qty_remark, 'qty_type': 'ok'})
                wo.production_id.lot_producing_id.write({'lot_type': "ok"})
                for pp in wo.production_id.move_raw_ids:
                    pp._onchange_product_uom_qty()
                    new_qty = float_round(
                        (wo.production_id.qty_producing - wo.production_id.qty_produced) * pp.unit_factor,
                        precision_rounding=pp.product_uom.rounding
                    )
                    pp.quantity = new_qty
                wo.production_id.button_mark_done()
                wo.production_id.confirm_next_operation_mo()
                if wo.production_id.state == 'done':
                    wo.production_id.create_productivity_line(productivity_records)
                    if wo.production_id.part_operation_line_id.final_inspection_need:
                        wo.production_id.create_final_inspection()
            else:
                # If no OK quantity, process one type in the current production and others separately
                if material_reject_qty > 0:
                    wo.production_id.write({'qty_producing': max(material_reject_qty, 0), 'notes': material_reject_reason,
                                              'qty_type': 'm_reject'})
                    wo.production_id.lot_producing_id.write({'lot_type': "m_reject"})
                    for pp in wo.production_id.move_raw_ids:
                        pp._onchange_product_uom_qty()
                        new_qty = float_round(
                            (wo.production_id.qty_producing - wo.production_id.qty_produced) * pp.unit_factor,
                            precision_rounding=pp.product_uom.rounding
                        )
                        pp.quantity = new_qty
                    wo.create_reject_rework_lot(material_reject_qty, material_reject_reason, 'm_reject',shift,emp_id, wo.production_id, wo.workcenter_id)
                    material_reject_qty = 0  # Mark as processed in the current production
                elif process_reject_qty > 0:
                    wo.production_id.write({'qty_producing': max(process_reject_qty, 0), 'notes': process_reject_reason,
                                              'qty_type': 'p_reject'})
                    wo.production_id.lot_producing_id.write({'lot_type': "p_reject"})
                    for pp in wo.production_id.move_raw_ids:
                        pp._onchange_product_uom_qty()
                        new_qty = float_round(
                            (wo.production_id.qty_producing - wo.production_id.qty_produced) * pp.unit_factor,
                            precision_rounding=pp.product_uom.rounding
                        )
                        pp.quantity = new_qty
                    wo.create_reject_rework_lot(process_reject_qty, process_reject_reason, 'p_reject',shift,emp_id, wo.production_id, wo.workcenter_id)

                    process_reject_qty = 0  # Mark as processed in the current production
                elif rework_qty > 0:
                    wo.production_id.write(
                        {'qty_producing': max(rework_qty, 0), 'notes': rework_reason, 'qty_type': 'rework'})
                    wo.production_id.lot_producing_id.write({'lot_type': "rework"})
                    for pp in wo.production_id.move_raw_ids:
                        pp._onchange_product_uom_qty()
                        new_qty = float_round(
                            (wo.production_id.qty_producing - wo.production_id.qty_produced) * pp.unit_factor,
                            precision_rounding=pp.product_uom.rounding
                        )
                        pp.quantity = new_qty
                    wo.create_reject_rework_lot(rework_qty, rework_reason, 'rework',shift,emp_id, wo.production_id, wo.workcenter_id)

                    rework_qty = 0  # Mark as processed in the current production

                wo.production_id.button_mark_done()
                if wo.production_id.state == 'done':
                    wo.production_id.create_productivity_line(productivity_records)


            # Process remaining quantities in separate records
            if material_reject_qty > 0:
                if wo.production_id.qty_type != 'm_reject':
                    wo.create_mo_scrap_entry(material_reject_qty, material_reject_reason, 'm_reject',shift,emp_id,
                                               productivity_records, wo.workcenter_id)

            if process_reject_qty > 0:
                if wo.production_id.qty_type != 'p_reject':
                    wo.create_mo_scrap_entry(process_reject_qty, process_reject_reason, 'p_reject',shift,emp_id, productivity_records, wo.workcenter_id)

            if rework_qty > 0:
                if wo.production_id.qty_type != 'rework':
                    wo.create_mo_scrap_entry(rework_qty, rework_reason, 'rework',shift,emp_id, productivity_records,wo.workcenter_id)

            if productivity_records and productivity_records.production_id.state == 'done':
                productivity_records.write({
                    'produced_qty': produced_qty,
                    'ok_qty': ok_qty,
                    'rework_qty': rework_qty,
                    'material_reject_qty': material_reject_qty,
                    'process_reject_qty': process_reject_qty,
                    'pause_reason': pause_reason,
                    'material_reject_reason': material_reject_reason,
                    'process_reject_reason': process_reject_reason,
                    'rework_reason': rework_reason,
                    'shift': shift,
                    'ok_qty_remark': ok_qty_remark,
                    'date_end': fields.Datetime.now(),
                })


        return productivity_records.id

    def create_reject_rework_lot(self, reject_qty, reason, type,shift,emp_id, backorder_mo, workcenter_id):
        print('----------------------====--=', emp_id, emp_id['id'], '====----------------------')
        # workcenter_id = backorder_mo.workorder_ids.mapped('workcenter_id').id
        lot_vals = {
            'name': 'New',
            'lot_id': backorder_mo.lot_producing_id.id,
            'product_id': backorder_mo.product_id.id,
            'quantity': reject_qty,
            'state': 'draft',
            'shift': shift,
            'operator_id': emp_id['id'],
            'reason': reason,
            'workcenter_id': workcenter_id.id,
            'customer_id': backorder_mo.job_id.partner_id.id,
            'job_id': backorder_mo.job_id.id,
            'mo_id': backorder_mo.id,
            'operation_no': backorder_mo.part_operation_line_id.operation_code,
        }
        lot_entry = self.env['reject.rework.lot'].create(lot_vals)
        return lot_entry


    def create_mo_scrap_entry(self, reject_qty, reason, type,shift,emp_id, productivity_records,workcenter_id):
        backorder_mo = self.production_id.procurement_group_id.mrp_production_ids.filtered(
            lambda mo: mo.id != self.production_id.id)
        backorder_mo = backorder_mo[-1]
        backorder_mo.write({'qty_producing': max(reject_qty, 0), 'notes': reason, 'qty_type': type})
        for move in backorder_mo.move_raw_ids:
            move._onchange_product_uom_qty()
            new_qty = float_round(
                (backorder_mo.qty_producing - backorder_mo.qty_produced) * move.unit_factor,
                precision_rounding=move.product_uom.rounding
            )
            move.quantity = new_qty
            move.picked = True
        backorder_mo.action_generate_serial()
        backorder_mo.lot_producing_id.lot_type = type
        backorder_mo.button_mark_done()
        if backorder_mo.state == 'done':
            backorder_mo.create_productivity_line(productivity_records)
        self.create_reject_rework_lot(reject_qty, reason, type,shift,emp_id, backorder_mo, workcenter_id)



    def stop_employee(self, employee_ids):
        """
        Unlinks employees from the work order and closes any active productivity records.
        """
        self.employee_ids = [Command.unlink(emp) for emp in employee_ids]
        self.env['mrp.workcenter.productivity'].search([
            ('employee_id', 'in', employee_ids),
            ('workorder_id', 'in', self.ids),
            ('date_end', '=', False)
        ])._close()


class MrpWorkcenterProductivity(models.Model):
    _inherit = "mrp.workcenter.productivity"

    produced_qty = fields.Float("Produced Quantity")
    ok_qty = fields.Float("OK Quantity")
    rework_qty = fields.Float("Rework Quantity")
    material_reject_qty = fields.Float("Material Reject Quantity")
    process_reject_qty = fields.Float("Process Reject Quantity")
    pause_reason = fields.Text("Pause Reason")
    material_reject_reason = fields.Text("Material Pause Reason")
    process_reject_reason = fields.Text("Process Pause Reason")
    rework_reason = fields.Text("Rework Reason")
    pdf_report = fields.Binary("PDF Report", readonly=True)
    lot_id = fields.Many2one('stock.lot', related='production_id.lot_producing_id')
    product_id = fields.Many2one('product.product', related='production_id.product_id')
    shift = fields.Selection(
        [('shift_I', 'Shift I'), ('shift_II', 'Shift II'), ('shift_III', 'Shift III'), ('shift_G', 'Shift G')],
        string='Shift')
    ok_qty_remark = fields.Text("OK Quantity Remark")
    productivity_line_ids = fields.One2many('productivity.line', 'workcenter_productivity_id',
                                            string='Productivity Tracking')

    def action_print_label(self):
        return self.env.ref('manufacturing_extended.report_mrp_workcenter_productivity').report_action(self)


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    job_started = fields.Boolean(string='Job Started', default=False)
