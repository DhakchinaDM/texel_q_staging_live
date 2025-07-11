from datetime import date, timedelta
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _description = "Product Template Forms"

    material_grade = fields.Char(string="Material Grade", tracking=True)
    draw_rev_no = fields.Char(string="Drawing Rev No", tracking=True)
    draw_rev_date = fields.Date(string="Drawing Rev Date", tracking=True)
    attachment = fields.Binary(string="Drawing Attachment")
    file_name = fields.Char()
    third_party_certificate = fields.Date("Third Party Certificate", tracking=True)
    third_party_certificate_attach = fields.Binary("Attachment")

    quality_parameters = fields.One2many('quality.parameter.line', 'product_id', tracking=True)
    final_parameters = fields.One2many('final.parameter.line', 'final_product_id', tracking=True)
    parameter_type = fields.Selection([
        ('raw', 'Raw'),
        ('parts', 'Parts')
    ], string="Parameters", compute='_compute_category_check')

    @api.depends('categ_id')
    def _compute_category_check(self):
        for i in self:
            i.parameter_type = False
            if i.categ_id.id in [self.env.ref('inventory_extended.category_raw_materials').id,
                                 self.env.ref('inventory_extended.category_semi_finished_goods').id]:
                i.write({
                    'parameter_type': 'raw'
                })
            elif i.categ_id.id == self.env.ref('inventory_extended.category_finished_goods').id:
                i.write({
                    'parameter_type': 'parts'
                })

    @api.model
    def notify_certificate_expiry(self):
        today = fields.Date.today()
        ten_day_before = today + timedelta(days=10)
        user_to_notify = self.search([
            ('third_party_certificate', '=', ten_day_before)
        ])
        if user_to_notify:
            expiry_ids = user_to_notify.mapped('name')
            if expiry_ids:
                tem = ', '.join(expiry_ids)
            body = f"""
                      Dear Stock Team,<br/><br/>
                      This is a reminder that the certificate for<br/><br/>
                      <b>Part Name :</b> {tem}<br/><br/>
                     <b>Third Party Certificate Expiry Date :</b> {ten_day_before}<br/><br/>
                      Kindly review the status and take the necessary steps to renew it promptly.<br/>
                      Regards,<br/>
                      Administrator<br/><br/>
                      <p align="center">
                      ----------------------------------This is a system-generated email----------------------------------------------</p>
                       """
            mail_value = {
                'subject': 'Third Party Certificate Expiring Soon',
                'body_html': body,
                'email_cc': "",
                'email_to': "",
                'email_from': "",
            }
            mail = self.env['mail.mail'].create(mail_value)
            mail.send()


class QualityParametersLine(models.Model):
    _name = 'quality.parameter.line'
    _description = 'Quality Parameters Line'

    product_id = fields.Many2one('product.template', string='Product')
    parameter_id = fields.Many2one('quality.parameter', string='Parameter')
    check_method_id = fields.Many2many('quality.check.method', string='Method of Check')
    specification = fields.Char(string='Specification')
    min_level = fields.Float(string='Minimum')
    max_level = fields.Float(string='Maximum')
    baloon_no = fields.Char(string='Ball No')

    @api.constrains('min_level', 'max_level')
    def _compute_level(self):
        for rec in self:
            if rec.min_level > rec.max_level:
                raise ValidationError(_('Alert! Kindly Enter the Max. and Min. Level values Properly.'))


class FinalParametersLine(models.Model):
    _name = 'final.parameter.line'
    _description = 'Final Parameters Line'

    final_product_id = fields.Many2one('product.template', string='Product')
    sl_no = fields.Integer(string='Sl. No')
    balloon_no = fields.Char(string='Ball No')
    characteristics = fields.Many2one('quality.parameter', string='Characteristics')
    final_specification = fields.Char(string='Specification')
    min_final = fields.Float(string='Minimum', digits=(16, 3))
    max_final = fields.Float(string='Maximum', digits=(16, 3))
    check_method_final = fields.Many2one('quality.check.method', string='Method of Checking')
    final_obs1 = fields.Float(string='Obs 1')
    final_obs2 = fields.Float(string='Obs 2')
    final_obs3 = fields.Float(string='Obs 3')
    final_obs4 = fields.Float(string='Obs 4')
    final_obs5 = fields.Float(string='Obs 5')
    remarks = fields.Text(string='Remarks/Status')
    final_inspect = fields.Many2one('final.inspection')
    invalid_min_max = fields.Boolean(compute='_compute_invalid_min_max')

    @api.constrains('min_final', 'max_final')
    def _compute_invalid_min_max(self):
        for record in self:
            record.invalid_min_max = False
            if record.min_final > record.max_final:
                record.invalid_min_max = True
                raise ValidationError(_('Alert! Kindly enter the Maximum and Minimum Values Properly'))
