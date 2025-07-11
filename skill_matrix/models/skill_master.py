from odoo import models, fields, api

class HREmployee(models.Model):
    _inherit = "hr.employee"

    def get_employee_skills(self, search_emp_code=None, skill_type_id=None, selected_skills=None):
        cr = self.env.cr

        # Check if search_emp_code is provided
        if search_emp_code:
            try:
                search_emp_code = int(search_emp_code)  # Convert to integer
            except ValueError:
                return {"error": "Invalid emp_code format. It should be a number."}

            emp_query = """
                SELECT id, name, emp_code FROM hr_employee
                WHERE emp_code = %s
            """
            cr.execute(emp_query, (search_emp_code,))
            print("##################################33")
        else:
            emp_query = "SELECT id, name, emp_code FROM hr_employee"
            cr.execute(emp_query)
            print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")

        all_employees = {row[0]: {"id": row[0], "name": row[1], "emp_code": row[2]} for row in cr.fetchall()}

        if not all_employees:
            return {"employees": [], "skills": [], "skill_levels": {}}

        # Fetch all skills with optional filtering
        skill_query = "SELECT id, name, skill_type_id, code FROM hr_skill WHERE 1=1"
        params = []

        if skill_type_id:
            skill_query += " AND skill_type_id = %s"
            params.append(skill_type_id)

        if selected_skills and isinstance(selected_skills, list):
            skill_query += " AND id IN %s"
            params.append(tuple(selected_skills))

        cr.execute(skill_query, tuple(params))
        all_skills = {row[0]: {"id": row[0], "name": row[1], "type_id": row[2], "code": row[3]} for row in
                      cr.fetchall()}

        # Fetch skill levels grouped by type_id
        cr.execute("SELECT name, skill_type_id FROM hr_skill_level")
        skill_levels_by_type = {}
        for level_name, type_id in cr.fetchall():
            skill_levels_by_type.setdefault(type_id, []).append(level_name)

        # Prepare employee skill dictionary
        employees = {
            emp_id: {
                "id": emp_id,
                "name": emp_data["name"],
                "emp_code": emp_data["emp_code"],
                "skills": {s["code"]: {"level": "-", "code": s["code"]} for s in all_skills.values()},
            }
            for emp_id, emp_data in all_employees.items()
        }

        # Fetch employee skill levels
        cr.execute("""
            SELECT es.employee_id, s.id, s.code, sl.name 
            FROM hr_employee_skill es
            JOIN hr_skill s ON es.skill_id = s.id
            JOIN hr_skill_level sl ON es.skill_level_id = sl.id
            WHERE es.employee_id IN %s
        """, (tuple(all_employees.keys()),))

        for emp_id, skill_id, skill_name, skill_level in cr.fetchall():
            if emp_id in employees:
                employees[emp_id]["skills"][skill_name] = skill_level

        return {
            "employees": list(employees.values()),
            "skills": list(all_skills.values()),
            "skill_levels": skill_levels_by_type,
        }

    def update_employee_skill(self, employee_id, skill_name, skill_level_name):

        """Update or insert an employee skill using Odoo ORM."""

        # Fetch Skill Record
        skill = self.env["hr.skill"].search([("code", "=", skill_name)], limit=1)
        if not skill:
            return {"error": "Skill not found"}

        # Fetch Skill Level Record
        skill_level = self.env["hr.skill.level"].search([("name", "=", skill_level_name),("skill_type_id", "=", skill.skill_type_id.id)], limit=1)
        if not skill_level:
            return {"error": "Skill level not found"}

        # Fetch Employee
        employee = self.browse(employee_id)
        if not employee:
            return {"error": "Employee not found"}

        # Check if the employee already has the skill
        emp_skill = self.env["hr.employee.skill"].search([
            ("employee_id", "=", employee.id),
            ("skill_id", "=", skill.id)
        ], limit=1)

        if emp_skill:
            # Update existing skill level
            emp_skill.skill_level_id = skill_level.id
        else:
            # Create new skill entry
            self.env["hr.employee.skill"].create({
                "employee_id": employee.id,
                "skill_id": skill.id,
                "skill_level_id": skill_level.id,
                "skill_type_id": skill.skill_type_id.id,
            })

        return {"success": True, "message": "Skill updated successfully"}