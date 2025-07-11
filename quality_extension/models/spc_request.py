from odoo import fields, models, api, _
from datetime import date, timedelta, datetime
from odoo.exceptions import ValidationError, UserError
import xlwt
from io import BytesIO
import base64
from base64 import b64decode, b64encode
from xlwt import easyxf, Borders
import io
import base64
from odoo.tools import base64_to_image
from PIL import Image
from odoo.exceptions import UserError, ValidationError
import os
import PIL
from odoo import models, fields, api, _
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import calendar


class SpcRequest(models.Model):
    _name = 'spc.request'
    _description = 'SPC Request'
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char(string='')
    product_id = fields.Many2one('product.template', string='Part No')
    parameter_id = fields.Many2one('quality.parameter', string='Parameter')
    specification = fields.Char(string='Specification', required=True)
    customer_name = fields.Many2one('res.partner', string='Customer Name')
    year = fields.Many2one('payroll.year.list', string='Year')
    month = fields.Selection([
        ('jan', 'January'),
        ('feb', 'February'),
        ('mar', 'March'),
        ('apr', 'April'),
        ('may', 'May'),
        ('jun', 'June'),
        ('july', 'July'),
        ('aug', 'August'),
        ('spe', 'September'),
        ('oct', 'October'),
        ('nov', 'November'),
        ('dec', 'December'),
    ], string="Month")
    create_date = fields.Date("Date")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.sudo().env['ir.sequence'].get('spc.request') or '/'
            res = super(SpcRequest, self).create(vals)
        return res

    state = fields.Selection(
        [('process', 'In Progress'),
         ('active', 'Active'),
         ('done', 'Done')], string="State", default='process')
    attachment = fields.Binary(string="Drawing Attachment")

    def process_to_active(self):
        if self.state == 'process':
            self.write({
                'state': 'active'
            })

    def active_to_done(self):
        if self.state == 'active':
            self.write({
                'state': 'done'
            })


