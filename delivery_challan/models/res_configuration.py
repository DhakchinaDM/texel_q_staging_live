from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    picking_terms = fields.Html(
        string="Default Picking Terms and Conditions", translate=True, store=True
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    use_picking_terms = fields.Boolean(
        default=False,
        readonly=False,
        config_parameter="delivery_challan.use_picking_terms",
    )
    picking_terms = fields.Html(
        related="company_id.picking_terms",
        string="Picking Terms & Conditions",
        readonly=False,
    )
