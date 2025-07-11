from odoo import models, fields, api, _
from odoo.tools.misc import unique
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, get_lang
from odoo.exceptions import AccessError, UserError, ValidationError



class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _description = "Product Template Forms"

    part_type = fields.Selection([('raw', 'Raw'), ('sfg', 'Semi Finish Goods'), ('fg', 'Finish Goods')],
                                 string="Part Type", default="raw",tracking=True)
    part_group = fields.Selection([('hv', 'High Volume'), ('lv', "Low Volume")], string="Part String", default='hv',tracking=True)
    part_status = fields.Selection([('production', 'Production'), ('service', "Service"), ('prototype', 'Prototype'),
                                    ('resale', 'Re Sale'), ('obsolete', 'Obsolete')], string="Part Status",
                                   default='production',tracking=True)
    grade = fields.Char(string="Grade",tracking=True)
    revision = fields.Text(string='Revision',tracking=True)
    revision_drawing = fields.Char(string='Part Drawing Revisions',tracking=True)
    min_stock_quan = fields.Float(string='Min Inv Quantity',tracking=True)
    max_stock_quan = fields.Float(string='Max Inv Quantity',tracking=True)
    cycle_frequency = fields.Selection(
        [('weekly', "Weekly"), ('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('semi_quar', 'Semi Quarterly'),
         ('annual', 'annually')],
        string="Cyclic Frequency",
        default='weekly',tracking=True)
    country_of_origin = fields.Many2one('res.country', string="Country Of Origin",tracking=True)
    symbol = fields.Many2one('res.currency', string='Special Symbol',tracking=True)
    building = fields.Many2one('stock.building', string="Main Building",tracking=True)
    piece_weight = fields.Float(string="Piece Weight",tracking=True)
    is_spare_bool = fields.Boolean(string='Is Spare', compute='_compute_spare', store=True)
    fg_bool = fields.Boolean(string='Is Finished Goods', compute='_compute_spare', store=True)
    make = fields.Char(string='Make',tracking=True)
    specification = fields.Char(string='Specification',tracking=True)
    sales_price = fields.Float(string='Sales Price USD' , digits=(16, 3),tracking=True)

    @api.depends('name', 'default_code')
    def _compute_display_name(self):
        for template in self:
            template.display_name = template.default_code if template.default_code else template.name

    @api.depends('categ_id')
    def _compute_spare(self):
        for record in self:
            record.is_spare_bool = True if record.categ_id.id == self.env.ref(
                'inventory_extended.category_maintenance').id else False
            record.fg_bool = True if record.categ_id.id == self.env.ref(
                'inventory_extended.category_finished_goods').id else False

    @api.onchange('default_code')
    def _onchange_default_code(self):
        if not self.default_code:
            return

        domain = [('default_code', '=', self.default_code)]
        if self.id.origin:
            domain.append(('id', '!=', self.id.origin))

        if self.env['product.template'].search(domain, limit=1):
            return {'warning': {
                'title': _("Note:"),
                'message': _("The Part No '%s' already exists.", self.default_code),
            }}

    @api.onchange('part_type')
    def onchange_part_type(self):
        if self.part_type == 'sfg' or self.part_type == 'fg':
            self.route_ids = [(5, 0, 0), (4, 1)]
        else:
            self.route_ids = [(5, 0, 0), (4, 5)]

    # @api.model_create_multi
    # def create(self, vals_list):
    #     res = super().create(vals_list)
    #     for vals in vals_list:
    #         if vals['categ_id']:
    #             category = self.env['product.category'].search([('id', '=', vals_list[0]['categ_id'])])
    #             if category.part_prefix and category.next_no:
    #                 ref_no = str(category.part_prefix) + str(category.next_no)
    #             else:
    #                 ref_no = False
    #             vals['default_code'] = ref_no
    #             res.default_code = ref_no
    #             category.write({
    #                 'next_no': category.next_no + 1,
    #             })
    #     return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for vals in vals_list:
            if vals['categ_id']:
                category = self.env['product.category'].search([('id', '=', vals['categ_id'])], limit=1)
                if category.part_prefix and category.next_no:
                    padded_next_no = str(category.next_no).zfill(category.sequence_size)
                    ref_no = f"{category.part_prefix}{padded_next_no}"
                # else:
                #     ref_no = False
                    vals['default_code'] = ref_no
                    res.default_code = ref_no
                    category.write({
                        'next_no': category.next_no + 1,
                    })
            else:
                raise UserError(_("The Product Category does not have a valid prefix or next number set."))
        return res


class Product(models.Model):
    _inherit = "product.product"

    @api.onchange('default_code')
    def _onchange_default_code(self):
        if not self.default_code:
            return

        domain = [('default_code', '=', self.default_code)]
        if self.id.origin:
            domain.append(('id', '!=', self.id.origin))

        if self.env['product.product'].search(domain, limit=1):
            return {'warning': {
                'title': _("Note:"),
                'message': _("The Part No '%s' already exists.", self.default_code),
            }}

    @api.depends('name', 'default_code', 'product_tmpl_id')
    @api.depends_context('display_default_code', 'seller_id', 'company_id', 'partner_id')
    def _compute_display_name(self):

        def get_display_name(name, code):
            if self._context.get('display_default_code', True) and code:
                return f'{code}'
            return name

        partner_id = self._context.get('partner_id')
        if partner_id:
            partner_ids = [partner_id, self.env['res.partner'].browse(partner_id).commercial_partner_id.id]
        else:
            partner_ids = []
        company_id = self.env.context.get('company_id')

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access_rights("read")
        self.check_access_rule("read")

        product_template_ids = self.sudo().product_tmpl_id.ids

        if partner_ids:
            # prefetch the fields used by the `display_name`
            supplier_info = self.env['product.supplierinfo'].sudo().search_fetch(
                [('product_tmpl_id', 'in', product_template_ids), ('partner_id', 'in', partner_ids)],
                ['product_tmpl_id', 'product_id', 'company_id', 'product_name', 'product_code'],
            )
            supplier_info_by_template = {}
            for r in supplier_info:
                supplier_info_by_template.setdefault(r.product_tmpl_id, []).append(r)

        for product in self.sudo():
            variant = product.product_template_attribute_value_ids._get_combination_name()

            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = self.env['product.supplierinfo'].sudo().browse(self.env.context.get('seller_id')) or []
            if not sellers and partner_ids:
                product_supplier_info = supplier_info_by_template.get(product.product_tmpl_id, [])
                sellers = [x for x in product_supplier_info if x.product_id and x.product_id == product]
                if not sellers:
                    sellers = [x for x in product_supplier_info if not x.product_id]
                # Filter out sellers based on the company. This is done afterwards for a better
                # code readability. At this point, only a few sellers should remain, so it should
                # not be a performance issue.
                if company_id:
                    sellers = [x for x in sellers if x.company_id.id in [company_id, False]]
            if sellers:
                temp = []
                for s in sellers:
                    seller_variant = s.product_name and (
                            variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                    ) or False
                    temp.append(get_display_name(seller_variant or name, s.product_code or product.default_code))

                # => Feature drop here, one record can only have one display_name now, instead separate with `,`
                # Remove this comment
                product.display_name = ", ".join(unique(temp))
            else:
                product.display_name = get_display_name(name, product.default_code)


class StockBuilding(models.Model):
    _name = 'stock.building'
    _description = "Stock Building"

    name = fields.Char(string="Name")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    bill_ref = fields.Char(string='Bill Ref')


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _product_id_change(self):
        if not self.product_id:
            return

        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        product_lang = self.product_id.with_context(
            lang=get_lang(self.env, self.partner_id.lang).code,
            partner_id=self.partner_id.id,
            company_id=self.company_id.id,
        )
        self.name = self.product_id.name

        self._compute_tax_id()


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    product_name = fields.Char(string='Part Name', related='product_id.name')


class ProductCategory(models.Model):
    _inherit = "product.category"

    part_prefix = fields.Char(string='Prefix', size=4)
    next_no = fields.Integer(string='Next Number')
    sequence_size = fields.Integer(string='Sequence Size', default=4)


# class MrpBom(models.Model):
#     _inherit = 'mrp.bom'
#
#     @api.model
#     def get_finished_goods(self):
#         fg_products = self.env.ref('inventory_extended.category_finished_goods').id
#         return [('categ_id', '=', fg_products), ('type', 'in', ['product', 'consu'])]
#
#     product_tmpl_id = fields.Many2one(
#         'product.template', 'Product',
#         check_company=True, index=True,
#         domain=lambda self: self.get_finished_goods(), required=True)


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    @api.model
    def get_finished_goods(self):
        fg_products = self.env.ref('inventory_extended.category_finished_goods').id
        return [('categ_id', '!=', fg_products)]

    product_id = fields.Many2one('product.product', 'Component', required=True, check_company=True, domain=lambda self: self.get_finished_goods())
