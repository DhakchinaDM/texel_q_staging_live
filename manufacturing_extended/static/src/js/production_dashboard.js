/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class ProductionDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            empId: "",
            empId_value: "",
            password: "",
            isLoggedIn: false,
            employeeName: "",
            workcenters: [],
            selectedWorkcenter: null,
            jobs: [],
            loadedLot: null,
            bomComponents: [],
            selectedJob: null,
            stockLoaded : false,
        });

        this.login = this.login.bind(this);
        this.fetchWorkcenters = this.fetchWorkcenters.bind(this);
        this.selectWorkcenter = this.selectWorkcenter.bind(this);
        this.fetchJobs = this.fetchJobs.bind(this);
        this.selectJob = this.selectJob.bind(this);
        this.startJob = this.startJob.bind(this);
        this.pauseJob = this.pauseJob.bind(this);
        this.completeJob = this.completeJob.bind(this);
    }

    async login() {
        console.log('====================Login==================')
        if (!this.state.empId || !this.state.password) {
            alert("Please enter Employee ID and Password.");
            return;
        }

        try {
            const employees = await this.orm.searchRead("hr.employee",
                [["emp_code", "=", this.state.empId], ["work_phone", "=", this.state.password]],
                ["id", "name"]
            );

            if (employees.length > 0) {
                const employeeId = employees[0].id;
                this.state.isLoggedIn = true;
                this.state.employeeName = employees[0].name;
                this.state.empId_value = employees[0];

                // Check if employee has an active job
                const activeJobs = await this.orm.searchRead("mrp.workcenter.productivity",
                    [["employee_id", "=", employeeId], ["date_end", "=", false]],
                    ["id", "workcenter_id", "production_id", "workorder_id"]
                );
                console.log('Active Jobs:', activeJobs);
                if (activeJobs.length > 0) {
                    const activeWorkorder = await this.orm.searchRead("mrp.workorder", [["id", "=", activeJobs[0].workorder_id[0]]], ["id", "job_id", "name", "qty_production", "qty_produced", "qty_remaining", "duration", "production_id", "workcenter_id", "product_id", "move_raw_ids", "load_component", "available_qty_fg"]);
                    // Employee has an active job, directly show job details

                    this.state.selectedJob = activeWorkorder[0];
                    this.state.selectedWorkcenter = {
                        id: activeJobs[0].workcenter_id[0],
                        name: activeJobs[0].workcenter_id[1]
                    };
                    this.state.jobStarted = true;  // Mark job as started
                    const moId = await this.orm.searchRead("mrp.production", [["id", "=", activeWorkorder[0].production_id[0]]], ["id", "lot_ids"]);
                    const lotIds = moId[0].lot_ids;

                    if (lotIds.length > 0) {
                        const lots = await this.orm.searchRead("stock.lot", [["id", "in", lotIds]], ["id", "name", "product_qty"]);
                        this.state.loadedLot = lots.map(lot => ({ id: lot.id, name: lot.name, product_qty: lot.product_qty }));
                    } else {
                        this.state.loadedLot = [];
                    }
                    console.log("Loaded Lots:", this.state.loadedLot);

                } else {
                    // No active job, show available workcenters
                    await this.fetchWorkcenters();
                }
            } else {
                alert("Invalid Employee ID or Password");
            }
        } catch (error) {
            console.error("Login Error:", error);
        }
    }

    async fetchWorkcenters() {
        console.log('...............................')
        try {
            const workcenters = await this.orm.searchRead("mrp.workcenter", [["job_started", "=", false]], ["id", "name"]);
            this.state.workcenters = workcenters.length > 0 ? workcenters : [];
        } catch (error) {
            console.error("Error fetching workcenters:", error);
        }
    }

    async selectWorkcenter(workcenterId) {
        console.log('1111111111111111111111111111111', workcenterId)
        this.state.selectedWorkcenter = workcenterId;
        this.state.searchQuery = "";
        this.state.jobs = [];
        await this.fetchJobs(workcenterId);
    }

    async fetchJobs(workcenterId) {
        console.log('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^', workcenterId)
        try {
            const jobs = await this.orm.searchRead("mrp.workorder", [["workcenter_id", "=", workcenterId], ["job_started", "=", false],["production_state", "in", ["confirmed", "progress"]], ["available_qty_fg", ">", 0]], ["id", "job_id", "name", "qty_production", "qty_produced", "qty_remaining", "duration", "production_id", "workcenter_id", "product_id", "move_raw_ids", "load_component", "available_qty_fg"]);
            this.state.jobs = jobs.length > 0 ? jobs : [];
            console.log("Jobs fetched successfully:", this.state.jobs);
        } catch (error) {
            console.error("Error fetching jobs:", error);
        }
    }

    async selectJob(job) {
        this.state.selectedJob = job;
        this.state.searchQuery = "";
        this.state.jobStarted = false;  // Reset start state when switching jobs
        console.log("Selected Job:", this.state.selectedJob);

        const moId = await this.orm.searchRead("mrp.production", [["id", "=", this.state.selectedJob.production_id[0]]], ["id", "lot_ids"]);
        const lotIds = moId[0].lot_ids;

        if (lotIds.length > 0) {
            const lots = await this.orm.searchRead("stock.lot", [["id", "in", lotIds]], ["id", "name", "product_qty"]);
            this.state.loadedLot = lots.map(lot => ({ id: lot.id, name: lot.name, product_qty: lot.product_qty }));
        } else {
            this.state.loadedLot = [];
        }
        console.log("Loaded Lots:", this.state.loadedLot);
        // Fetching components
        const components = await this.orm.searchRead(
            "stock.move",
            [["raw_material_production_id", "=", this.state.selectedJob.production_id[0]]],
            ["id", "product_id", "product_qty", "quantity", "product_uom_qty"]
        );

        const production = await this.orm.searchRead(
            "mrp.production",
            [["id", "=", this.state.selectedJob.production_id[0]]],
            ["id", "location_src_id", "mrp_production_child_count", "mrp_production_backorder_count"]
        );
        if (this.state.selectedJob.load_component) {
            this.state.stockLoaded = true;
        } else {
            this.state.stockLoaded = false;
        }

//        if (production[0].mrp_production_backorder_count >= 2) {
//            this.state.stockLoaded = true;
//        }
//        if (production[0].mrp_production_child_count > 0){
//            this.state.stockLoaded = true;
//        }


        console.log("Selected Components:", components);

        // Store the components in state
        this.state.selectedJob.components = components;
    }

    async unloadComponent() {
        console.log('===================Unload====================', this.state.selectedJob)
        this.state.loading = true;

        try {
            const moId = this.state.selectedJob.production_id[0];

            const moData = await this.orm.searchRead("mrp.production", [["id", "=", moId]], ["lot_ids"]);
            const lotIds = moData.length ? moData[0].lot_ids : [];
            await this.orm.call("stock.move.line", "revert_selected_lot", [
                this.state.selectedJob.production_id[0]
            ]);

            if (lotIds.length > 0) {
                for (const lotId of lotIds) {
                    await this.orm.call("stock.lot", "write", [[lotId], {
                        loading: false,
                    }]);
                }

                this.state.loadedLot = [];
                this.state.stockLoaded = false;

                console.log("Successfully unloaded lots:", lotIds);
            } else {
                alert("No lots are currently loaded for this job.");
            }
        } catch (error) {
            console.error("Error during unloading lots:", error);
            alert("Failed to unload lots.");
        } finally {
            this.state.loading = false;
        }
    }


    async loadComponent() {
        if (!this.state.selectedJob) {
            alert("Please select a job first.");
            return;
        }

        try {
            // Fetch components (raw materials) for the selected job
            const components = await this.orm.searchRead(
                "stock.move",
                [["raw_material_production_id", "=", this.state.selectedJob.production_id[0]]],
                ["id", "product_id", "product_uom_qty"]
            );

            console.log('Fetched Components:', components);

            if (!components.length) {
                alert("No components found for this job.");
                return;
            }

            // Get all product IDs from components
            const productIds = components.map(component => component.product_id[0]);

            // Fetch production details to get the source location
            const production = await this.orm.searchRead(
                "mrp.production",
                [["id", "=", this.state.selectedJob.production_id[0]]],
                ["id", "location_src_id"]
            );

            if (!production.length) {
                alert("Production record not found.");
                return;
            }

            this.state.locationSrc = production[0].location_src_id;
            console.log('Production Source Location:', this.state.locationSrc);

            // Fetch lot quantities from stock.quant based on location_src_id
            const lotQuantities = await this.orm.searchRead(
                "stock.quant",
                [["product_id", "in", productIds], ["location_id", "=", this.state.locationSrc[0]], ["quantity", ">", 0], ["available_quantity", ">", 0]],
                ["id", "lot_id", "product_id", "quantity"]
            );

            console.log('Fetched Lot Quantities:', lotQuantities);

            // Fetch lot details (name and lot_type)
            const lotIds = lotQuantities.map(lq => lq.lot_id[0]).filter(id => id);  // Remove null lot_ids
            let lots = [];

            if (lotIds.length) {
                lots = await this.orm.searchRead(
                    "stock.lot",
                    [["id", "in", lotIds]],
                    ["id", "name", "lot_type","loading"]
                );
            }

            console.log('Fetched Lots:', lots);

            // Map Lot Quantities to Component Products
            components.forEach(component => {
                const relatedLots = lotQuantities
                    .filter(lq => lq.product_id[0] === component.product_id[0])
                    .map(lq => {
                        const lot = lots.find(lot => lot.id === lq.lot_id[0]);
                        return {
                            id: lq.lot_id[0],
                            name: lot?.name || "Unknown",
                            quantity: lq.quantity,
                            lot_type: lot?.lot_type || null,
                            loading: lot.loading
                        };
                    })
                    .filter(lot => (lot.lot_type === 'ok' || lot.lot_type === null) && lot.loading === false); // Include only lots with lot_type 'ok' or 'false'

                component.lot_options = relatedLots;
                component.selected_lots = [];  // Store selected lot IDs with usage quantity
            });

            // Store the updated component list in the state
            this.state.bomComponents = components;

            // Show the modal
            $("#loadComponentModal").modal("show");

            // Apply Select2 after a short delay
            setTimeout(() => {
                $(".multi-select").select2({
                    placeholder: "Select Lots",
                    allowClear: true,
                    width: '100%'
                });
            }, 500);
        } catch (error) {
            console.error("Error loading components:", error);
        }
    }


    async confirmComponentSelection() {
        let selectedLotsData = [];
        this.state.loading = true;
        this.state.mo_id = this.state.selectedJob.production_id[0];
        this.state.job_id = this.state.selectedJob.id;


        $(".multi-select").each((index, element) => {
            const componentId = parseInt($(element).data("component"));
            const selectedLots = $(element).val() || [];

            const component = this.state.bomComponents.find(c => c.id === componentId);
            if (component) {
                let lotSelectionData = [];

                selectedLots.forEach(lotId => {
                    const lot = component.lot_options.find(l => l.id === parseInt(lotId));
                    if (lot) {
                        lotSelectionData.push({ lot_id: lot.id, quantity: lot.quantity });
                    }
                });

                selectedLotsData.push({
                    product_id: component.product_id[0],
                    lot_ids: lotSelectionData
                });
            }
        });

        if (selectedLotsData.length > 0) {
            try {
                await this.orm.call("stock.move.line", "update_selected_lot", [
                    selectedLotsData,
                    this.state.selectedJob.production_id[0]
                ]);

//                alert("Stock Moves Updated Successfully!");
                $("#loadComponentModal").modal("hide");
                this.state.stockLoaded = true;
                const moId = await this.orm.searchRead("mrp.production", [["id", "=", this.state.selectedJob.production_id[0]]], ["id", "lot_ids"]);
                const lotIds = moId[0].lot_ids;

                for (const lotId of lotIds) {
                    await this.orm.call("stock.lot", "write", [[lotId], {
                        loading: true,
                    }]);
                }

                if (lotIds.length > 0) {
                    const lots = await this.orm.searchRead("stock.lot", [["id", "in", lotIds]], ["id", "name", "product_qty"]);
                    this.state.loadedLot = lots.map(lot => ({ id: lot.id, name: lot.name, product_qty: lot.product_qty }));
                } else {
                    this.state.loadedLot = [];
                }
                console.log("Loaded Lots:", this.state.loadedLot);
            } catch (error) {
                console.error("Error updating stock.move.line:", error);
                alert("Failed to update stock moves.");
            }
        } else {
            alert("No selections made.");
        }
    }

    async startJob() {
        console.log('<<<<<<<<<<<<<<<<<<<<<<<<<<<<', this.state.selectedJob)
        if (!this.state.selectedJob) {
            alert("Please select a job first.");
            return;
        }

        try {
            // Start the job in Odoo
            await this.orm.call("mrp.workorder", "button_start", [[this.state.selectedJob.id]], { emp_id: this.state.empId });

            // Fetch the updated job details including the duration
            const workorders = this.state.selectedJob.id
             // Fetch the updated job details including the duration
//            const workorders = await this.orm.searchRead("mrp.workorder",
//                [["id", "=", this.state.selectedJob.id]],
//                ["id", "name", "duration", "production_id", "qty_production", "qty_produced", "qty_remaining"]
//            );

            if (workorders.length > 0) {
                this.state.selectedJob = workorders[0];

                // Fetch and update the stored duration from the database
                this.state.timerValue = this.formatDuration(this.state.selectedJob.duration || 0);
            }

            this.state.jobStarted = true;
            this.fetchLoadedQty();

            // Start the timer with the correct duration
            this.startTimer();
        } catch (error) {
            console.error("Error starting job:", error);
        }
    }

    pauseJob() {
        if (!this.state.selectedJob) {
            alert("Please select a job first.");
            return;
        }
        this.state.jobAction = "pause";
        this.fetchLoadedQty()
        console.log('OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO', this.state.selectedJob)

        $("#pauseJobModal").modal("show");
    }

    async submitPauseReason() {
        // Helper function to handle alerts
        const showAlert = (message) => {
            alert(message);
            return false;
        };

        // Get input values and convert them to numbers or default to 0
        const producedQty = parseInt(document.getElementById("produced_qty").value) || 0;
        const okQty = parseInt(document.getElementById("ok_qty").value) || 0;
        const materialRejectQty = parseInt(document.getElementById("material_reject_qty").value) || 0;
        const processRejectQty = parseInt(document.getElementById("process_reject_qty").value) || 0;
        const reworkQty = parseInt(document.getElementById("rework_qty").value) || 0;

        // Get text values from input fields
        const shift = document.getElementById("shift").value;
        const reason = document.getElementById("pause_reason").value.trim();
        const materialRejectReason = document.getElementById("material_reject_reason").value.trim();
        const processRejectReason = document.getElementById("process_reject_reason").value.trim();
        const reworkReason = document.getElementById("rework_reason").value.trim();
        const okQtyRemark = document.getElementById("ok_qty_remark").value.trim();

        // Validation checks for required fields
        if (!shift) return showAlert("Please select a shift.");
        if (!reason) return showAlert("Please enter a general pause reason.");
        if (materialRejectQty > 0 && !materialRejectReason) return showAlert("Please enter a reason for Material Reject Quantity.");
        if (processRejectQty > 0 && !processRejectReason) return showAlert("Please enter a reason for Process Reject Quantity.");
        if (reworkQty > 0 && !reworkReason) return showAlert("Please enter a reason for Rework.");
        if (!this.state.selectedJob) return showAlert("No job selected.");

        // Get job quantity and validate if produced quantity exceeds job quantity
        const jobQty = this.state.selectedJob.qty_production;
        if (producedQty > jobQty) {
            return showAlert(`Produced quantity (${producedQty}) cannot exceed job quantity (${jobQty}).`);
        }

        // Check if the sum of quantities matches the produced quantity
        const totalCheckedQty = okQty + materialRejectQty + processRejectQty + reworkQty;
        if (producedQty !== totalCheckedQty) {
            return showAlert(`Produced quantity (${producedQty}) must be equal to OK Qty (${okQty}) + Material Reject Qty (${materialRejectQty}) + Process Reject Qty (${processRejectQty}) + Rework Qty (${reworkQty}).`);
        }

        try {
            if (this.state.jobAction === "pause") {
                // Step 1: Call ORM method to generate serial numbers
                await this.orm.call("mrp.production", "action_generate_serial", [[this.state.selectedJob.production_id[0]]]);

                // Step 2: Call the button_pending function and pass pause data
                const productivityId = await this.orm.call("mrp.workorder", "button_pending", [[this.state.selectedJob.id]], {
                    pause_data: {
                        shift: shift,
                        emp_id: this.state.empId_value,
                        pause_reason: reason,
                        produced_qty: producedQty,
                        ok_qty: okQty,
                        rework_qty: reworkQty,
                        ok_qty_remark: okQtyRemark,
                        material_reject_qty: materialRejectQty,
                        material_reject_reason: materialRejectReason,
                        process_reject_qty: processRejectQty,
                        process_reject_reason: processRejectReason,
                        rework_reason: reworkReason,
                    }
                });
                console.log("employeeee_idddd as ner", this.state.empId_value);

                // Step 3: Check if the produced quantity matches the job quantity and update lot status
                const moId = await this.orm.searchRead("mrp.production", [["id", "=", this.state.selectedJob.production_id[0]]], ["id", "lot_ids","state"]);
                const lotIds = moId[0].lot_ids;

                if (producedQty === jobQty) {
                    for (const lotId of lotIds) {
                        await this.orm.call("stock.lot", "write", [[lotId], { loading: false }]);
                    }
                }
                console.log("Lots testing printingg", moId[0].state);

                // Step 4: Handle the printing of the label if production is complete
                if (moId[0].state === "done") {
                    const reportUrl = `/report/pdf/manufacturing_extended.report_mrp_workcenter_productivity_template/${productivityId}`;
                    window.open(reportUrl, "_blank");
                }

                // Step 5: Mark job as paused and reload the page
                this.state.jobPaused = true;
                location.reload();
            }

            // Clear timer interval and close modal
            clearInterval(this.state.timerInterval);
            $("#pauseJobModal").modal("hide");

        } catch (error) {
            console.error("Error:", error);
        }
    }


    async completeJob() {
        if (!this.state.selectedJob) {
            alert("Please select a job first.");
            return;
        }
        this.state.jobAction = "complete";

        // Set produced_qty and mark the field as read-only
        $("#produced_qty").val(this.state.selectedJob.available_qty_fg || 0);
        $("#produced_qty").prop("readonly", true);

        $("#pauseJobModal").modal("show");
    }
    selectNewJob() {
        this.state.selectedJob = null;
        this.state.jobCompleted = false;
        this.state.jobPaused = false;
        this.state.jobs = [];
        this.state.selectedWorkcenter = null;
        this.fetchWorkcenters();
    }

    formatDuration(seconds) {
        let hrs = Math.floor(seconds / 3600);
        let mins = Math.floor((seconds % 3600) / 60);
        let secs = Math.floor(seconds % 60);
        return `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
    }

    startTimer() {
        if (this.state.timerInterval) {
            clearInterval(this.state.timerInterval);
        }

        let currentDuration = this.state.selectedJob.duration || 0;

        this.state.timerInterval = setInterval(() => {
            currentDuration += 1;  // Increment seconds
            this.state.selectedJob.duration = currentDuration;
            this.state.timerValue = this.formatDuration(currentDuration);
        }, 1000);
    }
    deselectWorkcenter() {
        this.state.selectedWorkcenter = null;
    }

    logout() {
        this.state.isLoggedIn = false;
        this.state.empId = "";
        this.state.password = "";
    }

    deselectJob() {
        this.state.selectedJob = null;
    }

    toggleLotSelection(ev) {
        const lotId = ev.target.dataset.lotId;
        if (ev.target.checked) {
            this.state.selectedLots[lotId] = 0; // Default qty 0 when selected
        } else {
            delete this.state.selectedLots[lotId];
        }
    }

    updateLotQty(ev) {
        const lotId = ev.target.dataset.lotId;
        this.state.selectedLots[lotId] = ev.target.value;
    }

    async fetchLoadedQty() {
        const productionId = this.state.selectedJob.production_id[0];

        const records = await this.orm.searchRead(
            'stock.move.line',
            [
                ['production_id', '=', productionId],['lot_id', '!=', false]
            ],
            ['product_id', 'quantity']
        );

        this.state.loadedComponents = records;
        console.log('>>>>>>>>>>>..Loaded Components:', this.state.loadedComponents, productionId, this.state.selectedJob.production_id[0]);
    }

}

// Register the Component
ProductionDashboard.template = "ProductionDashboard";
registry.category("actions").add("production_dashboard", ProductionDashboard);
