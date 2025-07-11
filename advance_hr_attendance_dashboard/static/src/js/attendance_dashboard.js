/* @odoo-module */
import { Component, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class AttendanceDashboard extends Component {
    setup() {
        this.action = useService("action");
        this.state = useState({
            filteredDurationDates: [],
            employeeData: [],
            publicHolidays: []

        });
        this.orm = useService("orm");
        this.root = useRef("attendance-dashboard");
        this.startDate = "";
        this.endDate = "";
    }

    /**
     * Event handler for the change event on the start date field.
     */
    onStartDateChange(ev) {
        this.startDate = ev.target.value;
    }

    /**
     * Event handler for the change event on the end date field.
     */
    onEndDateChange(ev) {
        this.endDate = ev.target.value;
    }

    /**
     * Formats the leave data for display in the dashboard.
     */
    formatLeaveData(leaveData) {
        return leaveData.map((data) => {
            let displayLabel = data.state;
            if (data.state === "OD") displayLabel = "On-Duty";
            else if (data.state === "COMP-OFF") displayLabel = "Compensatory Off";
            else if (data.state === "W/O") displayLabel = "W/O";
            else if (data.state === "P/H") displayLabel = "P/H";
            else if (data.state === "W/O-P/H") displayLabel = "W/O-P/H";
            else if (!data.state) displayLabel = "Present";

            return {
                ...data,
                displayState: displayLabel,
            };
        });
    }


    async onFilterByDateRange() {
        if (this.startDate && this.endDate) {
            const result = await this.orm.call("hr.employee", "get_employee_leave_data", [
                { start_date: this.startDate, end_date: this.endDate },
            ]);
            this.state.filteredDurationDates = result.filtered_duration_dates;
            this.state.publicHolidays = result.public_holidays;

            this.state.employeeData = result.employee_data.map((employee) => {
                employee.leave_data = this.formatLeaveData(employee.leave_data);
                employee.totalPresentDays = employee.leave_data.filter(data => data.displayState === "P").length;
                return employee;
            });
        } else {
            alert("Please select both start and end dates.");
        }
    }

    isPublicHoliday(dateString) {
        return this.state.publicHolidays.find(holiday => holiday.date === dateString);
    }



    /**
     * Event handler for the 'change' event of the filter input element.
     * It triggers the onclick_this_filter method with the new filter value.
     * @param {Event} ev - The change event object.
     */
    onChangeFilter(ev) {
        ev.stopPropagation();
        this.onclick_this_filter(ev.target.value);
    }

    // On clicking search button, employees will be filtered
    _OnClickSearchEmployee(ev) {
        this.onFilterByDateRange();
        let searchbar = this.root.el.querySelector("#search-bar").value?.toLowerCase();
        var attendance_table_rows = this.root.el.querySelector("#attendance_table_nm").children[1];

        for (let tableData of attendance_table_rows.children) {
            let empName = tableData.children[0].getAttribute("data-name").toLowerCase();
            let empCode = tableData.children[1].getAttribute("data-emp-code").toLowerCase();

            // Show only exact match for emp_code or if emp_name contains search value
            if (empCode === searchbar || empName.includes(searchbar)) {
                tableData.style.display = "";
            } else {
                tableData.style.display = "none";
            }
        }
    }

//    _OnClickExcelReport(ev){
//        consol.log("Excel Report");
//        window.location.href = '/attendance/download_excel';
//    }



    // On clicking Print PDF button, report will be printed
    _OnClickPdfReport(ev) {
        const table = this.root.el.querySelector("#attendance_table_nm");
        let tHead = table.children[0].innerHTML;
        let tBody = table.children[1].innerHTML;
        console.log(tHead);
        return this.action.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: "advance_hr_attendance_dashboard.report_hr_attendance",
            report_file: "advance_hr_attendance_dashboard.report_hr_attendance",
            data: { tHead: tHead, tBody: tBody },
        });
    }

    _OnClickExcelReport(ev) {
        const start_date = this.startDate;  // Ensure this is properly set in your state
        const end_date = this.endDate;      // Ensure this is properly set in your state

        console.log(".>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>", start_date, end_date);

        if (!start_date || !end_date) {
            alert("Please select a start and end date.");
            return;
        }

        const url = `/attendance/download_excel?start_date=${start_date}&end_date=${end_date}`;
        window.location.href = url;
    }

    isSunday(dateString) {
        const date = new Date(dateString);
        return date.getDay() === 0; // Sunday is 0
    }




    async onclick_this_filter(ev) {
        await this.orm
            .call("hr.employee", "get_employee_leave_data", [ev])
            .then((result) => {
                this.result = result;
                this.state.filteredDurationDates = result.filtered_duration_dates;
                this.state.employeeData = result.employee_data;
            });
    }

    formatDate(inputDate) {
        const months = [
            "JAN",
            "FEB",
            "MAR",
            "APR",
            "MAY",
            "JUN",
            "JUL",
            "AUG",
            "SEP",
            "OCT",
            "NOV",
            "DEC",
        ];
        const parts = inputDate.split("-");
        const day = parts[2];
        const month = months[parseInt(parts[1], 10) - 1];
        const year = parts[0];
        return `${day}-${month}-${year}`;
    }
}

AttendanceDashboard.template = "AttendanceDashboard";
registry.category("actions").add("attendance_dashboard", AttendanceDashboard);
