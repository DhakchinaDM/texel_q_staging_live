/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class LocationBasedQuantReport extends Component {
    static template = "location_based_inventory.OdooServices";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            categories: [],
            products: [],
            allProducts: [],  // for full reset
            locations: [],
            stockData: {},
            selectedProduct: null,
            selectedCategory: null,
        });

        this.getQty = this.getQty.bind(this);
        this.getQuantIds = this.getQuantIds.bind(this);
        this.showQuantIds = this.showQuantIds.bind(this);
        this.onCategoryChange = this.onCategoryChange.bind(this);
        this.onProductChange = this.onProductChange.bind(this);

        onMounted(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.categories = await this.orm.searchRead("product.category", [], ["id", "name"]);

        const products = await this.orm.searchRead("product.product", [], ["id", "name", "default_code", "categ_id"]);
        this.state.products = products;
        this.state.allProducts = products;

        this.state.locations = await this.orm.searchRead("stock.location", [["usage", "=", "internal"]], ["id", "name"]);

        const quants = await this.orm.searchRead("stock.quant", [], ["id", "product_id", "location_id", "quantity"]);
        const grouped = {};

        for (const q of quants) {
            const pid = q.product_id?.[0];
            const lid = q.location_id?.[0];
            if (!grouped[pid]) grouped[pid] = {};
            if (!grouped[pid][lid]) grouped[pid][lid] = { quantity: 0, quantIds: [] };
            grouped[pid][lid].quantity += q.quantity;
            grouped[pid][lid].quantIds.push(q.id);
        }

        this.state.stockData = grouped;
    }

    getQty(productId, locationId) {
        const productData = this.state.stockData[productId];
        if (!productData) return 0;
        return productData[locationId]?.quantity || 0;
    }

    getQuantIds(productId, locationId) {
        const productData = this.state.stockData[productId];
        if (!productData) return [];
        return productData[locationId]?.quantIds || [];
    }

    async showQuantIds(quantIds) {
        if (!quantIds || quantIds.length === 0) {
            alert("No stock quants found.");
            return;
        }

        this.actionService.doAction({
            name: 'Stock Quants',
            type: 'ir.actions.act_window',
            res_model: 'stock.quant',
            views: [[false, 'list']],
            view_mode: 'form',
            domain: [['id', 'in', quantIds]],
            target: 'new',
        });
    }

    onCategoryChange(event) {
        const categoryId = event.target.value ? parseInt(event.target.value) : null;
        this.state.selectedCategory = categoryId;
        this.state.selectedProduct = null;

        if (categoryId) {
            this.state.products = this.state.allProducts.filter(p => p.categ_id?.[0] === categoryId);
        } else {
            this.state.products = this.state.allProducts;
        }
    }

    onProductChange(event) {
        this.state.selectedProduct = event.target.value ? parseInt(event.target.value) : null;
    }
}

registry.category("actions").add("location_based_inventory.OdooServices", LocationBasedQuantReport);
export default LocationBasedQuantReport;
