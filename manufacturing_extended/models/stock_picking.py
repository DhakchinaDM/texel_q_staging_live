from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    part_operation_line_id = fields.Many2one('part.operation.line', string='Part Operation Line')
    part_operation_line_ids = fields.Many2many('part.operation.line', string='Part Operation Line ', store=True)

    job_id = fields.Many2one('job.planning', string='Job', related='part_operation_line_id.job_id', store=True)

    def create_return_job_work(self):
        new_picking = False
        for picking in self:
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

            if self.stock_return_type == 'return':
                if self.dc_entry_type == 'dc':
                    new_picking = self.env['stock.picking'].create({
                        'partner_id': picking.partner_id.id,
                        'picking_type_id': picking.picking_type_id.return_picking_type_id.id,
                        'origin': f"Return of {picking.name}",
                        'location_id': picking.picking_type_id.return_picking_type_id.default_location_src_id.id,
                        # reverse of outgoing
                        'location_dest_id': picking.picking_type_id.return_picking_type_id.default_location_dest_id.id,
                        'quality': picking.quality,
                        'return_id': picking.id,
                        'move_ids_without_package': [],
                    })
                    for move in picking.move_ids_without_package:
                        # return_product_id = self.env['product.template'].search([
                        #     ('raw_id', '=', move.product_id.product_tmpl_id.id),
                        # ], limit=1)
                        self.env['stock.move'].create({
                            'name': move.name,
                            'product_id': move.product_id.product_variant_id.id,
                            'product_uom_qty': move.product_uom_qty,
                            'product_uom': move.product_uom.id,
                            'picking_id': new_picking.id,
                            'location_id': new_picking.picking_type_id.default_location_src_id.id,
                            'location_dest_id': new_picking.picking_type_id.default_location_dest_id.id,
                        })
            if self.dc_entry_type == 'jw':
                new_picking = self.env['stock.picking'].create({
                    'partner_id': picking.partner_id.id,
                    'picking_type_id': picking.picking_type_id.return_picking_type_id.id,
                    'origin': f"Return of {picking.name}",
                    'location_id': picking.picking_type_id.return_picking_type_id.default_location_src_id.id,
                    # reverse of outgoing
                    'location_dest_id': picking.picking_type_id.return_picking_type_id.default_location_dest_id.id,
                    'quality': picking.quality,
                    'return_id': picking.id,
                    'move_ids_without_package': [],
                })

                # Create move lines
                for move in picking.move_ids_without_package:
                    return_product_id = self.env['product.template'].sudo().search([
                        ('raw_id', '=', move.product_id.product_tmpl_id.id),
                    ], limit=1)
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", return_product_id)
                    self.env['stock.move'].create({
                        'name': move.name,
                        'product_id': return_product_id.product_variant_id.id,
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
                if jw_ids:
                    for pick in jw_ids:
                        pick.write({
                            'return_job_work_id': new_picking.id
                        })
                else:
                    picking.write({
                        'return_job_work_id': new_picking.id
                    })
        return new_picking

    def button_validate(self):
        res = super().button_validate()

        # Define mappings for picking types and categories
        picking_category_map = {
            'stock.picking_type_in': 'manufacturing_extended.manufacturing_iqc',
            'delivery_challan.return_jw_operation': 'manufacturing_extended.manufacturing_iqc_part',
        }

        # Get the current picking type's external ID
        current_picking_type = self.picking_type_id
        for picking_ref, iqc_ref in picking_category_map.items():
            if current_picking_type.id == self.env.ref(picking_ref).id:
                for move in self.move_ids_without_package:
                    if picking_ref == 'delivery_challan.return_jw_operation' and \
                            move.product_id.categ_id.id == self.env.ref(
                        'inventory_extended.category_semi_finished_goods').id:
                        iqc_picking_type_id = self.env.ref(iqc_ref).id
                    else:
                        iqc_picking_type_id = self.env.ref(iqc_ref).id

                    bom_line = self.env['mrp.bom.line'].search([
                        ('product_id', '=', move.product_id.id)
                    ], limit=1)
                    print("Bom Line", bom_line)
                    if bom_line:
                        fg_product = bom_line.bom_id.product_tmpl_id.product_variant_id
                        print("@@@@@@@@2",fg_product)
                        iqc_mo = self.env['mrp.production'].create({
                            'product_id': fg_product.id,
                            'product_qty': move.product_uom_qty,
                            'picking_type_id': iqc_picking_type_id,
                            'origin': self.name,
                        })
                        iqc_mo.action_confirm()
                        iqc_mo.button_plan()
                break  # Exit the loop once the matching picking type is processed

        return res

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    @api.model
    def update_selected_lot(self, product_lot_data, production_id):
        print('Updating selected lots for Production:', production_id, product_lot_data)

        production = self.env['mrp.production'].browse(production_id)
        if not production:
            print("❌ Production Order not found!")
            return False

        for data in product_lot_data:
            product_id = data.get('product_id')
            lot_ids = data.get('lot_ids', [])

            if not lot_ids:
                continue  # Skip if no lots are selected

            # Get the `stock.move` for this product in the MO
            move = self.env['stock.move'].search([
                ('product_id', '=', product_id),
                ('raw_material_production_id', '=', production_id)
            ], limit=1)

            if not move:
                print(f"❌ No stock.move found for Product ID {product_id}")
                continue

            move_lines = self.env['stock.move.line'].search([
                ('product_id', '=', product_id),
                ('production_id', '=', production_id),
            ])

            move_count = len(move_lines)
            lot_count = len(lot_ids)
            print('-_________fff---------------------', move_lines, move_count, lot_count, move)

            print(f'Product ID: {product_id}, Move Lines: {move_count}, Lots: {lot_count}')

            if not move_lines:
                # No existing move lines, create new ones for all lot IDs
                for lot_id in lot_ids:
                    final_qty = min(move.product_uom_qty, lot_id['quantity'])
                    new_move_line = self.env['stock.move.line'].create({
                        'lot_id': lot_id['lot_id'],
                        'quantity': final_qty,  # Correct field for done quantity
                        'product_id': product_id,
                        'move_id': move.id,
                        'production_id': production_id,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'company_id': production.company_id.id,
                    })
                    print(f'✅ Created New11 Move Line {new_move_line.id} with Lot {lot_id}')

            elif move_count == lot_count:
                for move_line, lot_id in zip(move_lines, lot_ids):
                    final_qty = min(move.product_uom_qty, lot_id['quantity'])
                    move_line.write({'lot_id': lot_id['lot_id'], 'quantity': final_qty})

            elif move_count > lot_count:
                move_lines_to_remove = move_lines[lot_count:]
                move_lines_to_update = move_lines[:lot_count]

                move_lines_to_remove.unlink()
                print(f'❌ Removed {len(move_lines_to_remove)} extra move lines')

                for move_line, lot_id in zip(move_lines_to_update, lot_ids):
                    final_qty = min(move.product_uom_qty, lot_id['quantity'])
                    move_line.write({'lot_id': lot_id['lot_id'], 'quantity': final_qty})
                    print(f'🔄 Updated Move Line {move_line.id} with Lot {lot_id}')

            elif move_count < lot_count:
                for move_line, lot_id in zip(move_lines, lot_ids):
                    final_qty = min(move.product_uom_qty, lot_id['quantity'])
                    move_line.write({'lot_id': lot_id['lot_id'], 'quantity': final_qty})
                    print(f'🔄 Updated Move Line {move_line.id} with Lot {lot_id}')

                for lot_id in lot_ids[move_count:]:
                    final_qty = min(move.product_uom_qty, lot_id['quantity'])
                    new_move_line = self.env['stock.move.line'].create({
                        'lot_id': lot_id['lot_id'],
                        'quantity': final_qty,
                        'product_id': product_id,
                        'move_id': move.id,
                        'production_id': production_id,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'company_id': production.company_id.id,
                    })
                    print(f'✅ Created New Move Line {new_move_line.id} with Lot {lot_id}')
            production.write({
                'load_component': True,
                'lot_ids': [(6, 0, [lot['lot_id'] for lot in lot_ids])]
            })

        return True

    @api.model
    def revert_selected_lot(self, production_id):
        print('Reverting selected lots for Production:', production_id)

        # Fetch the production record
        production = self.env['mrp.production'].browse(production_id)
        if not production:
            print("❌ Production Order not found!")
            return False

        # Fetch and delete the stock.move.line records associated with the production
        move_lines = self.env['stock.move.line'].search([('production_id', '=', production_id)])
        if move_lines:
            move_lines.unlink()
            print(f'❌ Deleted {len(move_lines)} stock.move.line records')

        # Reset the fields in the production record
        production.write({
            'load_component': False,
            'lot_ids': [(5, 0, 0)],  # Clear the lot_ids field
        })
        print('✅ Reverted production fields to original state')

        return True


class StockMove(models.Model):
    _inherit = "stock.move"

    stored_lot_ids = fields.Many2many(
        'stock.lot', string="Stored Lots",
        help="Stores lot numbers before move is completed"
    )
    part_operation_id = fields.Many2one('part.operation', string='Part Operation',
                                        related='product_tmpl_id.part_operation', store=True)
    op_no = fields.Char(string='Operation No', related='part_operation_id.operation_code', store=True)
    operation_list_id = fields.Many2one('mrp.operation.list', string='Operation List',
                                        related='product_tmpl_id.operation_list_id', store=True)

    @api.depends('move_line_ids.lot_id')
    def store_lot_numbers(self):
        """ Store lot numbers before move is completed """
        for move in self:
            if move.move_line_ids:
                move.stored_lot_ids = [(6, 0, move.move_line_ids.mapped('lot_id').ids)]


class StockLot(models.Model):
    _inherit = 'stock.lot'

    job_work_check = fields.Boolean()
    final_inspection_check = fields.Boolean()
    customer_release_check = fields.Boolean()
    lot_type = fields.Selection([('ok', 'Ok'), ('m_reject', 'Material'), ('p_reject', 'Process'), ('rework', 'Rework')],
                                string='Lot Type', tracking=True)
    loading = fields.Boolean(string='Loading', tracking=True)


class MergeDC(models.Model):
    _inherit = 'merge.dc'

    def create_r_dc(self):
        balance_qty = False
        StockPicking = self.env['stock.picking']
        StockMove = self.env['stock.move']

        if not self.merge_order_ids:
            raise UserError(_("No product lines found to process."))

        first_picking = self.picking_ids[0]
        partner = first_picking.partner_id
        picking_type_id = first_picking.picking_type_id.id
        location_dest_id = first_picking.location_dest_id.id
        location_id = first_picking.location_id.id

        # Create Received Picking Entry
        received_picking = StockPicking.create({
            'partner_id': partner.id,
            'picking_type_id': picking_type_id,
            'quality': first_picking.quality,
            'location_id': location_id,
            'ins_type': 'incoming_part',
            'location_dest_id': location_dest_id,
            'origin': ', '.join(self.picking_ids.mapped('name')),
            'move_ids_without_package': []
        })

        # Prepare balance picking data
        original_product_quantities = {}  # Store original picking quantities
        selected_product_quantities = {}  # Store received quantities from popup

        for picking in self.picking_ids:
            if picking.part_operation_line_id:
                received_picking.write({
                    'part_operation_line_ids': [(4, picking.part_operation_line_id.id)],
                })

            for move in picking.move_ids_without_package:
                product = move.product_id
                if product in original_product_quantities:
                    original_product_quantities[product] += move.product_uom_qty
                else:
                    original_product_quantities[product] = move.product_uom_qty

        from collections import defaultdict

        product_lines = defaultdict(list)
        for line in self.merge_order_ids:
            if line.confirm_qty > 0:
                product_lines[line.product_id].append(line)

        # Loop through each product group
        for product, lines in product_lines.items():
            total_received_qty = sum(line.confirm_qty for line in lines)
            return_product_id = self.env['product.template'].search([
                ('raw_id', '=', product.id),
            ], limit=1)

            # Create one stock move per product
            move = StockMove.create({
                'picking_id': received_picking.id,
                'name': "Merge DC",
                'product_id': return_product_id.product_variant_id.id,
                'product_uom_qty': total_received_qty,
                'product_uom': product.uom_id.id,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
            })

            # Store total received quantity
            selected_product_quantities[product] = total_received_qty

            # Collect all lot lines from all merge_order_ids
            for line in lines:
                confirm_qty = line.confirm_qty
                for lot_line in line.lot_ids:
                    if confirm_qty <= 0:
                        break
                    lot_confirm_qty = min(confirm_qty, lot_line.product_qty)
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'picking_id': received_picking.id,
                        'product_id': return_product_id.product_variant_id.id,
                        'product_uom_id': product.uom_id.id,
                        'quantity': lot_confirm_qty,
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'lot_id': lot_line.id,
                    })
                    confirm_qty -= lot_confirm_qty

        # Prepare balance picking moves
        balance_moves = []
        for product, original_qty in original_product_quantities.items():
            received_qty = selected_product_quantities.get(product, 0)
            balance_qty = original_qty - received_qty
            return_product_id = self.env['product.template'].search([
                ('raw_id', '=', product.id),
            ], limit=1)

            if balance_qty > 0:
                balance_moves.append({
                    'product_id': return_product_id.product_variant_id.id,
                    'product_uom_qty': balance_qty,
                    'name': "Balance DC",
                    'product_uom': product.uom_id.id,
                    'location_id': location_id,
                    'location_dest_id': location_dest_id,
                })

        # Create balance picking if needed
        balance_picking = None
        if balance_moves:
            balance_picking = StockPicking.create({
                'partner_id': partner.id,
                'ins_type': 'incoming_part',
                'quality': first_picking.quality,
                'picking_type_id': picking_type_id,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'origin': ', '.join(self.picking_ids.mapped('name')),
                'move_ids_without_package': []
            })

            for move_vals in balance_moves:
                move_vals['picking_id'] = balance_picking.id
                move = StockMove.create(move_vals)

                product = self.env['product.product'].browse(move_vals['product_id'])
                # Find lines in merge_order_ids matching the product
                lines = self.merge_order_ids.filtered(
                    lambda l: l.product_id.id == product.id and l.product_qty > l.confirm_qty)

                remaining_balance_qty = move_vals['product_uom_qty']
                for line in lines:
                    balance_qty = line.product_qty - line.confirm_qty
                    for lot in line.lot_ids:
                        if balance_qty <= 0:
                            break
                        lot_balance_qty = min(balance_qty, lot.product_qty)
                        if lot_balance_qty > 0:
                            self.env['stock.move.line'].create({
                                'move_id': move.id,
                                'picking_id': balance_picking.id,
                                'product_id': product.id,
                                'product_uom_id': product.uom_id.id,
                                'quantity': lot_balance_qty,
                                'location_id': location_id,
                                'location_dest_id': location_dest_id,
                                'lot_id': lot.id,
                            })
                            balance_qty -= lot_balance_qty

        # Confirm pickings
        received_picking.action_confirm()
        # received_picking.button_validate()
        received_picking.write({
            'job_work_status': 'send',
        })
        if balance_picking:
            balance_picking.action_confirm()

        # Cancel original pickings
        for picking in self.picking_ids:
            picking.action_cancel()
            picking.write({
                'job_work_id': received_picking.id,
                'job_work_status': 'send' if picking.picking_type_code == 'outgoing' else 'completed',
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': received_picking.id,
            'target': 'current',
        }