class SpcPlan(models.Model):
    _name = 'spc.plan'
    _description = 'SPC Plan'
    _inherit = ['mail.thread']

    name = fields.Char(string='', default='New', store=True, readonly=True)
    year = fields.Many2one('payroll.year.list', string='Year')
    rev_no = fields.Char(string='Rev No')
    prepared_by = fields.Many2one('hr.employee', string='Prepared By', required=True)
    approved_by = fields.Many2one('res.users', string='Approved By')
    spc_plan_ids = fields.One2many('spc.plan.line', 'spc_plan_id', string='SPC Plan Lines')
    product_id = fields.Many2one('product.template', string='Part No',
                                 domain=lambda self: self.get_finished_goods())
    part_name = fields.Char(string='Part Name', related='product_id.name')
    parameter_id = fields.Many2one('quality.parameter', string='Parameter')
    customer_name = fields.Many2one('res.partner', string='Customer Name')
    create_date = fields.Date("Date")
    state = fields.Selection(
        [('draft', 'Draft'),
         ('submit_for_approve', 'Approve'),
         ('approve', 'Confirm'),
         ('cancel', 'Cancel'),
         ('reject', 'Reject')],
        string="State", default='draft', required=True)
    end_year = fields.Many2one('hr.payroll.year', string='', store=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    logged_user = fields.Many2one('res.users', string='Logged User', compute='get_logged_user')

    def get_logged_user(self):
        self.logged_user = self.env.uid

    summary_file = fields.Binary(string='SPC Plan File')
    file_name = fields.Char(string='File Name')

    def draft_to_submit(self):
        if self.state == 'draft':
            self.write({
                'state': 'submit_for_approve'
            })

    def approve_to_confirm(self):
        if self.state == 'submit_for_approve':
            self.write({
                'state': 'approve'
            })

    def allow_reject(self):
        self.write({
            'state': 'reject'
        })

    def draft_submit(self):
        self.write({
            'state': 'draft'
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.sudo().env['ir.sequence'].get('spc.plan') or '/'
            res = super(SpcPlan, self).create(vals)
        return res

    @api.model
    def get_finished_goods(self):
        fg_products = self.env.ref('inventory_extended.category_finished_goods').id
        return [('categ_id', '=', fg_products)]

    @api.constrains('year')
    def one_year_check(self):
        for i in self:
            if i.year:
                domain = [('year', '=', i.year.id)]
                codes = self.search(domain)
                if len(codes) > 1:
                    for code in codes:
                        if code.id != i.id:
                            raise ValidationError(
                                _('Alert! The SPC Plan Already Exists for the Year.'))

    @api.constrains('end_year')
    def end_year_check(self):
        for i in self:
            if i.year:
                domain = [('end_year', '=', i.end_year.id)]
                codes = self.search(domain)
                if len(codes) > 1:
                    for code in codes:
                        if code.id != i.id:
                            raise ValidationError(
                                _('Alert! The SPC Plan Already Exists for the Year.'))

    def month_to_notify(self):
        mail_template = self.env.ref('quality_extension.spc_plan_template_id')
        today = datetime.now()
        spc = self.env['spc.plan.line'].search(
            [('year', '=', today.strftime('%Y')), ('month', '=', (int(today.strftime('%m')) + 1)),
             ('state', '=', 'process')])
        spc_record = []
        for rec in spc:
            rec_month = dict(rec._fields['month'].selection).get(rec.month)
            val = {
                'part_no': rec.product_id.default_code,
                'product_id': rec.product_id.name,
                'parameter': rec.parameter_id.name,
                'specification': rec.specification,
                'partner_id': rec.customer_name.name,
                'month': rec_month,
            }
            spc_record.append(val)
            rec.state = 'active'
        mail_template.with_context(spc_record=spc_record).send_mail(self.id, force_send=True)

    # def print_excel(self):
    #     workbook = xlwt.Workbook()
    #     worksheet1 = workbook.add_sheet('SPC PLAN')
    #     design_15 = easyxf(
    #         'align: horiz center, vert center; font: bold 1, height 320; pattern: pattern solid, fore_colour white;'
    #         'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
    #     design_16 = easyxf(
    #         'align: horiz center, vert center; font: bold 1, height 200; pattern: pattern solid, fore_colour white;'
    #         'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
    #     for i in range(2, 14):
    #         worksheet1.col(0).width = 1600
    #         worksheet1.col(1).width = 5000
    #         worksheet1.col(i).width = 4500
    #         worksheet1.col(14).width = 3500
    #         worksheet1.col(15).width = 3500
    #         worksheet1.col(16).width = 3500
    #         worksheet1.col(17).width = 4000
    #         worksheet1.col(18).width = 3500
    #
    #     worksheet1.row(3).height = 400
    #     worksheet1.row(4).height = 400
    #     rows = 0
    #     serial_no = 1
    #     worksheet1.set_panes_frozen(True)
    #     worksheet1.set_horz_split_pos(rows + 5)
    #
    #     if self.company_id.logo:
    #         image_data = base64.b64decode(self.company_id.logo)
    #         image_path = '/tmp/project_image.bmp'
    #         with open(image_path, 'wb') as img_file:
    #             img_file.write(image_data)
    #         image = Image.open(image_path)
    #         image = image.convert('RGB')
    #         image.thumbnail((130, 35))
    #         image.save(image_path, format='BMP')
    #         worksheet1.insert_bitmap(image_path, rows, 0)
    #         os.remove(image_path)
    #     cell_style_logo = easyxf(
    #         'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
    #     worksheet1.write_merge(0, 2, 0, 1, '', cell_style_logo)
    #     worksheet1.write_merge(0, 2, 2, 12, 'SPC PLAN', design_15)
    #     worksheet1.write_merge(rows, rows, 13, 17, 'DOC NO : QA/DI/D/03', design_16)
    #     rows += 1
    #     worksheet1.write_merge(rows, rows, 13, 17, 'REV NO : 00', design_16)
    #     rows += 1
    #     worksheet1.write_merge(rows, rows, 13, 17, 'DATE : 04.05.2020', design_16)
    #     rows += 1
    #
    #     worksheet1.write_merge(3, 4, 0, 0, '#', design_16)
    #     worksheet1.write_merge(3, 4, 1, 1, 'PART NO', design_16)
    #     worksheet1.write_merge(3, 4, 2, 2, 'PART NAME', design_16)
    #     worksheet1.write_merge(3, 4, 3, 3, 'PARAMETERS', design_16)
    #     worksheet1.write_merge(3, 4, 4, 4, 'SPECIFICATION', design_16)
    #     worksheet1.write_merge(3, 4, 5, 5, 'CUSTOMER NAME', design_16)
    #     list_of_months = list(calendar.month_name)[1:]
    #     print('=============MONTH   ===================', list_of_months)
    #     start_col = 6
    #     worksheet1.write_merge(rows, rows, start_col, start_col + len(list_of_months) - 1, 'Year & Month 2021-2022',
    #                            design_16)
    #     rows += 1
    #     for idx, month in enumerate(list_of_months):
    #         worksheet1.write(rows, start_col + idx, month, design_16)
    #     rows += 1
    #     s_no = 0
    #     for i in self.spc_plan_ids:
    #         s_no += 1
    #         worksheet1.write(rows, 0, s_no, design_16)
    #         worksheet1.write(rows, 1, i.product_id.default_code, design_16)
    #         worksheet1.write(rows, 2, i.product_id.name, design_16)
    #         worksheet1.write(rows, 3, i.parameter_id.name, design_16)
    #         worksheet1.write(rows, 4, i.specification, design_16)
    #         worksheet1.write(rows, 5, i.customer_name.name, design_16)
    #
    #     fp = BytesIO()
    #     workbook.save(fp)
    #     fp.seek(0)
    #     excel_file = base64.b64encode(fp.getvalue())
    #     fp.close()
    #
    #     self.write({
    #         'summary_file': excel_file,
    #         'file_name': 'SPC_PLAN.xls',
    #     })
    #
    #     return {
    #         'type': 'ir.actions.act_url',
    #         'url': '/web/content/?model=spc.plan&field=summary_file&download=true&id=%s&filename=spc_plan.xls' % (
    #             self.id),
    #         'target': 'new',
    #     }

    def print_excel(self):
        workbook = xlwt.Workbook()
        worksheet1 = workbook.add_sheet('SPC PLAN')

        design_15 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 320; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        design_16 = easyxf(
            'align: horiz center, vert center; font: bold 1, height 200; pattern: pattern solid, fore_colour white;'
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        for i in range(2, 14):
            worksheet1.col(0).width = 1600
            worksheet1.col(1).width = 5000
            worksheet1.col(i).width = 4500
        worksheet1.row(3).height = 400
        worksheet1.row(4).height = 400
        rows = 0
        serial_no = 1
        worksheet1.set_panes_frozen(True)
        worksheet1.set_horz_split_pos(rows + 5)
        if self.company_id.logo:
            image_data = base64.b64decode(self.company_id.logo)
            image_path = '/tmp/project_image.bmp'
            with open(image_path, 'wb') as img_file:
                img_file.write(image_data)
            image = Image.open(image_path)
            image = image.convert('RGB')
            image.thumbnail((130, 35))
            image.save(image_path, format='BMP')
            worksheet1.insert_bitmap(image_path, rows, 0)
            os.remove(image_path)
        cell_style_logo = easyxf(
            'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;')
        worksheet1.write_merge(0, 2, 0, 1, '', cell_style_logo)
        worksheet1.write_merge(0, 2, 2, 12, 'SPC PLAN', design_15)
        worksheet1.write_merge(rows, rows, 13, 17, 'DOC NO : QA/DI/D/03', design_16)
        rows += 1
        worksheet1.write_merge(rows, rows, 13, 17, f'REV NO : {self.rev_no or "00"}', design_16)
        rows += 1
        worksheet1.write_merge(rows, rows, 13, 17, f'DATE : {fields.Date.today().strftime("%d.%m.%Y")}', design_16)
        rows += 1
        worksheet1.write_merge(3, 4, 0, 0, '#', design_16)
        worksheet1.write_merge(3, 4, 1, 1, 'PART NO', design_16)
        worksheet1.write_merge(3, 4, 2, 2, 'PART NAME', design_16)
        worksheet1.write_merge(3, 4, 3, 3, 'PARAMETERS', design_16)
        worksheet1.write_merge(3, 4, 4, 4, 'SPECIFICATION', design_16)
        worksheet1.write_merge(3, 4, 5, 5, 'CUSTOMER NAME', design_16)
        list_of_months = list(calendar.month_name)[1:]
        start_col = 6
        worksheet1.write_merge(rows, rows, start_col, start_col + len(list_of_months) - 1,
                               f'Year & Month {self.year.name}', design_16)
        rows += 1
        for idx, month in enumerate(list_of_months):
            worksheet1.write(rows, start_col + idx, month, design_16)
        rows += 1
        for i in self.spc_plan_ids:
            worksheet1.write(rows, 0, serial_no, design_16)
            worksheet1.write(rows, 1, i.product_id.default_code, design_16)
            worksheet1.write(rows, 2, i.product_id.name, design_16)
            worksheet1.write(rows, 3, i.parameter_id.name, design_16)
            worksheet1.write(rows, 4, i.specification, design_16)
            worksheet1.write(rows, 5, i.customer_name.name, design_16)
            for idx, month in enumerate(list_of_months):
                if str(idx + 1) == i.month:
                    worksheet1.write(rows, start_col + idx, '✅', design_16)
                else:
                    worksheet1.write(rows, start_col + idx, '-', design_16)
            rows += 1
            serial_no += 1
        fp = BytesIO()
        workbook.save(fp)
        fp.seek(0)
        excel_file = base64.b64encode(fp.getvalue())
        fp.close()

        self.write({
            'summary_file': excel_file,
            'file_name': 'SPC_PLAN.xls',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=spc.plan&field=summary_file&download=true&id=%s&filename=spc_plan.xls' % (
                self.id),
            'target': 'new',
        }


PRIORITY_MAPPING = {
    'expired': 5,
    'reschedule': 4,
    'live': 3,
    'on_Progress': 2,
    'none': 1,
}


class SpcPlanLine(models.Model):
    _name = 'spc.plan.line'
    _description = 'SPC Request'
    _order = 'priority_order asc,create_date desc'
    _inherit = ['mail.thread']

    spc_plan_id = fields.Many2one('spc.plan')
    doc_num = fields.Char(string='Document Number', tracking=True)
    rev_num = fields.Char(string='Revision Number', tracking=True)
    rev_date = fields.Date(string='Revision Date', tracking=True)
    product_id = fields.Many2one('product.template', string='Part No',
                                 domain=lambda self: self.get_finished_products())
    line_id = fields.Many2one('spc.plan.line', string='SPC_line_id', tracking=True)
    part_name = fields.Char(string='Part Name', related='product_id.name', tracking=True)
    parameter_id = fields.Many2one('quality.parameter', string='Parameter', tracking=True)
    specification = fields.Char(string='Specification', tracking=True)
    customer_name = fields.Many2one('res.partner', string='Customer Name', tracking=True)
    month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string="Month")

    part_drawing_no = fields.Char(string='Drawing Revision No', tracking=True)
    part_drawing_date = fields.Date(string="Drawing Revision Date", tracking=True)
    spc_state = fields.Selection([
        ('none', 'None'),
        ('done', 'Done')
    ], string='Spc State', tracking=True)

    def function_state(self):
        for i in self:
            i.spc_state = 'done'

    @api.onchange('product_id')
    def revision_part_no(self):
        for i in self.product_id:
            self.part_drawing_no = i.draw_rev_no
            self.part_drawing_date = i.draw_rev_date

    name = fields.Char(string='', default='New', store=True, readonly=True)
    mmr_frequency_selection = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarter', 'Quarter'),
        ('half', 'Half-yearly'),
        ('year', 'Yearly')
    ], string='Duration', default='year')
    year_calculation_selection = fields.Selection([
        ('live', 'Live'),
        ('on_Progress', 'Deadline'),
        ('expired', 'Expired'),
        ('reschedule', 'Rescheduled'),
        ('none', 'Request')
    ], string='Year calculation', compute='year_calculation_selection_new_spc')

    priority_order = fields.Integer(string="Priority Order")
    current_date = fields.Date("Current Date",compute='current_date_changes')


    def priority_values(self):
        for request in self:
            if request.year_calculation_selection == 'reschedule':

                request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)

            if request.year_calculation_selection == 'live':

                request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)

            if request.year_calculation_selection == 'on_Progress':

                request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)

            if request.year_calculation_selection == 'expired':

                request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)

            if request.year_calculation_selection == 'none':

                request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)

    def current_date_changes(self):
        today = fields.Date.today()
        for i in self:
            i.current_date = today



    start_date = fields.Date("From Date")
    early_done = fields.Date("Early Done Date")
    end_date = fields.Date("Due Date", compute='end_date_changes')

    def function_create_spc_plan(self):
        spc_plan_search = self.env['spc.plan.line'].search([])
        for i in spc_plan_search:
            i.priority_values()
            if i.year_calculation_selection == 'on_Progress':
                if i.resecheduled_boolean == False:
                    spc_plan = self.env['spc.plan.line'].create({
                        'product_id': i.product_id.id,
                        'parameter_id': i.parameter_id.id,
                        'specification': i.specification,
                        'customer_name': i.customer_name.id,
                        'line_id': i.id,
                        'gauges_id': i.gauges_id.id,
                    })
                    spc_plan.revision_part_no()
                    i.resecheduled_boolean = True

    @api.depends('end_date')
    def year_calculation_selection_new_spc(self):
        today = fields.Date.today()
        for request in self:
            if request.end_date:
                if request.early_done:
                    if request.year_calculation_selection != 'expired':
                        if request.start_date <= request.early_done <= request.end_date:
                            request.year_calculation_selection = 'expired'
                else:
                    before_ten = request.end_date - timedelta(days=10)
                    if request.start_date <= today < before_ten:
                        request.year_calculation_selection = 'live'
                        request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)



                    elif before_ten <= today < request.end_date:
                        request.year_calculation_selection = 'on_Progress'
                        request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)


                    elif request.end_date <= today:
                        request.year_calculation_selection = 'expired'
                        request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)


                    else:
                        request.year_calculation_selection = 'none'
                        request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)



            elif request.resecheduled_boolean:
                request.year_calculation_selection = 'reschedule'
                request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)



            else:
                request.year_calculation_selection = 'none'
                request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)

    @api.depends('year_calculation_selection')
    def priority_order_spc_compute_(self):
        today = fields.Date.today()
        for request in self:
            if request.end_date:
                before_ten = request.end_date - timedelta(days=10)
                if request.start_date <= today < before_ten:
                        request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)



                elif before_ten <= today < request.end_date:
                        request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)


                elif request.end_date <= today:
                        request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)


                else:
                        request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)



            elif request.resecheduled_boolean:
                    request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)



            else:
                    request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)

    @api.depends('start_date')
    def end_date_changes(self):
        for request in self:
            if request.start_date:
                request.end_date = request.start_date + relativedelta(years=1, days=-1)
                if request.line_id:
                    request.line_id.early_done = request.start_date
                if request.line_id.line_id:
                    request.line_id.line_id.early_done = request.start_date
            else:
                request.end_date = ''



    def view_old_new_records(self):
        return {
            'name': _('SPC Plan'),
            'type': 'ir.actions.act_window',
            'res_model': 'spc.plan.line',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('line_id', '=', self.id)],
            'target': 'current'
        }

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('conditionally_approved', 'Conditionally Approved'),
        ('revisit', 'Revision')], string="State", default='draft', tracking=True)
    attachment = fields.Binary(string="SPC Graph")
    attachment_1 = fields.Binary(string="SPC Data")
    attachment_2 = fields.Binary(string="Attachment 1")
    attachment_3 = fields.Binary(string="Attachment 2")
    pdf_file = fields.Many2many('ir.attachment',string="Attachment File")
    file_name = fields.Char("File Name 1")
    file_name_1 = fields.Char("File Name 2")
    file_name_2 = fields.Char("File Name 3")
    file_name_3 = fields.Char("File Name 4")
    year = fields.Many2one('payroll.year.list', string='Year', related='spc_plan_id.year')
    process_capability = fields.Char(string='Process Capability', help='CP')
    capability_boolean = fields.Boolean(string='capability_boolean', compute='onchange_process_capability')
    resecheduled_boolean = fields.Boolean(string='resecheduled_boolean')
    text = fields.Char()
    related_record = fields.Integer("record", compute='related_search_count')

    def related_search_count(self):
        for rec in self:
            rec.related_record = self.env['spc.plan.line'].sudo().search_count([('line_id', '=', rec.id)])

    @api.onchange('process_capability')
    def onchange_process_capability(self):
        for i in self:
            if i.process_capability:
                if float(i.process_capability) < 1.67:
                    i.capability_boolean = True
                    i.text = 'The CPK must be 1.67 and above!!\nKindly reschedule it.'
                else:
                    i.capability_boolean = False
                    i.text = ''
            else:
                i.capability_boolean = False
                i.text = ''

    def values_for_resecheduled(self):
        for i in self:
            spc_plan = self.env['spc.plan.line'].create({
                'product_id': i.product_id.id,
                'parameter_id': i.parameter_id.id,
                'specification': i.specification,
                'customer_name': i.customer_name.id,
                'line_id': i.id,
                'gauges_id': i.gauges_id.id,
            })
            i.resecheduled_boolean = True

    product_capability = fields.Char(string='Product Capability', help='CPK')
    gauges_id = fields.Many2one('mmr.list', string='Gauges', )

    conditional_approve_remark = fields.Text('First Approve Remarks')
    conditional_approve_remark_time = fields.Datetime()
    first_approve = fields.Many2one('res.users', string='First Approve')
    second_approve = fields.Many2one('res.users', string='Second Approve')
    revision_count = fields.Integer(string='Revision Count', compute='_compute_revision_count')
    conditional_approve_remark_two = fields.Text('Second Approve Remarks')
    conditional_approve_remark_two_time = fields.Datetime()
    first_approve_done = fields.Boolean()
    done_bool = fields.Boolean()
    reject_remark = fields.Text('Revision Remarks')
    first_approve_reject = fields.Many2one('res.users')
    approve_remark_time = fields.Datetime()
    reject_remark_2 = fields.Text()
    first_approve_reject_2 = fields.Many2one('res.users')
    approve_remark_time_2 = fields.Datetime()

    # @api.depends('product_id', 'parameter_id')
    # def compute_gauges(self):
    #     for i in self:
    #         gauge = False
    #         if i.product_id and i.parameter_id:
    #             gauge = self.env['mmr.list'].search([
    #                 ('part_name', '=', i.product_id.id), ('parameter_id', '=', i.parameter_id.id)
    #             ])
    #         i.gauges_id = gauge

    def action_approve(self):
        if self.attachment:
            self.write({
                'state': 'approved',
                'done_bool': True,
            })
        else:
            raise UserError(_("Please upload an Attachment."))

    def action_conditionally_approve(self):
        self.write({
            'state': 'conditionally_approved'
        })

    def action_revision(self):
        base_name = self.name.split('-')[-1]
        existing_revisions = self.search_count([
            ('spc_plan_id', '=', self.spc_plan_id.id),
            ('name', 'like', f'R%-{base_name}')
        ])
        new_revision_number = existing_revisions + 1
        new_revision_name = f'R{new_revision_number}-{base_name}'
        new_record_vals = {
            'spc_plan_id': self.spc_plan_id.id,
            'product_id': self.product_id.id,
            'parameter_id': self.parameter_id.id,
            'specification': self.specification,
            'customer_name': self.customer_name.id,
            'month': self.month,
            'name': new_revision_name,
            'state': 'draft',
            'attachment': self.attachment,
            'file_name': self.file_name,
            'year': self.year.id,
            'process_capability': self.process_capability,
            'product_capability': self.product_capability,
            'gauges_id': self.gauges_id.id,
        }
        self.create(new_record_vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'New':
                vals['name'] = self.sudo().env['ir.sequence'].next_by_code('spc.plan.line') or '/'
        res = super(SpcPlanLine, self).create(vals_list)
        return res

    @api.model
    def get_finished_products(self):
        fg_products = self.env.ref('inventory_extended.category_finished_goods').id
        return [('categ_id', '=', fg_products)]

    @api.depends('name')
    def _compute_revision_count(self):
        for record in self:
            base_name = record.name.split('-')[-1]
            revision_records = self.env['spc.plan.line'].search_count([
                ('spc_plan_id', '=', record.spc_plan_id.id),
                ('name', 'like', f'R%-{base_name}')
            ])
            record.revision_count = revision_records

    def view_revision(self):
        base_name = self.name.split('-')[-1]
        return {
            'name': _('Revision'),
            'type': 'ir.actions.act_window',
            'res_model': 'spc.plan.line',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [
                ('spc_plan_id', '=', self.spc_plan_id.id),
                ('name', 'like', f'R%-{base_name}')
            ],
            'target': 'current'
        }

    def open_conditional_approve(self):
        view_id = self.env['spc.approve.remarks']
        return {
            'type': 'ir.actions.act_window',
            'name': 'Conditional Approve Remarks',
            'res_model': 'spc.approve.remarks',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': view_id.id,
            'view_id': self.env.ref('quality_extension.spc_remarks_wizard', False).id,
            'target': 'new',
        }

    def open_reject_approve(self):
        view_id = self.env['spc.reject.remarks']
        return {
            'type': 'ir.actions.act_window',
            'name': 'Revision Remarks',
            'res_model': 'spc.reject.remarks',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': view_id.id,
            'view_id': self.env.ref('quality_extension.spc_reject_wizard', False).id,
            'target': 'new',
        }
