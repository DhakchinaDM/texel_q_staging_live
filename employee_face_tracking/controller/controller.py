from odoo import http, fields
from odoo.http import request
import base64


class AttendanceController(http.Controller):

    @http.route('/mark/attendance', type='json', auth='user', csrf=False)
    def mark_attendance(self, **post):
        barcode = post.get('barcode')
        image_data = post.get('image_data')  # base64 image with prefix

        print(f"Received barcode: {barcode}")

        employee = request.env['hr.employee'].sudo().search([('barcode', '=', barcode)], limit=1)
        if not employee:
            return {'message': 'Employee not found.'}
        # Remove base64 header if present
        if image_data and image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        print(f"Processed image data length: {len(image_data)}")
        # Mark attendance with captured image

        existing = request.env['hr.attendance'].sudo().search(
            [('employee_id', '=', employee.id), ('check_out', '=', False)],
            limit=1
        )
        if existing:
            existing.write({
                'check_out': fields.Datetime.now(),
                'check_out_image': image_data,  # Save as binary
            })
            message = {'message': f'Attendance CheckedOut {employee.name}.'}
        else:
            request.env['hr.attendance'].sudo().create({
                'employee_id': employee.id,
                'check_in': fields.Datetime.now(),
                'check_in_image': image_data,  # Save as binary
            })
            # message = {'message': f'Attendance CheckIn {employee.name} {fields.Datetime.now()}.'}
            message = {'message': f'Attendance CheckIn {employee.name}.'}
        return message




# class HrAttendance(http.Controller):


    #
    # @http.route('/hr_attendance/face_mode_menu', auth='user', type='http')
    # def face_menu_item_action(self):
    #     # better use route with company_id suffix
    #     if request.env.user.user_has_groups("hr_attendance.group_hr_attendance_manager"):
    #         # Auto log out will prevent users from forgetting to log out of their session
    #         # before leaving the kiosk mode open to the public. This is a prevention security
    #         # measure.
    #         request.session.logout(keep_db=True)
    #         return request.redirect(request.env.company.attendance_face_url)
    #     else:
    #         return request.not_found()
    #
    # @http.route('/hr_attendance/face_mode_menu/<int:company_id>', auth='user', type='http')
    # def face_menu_item_action2(self, company_id):
    #     request.update_context(allowed_company_ids=[company_id])
    #     return self.face_menu_item_action()