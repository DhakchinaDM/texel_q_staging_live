from odoo import models, fields, api, exceptions

class OperatorSession(models.Model):
    _name = "operator.session"
    _description = "Employee Work Center Session"

    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
    workcenter_id = fields.Many2one("mrp.workcenter", string="Work Center")
    login_time = fields.Datetime("Login Time", default=fields.Datetime.now)
    logout_time = fields.Datetime("Logout Time")
    active = fields.Boolean("Active", default=True)

    @api.model
    def login_employee(self, emp_id, phone):
        """Authenticate employee and log session"""
        employee = self.env["hr.employee"].search([("id", "=", emp_id), ("work_phone", "=", phone)], limit=1)
        if not employee:
            raise exceptions.ValidationError("Invalid Employee ID or Phone Number")

        # Check if the employee is already logged in
        existing_session = self.search([("employee_id", "=", employee.id), ("active", "=", True)], limit=1)
        if existing_session:
            raise exceptions.ValidationError("Employee is already logged in!")

        print('+++++++++++++++++++++++++++++=======', employee.name)

        # Create a new session
        return self.create({"employee_id": employee.id})

    @api.model
    def logout_employee(self, employee_id):
        session = self.search([("employee_id", "=", employee_id), ("active", "=", True)], limit=1)
        if session:
            session.write({"active": False})  # Mark session inactive
        return True
