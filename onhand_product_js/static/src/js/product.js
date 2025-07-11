/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class InventoryOnHandProductReport extends Component {
    static template = "on_hand_product_js.Odoo";

    setup() {
        this.rpc = useService("rpc");

        this.state = useState({
            products: [],
            selectedProductId: null,
            selectedLotType: '',
            routingLines: [],
            grandTotal: 0,
            operationCodes: [],
            selectedOperationCodes: [],
        });

        this.onProductChange = this.onProductChange.bind(this);
        this.onLotTypeChange = this.onLotTypeChange.bind(this);
        this.onOperationCodeChange = this.onOperationCodeChange.bind(this);
        this.searchRoutingByProduct = this.searchRoutingByProduct.bind(this);

        onMounted(() => {
            this.loadFGProducts();
            setTimeout(() => {
               $(".multi-select").select2({
                   placeholder: "Select Operation Codes",
                   allowClear: true,
                   width: '100%'
               });
           }, 100);
        });
    }

    async loadFGProducts() {
        const products = await this.rpc("/on_hand_product/fg_products", {});
        this.state.products = products;
    }

    onProductChange(event) {
        this.state.selectedProductId = parseInt(event.target.value);
        this.state.selectedOperationCodes = [];
        this.state.operationCodes = [];
        this.searchRoutingByProduct();
        this.loadOperationCodes();
    }

    onLotTypeChange(event) {
        this.state.selectedLotType = event.target.value;
        this.searchRoutingByProduct();
    }

   onOperationCodeChange(event) {
       const selected = $(".multi-select").val() || [];
       this.state.selectedOperationCodes = selected;
       console.log("Selected Operation Codes:", this.state.selectedOperationCodes);
       $(".multi-select").each((index, element) => {
            const selected = $(element).val() || [];
            this.state.selectedOperationCodes = selected;
       });

       console.log("Selected Operation Codes after search:", this.state.selectedOperationCodes);


   }

   onSearchClick(event){
       const selected = $(".multi-select").val() || [];
       this.state.selectedOperationCodes = selected;
       console.log("Selected Operation Codes:", this.state.selectedOperationCodes);
       $(".multi-select").each((index, element) => {
            const selected = $(element).val() || [];
            this.state.selectedOperationCodes = selected;
       });
       this.searchRoutingByProduct()
       console.log("Selected Operation Codes after search:", this.state.selectedOperationCodes);
   }




    async loadOperationCodes() {
        if (!this.state.selectedProductId) return;

        const codes = await this.rpc("/on_hand_product/operation_codes", {
            product_id: this.state.selectedProductId,
        });
        this.state.operationCodes = codes;
    }

    async searchRoutingByProduct() {
        this.state.routingLines = [];
        this.state.grandTotal = 0;

        if (!this.state.selectedProductId) return;

        const data = await this.rpc("/on_hand_product/get_data", {
            product_id: this.state.selectedProductId,
            lot_type: this.state.selectedLotType,
            op_code: this.state.selectedOperationCodes,
        });

        const filtered = this.state.selectedOperationCodes.length
            ? data.filter(line => this.state.selectedOperationCodes.includes(line.operation_code))
            : data;

        this.state.routingLines = filtered;
        this.state.grandTotal = filtered.reduce((sum, line) => sum + (line.total || 0), 0);
    }
}

registry.category("actions").add("on_hand_product_js.Odoo", InventoryOnHandProductReport);
export default InventoryOnHandProductReport;
