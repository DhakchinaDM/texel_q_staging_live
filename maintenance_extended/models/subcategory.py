from odoo import fields, models, api


class SubCategory(models.Model):
    _name = "subcate.details"
    _description = "Sub Category"

    @api.depends('equipment_ids')
    def _compute_fold(self):
        self.fold = False
        for category in self:
            category.fold = False if category.equipment_count else True

    name = fields.Char(string="Sub Category ", help='hi hell0')
    code = fields.Char(string="Code")
    category_id = fields.Many2one('maintenance.equipment.category', string="Category")
    image = fields.Image(string="Image")
    equipment_count = fields.Integer(string="Equipment", compute='_subcategory_count')
    equipment_ids = fields.One2many('maintenance.equipment', 'subcategory_id', string='Equipments', copy=False)

    def _subcategory_count(self):
        equipment_data = self.env['maintenance.equipment'].read_group([('subcategory_id', 'in', self.ids)],
                                                                      ['subcategory_id'], ['subcategory_id'])
        mapped_data = dict([(m['subcategory_id'][0], m['subcategory_id_count']) for m in equipment_data])
        for category in self:
            category.equipment_count = mapped_data.get(category.id, 0)

    def action_equipment_category(self):
        return {
            'name': 'Equipment',
            'view_mode': 'tree,form,kanban,graph',
            'domain': [('subcategory_id', '=', self.ids)],
            'res_model': 'maintenance.equipment',
            'type': 'ir.actions.act_window',
            'context': {'create': True, 'active_test': False},
        }
