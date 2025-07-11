from odoo import fields, models, api, _
from datetime import date
from datetime import date, timedelta
from odoo.exceptions import ValidationError


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"
    _rec_name = 'name'

    mobile = fields.Char(string="Mobile")
    image = fields.Binary(string="Image")
    equipment_checklist_ids = fields.One2many('check.details', 'check_id')
    date = fields.Date(default=fields.Date.today(), readonly=True)
    last_maintenance_date = fields.Date(string='Last Maintenance Date')
    codefor = fields.Char(compute="_compute_vehicle_name", string="Equipment Id")
    Equipmentcode = fields.Char(string='Equipment Code', required=True, copy=False, readonly=True,
                                default=lambda self: _('New'))
    newmachine = fields.Selection([('new', 'New Machinery'), ('existing', 'Existing Machinery')], string="Machine Type",
                                  default='new')
    production_selection = fields.Selection([('production', 'Production'), ('non', 'Non-Production')],
                                            string="Production Type",
                                            default='production')
    subcategory_id = fields.Many2one('subcate.details', string="Sub Category", required=True,
                                     domain="[('category_id', '=', category_id)]", )
    equipment_assign_to = fields.Selection([
        ('department', 'Department'),
        ('employee', 'Employee'),
        ('other', 'Other')
    ], string='Used By', required=True, default='employee',
        ondelete={'employee': 'set default', 'common': 'set default'})
    machine_category = fields.Selection([('machinary', 'Machinary '), ('equipment', 'Equipment')],
                                        string="Maintenance Category", default='machinary')
    newmequipment = fields.Selection([('new', ' New Equipment'), ('existing', 'Existing Equipment')],
                                     string=" Machine Type", default='new')
    # internal_maintenace_count = fields.Integer(compute='_compute_internal_maintenace_count',
    #                                            string='Internal Maintenance',
    #                                            default=0)
    external_maintenace_count = fields.Integer(compute='_compute_external_maintenace_count',
                                               string='External Maintenance',
                                               default=0)

    equipment_history_ids = fields.One2many('maintenance.equipment.history', 'equipment_id')
    external_equipment_history_ids = fields.One2many('maintenance.equipment.history.external', 'external_equipment_id')
    spare_ids = fields.One2many('spare.details', 'machine_id', string='Spare Ids')
    pmc_ids = fields.One2many('preventive.maintenance.check', 'machine_id', string='Preventive Maintenance Check')
    machine_history_ids = fields.One2many('machine.history', 'machine_id', string='Machine History')
    cm_ids = fields.One2many('corrective.maintenance', 'machine_id', string='CMC ')
    amc_start_date = fields.Date(string='AMC Start Date')
    amc_end_date = fields.Date(string='AMC End Date')
    amc_supplier = fields.Char(string='AMC Supplier')
    amc_attachment = fields.Binary(string='AMC Attachment')
    machine_type_mc = fields.Char(string='MC Type')
    machine_type_mc_id = fields.Many2one('mc.type', string='MC Types')

    @api.constrains('spare_ids')
    def _check_unique_machine_spare(self):
        for record in self:
            product_ids = [line.product_id.id for line in record.spare_ids if line.product_id]
            if len(product_ids) != len(set(product_ids)):
                raise ValidationError(_("Each Spare must have a unique product. Duplicate products are not allowed."))

    def create_mrp_workcenter(self):
        Equipment = self.env['maintenance.equipment']
        Workcenter = self.env['mrp.workcenter']

        # Get all equipment and existing workcenter names
        all_equipment = Equipment.search([])
        existing_workcenters = Workcenter.search([])

        # Use a set for quick lookups
        existing_names = set(existing_workcenters.mapped('name'))

        for equipment in all_equipment:
            if equipment.name not in existing_names:
                if equipment.production_selection == 'production':
                    # Create new workcenter if not already present
                    workcenter = Workcenter.create({
                        'name': equipment.name,
                        'equipment_ids': [(4, equipment.id)],
                    })
                    equipment.workcenter_id = workcenter.id
                    existing_names.add(equipment.name)  # Update the set
            else:
                # Optionally link existing workcenter to equipment
                if equipment.production_selection == 'production':
                    matched_wc = existing_workcenters.filtered(lambda wc: wc.name == equipment.name)
                    if matched_wc:
                        equipment.workcenter_id = matched_wc[0].id

    def send_amc_mail(self):
        today_plus_ten = date.today() + timedelta(days=10)
        records = self.env['maintenance.equipment'].search(
            [('amc_end_date', '=', today_plus_ten)])
        if records:
            pmc_ids = records.mapped('name')
            if pmc_ids:
                pmc = ', '.join(pmc_ids)
                body = f"""
                    Dear Maintenance Team,<br/><br/>
                    The following Machines' AMC is expiring on {today_plus_ten}:<br/><br/>
                    {pmc}<br/><br/>
                    Please take the necessary action to renew the AMC contracts.<br/><br/>
                    Regards,<br/>
                    Administrator<br/><br/>
                    <p align="center">
                    ----------------------------------This is a system-generated email----------------------------------------------</p>
                """
                mail_value = {
                    'subject': 'Machines AMC Expiring Soon',
                    'body_html': body,
                    'email_cc': "",
                    'email_to': "",
                    'email_from': "",
                }
                mail = self.env['mail.mail'].create(mail_value)
                mail.send()

    # def send_amc_mail(self):
    #     today_plus_ten = date.today() + timedelta(days=10)
    #     records = self.env['maintenance.equipment'].search(
    #         [('amc_end_date', '=', today_plus_ten)])
    #     for record in records:
    #         pass

    @api.depends('serial_no')
    def _compute_display_name(self):
        for record in self:
            if record.serial_no:
                record.display_name = record.name
            else:
                record.display_name = record.name

    @api.model
    def default_get(self, fields):
        result = super(MaintenanceEquipment, self).default_get(fields)
        result.update({'pmc_ids': [(0, 0, {
            'preventive_maintenance_type': 'quarterly'}), (0, 0, {
            'preventive_maintenance_type': 'semi_annually'}), (0, 0, {
            'preventive_maintenance_type': 'annually'})]})
        return result

    # def _compute_internal_maintenace_count(self):
    #     self.internal_maintenace_count = self.env['material.requisition.indent'].sudo().search_count(
    #         [('equipment_name', '=', self.name)])

    def _compute_external_maintenace_count(self):
        self.external_maintenace_count = self.env['service.request'].sudo().search_count(
            [('equip_name', '=', self.name)])

    #
    # def internal_maintenance_list(self):
    #     self.sudo().ensure_one()
    #     form_view = self.sudo().env.ref('material_requisition.view_stock_indent_indent_form')
    #     tree_view = self.sudo().env.ref('material_requisition.view_indent_indent_tree')
    #     return {
    #         'name': _('Internal Maintenance List'),
    #         'res_model': 'material.requisition.indent',
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'tree,form',
    #         'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
    #         'domain': [('equipment_name', '=', self.name)],
    #     }

    def external_maintenance_list(self):
        self.sudo().ensure_one()
        form_view = self.sudo().env.ref('maintenance_extended.service_request11')
        tree_view = self.sudo().env.ref('maintenance_extended.view_service_tree1')
        return {
            'name': _('External Maintenance List'),
            'res_model': 'service.request',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('equip_name', '=', self.name)],
        }

    @api.onchange('subcategory_id')
    def onchange_category_id(self):
        if self.subcategory_id:
            if self.subcategory_id.image:
                self.image = self.subcategory_id.image

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            if 'name' in val:
                if val['production_selection'] == 'production':
                    workcenter = self.env['mrp.workcenter'].create({
                        'name': val['name']
                    })
                    val['workcenter_id'] = workcenter.id
                val['Equipmentcode'] = self.sudo().env['ir.sequence'].next_by_code('equipment.code') or '/'
        return super().create(vals_list)

    def _compute_vehicle_name(self):
        for record in self:
            record.codefor = record.Equipmentcode if record.Equipmentcode else 'New'


