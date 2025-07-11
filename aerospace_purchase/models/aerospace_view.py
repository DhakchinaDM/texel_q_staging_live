from odoo import fields, models, api, _

class PurchaseInheritAreo(models.Model):
    _inherit = 'purchase.order'

    purchase_aerospace_ids =fields.One2many('purchase.aerospace','aerospace_id',string="Purchase Aerospace")
    terms_and_conditin = fields.Html(string="")
    purchase_catogery = fields.Selection([
        ('aerospace', 'Aerospace'), ('automotive', 'Automotive'), ], string="Catogery Type", default='automotive')

class PurchaseAreospace(models.Model):
    _name = 'purchase.aerospace'
    _description = 'Purchase Aerospace'

    aerospace_id = fields.Many2one('purchase.order',string="connectivity to PO")
    name = fields.Char(string="Areospace")
    partid = fields.Char(string="PART ID")
    part_drw_no = fields.Char(string="PART DRW NO")
    rev_no = fields.Integer(string="Rev NO")    
    part_name = fields.Char(string="PART NAME")
    material_spec = fields.Char(string="Material spec")
    process = fields.Char(string="Process")
    document_ref = fields.Char(string="Document Ref")
    qty = fields.Float(string="QTY")
    units = fields.Many2one('uom.uom',string="UNITS")
    unit_prce = fields.Float(string="UNITS PRICE")
    line_total = fields.Float(string="LINE TOTAL",compute="_compute_line_total")
    tax = fields.Many2one('account.tax',string="Taxes")
    tax_val = fields.Float(string="Tax Value",compute="_compute_tax_value", store=True)


    @api.depends('line_total', 'tax')
    def _compute_tax_value(self):
        for rec in self:
            if rec.tax:
                tax_percentage = rec.tax.amount / 100  
                rec.tax_val = rec.line_total * tax_percentage
                rec.line_total = rec.line_total + rec.tax_val
            else:
                rec.tax_val = 0.0 

    @api.depends('qty', 'unit_prce')
    def _compute_line_total(self):
        for i in self:
            total = i.unit_prce * i.qty
            i.line_total = total

    
    
