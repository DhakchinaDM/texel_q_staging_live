from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api, _


class FinalInspection(models.Model):
    _inherit = 'final.inspection'

    part_operation_line_id = fields.Many2one('part.operation.line', string='Part Operation')
    lot_ids = fields.Many2many('stock.lot', string='Lot No')
    mo_id = fields.Many2one('mrp.production', string='Manufacturing Order')
    job_id = fields.Many2one('job.planning', string='Job ID', related='part_operation_line_id.job_id', store=True)

    def action_approval(self):
        res = super().action_approval()
        # self.part_operation_line_id.write({
        #     'lot_ids': [(6, 0, self.lot_ids.ids)],
        # })
        self.create_final_mo()
        return res

    def create_final_mo(self):
        self.ensure_one()
        if not self.product_id:
            raise UserError(_('Please select a product before creating a MO.'))
        if not self.qty or self.qty <= 0:
            raise UserError(_('Please enter a valid quantity for the MO.'))

        mo_vals = {
            'product_id': self.job_id.part_no.product_variant_id.id,
            'product_qty': self.qty,
            'product_uom_id': self.product_id.uom_id.id,
            'state': 'draft',
        }
        mo = self.env['mrp.production'].create(mo_vals)
        print('MO Created++++++++++++++++++++++++++++++++++++++++++++=:', mo.id)

        # Confirm MO to generate stock moves
        mo.action_confirm()

        lot_index = 0
        for move in mo.move_raw_ids:
            move_lines = move.move_line_ids
            if not move_lines:
                # Create a move line if not already present
                if self.lot_ids and lot_index < len(self.lot_ids):
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'product_id': move.product_id.id,
                        'product_uom_id': move.product_uom.id,
                        'quantity': move.product_uom_qty,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'lot_id': self.lot_ids[lot_index].id,
                    })
                    lot_index += 1
                else:
                    raise UserError(_('Not enough lot numbers provided for the components.'))
            else:
                # Update existing move lines with lot numbers
                for move_line in move_lines:
                    if self.lot_ids and lot_index < len(self.lot_ids):
                        move_line.lot_id = self.lot_ids[lot_index].id
                        lot_index += 1
                    else:
                        raise UserError(_('Not enough lot numbers provided for the components.'))

        # Mark MO as done
        mo.button_mark_done()
        mo.create_productivity_line(False)
        self.part_operation_line_id.write({
            'lot_ids': [(6, 0, [mo.lot_producing_id.id])],
        })



class CustomerRelease(models.Model):
    _inherit = 'customer.release'

    part_operation_line_id = fields.Many2one('part.operation.line', string='Part Operation')

    lot_ids = fields.Many2many('stock.lot', string='Lot No')





