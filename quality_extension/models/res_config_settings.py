from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    _description = 'Res Config Settings'

    approve_iqc = fields.Boolean(
        string="Approve IQC Without Parameters", help="Tick to enable Approve IQC Without Parameters",
        config_parameter="quality_extension.enable_auto_checkout")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update({
            'approve_iqc': self.env['ir.config_parameter'].sudo().get_param(
                'quality_extension.approve_iqc', default=False),
        })
        return res

    def set_values(self):
        self.env['ir.config_parameter'].sudo().set_param('quality_extension.approve_iqc', self.approve_iqc)
        super(ResConfigSettings, self).set_values()
