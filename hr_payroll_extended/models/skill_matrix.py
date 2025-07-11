from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from datetime import date, datetime
import xlwt
from io import BytesIO
import base64
from base64 import b64decode, b64encode
from xlwt import easyxf, Borders
import io
import base64
from odoo.tools import base64_to_image
from PIL import Image
from openpyxl import load_workbook
import pandas as pd
from odoo.exceptions import UserError, ValidationError
import os
import PIL


class SkillMatrix(models.Model):
    _name = 'skill.matrix'
    _description = 'Skill Matrix'

    name = fields.Char(string='Name', default='New')
    employee_id = fields.Many2many('hr.employee', string='Employee',
                                   domain="""[('department_id','=',department_id)]""")
    date = fields.Date()
    department_id = fields.Many2many('hr.department', string='Department')
    skill_id = fields.Many2many('hr.skill.type', string='Skill Type')
    emp_skill_id = fields.Many2many('hr.skill', string='Skills', domain="[('skill_type_id', 'in', skill_id)]")
    file_name = fields.Char('File Name')
    report_printed = fields.Boolean('Report')
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    data_html = fields.Html(string='Excel Data', readonly=True)
    is_executed = fields.Boolean(string='Is Executed')
    summary_file = fields.Binary('Skill Matrix')
    entry_type = fields.Selection([('all', 'All Skill'), ('assigned', 'Assigned Skill')], default="all",
                                  string='Entry Type', )
    single_employee_id = fields.Many2one('hr.employee', string=' Employee',
                                         domain="""[('department_id','=',department_id)]""")

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.sudo().env['ir.sequence'].next_by_code('skill.matrix') or '/'
        return super().create(vals_list)

    def download_excel(self):
        self.print_skill_matrix()
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=skill.matrix&id=%s&field=summary_file&download=true&filename=SkillMatrix.xlsx' % self.id,
            'target': 'new',
        }

    def print_skill_matrix(self):
        workbook = xlwt.Workbook()
        worksheet1 = workbook.add_sheet('Skill Matrix')
        design_15 = easyxf('align: horiz center, vert center; font: bold 1, height 320;')
        design_16 = easyxf('align: horiz center, vert center; font: height 200;')
        design_18 = easyxf('align: horiz center, vert center; font: bold 1, height 200;')
        design_20 = easyxf('align: horiz left, vert center; font: height 200;')
        design_21 = easyxf('align: horiz center, vert center; font: height 200;')

        for i in range(0, 14):
            worksheet1.col(i).width = 6000
        worksheet1.col(1).width = 256 * 30
        worksheet1.row(0).height_mismatch = True
        worksheet1.row(0).height = 800
        worksheet1.row(2).height = 450
        worksheet1.row(3).height = 450

        rows = 0
        col = 0
        worksheet1.set_panes_frozen(True)
        worksheet1.set_horz_split_pos(rows + 5)
        worksheet1.set_vert_split_pos(col + 1)

        if self.company_id.logo:
            image_data = base64.b64decode(self.company_id.logo)
            image_path = '/tmp/project_image.bmp'
            with open(image_path, 'wb') as img_file:
                img_file.write(image_data)
            image = Image.open(image_path)
            image = image.convert('RGB')
            image.thumbnail((170, 35))
            image.save(image_path, format='BMP')
            worksheet1.insert_bitmap(image_path, rows, 0)
            os.remove(image_path)

        cell_style_logo = easyxf()
        worksheet1.write_merge(rows, rows, 0, 1, '', cell_style_logo)
        worksheet1.write_merge(rows, rows, 2, 8, str(self.company_id.name), design_15)
        rows += 1

        # Company address
        address = ' '.join(filter(None, [
            self.company_id.street,
            self.company_id.street2,
            self.company_id.state_id.name,
            self.company_id.zip
        ]))
        worksheet1.write_merge(rows, rows, 0, 8, address, design_16)
        rows += 1

        # Title
        title = "Skill Matrix"
        worksheet1.write_merge(rows, rows, 0, 8, title, design_15)
        rows += 1

        skill_types = self.env['hr.skill.type'].search([('id', 'in', self.skill_id.ids)]) if self.skill_id else \
            self.env['hr.skill.type'].search([])
        skills = {skill_type.name: self.env['hr.skill'].search([('skill_type_id', '=', skill_type.id)]) for skill_type
                  in skill_types}

        worksheet1.write(rows, 0, 'Employee', design_18)
        worksheet1.write(rows, 1, 'Employee Image', design_18)
        col = 2
        for skill_type in skill_types:
            skill_names = [skill.name for skill in skills[skill_type.name]] if skills[skill_type.name] else ['-']
            if col + len(skill_names) - 1 > 255:
                continue
            worksheet1.write_merge(rows, rows, col, col + len(skill_names) - 1, skill_type.name, design_18)
            col += len(skill_names)

        rows += 1
        col = 2
        for skill_type in skill_types:
            for skill in skills[skill_type.name]:
                if col > 255:
                    print(f"Warning: Writing skill '{skill.name}' exceeds column limit. Stopping.")
                    break
                worksheet1.write(rows, col, skill.name, design_18)
                col += 1
            if not skills[skill_type.name]:
                if col > 255:
                    break
                worksheet1.write(rows, col, '-', design_18)
                col += 1

        rows += 1
        custom_color_index = 0x21
        domain = []

        if self.employee_id:
            domain.append(('id', 'in', self.employee_id.ids))
        if self.department_id:
            domain.append(('department_id', 'in', self.department_id.ids))
        if self.employee_id and self.department_id:
            domain.append(('id', 'in', self.employee_id.ids))
            domain.append(('department_id', 'in', self.department_id.ids))

        employees = self.env['hr.employee'].search(domain)
        for employee in employees:
            worksheet1.write(rows, 0, employee.name, design_20)
            if employee.image_1920:
                try:
                    image_data = base64.b64decode(employee.image_1920)
                    image_path = '/tmp/project_image.bmp'
                    with open(image_path, 'wb') as img_file:
                        img_file.write(image_data)
                    image = Image.open(image_path)
                    image = image.convert('RGB')
                    image.thumbnail((150, 45))
                    image.save(image_path, format='BMP')
                    worksheet1.insert_bitmap(image_path, rows, 1)
                    os.remove(image_path)
                except (base64.binascii.Error, PIL.UnidentifiedImageError, Exception) as e:
                    print(f"Error processing image for employee {employee.name}: {e}")

            rows += 2
            col = 2

            for skill_type in skill_types:
                for skill in skills[skill_type.name]:
                    if col > 255:
                        print(f"Warning: Writing skill level for '{skill.name}' exceeds column limit. Stopping.")
                        break

                    skill_record = self.env['hr.employee.skill'].search(
                        [('employee_id', '=', employee.id), ('skill_id', '=', skill.id)], limit=1)
                    skill_level = skill_record.skill_level_id.name if skill_record else '-'
                    if skill_record and skill_record.skill_level_id.color:
                        color = skill_record.skill_level_id.color.lstrip('#')
                        if len(color) == 6:
                            r = int(color[0:2], 16)
                            g = int(color[2:4], 16)
                            b = int(color[4:6], 16)
                            xlwt.add_palette_colour(f'custom_color_{custom_color_index}', custom_color_index)
                            workbook.set_colour_RGB(custom_color_index, r, g, b)
                            custom_style = easyxf(
                                f'align: horiz center, vert center; font: height 200; pattern: pattern solid, fore_colour custom_color_{custom_color_index};')
                            worksheet1.write(rows, col, skill_level, custom_style)
                            custom_color_index += 1
                        else:
                            worksheet1.write(rows, col, skill_level, design_21)
                    else:
                        worksheet1.write(rows, col, skill_level, design_21)
                    col += 1

                if not skills[skill_type.name]:
                    if col > 255:
                        break
                    worksheet1.write(rows, col, '-', design_21)
                    col += 1

            rows += 1

        fp = BytesIO()
        workbook.save(fp)
        fp.seek(0)
        excel_file = base64.b64encode(fp.read())
        self.write({
            'summary_file': excel_file,
            'file_name': 'Employee Skill Matrix.xls',
            'report_printed': True
        })
        fp.close()
        return {
            'view_mode': 'form',
            'name': 'Skill Matrix',
            'res_id': self.id,
            'res_model': 'skill.matrix',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'target': 'new',
        }

    def get_excel_data(self):
        for rec in self:
            rec.data_html = False
            domain = []

            if self.entry_type == 'all':
                if self.employee_id:
                    domain.append(('id', 'in', self.employee_id.ids))
                if self.department_id:
                    domain.append(('department_id', 'in', self.department_id.ids))
                if self.employee_id and self.department_id:
                    domain.append(('id', 'in', self.employee_id.ids))
                    domain.append(('department_id', 'in', self.department_id.ids))
                employees = self.env['hr.employee'].search(domain)

            elif self.entry_type == 'assigned':
                if self.single_employee_id:
                    employees = self.env['hr.employee'].search([('id', '=', self.single_employee_id.id)])
                else:
                    employees = self.env['hr.employee']

            data = [{
                'employee': emp.name,
                'employee_id': emp.id,
                'employee_image': emp.image_1920 if emp.image_1920 else None
            } for emp in employees]

            # Fetch Skill Types linked to employees
            skill_types = self.env['hr.skill.type'].search([('id', 'in', self.skill_id.ids)]) if self.skill_id else \
                self.env['hr.skill.type'].search([])

            if self.entry_type == 'assigned':
                # Fetch employee skills from hr.employee.skill
                skills = {}
                for skill_type in skill_types:
                    employee_skills = self.env['hr.employee.skill'].search([
                        ('employee_id', 'in', employees.ids),
                        ('skill_id.skill_type_id', '=', skill_type.id)
                    ])

                    skills[skill_type.name] = employee_skills.mapped('skill_id')
            else:
                if self.emp_skill_id:
                    # Fetch only selected skills from hr.skill
                    skills = {
                        skill_type.name: self.env['hr.skill'].search(
                            [('id', 'in', self.emp_skill_id.ids), ('skill_type_id', '=', skill_type.id)]) for skill_type
                        in skill_types
                    }
                else:
                    # Fetch all skills from hr.skill
                    skills = {
                        skill_type.name: self.env['hr.skill'].search([('skill_type_id', '=', skill_type.id)]) for
                        skill_type in skill_types
                    }

            # Construct Table Headers
            table_header = "<th style='border:1px solid black !important;background-color: lightblue;'>Employee</th>"
            table_header += "<th style='border:1px solid black !important;background-color: lightblue;'>Employee Image</th>"
            main_headers = ""
            sub_headers = ""

            for skill_type, skill_list in skills.items():
                main_headers += f"<th style='border:1px solid black !important; background-color: lightblue;' colspan='{len(skill_list)}'>{skill_type}</th>"
                for skill in skill_list:
                    sub_headers += f"<th style='border:1px solid black !important; background-color: lightgray;' title='{skill.name}'>{skill.code}</th>"

            table_header += main_headers
            table_datas = ""

            for body in data:
                table_datas += "<tr>"
                table_datas += f"<td style='border:1px solid black !important;background-color: white;'>{body['employee']}</td>"
                if body['employee_image']:
                    image_src = f"data:image/png;base64,{body['employee_image'].decode()}"
                    table_datas += f"<td style='border:1px solid black !important;background-color: white;'>"
                    table_datas += f"<img src='{image_src}' alt='No Image' style='width:70px; height:70px;' />"
                    table_datas += "</td>"
                else:
                    table_datas += "<td style='border:1px solid black !important; background-color: white;'>No Image</td>"

                for skill_type, skill_list in skills.items():
                    for skill in skill_list:
                        skill_record = self.env['hr.employee.skill'].search(
                            [('employee_id', '=', body['employee_id']), ('skill_id', '=', skill.id)], limit=1)
                        skill_level = skill_record.skill_level_id.level_id.image
                        if skill_level:
                            image_src = f"data:image/png;base64,{skill_level.decode()}"
                            table_datas += f"<td style='border:1px solid black !important; background-color: white;'><img src='{image_src}' alt='No Image' style='width:35px; height:35px;' /></td>"
                        else:
                            table_datas += f"<td style='border:1px solid black !important; background-color: white;'><img src='skill_matrix/static/images/naa.png' alt='Level' style='height:35px;width:35px'> <img/></td>"
                table_datas += "</tr>"

            main_header_row = f"<tr style='border:1px solid black !important;background: lightblue; position: sticky; top: 0.5px; z-index: 2;outline-style: solid;outline-width: thin;'>{table_header}</tr>"
            empty_cells = '<td style="border:1px solid black !important; background-color: lightgray;"></td>' * 2
            sub_header_row = f"<tr style='border:1px solid black !important; background: lightgray; position: sticky; top: 39px; z-index: 1;outline-style: solid;outline-width: thin;'>{empty_cells}{sub_headers}</tr>"

            html_table = f"""
                <div style="overflow:auto; max-height: 400px;">
                    <table class="table text-center table-border table-sm" style="width:max-content; border-collapse: collapse;">
                        <thead style="outline-style: solid;outline-width: thin;">
                            {main_header_row}
                            {sub_header_row}
                        </thead>
                        <tbody>
                            {table_datas}
                        </tbody>
                    </table>
                </div>
            """

            rec.data_html = html_table
            rec.report_printed = True
