/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


const { onWillStart } = owl;

class ProductivityDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            products: [], // List of FG products
            selectedProductId: null, // Selected product ID
            productivityData: [],
            groupedData: {},
            startDate: "",  // Start date filter
            endDate: "",    // End date filter
        });
        this.rpc = useService("rpc");

        onMounted(this.loadProducts.bind(this));
    }

    async loadProducts() {
        // Fetch finished goods products from backend
        try {
            const products =  await this.rpc("/get_finished_goods");
            this.state.products = products;
            console.log("Finished goods products:", products);

            // Set the default selected product and load data
            if (products.length) {
                this.state.selectedProductId = products[0].id;
                this.loadData();
            }
        } catch (error) {
            console.error("Failed to fetch finished goods products:", error);
        }
    }

    async loadData() {
        if (!this.state.selectedProductId) return;

        try {
            const groupedData = await this.rpc("/get_productivity_data", {
                product_id: this.state.selectedProductId,
                start_date: this.state.startDate,
                end_date: this.state.endDate,
            });
            this.state.groupedData = groupedData;
        } catch (error) {
            console.error("Failed to fetch productivity data:", error);
        }
    }

    onStartDateChange(event) {
        this.state.startDate = event.target.value;
        this.loadData();
    }

    onEndDateChange(event) {
        this.state.endDate = event.target.value;
        this.loadData();
    }



    onProductChange(event) {
        this.state.selectedProductId = parseInt(event.target.value);
        console.log('Selected Product ID:', this.state.selectedProductId);
        this.loadData();
    }

    async printReport(recordId){
        const reportUrl = `/report/pdf/manufacturing_extended.report_mrp_single_productivity_template/${recordId}`;
        window.open(reportUrl, "_blank");
    }
}

ProductivityDashboard.template = "productivity_dashboard_template";
registry.category("actions").add("productivity_dashboard_action", ProductivityDashboard);
