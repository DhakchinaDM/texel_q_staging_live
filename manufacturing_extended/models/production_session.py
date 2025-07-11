from odoo import models, fields, api

class ProductionSession(models.Model):
    _name = 'production.session'
    _description = 'Production Session Tracking'

    emp_id = fields.Many2one('hr.employee', string="Employee")
    workcenter_id = fields.Many2one('mrp.workcenter', string="Work Center")
    job_id = fields.Many2one('mrp.workorder', string="Job")
    start_time = fields.Datetime(string="Start Time")
    elapsed_time = fields.Float(string="Elapsed Time (Seconds)", default=0)
    state = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], default='inactive', string="Session State")


    @api.model
    def get_employee_session(self, emp_code):
        """Retrieve active session for an employee."""
        return self.search_read([('emp_id.emp_code', '=', emp_code)], ["id", "emp_id", "workcenter_id", "job_id", "start_time", "elapsed_time", "state"], limit=1)

    @api.model
    def save_employee_session(self, values):
        """Create or update an employee session."""
        session = self.search([('emp_id', '=', values.get("emp_id"))], limit=1)
        print('LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLllll', values, session)
        if session:
            session.write(values)
        else:
            values['start_time'] = fields.Datetime.now()
            session = self.create(values)
            print('22222222222222222222222222222222222222222222222222222222', session)
        return session.id

    @api.model
    def clear_employee_session(self, emp_code):
        """Clear session when an employee logs out."""
        # self.search([('emp_id.emp_code', '=', emp_code)]).unlink()
        print('KKKKKKKKKKKKKKKKK')
