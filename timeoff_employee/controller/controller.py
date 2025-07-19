# controllers/employee_leave_controller.py

from odoo import http, fields
from odoo.http import request


class EmployeeLeaveController(http.Controller):

    @http.route('/employee/leave/types', type='json', auth='public', csrf=False)
    def get_leave_types(self, employee_id):
        employee = request.env['hr.employee'].sudo().browse(int(employee_id))
        company_id = employee.company_id.id if employee.company_id else False
        today = fields.Date.today()

        leave_type_domain = [
            ('company_id', 'in', [company_id, False]),
            '|',
            ('requires_allocation', '=', 'no'),
            ('has_valid_allocation', '=', True),
        ]
        leave_types = request.env['hr.leave.type'].sudo().search(leave_type_domain)

        result = []
        for lt in leave_types:
            allocations = request.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', employee.id),
                ('holiday_status_id', '=', lt.id),
                ('state', '=', 'validate'),
                ('date_from', '<=', today),
                ('date_to', '>=', today),
            ])

            total_allocated = sum(a.number_of_days_display for a in allocations)

            used = 0
            draft = 0
            for alloc in allocations:
                leaves = request.env['hr.leave'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('holiday_status_id', '=', lt.id),
                    ('state', '=', 'validate'),
                    ('date_from', '>=', alloc.date_from),
                    ('date_to', '<=', alloc.date_to),
                ])
                used += sum(l.number_of_days_display for l in leaves)

                leaves_draft = request.env['hr.leave'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('holiday_status_id', '=', lt.id),
                    ('state', '=', 'confirm'),
                    ('date_from', '>=', alloc.date_from),
                    ('date_to', '<=', alloc.date_to),
                ])
                draft += sum(l.number_of_days_display for l in leaves_draft)
            if total_allocated != 0:
                result.append({
                    'id': lt.id,
                    'name': lt.name,
                    'allocated_days': total_allocated,
                    'draft': draft,
                    'used_days': used,
                    'remaining_days': total_allocated - used,
                })

        return result

    @http.route('/employee/submit/leave', type='json', auth='public', csrf=False)
    def submit_leave(self, **kwargs):
        try:
            employee_id = int(kwargs['employee_id'])
            employee = request.env['hr.employee'].sudo().browse(employee_id)
            holiday_status_id = int(kwargs['holiday_status_id'])
            reason = kwargs.get("name", "Time Off Request")

            date_from = fields.Datetime.to_datetime(kwargs["date_from"] + " 00:00:00")
            date_to = fields.Datetime.to_datetime(kwargs["date_to"] + " 23:59:59")
            print("22222222222222222222222222222", employee_id, holiday_status_id, reason, date_from, date_to)
            leave = request.env['hr.leave'].sudo().create({
                'employee_ids': [(6, 0, [employee.id])],  # ✅ fixed
                'employee_id': employee.id,  # ✅ fixed
                'mode_company_id': request.env.company.id,
                'holiday_status_id': holiday_status_id,
                'request_date_from': date_from,
                'request_date_to': date_to,
                'name': reason,
            })
            return {'success': True, 'leave_id': leave.id}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/employee/leave/details', type='json', auth='public', csrf=False)
    def get_leave_details(self, **kwargs):
        try:
            employee_id = int(kwargs['employee_id'])
            holiday_status_id = int(kwargs['holiday_status_id'])
            today = fields.Date.today()
            allocations = request.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', employee_id),
                ('holiday_status_id', '=', holiday_status_id),
                ('state', '=', 'validate'),
                ('date_from', '<=', today),
                ('date_to', '>=', today),
            ])
            result = []
            for alloc in allocations:
                # Confirmed Leaves
                confirmed = request.env['hr.leave'].sudo().search([
                    ('employee_id', '=', employee_id),
                    ('holiday_status_id', '=', holiday_status_id),
                    ('state', '=', 'validate'),
                    ('date_from', '>=', alloc.date_from),
                    ('date_to', '<=', alloc.date_to),
                ])
                for leave in confirmed:
                    result.append({
                        'state': 'Approved',
                        'date_from': str(leave.date_from.date()),
                        'date_to': str(leave.date_to.date()),
                        'reason': leave.name,
                    })
                # Draft (Waiting for approval)
                draft = request.env['hr.leave'].sudo().search([
                    ('employee_id', '=', employee_id),
                    ('holiday_status_id', '=', holiday_status_id),
                    ('state', '=', 'confirm'),
                    ('date_from', '>=', alloc.date_from),
                    ('date_to', '<=', alloc.date_to),
                ])
                for leave in draft:
                    result.append({
                        'state': 'Waiting Approval',
                        'date_from': str(leave.date_from.date()),
                        'date_to': str(leave.date_to.date()),
                        'reason': leave.name,
                    })
            return result
        except Exception as e:
            return []