class MaintenanceEquipmentHistory(models.Model):
    _name = "maintenance.equipment.history"
    _description = "Maintenance Equipment History"
    _rec_name = 'maintenance_request_code'

    equipment_id = fields.Many2one('maintenance.equipment', string='Equipment_id')
    maintenance_team_id = fields.Many2one('maintenance.team', string='Maintenance Team')
    maintenance_request_name = fields.Many2one('maintenance.request', string='Name')
    maintenance_request_code = fields.Char(string='Number')
    maintenance_duration = fields.Char(string=' Number')
    maintenance_request_ref = fields.Char(string='Reference')
    maintenance_end_date = fields.Date(string='Service Date')
    maintenance_type = fields.Selection([
        ('corrective', 'BreakDown'),
        ('preventive', 'Preventive'),
    ], string="Maintenance Type")
    request_created_by = fields.Many2one('hr.employee', string='Created By')
    request_responsible = fields.Many2one('hr.employee', string='Responsible')


class MaintenanceEquipmentHistoryExternal(models.Model):
    _name = "maintenance.equipment.history.external"
    _description = "Maintenance Equipment History External"

    external_equipment_id = fields.Many2one('maintenance.equipment', string='Equipment_id')

    maintenance_team_id = fields.Many2one('maintenance.team', string='Maintenance Team')
    maintenance_request_code = fields.Many2one('service.request', string='Number')
    maintenance_request_name = fields.Char(string='Name')
    maintenance_request_ref = fields.Char(string='Reference')
    maintenance_end_date = fields.Datetime(string='Service Date')
    # maintenance_type = fields.Many2one('service.request', string="Service Type")
    maintenance_type = fields.Many2one('equipment.support.details', string="Service Type")
    request_by = fields.Char(string='Request BY')
    request_assigned_by = fields.Many2one('hr.employee', string='Assigned By')
    request_incharge = fields.Many2one('hr.employee', string='Service Takeover Incharge')
    request_manager = fields.Many2one('hr.employee', string='Manager')
    request_supplier_id = fields.Many2one('res.partner', string='Supplier')
    request_supplier = fields.Many2one('hr.employee', string=' Supplier')


class Checklist(models.Model):
    _name = 'check.details'
    _description = 'Check Details'

    check_id = fields.Many2one('maintenance.equipment', string="Equipment Name ")
