/** @odoo-module **/

// Disable no-alert rule for the lines where confirm is used
/* eslint-disable no-alert */
import {FormController} from "@web/views/form/form_controller";
import {ListController} from "@web/views/list/list_controller";
import {useRef} from "@odoo/owl";
import {useSetupView} from "@web/views/view_hook";

const oldSetup = FormController.prototype.setup;
const oldonPagerUpdated = FormController.prototype.onPagerUpdate;

const Formsetup = function () {
    this.rootRef = useRef("root");
    useSetupView({
        beforeLeave: () => {
            if (this.model.root.dirty) {
                if (confirm("Do you want to save changes Automatically?")) {
                    return this.model.root.save({
                        reload: false,
                        onError: this.onSaveError.bind(this),
                    });
                }
                this.model.root.discard();
                return true;
            }
        },
    });
    const result = oldSetup.apply(this, arguments);
    return result;
};
FormController.prototype.setup = Formsetup;

const onPagerUpdate = async function () {
    const dirty = await this.model.root.isDirty();
    if (dirty) {
        if (confirm("Do you want to save changes Automatically?")) {
            return oldonPagerUpdated.apply(this, arguments);
        }
        this.model.root.discard();
    }
    return oldonPagerUpdated.apply(this, arguments);
};

// Assign setup to FormController

FormController.prototype.onPagerUpdate = onPagerUpdate;

const ListSuper = ListController.prototype.setup;
const Listsetup = function () {
    useSetupView({
        rootRef: this.rootRef,
        beforeLeave: () => {
            const list = this.model.root;
            const editedRecord = list.editedRecord;
            if (editedRecord && editedRecord.isDirty) {
                if (confirm("Do you want to save changes Automatically?")) {
                    if (!list.unselectRecord(true)) {
                        throw new Error("View can't be saved");
                    }
                } else {
                    this.onClickDiscard();
                    return true;
                }
            }
        },
    });
    const result = ListSuper.apply(this, arguments);
    return result;
};
ListController.prototype.setup = Listsetup;
