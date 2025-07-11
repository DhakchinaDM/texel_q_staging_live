///// /* @odoo-module */
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { _t } from "@web/core/l10n/translation";

export class SavePopup extends FormController {
    async save(params) {
        const { saveAndNew } = params || {};
        const result = await super.save({ saveAndNew });
        if (result && this.model.root.data.display_name) {
            const displayName = this.model.root.data.display_name;
            this.env.services['notification'].add(
                _t(`Your record ${displayName} has been saved!`),
                {
                    type: 'success',
                }
            );
        }
        return result;
    }
}

const formView = registry.category('views').get('form');
formView.Controller = SavePopup;
