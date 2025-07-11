from odoo import fields, models, tools, api


class ProcessRouting(models.Model):
    _name = 'process.routing'
    _description = 'Process Routing'
    _rec_name = 'product_id'

    # INVISIBLE FIELDS START
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    logged_user = fields.Many2one('res.users', string='Logged User', compute='get_logged_user')
    active = fields.Boolean(default=True)
    # INVISIBLE FIELDS END

    product_id = fields.Many2one('product.template', string='Part No',
                                 domain=lambda self: self._get_finish_good_domain())

    product_name = fields.Char(string='Part Name', related='product_id.name')
    bom_id = fields.Many2one('mrp.bom', string='BOM', compute='get_bom')
    order_lines = fields.One2many('part.operation', 'routing_id', string='Part Operations')


    def set_process_routing(self):
        product_id = False
        last_operation_product = False  # Store the last operation's output product

        print('---------set_process_routing---------', self.order_lines)

        for part in self.order_lines:
            print('-------operation_type-----------', part.operation_type)
            if part.operation_type == 'internal':
                if part.production_op and not part.out_product_id:
                    # Ensure BOM lines exist
                    if not part.operation_bom_lines:
                        part.operation_bom_lines = [(0, 0, {
                            "product_id": product_id.id,  # ✅ Ensure valid ID
                            "quantity": 1,
                        })]
                    else:
                        for line in part.operation_bom_lines:
                            if line.product_id and line.quantity > 0:
                                product_id = line.product_id
                    workcenter = self.env['mrp.workcenter'].search([], limit=1)
                    print('________________------------------', workcenter)
                    part.raw_id = product_id.id

                    if part.operation_bom_lines:
                        if not part.shippable:
                            # Create new Semi-Finished Product
                            product_id = self.env['product.template'].sudo().create({
                                'name': f"{part.product_id.name} - {part.operation_code}",
                                'default_code': f"{part.product_id.default_code} - {part.operation_code}",
                                'categ_id': self.env.ref('inventory_extended.category_semi_finished_goods').id,
                                'detailed_type': 'product',
                                'route_ids': [(6, 0, [self.env.ref('mrp.route_warehouse0_manufacture').id])],
                                'tracking': 'lot',
                                'auto_create_lot': True,
                                'raw_id': part.raw_id.id,
                                'operation_list_id': part.operation_list_id.id,
                                'part_operation': part.id,
                            })
                            product_id.write({'default_code': f"{part.product_id.default_code} - {part.operation_code}"})
                            part.write({'out_product_id': product_id.id})

                            # Create BOM for the new product
                            bom_id = self.env['mrp.bom'].sudo().create({
                                'product_tmpl_id': part.out_product_id.id,
                                'product_qty': 1,
                                'bom_line_ids': [(0, 0, {
                                    'product_id': line.product_id.product_variant_id.id,
                                    'product_qty': line.quantity,
                                }) for line in part.operation_bom_lines if line.product_id and line.quantity > 0],
                                'operation_ids': [(0, 0, {
                                    'name': part.operation_description,
                                    'workcenter_id': workcenter.id,
                                })]
                            })
                            part.write({'bom_id': bom_id.id})
                            # Store the created operation in part.operation_id
                            if bom_id.operation_ids:
                                part.operation_id = bom_id.operation_ids[0].id
                        else:
                            part.write({'out_product_id': self.product_id.id})
                            part.out_product_id.write({
                                'raw_id': part.raw_id.id,
                                'operation_list_id': part.operation_list_id.id,
                                'part_operation': part.id,
                            })
                            fg_bom = self.env['mrp.bom'].sudo().create({
                                'product_tmpl_id': self.product_id.id,  # Finished Product
                                'product_qty': 1,
                                'bom_line_ids': [(0, 0, {
                                    'product_id': line.product_id.product_variant_id.id,
                                    'product_qty': line.quantity,
                                }) for line in part.operation_bom_lines if line.product_id and line.quantity > 0],
                                'operation_ids': [(0, 0, {
                                    'name': part.operation_description,
                                    'workcenter_id': workcenter.id,
                                })]
                            })
                            part.write({'bom_id': fg_bom.id})
                            if fg_bom.operation_ids:
                                part.operation_id = fg_bom.operation_ids[0].id
                elif not part.production_op and not part.out_product_id:
                    part.write({'out_product_id': product_id.id})
                    part.out_product_id.write({
                        # 'raw_id': product_id.id,
                        'operation_list_id': part.operation_list_id.id,
                        'part_operation': part.id,
                    })
                elif not part.production_op and part.out_product_id:
                    print('------------------', part.operation_list_id.id)
                    part.out_product_id.write({
                        'operation_list_id': part.operation_list_id.id,
                        'part_operation': part.id,
                    })

            else:
                part.write({'out_product_id': product_id.id})
                product_id = self.env['product.template'].sudo().create({
                    'name': f"{part.product_id.name} - {part.operation_code}",
                    'default_code': f"{part.product_id.default_code} - {part.operation_code}",
                    'categ_id': self.env.ref('inventory_extended.category_semi_finished_goods').id,
                    'detailed_type': 'product',
                    'route_ids': [(6, 0, [self.env.ref('mrp.route_warehouse0_manufacture').id])],
                    'tracking': 'lot',
                    'auto_create_lot': True,
                    'operation_list_id': part.operation_list_id.id,
                    'part_operation': part.id,
                    'raw_id': part.out_product_id.id,
                })
                product_id.write({'default_code': f"{part.product_id.default_code} - {part.operation_code}"})


    @api.model
    def _get_finish_good_domain(self):
        finished_goods_category = self.env.ref('inventory_extended.category_finished_goods')
        return [('categ_id', '=', finished_goods_category.id)]

    @api.depends('product_id')
    def get_bom(self):
        for rec in self:
            rec.bom_id = self.env['mrp.bom'].search([('product_tmpl_id', '=', rec.product_id.id)], limit=1)
