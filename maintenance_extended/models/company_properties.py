from datetime import date
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError


class CompanyProperties(models.Model):
    _name = 'company.properties'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Company Properties'

    name = fields.Char("Name")
    asset_no = fields.Char("Asset Number")
    image = fields.Binary("Image")
    company_id = fields.Many2one('res.company', 'Company', index=True)

    location = fields.Char("Location", tracking=True)
    user = fields.Many2one('res.users', "User", tracking=True)
    purchase_date = fields.Date("Purchase Date", tracking=True)
    price = fields.Float("Price", tracking=True)
    notes = fields.Char("Notes", tracking=True)
    system_model = fields.Char("System Model",tracking=True)
    cpu = fields.Char("CPU",tracking=True)
    ram = fields.Char("RAM",tracking=True)
    status = fields.Selection(
        [('1', 'Working'),
         ('2', 'Non-Working'),
         ('3', 'Scrap'),
         ], 'Status', tracking=True)
    account_status = fields.Selection(
        [('1', 'Deprecation'),
         ('2', 'In-Deprecation'),
         ('3', 'Scrap'),
         ], 'Account Status', tracking=True)
    memory_type =  fields.Char('Memory Type', tracking=True)
    properties_type =  fields.Selection(
        [('1', 'Computer ,Laptop & Accessories'),
         ('2', 'Electrical Items'),
         ('3', 'Plant & Machinery'),
         ('4', 'Furniture & Fittings'),
         ('5', 'Intangible Assets'),
         ('6', 'Office Equipments'),
         ('7', 'Factory Shed Improvement'),
         ('8', 'Vechile'),
         ], 'Properties Type',default="1", tracking=True)
    os = fields.Char("Operating System",tracking=True)
    graphics_card = fields.Char("Graphics Card",tracking=True)
    other_hardware = fields.Char("Other Hardware",tracking=True)

    os_licence = fields.Char("OS License",tracking=True)
    product_id = fields.Char("Product Id",tracking=True)
    licence_key = fields.Char("License Key",tracking=True)
    software = fields.Char("Software",tracking=True)
    software_id = fields.Char("Software ID",tracking=True)
    software_key = fields.Char("Software Key",tracking=True)
    anti_virus = fields.Char("Anti-virus",tracking=True)
    ip_address =  fields.Selection(
        [('static', 'Static'),
         ('dynamic', 'Dynamic'),
         ], 'Ip Address', tracking=True)
    mac_address = fields.Char("Mac-Address",tracking=True)
    network_type =  fields.Selection(
        [('wired', 'Wired'),
         ('wireless', 'Wireless'),
         ], 'Network Type', tracking=True)
    warranty_info = fields.Char("Warranty Information",tracking=True)
    maintenance_schedule = fields.Char("Maintenance Schedule",tracking=True)
    properties_ids = fields.One2many('company.properties.line','properties_id',string="Line")

    def scrap_state(self):
        for i in self:
            i.status = '3'
            i.account_status = '3'
    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            values['asset_no'] = self.sudo().env['ir.sequence'].next_by_code('properties.seq') or '/'
        res = super(CompanyProperties, self).create(values_list)
        return res







class CompanyPropertiesLine(models.Model):
    _name = 'company.properties.line'
    _description = 'Company Properties Line'

    date = fields.Date("Date")
    description = fields.Char("Description")
    price = fields.Float("Price")
    qty = fields.Integer("Quantity")
    remarks = fields.Char("Remarks")
    properties_id = fields.Many2one('company.properties')
