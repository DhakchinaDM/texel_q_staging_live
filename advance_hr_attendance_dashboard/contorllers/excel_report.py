import io
import xlsxwriter
from odoo import http
from odoo.http import request
from datetime import datetime


class AttendanceController(http.Controller):

    @http.route('/attendance/download_excel', type='http', auth='user')
    def download_excel(self, **kwargs):
        print("++++++++++++++++++++++Excel report generation started++++++++++++++++++++++++++++++")
        # Get parameters from the request
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        print(")))))))))))))))))))))Start Date:", start_date)
        print(')))))))))))))))))))))End Date:', end_date)

        # Ensure valid dates
        if not start_date or not end_date:
            return request.not_found()

        # Fetch employee leave data
        employee_leave_data = request.env['hr.employee'].sudo().get_employee_leave_data({
            'start_date': start_date,
            'end_date': end_date
        })
        print(")))))))))))))))))))))Employee Leave Data:", employee_leave_data)

        employee_data = employee_leave_data.get('employee_data', [])
        dates = employee_leave_data.get('filtered_duration_dates', [])
        print(")))))))))))))))))))))Filtered Duration Dates:", dates)
        print(")))))))))))))))))))))Employee Data:", employee_data)

        # Create an in-memory Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Attendance Report')

        # Define cell formats
        bold = workbook.add_format({'bold': True})
        center_format = workbook.add_format({'align': 'center'})

        # Set headers
        headers = ['Employee Name', 'Employee Code'] + dates + ['Total Absent']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, bold)

        # Write employee data
        row = 1
        for employee in employee_data:
            print("-------------------Employee:", employee)
            worksheet.write(row, 0, employee.get('name', ''))
            worksheet.write(row, 1, employee.get('emp_code', ''))

            col = 2
            for leave_record in employee.get('leave_data', []):
                worksheet.write(row, col, leave_record.get('state', ''), center_format)
                col += 1

            worksheet.write(row, col, employee.get('total_absent_count', 0))
            row += 1

        workbook.close()
        output.seek(0)

        # Send response
        return request.make_response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', 'attachment; filename="Attendance_Report.xlsx"')
            ]
        )
