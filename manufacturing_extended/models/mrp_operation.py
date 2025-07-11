from odoo import api, fields, models, _


class MrpOperationList(models.Model):
    _name = "mrp.operation.list"
    _description = "MRP Operation List"

    name = fields.Char(string="Operation Name", required=True)
    operation_code = fields.Char(string="Operation Code", required=True)
    picking_type_id = fields.Many2one('stock.picking.type', string="Picking Type", required=True)