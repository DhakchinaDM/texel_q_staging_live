from email.policy import default

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class QualityParameters(models.Model):
    _name = 'quality.parameter'
    _description = 'Quality Parameters'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Name', tracking=True)
    observation_no_need = fields.Boolean(string='Observation No Need')

    # @api.constrains('name')
    # def _check_name(self):
    #     for record in self:
    #         if record.mobile:
    #             domain = [('name', '=', record.name)]
    #             codes = self.search(domain)
    #             if len(codes) > 1:
    #                 for code in codes:
    #                     if code.id != record.id:
    #                         raise ValidationError(
    #                             _('Alert! The Parameter already exists.'))


class QualityCheckMethod(models.Model):
    _name = 'quality.check.method'
    _description = 'Quality Check Method'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Name', tracking=True)

    # @api.constrains('name')
    # def _check_name(self):
    #     for record in self:
    #         if record.mobile:
    #             domain = [('name', '=', record.name)]
    #             codes = self.search(domain)
    #             if len(codes) > 1:
    #                 for code in codes:
    #                     if code.id != record.id:
    #                         raise ValidationError(
    #                             _('Alert! The Method of Check already exists.'))

