/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class EmployeeSkillMatrix extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            employees: [],
            skills: [],
            skill_types: [],  // Store skill types
            skill_levels: [],
            search_query: "",
            selected_skill_type: "",  // Store selected skill type
            selected_skills: [],  // Store selected skills
            isLoading: false,
        });
        this.fetchSkillTypes();

    }

    async fetchSkillTypes() {
        try {
            const result = await this.orm.call("hr.skill.type", "search_read", [[], ["id", "name"]]);
            this.state.skill_types = result;
        } catch (error) {
            console.error("❌ Error fetching skill types:", error);
        }
    }

    updateSkillType(ev) {
        this.state.selected_skill_type = ev.target.value;
        this.fetchEmployeeSkills();
    }

    updateSelectedSkills(ev) {
        console.log("checking logg for this function");
        this.state.selected_skills = Array.from(ev.target.selectedOptions, (opt) => opt.value);
        this.fetchEmployeeSkills();
    }

    async fetchEmployeeSkills() {
        this.state.isLoading = true;
        try {
            const result = await this.orm.call("hr.employee", "get_employee_skills", [
                [],
                this.state.search_query,
                this.state.selected_skill_type,
                this.state.selected_skills
            ]);

            this.state.employees = result.employees;
            this.state.skills = result.skills;
            this.state.skill_levels = result.skill_levels;
            $(".select2").select2({
                placeholder: "Select skills...",
                allowClear: true
            });

        } catch (error) {
            console.error("❌ Error fetching employee skills:", error);
        }
        this.state.isLoading = false;
    }

    updateSearchQuery(ev) {
        this.state.search_query = ev.target.value.trim();
        this.fetchEmployeeSkills();
    }

    async updateSkillLevel(ev) {
        const employeeId = parseInt(ev.target.dataset.employeeId);
        console.log('111111111111111111111111111111111111111111111111111111111111111111111111',ev);
        console.log('222222222222222222222222222222222222222222222222222222222222',ev.target);
        console.log('33333333333333333333333333333333333333333333333333333333333333333333333333',ev.target.dataset);
        console.log('44444444444444444444444444444444444444444444444444444444444',ev.target.dataset.skill);
        const skillName = ev.target.dataset.skill;
        const newLevel = ev.target.value;

        console.log(`🔄 Updating skill ${skillName} for Employee ${employeeId} to Level ${newLevel}...`);

        try {
            const result = await this.orm.call("hr.employee", "update_employee_skill", [[], employeeId, skillName, newLevel]);
            console.log("✅ Skill update response:", result);
            // Update UI dynamically
            this.state.employees = this.state.employees.map(emp => {

                console.log('LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL', emp, emp.skills)
                if (emp.id === employeeId && emp.skills.hasOwnProperty(skillName)) {
                    emp.skills[skillName] = newLevel;
                }
                console.error("ddddddddddddddddd",emp.skills.hasOwnProperty(skillName))
                return emp;
            });
        } catch (error) {
            console.error("❌ Error updating skill:", error);
        }
    }
}

// Register the OWL component
EmployeeSkillMatrix.template = "employee_skill_matrix_template";
registry.category("actions").add("skill_master", EmployeeSkillMatrix);
