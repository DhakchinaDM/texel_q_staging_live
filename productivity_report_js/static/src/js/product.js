/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class ProductivityProductReport extends Component {
    static template = "productivity_report_js.OdooServices";

    setup() {
        this.rpc = useService("rpc");

        this.state = useState({
            products: [],
            selectedProductId: null,
            fromDate: "",
            toDate: "",
            routingLines: [],
        });

        this.onDateChange = this.onDateChange.bind(this);
        this.onProductChange = this.onProductChange.bind(this);
        this.searchRoutingByProduct = this.searchRoutingByProduct.bind(this);

        onMounted(() => {
            this.loadFGProducts();
        });
    }

    async loadFGProducts() {
        const products = await this.rpc("/productivity_report/fg_products", {});
        this.state.products = products;
    }

    onDateChange(event) {
        const { name, value } = event.target;
        this.state[name] = value;
        if (this.state.selectedProductId) {
            this.searchRoutingByProduct();
        }
    }

    onProductChange(event) {
        this.state.selectedProductId = parseInt(event.target.value);
        this.searchRoutingByProduct();
    }

    async searchRoutingByProduct() {
        this.state.routingLines = [];

        if (!this.state.selectedProductId) return;

        const data = await this.rpc("/productivity_report/get_data", {
            product_id: this.state.selectedProductId,
            from_date: this.state.fromDate,
            to_date: this.state.toDate,
        });

        this.state.routingLines = data;
    }
}

registry.category("actions").add("productivity_report_js.OdooServices", ProductivityProductReport);
export default ProductivityProductReport;
