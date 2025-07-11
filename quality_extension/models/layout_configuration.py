from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class LayoutConfiguration(models.Model):
    _name = 'layout.configuration'
    _description = 'Layout Description'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'part_name'

    # name = fields.Char(compute='_compute_name', store=True)
    user_id = fields.Many2one('res.users', string='User Name', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    active = fields.Boolean(default=True)

    part_no = fields.Many2one('product.template', string='Part No.',
                              domain=lambda self: self._get_layout_product_domain())
    part_name = fields.Char(string='Part Name', related='part_no.name')

    layout_parameter_ids = fields.One2many('layout.parameter', 'layout_id')

    @api.constrains('part_no')
    def _check_name(self):
        for record in self:
            if record.part_no:
                domain = [('part_no', '=', record.part_no.id)]
                codes = self.search(domain)
                if len(codes) > 1:
                    for code in codes:
                        if code.id != record.id:
                            raise ValidationError(
                                _('Alert! The Part already exists for the Layout Configuration.'))

    @api.model
    def _get_layout_product_domain(self):
        finished_goods_category = self.env.ref('inventory_extended.category_finished_goods')
        return [('categ_id', '=', finished_goods_category.id)]


class LayoutParameter(models.Model):
    _name = 'layout.parameter'
    _description = 'Layout Parameter'

    layout_id = fields.Many2one('layout.configuration')
    sequence = fields.Char(string='Sequence')
    description = fields.Many2one('quality.parameter')
    spl = fields.Char(string='SPL')
    specification = fields.Html(string='Specification')
    minimum = fields.Float(string='Minimum')
    maximum = fields.Float(string='Maximum')
    method_of_check = fields.Many2one('quality.check.method')
    observation1 = fields.Float(string='Obs 1')
    observation2 = fields.Float(string='Obs 2')
    observation3 = fields.Float(string='Obs 3')
    observation4 = fields.Float(string='Obs 4')
    observation5 = fields.Float(string='Obs 5')
    remarks = fields.Text(string='Remarks')
    lyr_id = fields.Many2one('layout.inspection')
    invalid_min_max = fields.Boolean(compute='_invalid_min_max_value')
    baloon_no = fields.Char(string='Ball No')


    @api.constrains('minimum', 'maximum')
    def _invalid_min_max_value(self):
        for record in self:
            record.invalid_min_max = False
            if record.minimum > record.maximum:
                record.invalid_min_max = True
                raise ValidationError(_('Alert! Enter the Minimum and Maximum Level Properly.'))
