/** @odoo-module */
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { onWillStart } = owl;

class MrpDashboard extends Component {
    setup() {
        this.state = useState({
            dynamicHeaders: [],
            products: [],
            suppliers: [],
            inventoryData: [],
            integerField: 0,
            duration: "day",
            productId: "null",
            supplierId: "null",
        });
        this.actionService = useService("action");
        this.rpc = useService("rpc");
        onWillStart(this.loadFilterOptions.bind(this));
        this.loadFilterOptions();
    }

    async loadFilterOptions() {
        try {
            const filterData = await this.rpc("/product/filter");
            console.log("Filter Options Received:", filterData);
            this.state.products = filterData[0];
            this.state.suppliers = filterData[1];
        } catch (error) {
            console.error("Error loading filter options:", error);
        }
    }

    JobPlan(part_no) {
        console.log("=======part_no", part_no);
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "job.planning",
            name: "Job Planning",
            view_mode: "form",
            view_type: "form",
            views: [[false, "form"]],
            target: "new",
            res_id: false,
            context: {
                default_part_no: part_no,
            },
        });
    }

    updateStateFromInput() {
        const integerField = parseInt(document.getElementById("integer_field")?.value || 0, 10);
        const duration = document.getElementById("filter_duration")?.value;
        const productId = document.getElementById("product_selection")?.value || "null";
        const supplierId = document.getElementById("supplier_selection")?.value || "null";

        this.state.integerField = integerField;
        this.state.duration = duration;
        this.state.productId = productId;
        this.state.supplierId = supplierId;
    }

    async loadHeaders() {
        this.updateStateFromInput();

        if (this.state.integerField > 0 && this.state.duration) {
            try {
                this.state.dynamicHeaders = await this.calculateHeaders(this.state.integerField, this.state.duration);
                console.log("Calculated Headers------:", this.state.dynamicHeaders);
                this.state.inventoryData = [];
            } catch (error) {
                console.error("Error calculating headers:", error);
            }
        } else {
            console.warn("Integer field or duration missing or invalid.");
            this.state.dynamicHeaders = [];
            this.state.inventoryData = [];
        }

        this.updateTable();
    }

    async calculateHeaders(integerField, duration) {
        let headers = [];
        const today = new Date();

        if (duration === "day") {
            for (let i = 0; i < integerField; i++) {
                const date = new Date(today);
                date.setDate(date.getDate() + i);
                headers.push(date.toISOString().split("T")[0]);
            }
        } else if (duration === "week") {
            for (let i = 0; i < integerField; i++) {
                const monday = new Date(today);
                monday.setDate(monday.getDate() - monday.getDay() + 1 + i * 7);
                const sunday = new Date(monday);
                sunday.setDate(monday.getDate() + 6);
                headers.push(`${monday.toISOString().split("T")[0]} to ${sunday.toISOString().split("T")[0]}`);
            }
        } else if (duration === "month") {
            for (let i = 0; i < integerField; i++) {
                const firstDay = new Date(Date.UTC(today.getFullYear(), today.getMonth() + i, 1));
                const lastDay = new Date(Date.UTC(today.getFullYear(), today.getMonth() + i + 1, 0));
                headers.push(`${firstDay.toISOString().split("T")[0]} to ${lastDay.toISOString().split("T")[0]}`);
            }
        } else if (duration === "year") {
            for (let i = 0; i < integerField; i++) {
                const year = today.getFullYear() + i;
                headers.push(`${year}-01-01 to ${year}-12-31`);
            }
        }

        console.log("Generated Headers:", headers);
        return headers;
    }

    async updateTable() {
        const { productId, supplierId, duration, integerField } = this.state;
        try {
            const inventoryData = await this.rpc("/get_product_inventory", {
                product_id: productId,
                supplier_id: supplierId,
                filter_duration: duration,
                integer_field: integerField,
            });

            console.log("Inventory Data Received:", inventoryData);
            this.state.inventoryData = inventoryData.inventory_data;

            const tableBody = document.getElementById("mrp_dashboard_table_body");
            tableBody.innerHTML = "";

            inventoryData.inventory_data.forEach((item) => {
                console.log("Processing Item:", item);

                const row1 = document.createElement("tr");
                row1.innerHTML = `
                    <td class="border" rowspan="3">${item.product_name}</td>
                    <td class="border" rowspan="3">${item.partner_id}</td>
                    <td class="border" rowspan="3">${item.qty_available}</td>
                    <td class="border">Purchase Release</td>
                    <td class="border">${item.past_due}</td>
                    ${this.state.dynamicHeaders
                        .map((header) => `<td class="border">${item.upcoming[header] || 0}</td>`)
                        .join("")}
                `;
                tableBody.appendChild(row1);

                const row2 = document.createElement("tr");
                row2.innerHTML = `
                    <td class="border">Customer Release</td>
                    <td class="border">${item.past_due_customer_release || 0}</td>
                    ${this.state.dynamicHeaders
                        .map((header) => `<td class="border">${item.customer_release[header] || 0}</td>`)
                        .join("")}
                `;
                tableBody.appendChild(row2);

                const row3 = document.createElement("tr");
                row3.innerHTML = `
                    <td class="border">
                        Job Demand
                        <button type="button" class="btn btn-primary btn-sm rounded-circle align-items-center">
                            <i class="fa fa-plus"></i>
                        </button>
                    </td>
                    <td class="border">${item.past_due_job_demand || 0}</td>
                    ${this.state.dynamicHeaders
                        .map((header) => `<td class="border">${item.job_demand[header] || 0}</td>`)
                        .join("")}
                `;
                const button = row3.querySelector("button");
                button.addEventListener("click", () => this.JobPlan(item.product_id));
                tableBody.appendChild(row3);
            });
        } catch (error) {
            console.error("Error updating table:", error);
        }
    }
}

MrpDashboard.template = "MrpDashboard";
registry.category("actions").add("mrp_dashboard", MrpDashboard);