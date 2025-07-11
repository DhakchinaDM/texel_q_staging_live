from odoo import fields, models, api, _
from datetime import date
from odoo.exceptions import UserError, ValidationError
import math
from decimal import Decimal, InvalidOperation


class IncomingInspection(models.Model):
    _name = 'incoming.inspection'
    _description = 'Incoming Inspection'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _order = "create_date desc"

    name = fields.Char(string="Name", store=True, readonly=True)
    material_grade = fields.Char(string="Material Grade")
    draw_rev_no = fields.Char(string="Drawing Rev No")
    draw_rev_date = fields.Date(string="Drawing Rev Date")
    product_id = fields.Many2one('product.template', string="Product Name")
    part_no = fields.Char(string="Part No", compute='_compute_part_no_and_name')
    part_name = fields.Char(string="Part Name", compute='_compute_part_no_and_name')
    partner_id = fields.Many2one('res.partner', string="Supplier")
    purchase_id = fields.Many2one('purchase.order', string="PO No")
    po_date = fields.Date(string="PO Date")
    batch_no = fields.Char(string="Batch No")
    inspector_id = fields.Many2one('hr.employee', string="Inspector Name")
    lot_qty = fields.Float(string="Lot Qty")
    dc_invoice_no = fields.Char(string="DC/Invoice No")
    sample_size = fields.Float(string="Sample Size", compute='compute_incoming_qty')
    inspection_date = fields.Date(string="Inspection Date")
    type = fields.Selection([('raw', 'Raw Material'),
                             ('sub_cont', 'Sub Contract')],
                            string="Type", default="raw")
    state = fields.Selection(
        [('draft', 'Draft'),
         ('inspector_approved', 'Waiting for Second Approval'),
         ('inspector_c_approved', 'Conditionally Approved'),
         ('engineer_approved', 'Approved'),
         ('engineer_c_approved', 'Conditionally Approved'),
         ('reject', 'Rejected'),
         ('done', 'Approved'),
         ],
        string="Status", default='draft', required=True, tracking=True)

    parameters_ids = fields.One2many('parameter.check.line', 'request_id')
    picking_id = fields.Many2one('stock.picking', string='Picking')

    inspector_approve_by = fields.Many2one('res.users', string='Approved By')
    engineer_approve_by = fields.Many2one('res.users', string=' Approved By')
    inspector_approve_on = fields.Datetime(string='Approved On')
    engineer_approve_on = fields.Datetime(string=' Approved On')

    inspector_approve_type = fields.Selection([
        ('approve', 'Approved'),
        ('conditional_approve', 'Conditional Approved'),
    ], string='Approve type')
    engineer_approve_type = fields.Selection([
        ('approve', 'Approved'),
        ('conditional_approve', 'Conditional Approved'),
    ], string=' Approve type')
    conditional_approve_remark = fields.Text()

    part_type = fields.Selection([
        ('automotive', 'Automotive'),
        ('aero_space', 'Aero Space'),
    ], string='Part type', default='automotive')

    inspection_type = fields.Selection([
        ('sampling', 'Sampling'),
        ('full', '100%'),
    ], string='Inspection type', default='sampling', tracking=True)

    observation_attachment = fields.Binary(string="Observation Attachment")
    supplier_test_need = fields.Boolean(string="Supplier Test Report Needed")
    supplier_test_report = fields.Binary(string="Supplier Test Report")
    material_test_need = fields.Boolean(string="Material Test Attachment ")
    material_test_attachment = fields.Binary(string="Material Test Attachment")
    material_test_report = fields.Binary(string="Material Test Certificate")
    material_test_date = fields.Date('Third Party Date')
    certificate_if_needed = fields.Boolean(string='If Needed Third Party Material Test Certificate')
    inspection_incoming_type = fields.Selection([
        ('incoming_raw', 'Raw'),
        ('incoming_part', 'Parts'),
    ], default='incoming_raw')
    vendor_credit_note = fields.Many2one('account.move')
    dc_ref_id = fields.Many2one('stock.picking')
    stock_move_id = fields.Many2one('stock.move')
    file_name_1 = fields.Char()
    file_name_2 = fields.Char()
    file_name_3 = fields.Char()
    file_name_4 = fields.Char()

    other_document_need = fields.Boolean(string="Other Document Needed")
    other_document_report = fields.Binary(string="Other Document Report")
    file_name_5 = fields.Char()
    grn_date = fields.Date()
    allow_reject_bool = fields.Boolean()
    rejected_qty = fields.Float()
    accepted_qty = fields.Float(string="Accepted Qty", compute='compute_accepted_qty')

    reject_remarks = fields.Text(string='Reject Reason')
    reject_date = fields.Date(string='Rejected On')
    rejected_by = fields.Many2one('res.users', string='Rejected By')

    alert_message = fields.Char(string="Alert Message", compute="_compute_alert_message", )
    allow_record_approve = fields.Boolean(string="Allow Approve")
    status_dcn =fields.Selection([('debit_note', 'Debit Note'), ('dc', 'Delivery Challan')], string='Status ')
    # lot_id = fields.Many2one('stock.lot', string='Lot No', store=True, related='picking_id.lot_id')

    lot_id = fields.Many2one('stock.lot', string='Lot No')

    # @api.depends('picking_id')
    # def _compute_lot_id(self):
    #     for record in self:
    #         lot = False
    #         print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    #         if record.picking_id:
    #             print("11111111111111111111111111111111111111111")
    #
    #             for move in record.picking_id.move_ids_without_package:
    #                 print("222222222222222222222222222222222222222222222")
    #
    #                 if move.product_id.product_tmpl_id.id == record.product_id.id:
    #                     print("33333333333333333333333333333333333333333333333")
    #
    #                     lot = move.lot_ids[:1]
    #         record.lot_id = lot.id if lot else False

    @api.depends('lot_qty', 'rejected_qty')
    def compute_accepted_qty(self):
        for record in self:
            if record.lot_qty and record.rejected_qty:
                record.accepted_qty = record.lot_qty - record.rejected_qty
            else:
                record.accepted_qty = 0.0


    @api.depends('product_id', 'product_id.default_code', 'product_id.name')
    def _compute_part_no_and_name(self):
        for i in self:
            i.part_no = i.product_id.default_code if i.product_id.default_code else None
            i.part_name = i.product_id.name

    @api.depends('lot_qty', 'rejected_qty', 'reject_remarks', 'reject_date', 'rejected_by')
    def _compute_alert_message(self):
        for record in self:
            if record.rejected_qty and record.rejected_by:
                record.alert_message = (
                    f"Inspection completed for a total quantity of {record.lot_qty}. "
                    f"A total of {record.rejected_qty} units were rejected due to '{record.reject_remarks or 'no specified reason'}', "
                    f"by {record.rejected_by.name or 'an unidentified person'} on {record.reject_date.strftime('%d-%m-%Y') or 'an unspecified date'}."
                )
            else:
                record.alert_message = ''

    @api.depends('product_id')
    def compute_material_test_certificate(self):
        for i in self:
            if i.product_id:
                i.material_test_report = i.product_id.third_party_certificate_attach
                i.material_test_date = i.product_id.third_party_certificate
            else:
                i.material_test_report = False
                i.material_test_date = False

    def fetch_parameters(self):
        self.parameters_ids = [(2, pd.id, 0) for pd in self.parameters_ids]
        self.parameters_ids = [(0, 0, {
            'parameter_id': p.parameter_id.id,
            'check_method_id': [(6, 0, p.check_method_id.ids)],
            'specification': p.specification,
            'min_level': p.min_level,
            'max_level': p.max_level,
            'baloon_no': p.baloon_no,
        }) for p in self.product_id.quality_parameters]

    @api.depends('inspection_type', 'lot_qty')
    def compute_incoming_qty(self):
        for record in self:
            record.sample_size = 0
            if record.inspection_type == 'sampling':
                ty = False
                if record.inspection_incoming_type == 'incoming_raw':
                    ty = 'raw'
                elif record.inspection_incoming_type == 'incoming_part':
                    ty = 'parts'
                sample = self.env['quality.sampling'].sudo().search(
                    [('model_id', '=', self._name), ('type', '=', ty), ], limit=1)
                for i in sample.sampling_ids.filtered(
                        lambda x: x.min_lot_qty <= record.lot_qty <= x.max_lot_qty):
                    record.sample_size = i.sample_size
            elif record.inspection_type == 'full':
                record.sample_size = record.lot_qty

    def check_observation(self):
        approve_iqc = self.env['ir.config_parameter'].sudo().get_param('quality_extension.approve_iqc')
        if not self.inspector_id:
            raise UserError(_("Please Enter Inspector Name"))
        if not self.batch_no:
            raise UserError(_("Please Enter Batch No"))
        if not self.inspection_date:
            raise UserError(_("Please Enter Inspection Date"))
        if not approve_iqc:
            if not self.parameters_ids:
                raise UserError(_("Please Enter Parameter Details"))
            for i in self.parameters_ids:
                if not i.parameter_id.observation_no_need:
                    sample_qty = int(self.sample_size or 0)
                    required_observations = min(sample_qty, 5)
                    observations = [
                        i.observation_1,
                        i.observation_2,
                        i.observation_3,
                        i.observation_4,
                        i.observation_5
                    ]
                    for idx in range(required_observations):
                        if not observations[idx]:
                            raise UserError(_("Please enter Observation %d details for Parameter %s." % (idx + 1,
                                                                                                         i.parameter_id.name)))
                    if not i.remarks:
                        raise UserError(_("Please enter Remarks for Parameter %s." % i.parameter_id.name))
        else:
            if not self.observation_attachment:
                raise UserError(_("Please Upload the Observation Attachment"))

    def view_vendor_credit_note(self):
        return {
            'name': _('Vendor Credit Note'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': self.id,
            'domain': [('id', '=', self.vendor_credit_note.id)],
            'target': 'current'
        }

    def view_dc(self):
        return {
            'name': _('Delivery Challan'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': self.id,
            'domain': [('id', '=', self.dc_ref_id.id)],
            'target': 'current'
        }

    def view_good_receipt_note(self):
        return {
            'name': _('Goods Receipt Notes'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': self.id,
            'domain': [('id', '=', self.picking_id.id)],
            'target': 'current'
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals['inspection_incoming_type'] == 'incoming_raw':
                vals['name'] = self.sudo().env['ir.sequence'].get('incoming.inspection') or '/'
                res = super(IncomingInspection, self).create(vals)
            else:
                vals['name'] = self.sudo().env['ir.sequence'].get('incoming.inspection.parts') or '/'

                res = super(IncomingInspection, self).create(vals)
        return res

    def inspector_approve(self):

        if not self.allow_record_approve:
            self.check_observation()
        else:
            if not self.observation_attachment:
                self.check_observation()
        
        self.write({
            'state': 'inspector_approved',
            'inspector_approve_by': self.env.user.id,
            'inspector_approve_on': fields.Datetime.now(),
            'inspector_approve_type': 'approve',
        })

    def inspector_c_approve(self):
        self.check_observation()
        self.write({
            'state': 'inspector_c_approved',
            'inspector_approve_by': self.env.user.id,
            'inspector_approve_on': fields.Datetime.now(),
            'inspector_approve_type': 'conditional_approve',
        })

    def open_conditional_approve(self):
        view_id = self.env['conditional.approve.remarks']
        return {
            'type': 'ir.actions.act_window',
            'name': 'Conditional Approve Remarks',
            'res_model': 'conditional.approve.remarks',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': view_id.id,
            'view_id': self.env.ref('quality_extension.conditional_approve_remarks_wizard', False).id,
            'context': {'default_record_type': 'inspector'},
            'target': 'new',
        }

    def engineer_approve(self):
        self.write({
            'state': 'inspector_approved',
            'engineer_approve_by': self.env.user.id,
            'engineer_approve_on': fields.Datetime.now(),
            'engineer_approve_type': 'approve',
        })
        self.complete_receipt()

    def engineer_c_approve(self):
        view_id = self.env['conditional.approve.remarks']
        return {
            'type': 'ir.actions.act_window',
            'name': 'Conditional Approve Remarks',
            'res_model': 'conditional.approve.remarks',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': view_id.id,
            'view_id': self.env.ref('quality_extension.conditional_approve_remarks_wizard', False).id,
            'context': {'default_default_remark': self.conditional_approve_remark, 'default_record_type': 'engineer'},
            'target': 'new',
        }
        # self.write({
        #     'state': 'inspector_c_approved',
        #     'engineer_approve_by': self.env.user.id,
        #     'engineer_approve_on': fields.Datetime.now(),
        #     'engineer_approve_type': 'conditional_approve',
        # })
        # self.complete_receipt()

    def complete_receipt(self):
        self.write({
            'state': 'done',
        })
        # if self.picking_id:
        #     self.picking_id.write({'state': 'assigned'})
        # self.picking_id.button_validate()
        # Multiple Product in picking (BackOrder)
        # pickings_to_validate = [self.picking_id.id]
        #
        # if pickings_to_validate:
        #     pickings_to_validate = self.env['stock.picking'].browse(pickings_to_validate).with_context(skip_backorder=True)
        #     return pickings_to_validate.button_validate()
        # return True

    def approve_to_confirm(self):
        if self.state == 'submit_for_approve':
            self.write({
                'state': 'approve'
            })

    def allow_reject(self):
        if self.inspection_type == 'sampling':
            self.inspection_type = 'full'
            self.message_post(body="Inspection moved to 100% due to sampling rejection.")
        # elif self.inspection_type == 'full':
        #     view_id = self.env['incoming.inspection.wizard']
        #     return {
        #         'type': 'ir.actions.act_window',
        #         'name': 'Reject Quantity',
        #         'res_model': 'incoming.inspection.wizard',
        #         'view_type': 'form',
        #         'view_mode': 'form',
        #         'res_id': view_id.id,
        #         'view_id': self.env.ref('quality_extension.incoming_inspection_wizard_form', False).id,
        #         'target': 'new',
        #         'context': {
        #             'default_sample_qty': self.sample_size,
        #         },
        #     }
        self.allow_reject_bool = True
        self.state = 'reject'

    def create_dn_dc(self):
        view_id = self.env['incoming.inspection.wizard']
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Quantity',
            'res_model': 'incoming.inspection.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': view_id.id,
            'view_id': self.env.ref('quality_extension.incoming_inspection_wizard_form', False).id,
            'target': 'new',
            'context': {
                'default_sample_qty': self.sample_size,
                'default_how_many_qty_rejected': self.rejected_qty,
                'default_allow_dn_dc': True,
            },
        }

    def draft_submit(self):
        self.write({
            'state': 'draft'
        })


class ParameterCheckLine(models.Model):
    _name = 'parameter.check.line'
    _description = 'Parameter Check Line'

    request_id = fields.Many2one('incoming.inspection', string='Request No')
    parameter_id = fields.Many2one('quality.parameter', string='Parameter')
    observation_no_need = fields.Boolean(string='Observation No Need', compute='compute_observation_need')
    check_method_id = fields.Many2many('quality.check.method', string='Method of Check')
    specification = fields.Char(string='Specification')
    min_level = fields.Float(string='Minimum')
    max_level = fields.Float(string='Maximum')
    baloon_no = fields.Char(string='Ball No')
    invalid_level_check = fields.Boolean(compute='compute_invalid_level_check')
    remarks = fields.Char(string='Remarks')
    observation_1 = fields.Char(string='Observation 1')
    observation_2 = fields.Char(string='Observation 2')
    observation_3 = fields.Char(string='Observation 3')
    observation_4 = fields.Char(string='Observation 4')
    observation_5 = fields.Char(string='Observation 5')
    level_check = fields.Selection([
        ('diff_1', 'Diff one'),
        ('diff_2', 'Diff Two'),
        ('diff_3', 'Diff Three'),
        ('diff_4', 'Diff Four'),
        ('diff_5', 'Diff Five'),
    ], string='Level Check')
    obser_1_check = fields.Boolean(string='Check One', compute='_compute_level_checks')
    obser_2_check = fields.Boolean(string='Check Two', compute='_compute_level_checks')
    obser_3_check = fields.Boolean(string='Check Three', compute='_compute_level_checks')
    obser_4_check = fields.Boolean(string='Check Four', compute='_compute_level_checks')
    obser_5_check = fields.Boolean(string='Check Five', compute='_compute_level_checks')

    obs_status = fields.Selection([
        ('okay', 'Okay'),
        ('not_okay', 'Not Okay'),
    ], string='Status')

    @api.depends('parameter_id')
    def compute_observation_need(self):
        for i in self:
            if i.parameter_id.observation_no_need:
                i.observation_no_need = True
            else:
                i.observation_no_need = False

    @api.constrains('min_level', 'max_level')
    def compute_invalid_level_check(self):
        for record in self:
            record.invalid_level_check = False
            if record.min_level > record.max_level:
                record.invalid_level_check = True
                raise ValidationError(_('Alert! Kindly Enter Minimum and Maximum values Properly.'))

    # @api.onchange('observation_1', 'observation_2', 'observation_3', 'observation_4', 'observation_5')
    # def _check_decimal_places(self):
    #     for record in self:
    #         try:
    #             if not record.parameter_id.observation_no_need:
    #                 def format_decimal(value):
    #                     dec_value = Decimal(str(value)).quantize(Decimal('1.0000'), rounding='ROUND_DOWN')
    #                     return dec_value.normalize()
    #                 record.observation_1 = format_decimal(float(record.observation_1))
    #                 record.observation_2 = format_decimal(float(record.observation_2))
    #                 record.observation_3 = format_decimal(float(record.observation_3))
    #                 record.observation_4 = format_decimal(float(record.observation_4))
    #                 record.observation_5 = format_decimal(float(record.observation_5))
    #         except (InvalidOperation, ValueError):
    #             raise ValidationError(_('Alert! The Observations must have only numeric values'))

    @api.depends('observation_1', 'observation_2', 'observation_3', 'observation_4', 'observation_5')
    def _compute_level_checks(self):
        for rec in self:
            for i in range(1, 6):
                setattr(rec, f'obser_{i}_check', False)
            setattr(rec, 'obs_status', 'okay')
            if not any(getattr(rec, f'observation_{i}') for i in range(1, 6)):
                rec.obs_status = False
                continue
            if not rec.parameter_id.observation_no_need:
                for i in range(1, 6):
                    observation = getattr(rec, f'observation_{i}')
                    try:
                        if observation and (float(observation) < rec.min_level or float(observation) > rec.max_level):
                            setattr(rec, f'obser_{i}_check', True)
                            setattr(rec, 'obs_status', 'not_okay')
                    except ValueError as e:
                        pass
