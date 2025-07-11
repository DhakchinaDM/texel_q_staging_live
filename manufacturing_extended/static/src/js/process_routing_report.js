/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
export class ProcessRoutingReport extends ListController {
   setup() {
       super.setup();
   }
   ProReport() {
       this.actionService.doAction({
          type: 'ir.actions.act_window',
          res_model: 'process.routing.wizard',
          name:'Reporting',
          view_mode: 'form',
          view_type: 'form',
          views: [[false, 'form']],
          target: 'new',
          res_id: false,
      });
   }
}
registry.category("views").add("button_process_routing_tree", {
   ...listView,
   Controller: ProcessRoutingReport,
   buttonTemplate: "process_routing.ListView.Buttons",
});