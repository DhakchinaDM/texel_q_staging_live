from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date


class IncomingInspectionWizard(models.TransientModel):
    _name = 'incoming.inspection.wizard'
    _description = 'Incoming Inspection'

    sample_qty = fields.Float(string='Sample Quantity')
    how_many_qty_rejected = fields.Float(string='Rejected Quantity')
    reject_remarks = fields.Text(string='Reject Reason')
    reject_date = fields.Date(string='Rejected On', default=date.today())
    rejected_by = fields.Many2one('res.users', string='Rejected By', default=lambda self: self.env.user, readonly=True)
    type = fields.Selection([('debit_note', 'Debit Note'), ('dc', 'Delivery Challan')], string='Type')
    allow_dn_dc = fields.Boolean()

    def submit(self):
        if self.how_many_qty_rejected <= 0.00:
            raise ValidationError(_('Alert! The Rejected Quantity cannot be zero or negative.'))
        applicant_id = self._context.get('active_ids')[0]
        active_inspection = self.env['incoming.inspection'].browse(applicant_id)
        if not active_inspection:
            raise ValidationError(_('The active inspection record is not found.'))
        if self.how_many_qty_rejected > self.sample_qty:
            raise ValidationError(_('Rejected Quantity cannot exceed Sample Quantity.'))
        if self.allow_dn_dc:
            if self.type == 'debit_note':
                active_inspection.write({
                    'status_dcn': self.type,
                })
                
                debit_note = self.env['account.move'].create({
                    'move_type': 'in_refund',
                    'partner_id': active_inspection.partner_id.id,
                    'ref': active_inspection.dc_invoice_no,
                    'invoice_line_ids': [(0, 0, {
                        'product_id': active_inspection.product_id.product_variant_id.id,
                        'quantity': self.how_many_qty_rejected,
                        'price_unit': active_inspection.stock_move_id.price_unit,
                    })],
                })
                active_inspection.vendor_credit_note = debit_note.id
                active_inspection.message_post(
                    body=_(
                        f'{self.how_many_qty_rejected} quantities rejected; Refund created via Debit Note {debit_note.name}.'))
            else:
                active_inspection.write({
                    'status_dcn': self.type,
                })
                
                location = self.env.ref('stock.stock_location_suppliers')
                location_dest = self.env.ref('stock.stock_location_stock')
                dc = self.env['stock.picking'].create({
                    'partner_id': active_inspection.partner_id.id,
                    'picking_type_id': self.env.ref('stock.picking_type_out').id,
                    'origin': active_inspection.name,
                    'bill_ref': active_inspection.name,
                    'move_ids_without_package': [(0, 0, {
                        'product_id': active_inspection.product_id.product_variant_id.id,
                        'name': active_inspection.product_id.name,
                        'product_uom_qty': self.how_many_qty_rejected,
                        'quantity': self.how_many_qty_rejected,
                        'location_id': location.id,
                        'location_dest_id': location_dest.id,
                    })],
                })
                active_inspection.dc_ref_id = dc.id
                active_inspection.message_post(
                    body=_(
                        f'{self.how_many_qty_rejected} quantities rejected; Delivery Challan created {dc.name}.'))
            remaining_qty = self.sample_qty - self.how_many_qty_rejected
            if remaining_qty > 0:
                active_inspection.picking_id.move_ids_without_package[0].write({
                    'product_uom_qty': remaining_qty,
                    'quantity': remaining_qty
                })
                active_inspection.picking_id.button_validate()
            else:
                active_inspection.picking_id.action_cancel()
        else:
            print('======else')
            active_inspection.write({
                'rejected_qty': self.how_many_qty_rejected,
                'reject_remarks': self.reject_remarks,
                'reject_date': self.reject_date,
                'rejected_by': self.rejected_by,
            })
            active_inspection.state = 'reject'
            self.split_lot()


    def split_lot(self):
        reject_lot = ''
        applicant_id = self._context.get('active_ids')[0]
        active_inspection = self.env['incoming.inspection'].browse(applicant_id)

        for incoming in active_inspection:
            if incoming.lot_id:
                product = incoming.product_id.product_variant_id
                location = incoming.picking_id.location_dest_id

                # ✔ Reduce quantity from the original lot (system-safe method)
                self.env['stock.quant']._update_available_quantity(
                    product, location, -self.how_many_qty_rejected,
                    lot_id=incoming.lot_id
                )

                # ✔ Create new reject lot
                reject_lot = self.env['stock.lot'].sudo().create({
                    'product_id': product.id,
                    'lot_type': 'm_reject',
                })

                # ✔ Add rejected quantity to the new reject lot
                self.env['stock.quant']._update_available_quantity(
                    product, location, self.how_many_qty_rejected,
                    lot_id=reject_lot
                )
                reject_rework_lot = self.env['reject.rework.lot'].create({
                    'product_id': incoming.product_id.product_variant_id.id,
                    'lot_id': reject_lot.id,
                    'quantity': self.how_many_qty_rejected,
                    'confirm_qty': self.how_many_qty_rejected,
                    'reason': self.reject_remarks,
                    'state': 'done',
                    'supplier_id': incoming.partner_id.id,
                    'process_name': 'Income Inspection',
                    'lot_type': 'm_reject',
                    'reject_entry_type': 'iqc_raw',
                })
        print('======344==============split_lot', reject_lot, reject_lot.product_qty, incoming.lot_id, incoming.lot_id.product_qty)
        print('====================split_lot', reject_lot)


    # def create_reject_rework(self, reject_lot, product_id):
    #     lot_vals = {
    #         'name': 'New',
    #         'lot_id': reject_lot.id,
    #         'product_id': product_id.id,
    #         'quantity': self.how_many_qty_rejected,
    #         'state': 'done',
    #         'reason': reason,
    #         'workcenter_id': workcenter_id,
    #         'customer_id': backorder_mo.job_id.partner_id.id,
    #         'job_id': backorder_mo.job_id.id,
    #         'mo_id': backorder_mo.id,
    #         'operation_no': backorder_mo.part_operation_line_id.operation_code,
    #     }
    #     lot_entry = self.env['reject.rework.lot'].create(lot_vals)
