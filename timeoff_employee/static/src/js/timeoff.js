/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class EmployeeCommonTimeoff extends Component {
    static template = "timeoff_employee.Odoo";

    setup() {
        this.rpc = useService("rpc");

        this.state = useState({
            empId: "",
            password: "",
            error: "",
            loggedIn: false,
            employeeName: "",
            employeeId: null,
            leaveTypes: [],
            showModal: false,
            selectedLeaveType: null,
            leaveForm: {
                date_from: "",
                date_to: "",
                reason: "",
            },
            draftDetails: [],     // NEW
            showDraftModal: false // NEW
        });
        this.login = this.login.bind(this);
        this.logout = this.logout.bind(this);
        this.openModal = this.openModal.bind(this);
        this.closeModal = this.closeModal.bind(this);
        this.openDraftDetails = this.openDraftDetails.bind(this);
        this.submitLeaveRequest = this.submitLeaveRequest.bind(this);
    }

    async login() {
        if (!this.state.empId || !this.state.password) {
            this.state.error = "Please enter Employee ID and Password.";
            return;
        }

        try {
            const employees = await this.rpc("/web/dataset/call_kw/hr.employee/search_read", {
                model: "hr.employee",
                method: "search_read",
                args: [],
                kwargs: {
                    domain: [["emp_code", "=", this.state.empId], ["work_phone", "=", this.state.password]],
                    fields: ["id", "name"],
                },
            });

            if (employees.length > 0) {
                const emp = employees[0];
                this.state.loggedIn = true;
                this.state.employeeName = emp.name;
                this.state.employeeId = emp.id;
                this.state.error = "";

                const leaveTypes = await this.rpc("/employee/leave/types", {
                    employee_id: emp.id,
                });
                this.state.leaveTypes = leaveTypes;
            } else {
                this.state.error = "Invalid credentials.";
            }
        } catch (error) {
            console.error(error);
            this.state.error = "Login failed due to server error.";
        }
    }

    logout() {
        location.reload();
    }

    openModal(leaveType) {
        this.state.selectedLeaveType = leaveType;
        this.state.showModal = true;
    }

    closeModal() {
        this.state.showModal = false;
        this.state.leaveForm = {
            date_from: "",
            date_to: "",
            reason: "",
        };
    }

    async openDraftDetails(leaveType) {
        console.log("Fetching draft details for leave type:", leaveType);
        try {
            const result = await this.rpc("/employee/leave/details", {
                employee_id: this.state.employeeId,
                holiday_status_id: leaveType.id
            });
            console.log("Draft details fetched:", result);
            this.state.draftDetails = result;
            this.state.selectedLeaveType = leaveType;
            this.state.showDraftModal = true;
        } catch (error) {
            console.error("Error fetching draft details", error);
        }
    }


    async submitLeaveRequest() {
        const { date_from, date_to, reason } = this.state.leaveForm;

        if (!date_from || !date_to) {
            alert("Please fill in both start and end dates.");
            return;
        }
        console.log("Submitting leave request:",this.state.employeeId , this.state.selectedLeaveType.id , date_from , date_to, reason);

//        try {
            const result = await this.rpc("/employee/submit/leave", {
                employee_id: this.state.employeeId,
                holiday_status_id: this.state.selectedLeaveType.id,
                date_from,
                date_to,
                name: reason || "Time Off Request",
            });

            if (!result.success) {
                alert("Failed: " + result.error);
                return;
            }

            alert("Leave request submitted!");
            this.closeModal();
//        } catch (error) {
//            console.error(error);
//            alert("Error while submitting leave.");
//        }
    }
}

registry.category("actions").add("timeoff_employee.Odoo", EmployeeCommonTimeoff);
export default EmployeeCommonTimeoff;
