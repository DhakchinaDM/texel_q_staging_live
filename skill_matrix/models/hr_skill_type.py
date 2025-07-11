from odoo import api, fields, models, tools, _


class HrSkillLevel(models.Model):
    _inherit = 'hr.skill.level'
    _description = 'Hr Skill Level'

    color = fields.Char(string='Color')
    description = fields.Char()
    level_id = fields.Many2one('matrix.skill.level', string='Level Master')
    level_image = fields.Binary(string="Image Level")


class HrSkillType(models.Model):
    _inherit = 'hr.skill.type'
    _description = 'Hr Skill Type'

    def generate_fg(self):
        if self.id == self.env.ref('skill_matrix.hr_skill_type2').id:

            existing_codes = self.skill_ids.mapped('code')
            finished_goods = self.env['product.template'].search(
                [('categ_id.id', '=', self.env.ref('inventory_extended.category_finished_goods').id)]
            )
            new_skills = [
                (0, 0, {
                    'code': product.default_code,
                    'name': product.name,
                })
                for product in finished_goods
                if product.default_code not in existing_codes
            ]
            if new_skills:
                self.write({'skill_ids': new_skills})

    @api.model
    def default_get(self, fields):
        result = super(HrSkillType, self).default_get(fields)
        line_val = []
        skills = self.env['matrix.skill.level'].search([])
        for i in skills:
            line = (0, 0, {
                'name': i.name,
                'level_id': i.id,
                'level_progress': i.progress,
                'description': i.description,
            })
            line_val.append(line)
        result.update({
            'skill_level_ids': line_val,
        })
        return result


class HrSkill(models.Model):
    _inherit = 'hr.skill'
    _description = 'Hr Skill'
    _rec_name = 'code'

    code = fields.Char()
