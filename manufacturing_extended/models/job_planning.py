from odoo.exceptions import ValidationError, UserError
from odoo import api, fields, models, _


class JobPlanning(models.Model):
    _name = 'job.planning'
    _description = 'Job Planning'
    _inherit = ['mail.thread.cc', 'mail.thread.main.attachment', 'mail.activity.mixin']

    @api.model
    def get_finished_goods(self):
        fg_products = self.env.ref('inventory_extended.category_finished_goods').id
        return [('categ_id', 'in', [fg_products]), ('type', 'in', ['product', 'consu'])]

    # INVISIBLE FIELDS START
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    active = fields.Boolean(default=True)
    foreclose = fields.Boolean(string='Foreclose', default=False, help="If checked, this job will be foreclosed and no further operations can be performed on it.")
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
    state = fields.Selection([('new', 'New'), ('complete', 'Completed')], default='new')
    mo_id = fields.Many2one('mrp.production', string='MO ID')
    bom_id = fields.Many2one('mrp.bom', string='BOM ID', compute='get_bom')
    mo_state = fields.Selection(related='mo_id.state', string='MO State')
    process_routing_id = fields.Many2one('process.routing', string='Process Routing', compute='get_process_routing')
    tracking_id = fields.Many2one('job.order.tracking', string='Tracking ID')
    operation_ids_line = fields.One2many('part.operation.line', related='tracking_id.operation_ids', string='Operations')


    def action_force_close(self):
        self.tracking_id.action_force_close()
        self.foreclose =True


    # job_tracking_count = fields.Float(string='Job Tracking Count', compute='_compute_job_tracking_count')
    #
    # @api.depends('tracking_id')
    # def _compute_job_tracking_count(self):
    #     for rec in self:
    #         rec.job_tracking_count = len(rec.tracking_id)

    def get_job_tracking_details(self):
        self.sudo().ensure_one()
        form_view = self.sudo().env.ref('manufacturing_extended.job_order_tracking_form_view')
        tree_view = self.sudo().env.ref('manufacturing_extended.job_order_tracking_tree_view')
        return {
            'name': _('Job Order Tracking'),
            'res_model': 'job.order.tracking',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('id', '=', self.tracking_id.id)],
        }

    @api.depends('part_no')
    def get_process_routing(self):
        for rec in self:
            rec.process_routing_id = self.env['process.routing'].search([('product_id', '=', rec.part_no.id)], limit=1)

    @api.depends('part_no')
    def get_bom(self):
        for rec in self:
            rec.bom_id = self.env['mrp.bom'].search([('product_tmpl_id', '=', rec.part_no.id)], limit=1)

    @api.constrains('job_qty')
    def restrict_job_qty(self):
        if self.job_qty <= 0.00:
            raise ValidationError("Alert, Mr. %s.\nJob Quantity cannot be Zero."
                                  % self.env.user.name)

    def action_confirm(self):

        self.track_process_routing()
        self.write({
            'state': 'complete',
        })
        if self.tracking_id:
            for operation in self.tracking_id.operation_ids:
                # part_operation_id
                op_iqc_raw = self.env.ref('manufacturing_extended.op_iqc_raw').id
                op_iqc_part = self.env.ref('manufacturing_extended.op_iqc_part').id
                if operation.operation_type == 'internal' and operation.production_op:
                    if operation.part_operation_id.operation_list_id.id != op_iqc_raw and operation.part_operation_id.operation_list_id.id != op_iqc_part:
                        mo_order = operation.create_mo_order()
                        operation.write({
                            'mo_ids': [(4, mo_order.id)],
                        })
                        mo_order.write({
                            'part_operation_line_id': operation.id,
                        })

        # self.write({
        #     'state': 'complete',
        #     'mo_id': mo_order.id,
        # })

    # def update_job_id_recursive(self, mo):
    #     """
    #     Recursively updates job_id for the given MO and its child MOs.
    #     """
    #     if not mo:
    #         return
    #
    #     print(f"Updating job_id for MO: {mo.name}")
    #
    #     # Find child MOs where this MO is the origin
    #     child_mos = self.env['mrp.production'].search([('origin', '=', mo.name)])
    #
    #     for child_mo in child_mos:
    #         child_mo.write({'job_id': self.id})
    #         child_mo.do_unreserve()
    #         child_mo.workorder_ids._compute_available_qty_fg()
    #         print(f"Updated job_id for Child MO: {child_mo.name}")
    #
    #         # Recursively update its child MOs
    #         self.update_job_id_recursive(child_mo)

    def track_process_routing(self):
        production = self.env['mrp.production'].search([('job_id', '=', self.id)])
        print(')))))))))))))))))))))))))))))))', production)
        job_order_tracking = self.env['job.order.tracking'].create({
            'partner_id': self.partner_id.id,
            'part_no': self.part_no.id,
            'job_qty': self.job_qty,
            'job_prod': self.job_prod,
            'inv_qty': self.inv_qty,
            'job_allocation': self.job_allocation,
            'job_type': self.job_type,
            'job_priority': self.job_priority,
            'status_current_operation': self.status_current_operation,
            'schedule_job_complete': self.schedule_job_complete,
            'job_due': self.job_due,
            'order_ref': self.order_ref,
            'order_due': self.order_due,
            'quantity': self.quantity,
            'state': 'progress',
            'job_id': self.id,
            'process_routing_id': self.process_routing_id.id,
            'operation_ids': [(0, 0, {
                'sequence': operation.sequence,
                'operation_id': operation.operation_id.id,
                'part_operation_id': operation.id,
                'operation_qty': self.job_qty,
                'balance_qty': 0,
                'job_id': self.id,
                'production_op': operation.production_op,
                'shippable': operation.shippable,
                'operation_code': operation.operation_code,
                'supplier_id': operation.partner_id.id,
                'bom_id': operation.bom_id.id,
                'mo_ids': [(6, 0, [mo.id for mo in production if mo.bom_id and mo.bom_id.id == operation.bom_id.id])],
                'operation_type': operation.operation_type,
            }) for operation in self.process_routing_id.order_lines],
        })
        self.write({'tracking_id': job_order_tracking.id})

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.sudo().env['ir.sequence'].next_by_code('job.planning') or '/'
        return super().create(vals_list)
