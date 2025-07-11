from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    purchase_terms = fields.Html(
        string="Default Purchase Terms and Conditions", translate=True, store=True
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    use_purchase_terms = fields.Boolean(
        default=False,
        readonly=False,
        config_parameter="rich-text-editor-for-term-condition.use_purchase_terms",
    )
    purchase_terms = fields.Html(
        related="company_id.purchase_terms",
        string="Purchase Terms & Conditions",
        readonly=False,
    )


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model
    def _default_note(self):
        return (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("rich-text-editor-for-term-condition.use_purchase_terms")
                and self.env.company.purchase_terms
                or ""
        )

    notes = fields.Html("Terms and conditions", default=_default_note)
