from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CorrectiveMaintenance(models.Model):
    _name = 'corrective.maintenance'
    _description = 'Corrective Maintenance'
    _inherit = ['mail.thread.cc', 'mail.thread.main.attachment', 'mail.activity.mixin']

    doc_num = fields.Char(string='Document Number', tracking=True )
    rev_date = fields.Date(string='Revision Date', tracking=True )
    rev_num = fields.Char(string='Revision Number', tracking=True)


    name = fields.Char(string="Name", default='New')
    machine_id = fields.Many2one('maintenance.equipment', string='Machine Name')
    machine_no = fields.Char(string='Machine Number', compute='compute_machine_details')
    machine_serial_no = fields.Char(string='Machine Serial Number', compute='compute_machine_details')
    maintenance_type = fields.Selection([
        ('corrective', 'BreakDown'),
        ('preventive', 'Predictive'),
    ], default='corrective', string="Maintenance Type")
    break_down_time = fields.Datetime(string='Break Down Time')
    description = fields.Text(string='Description')
    root_case = fields.Char(string='Root Cause')
    request_raised_for = fields.Many2one('hr.employee', string='Request Raised For')
    shift_type = fields.Selection([('a', 'Shift I'), ('b', 'Shift II'), ('c', 'Shift III'), ('g', 'Shift G')])
    action_taken = fields.Char(string='Action Taken')
    work_done_by = fields.Many2one('res.users', string='Work Done By  ', default=lambda self: self.env.user)
    work_done_byy = fields.Many2one('hr.employee', string='Work Done By')
    partner_id = fields.Many2one('res.partner', string='Partner Name', compute='compute_partner')
    restart_time = fields.Datetime(string='Restart Time')
    duration = fields.Char(string='Duration', compute='compute_duration')
    duration_float = fields.Float(string='Duration  ', compute='compute_duration')
    remarks = fields.Char(string='Remark')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft', string="State")
    delivery_state = fields.Selection([
        ('draft', 'Draft'),
        ('delivery', 'Delivery'),
        ('delivery_create', 'Delivery Created'),
        ('purchase', 'Purchase')
    ], default='draft', string="Delivery State", compute='compute_spare_details')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
                                   default=lambda self: self.env.ref('stock.warehouse0', raise_if_not_found=False))
    spare_ids = fields.One2many('corrective.maintenance.spare', 'corrective_id')
    delivery_id = fields.Many2one('stock.picking', string='Delivery')
    delivery_count = fields.Integer(string='Delivery Count', compute='_compute_delivery_count')
    indentification_time = fields.Datetime(string='Identification Time')

    spare_replaced = fields.Boolean('Spare Replaced')

    preventive_maintenance_id = fields.Many2one('preventive.maintenance.check', string='Predictive Maintenance ID')

    def _compute_delivery_count(self):
        for rec in self:
            rec.delivery_count = self.env['stock.picking'].sudo().search_count(
                [('id', '=', self.delivery_id.id)])

    def action_delivery_count(self):
        return {
            'name': _('Delivery'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': self.id,
            'domain': [('id', '=', self.delivery_id.id)],
            'target': 'current'
        }

    @api.depends('work_done_by')
    def compute_partner(self):
        for i in self:
            if i.work_done_by:
                partner = self.env['res.partner'].search([('user_id', '=', i.work_done_by.id)])
                i.write({
                    'partner_id': i.work_done_by.partner_id.id,
                })
            else:
                i.write({
                    'partner_id': False,
                })

    def action_done(self):
        if self.spare_ids:
            for s in self.spare_ids:
                if s.required_qty <= 0:
                    raise ValidationError(
                        f"Alert, Mr. {self.env.user.name}.\nPlease Mention the Required Qty of the Spare {s.product_id.name}.")
        if not self.indentification_time:
            raise ValidationError(
                f"Alert, Mr. {self.env.user.name}.\nPlease enter the Indentification Time.")
        if not self.break_down_time:
            raise ValidationError(
                f"Alert, Mr. {self.env.user.name}.\nPlease enter the Break Down Time.")
        if not self.restart_time:
            raise ValidationError(
                f"Alert, Mr. {self.env.user.name}.\nPlease enter the Restart Time.")
        if not self.description:
            raise ValidationError(
                f"Alert, Mr. {self.env.user.name}.\nPlease enter the Description.")
        if not self.remarks:
            raise ValidationError(
                f"Alert, Mr. {self.env.user.name}.\nPlease enter the Remarks.")
        if not self.request_raised_for:
            raise ValidationError(
                f"Alert, Mr. {self.env.user.name}.\nPlease enter the Request Raised For.")
        if not self.shift_type:
            raise ValidationError(
                f"Alert, Mr. {self.env.user.name}.\nPlease enter the Shift Type.")
        if not self.action_taken:
            raise ValidationError(
                f"Alert, Mr. {self.env.user.name}.\nPlease enter the Action Taken.")
        if not self.root_case:
            raise ValidationError(
                f"Alert, Mr. {self.env.user.name}.\nPlease enter the Root Case.")
        if self.spare_ids:
            if self.delivery_id:
                if self.delivery_id.state != 'done':
                    raise ValidationError(
                        f"Alert, Mr. {self.env.user.name}.\nPlease Complete the Delivery.")
            else:
                raise ValidationError(
                    f"Alert, Mr. {self.env.user.name}.\nPlease Create the Delivery to proceed")

        if self.spare_ids:
            for s in self.spare_ids:
                if s.required_qty <= 0:
                    raise ValidationError(
                        f"Alert, Mr. {self.env.user.name}.\nPlease Mention the Required Qty of the Spare {s.product_id.name}.")
        data = []
        for rec in self:
            if rec.maintenance_type == 'corrective':
                type = 'corrective'
            else:
                type = 'predictive'
            val = (0, 0, {
                'machine_id': rec.machine_id.id,
                'type': 'predictive',
                'user_id': rec.work_done_by.id,
                'actual_date': rec.restart_time,
                'plan_hours': rec.duration_float,
                'plan_date': rec.break_down_time,
                'reference': 'corrective.maintenance,' + str(rec.id)
            })
            data.append(val)
            rec.machine_id.write({
                'machine_history_ids': data
            })
        self.write({
            'state': 'done',
        })

    @api.depends('break_down_time', 'restart_time')
    def compute_duration(self):
        for i in self:
            if i.break_down_time and i.restart_time:
                duration = i.restart_time - i.break_down_time
                days = duration.days
                hours, remainder = divmod(duration.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)

                duration_parts = []
                if days > 0:
                    duration_parts.append(f'{days} Days')
                if hours > 0:
                    duration_parts.append(f'{hours} Hrs')
                if minutes > 0:
                    duration_parts.append(f'{minutes} Mins')
                if seconds > 0:
                    duration_parts.append(f'{seconds} Sec')
                duration_str = ', '.join(duration_parts)
                i.duration = duration_str if duration_parts else '-'

                total_hours = days * 24 + hours + minutes / 60 + seconds / 3600
                i.duration_float = total_hours
            else:
                i.duration = False
                i.duration_float = 0.0

    @api.depends('machine_id')
    def compute_machine_details(self):
        for i in self:
            if i.machine_id:
                i.write({
                    'machine_no': i.machine_id.codefor,
                    'machine_serial_no': i.machine_id.serial_no,
                })
            else:
                i.write({
                    'machine_no': False,
                    'machine_serial_no': False,
                })

    @api.depends('spare_ids', 'delivery_id')
    def compute_spare_details(self):
        state = False
        for i in self:
            if not i.delivery_id:
                for j in i.spare_ids:
                    if j.available_qty < j.required_qty:
                        state = 'purchase'
                    else:
                        state = 'delivery'
            else:
                state = 'delivery_create'
            i.write({
                'delivery_state': state,
            })

    def action_delivery(self):
        for line in self.spare_ids:
            if line.available_qty <= 0.00:
                raise ValidationError(_('Alert! Delivery cannot proceed. Out Of Stock.'))
            if line.required_qty <= 0.00:
                raise ValidationError(_('Alert! Delivery cannot proceed. Please Enter the Required Quantity.'))
        picking_type_id = self.env.ref('stock.picking_type_out').id
        picking_vals = {
            'partner_id': self.partner_id.id,
            'picking_type_id': picking_type_id,
            'location_id': self.warehouse_id.lot_stock_id.id,
            'location_dest_id': self.partner_id.property_stock_customer.id,
            'origin': self.name,
            'move_ids_without_package': [],
        }
        picking = self.env['stock.picking'].create(picking_vals)

        for line in self.spare_ids:
            move_vals = {
                'name': line.corrective_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.required_qty,
                'product_uom': line.product_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': self.warehouse_id.lot_stock_id.id,
                'location_dest_id': self.partner_id.property_stock_customer.id,
            }
            self.env['stock.move'].create(move_vals)
        self.write({
            'delivery_id': picking.id,
        })
        picking.action_confirm()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': picking.id,
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            if val['maintenance_type'] == 'corrective':
                val['name'] = self.sudo().env['ir.sequence'].next_by_code('corrective.maintenance') or 'New'
            else:
                val['name'] = self.sudo().env['ir.sequence'].next_by_code('predictive.maintenance') or 'New'

        return super().create(vals_list)


class CorrectiveMaintenanceSpare(models.Model):
    _name = 'corrective.maintenance.spare'
    _description = 'Corrective Maintenance Spare'
    _inherit = ['mail.thread.cc', 'mail.thread.main.attachment', 'mail.activity.mixin']

    corrective_id = fields.Many2one('corrective.maintenance', string='BreakDown')
    product_id = fields.Many2one('product.product', string='Critical Spares')
    available_qty = fields.Float(string='Available Qty', compute='compute_product_details')
    required_qty = fields.Float(string='Required Qty')

    @api.depends('product_id')
    def compute_product_details(self):
        for i in self:
            if i.product_id:
                i.write({
                    'available_qty': i.product_id.qty_available,
                })
            else:
                i.write({
                    'available_qty': False,
                })
