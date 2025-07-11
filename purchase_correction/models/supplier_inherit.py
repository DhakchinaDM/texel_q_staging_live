from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    @api.constrains('mobile')
    def _check_name(self):
        for record in self:
            if record.mobile:
                domain = [('mobile', '=', record.mobile)]
                codes = self.search(domain)
                if len(codes) > 1:
                    for code in codes:
                        if code.id != record.id:
                            raise ValidationError(
                                _('Alert! The Supplier already exists.'))
