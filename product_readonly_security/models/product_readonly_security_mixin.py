from odoo import _, api, models
from odoo.exceptions import AccessError
from odoo.tools import config


class ProductReadonlySecurityMixin(models.AbstractModel):
    _name = "product.readonly.security.mixin"
    _description = "Mixin to use Product Readonly Security"

    # @api.model
    # def check_access_rights(self, operation, raise_exception=True):
    #     """Override security to restrict read, create, and edit operations if the group is ticked."""
    #     user = self.env.user
    #     group = "product_readonly_security.group_product_edition"
    #     test_condition = not config["test_enable"] or (
    #             config["test_enable"]
    #             and self.env.context.get("test_product_readonly_security"))
    #     group_ticked = user.has_group(group)
    #     if (test_condition
    #             and operation != "read"
    #             and not self.env.su
    #             and group_ticked
    #     ):
    #         if raise_exception:
    #             raise AccessError(
    #                 _(
    #                     "Sorry, you are not allowed to read, create, or edit parts. "
    #                     "Please contact your administrator for further information."
    #                 ))
    #         return False
    #     return super().check_access_rights(operation=operation, raise_exception=raise_exception)


    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        """Restrict delete operation if group is ticked."""
        user = self.env.user
        group = "product_readonly_security.group_product_edition"
        test_condition = not config["test_enable"] or (
                config["test_enable"]
                and self.env.context.get("test_product_readonly_security")
        )
        group_ticked = user.has_group(group)
        if (
                test_condition
                and operation == "unlink"  # only restrict delete
                and not self.env.su
                and group_ticked
        ):
            if raise_exception:
                raise AccessError(
                    _(
                        "Sorry, you are not allowed to delete records. "
                        "Please contact your administrator for further information."
                    )
                )
            return False
        return super().check_access_rights(operation=operation, raise_exception=raise_exception)
