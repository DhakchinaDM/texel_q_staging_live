/** @odoo-module */
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { onWillStart } = owl;

class CRDashboard extends Component {
    setup() {
        this.state = useState({
            dynamicHeaders: [],
            products: [],
            suppliers: [],
            inventoryData: [],
            productId: "null",
            supplierId: "null",
        });
        this.actionService = useService('action');
        this.rpc = useService("rpc");
        onWillStart(this.loadFilterOptions.bind(this));
        this.loadFilterOptions();
        this.updateTable();
    }

    async loadFilterOptions() {
        try {
            const filterData = await this.rpc("/customer/filter");
            console.log("Filter Options Received:", filterData);
            this.state.products = filterData[0];
            this.state.suppliers = filterData[1];
        } catch (error) {
            console.error("Error loading filter options:", error);
        }
    }

    updateStateFromInput() {
        const productId = document.getElementById("product_selection")?.value || "null";
        const supplierId = document.getElementById("supplier_selection")?.value || "null";
        this.state.productId = productId;
        this.state.supplierId = supplierId;
    }

    async updateTable() {
        this.updateStateFromInput();
        const { productId, supplierId } = this.state;
        try {
            const inventoryData = await this.rpc("/get_customer_release", {
                product_id: productId,
                supplier_id: supplierId,
            });

            console.log("Inventory Data Received:", inventoryData, productId, supplierId);
            this.state.inventoryData = inventoryData.inventory_data;

            const tableBody = document.getElementById("cr_dashboard_table_body");
            tableBody.innerHTML = "";
            if (inventoryData.inventory_data.length > 0){
                inventoryData.inventory_data.forEach((item) => {
                    console.log("Processing Item:", item);
                    const row1 = document.createElement("tr");
                    row1.innerHTML = `
                        <td class="border">${item.customer}</td>
                        <td class="border">${item.po_ref}</td>
                        <td class="border">${item.ship_to}</td>
                        <td class="border">${item.part_no}</td>
                        <td class="border">${item.qty_ready}</td>
                        <td class="border">${item.qty_loaded}</td>
                        <td class="border">${item.due_date}</td>
                        <td class="border">${item.rel_qty}</td>
                    `;
                    tableBody.appendChild(row1);
                });
            }
            else{
                tableBody.innerHTML = "";
            }
        } catch (error) {
            console.error("Error updating table:", error);
        }
    }
}

CRDashboard.template = "CRDashboard";
registry.category("actions").add("cr_dashboard", CRDashboard);
