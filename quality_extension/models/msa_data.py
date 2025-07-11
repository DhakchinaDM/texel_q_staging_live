from odoo import models, fields, api, _
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

PRIORITY_MAPPING = {
    'expired': 5,
    'reschedule': 4,
    'live': 3,
    'on_Progress': 2,
    'none': 1,
}


class MsaData(models.Model):
    _name = 'msa.data'
    _description = 'MSA Data'
    _order = 'priority_order asc,create_date desc'
    _inherit = ['mail.thread']

    @api.model
    def get_finished_goods(self):
        fg_products = self.env.ref('inventory_extended.category_finished_goods').id
        return [('categ_id', 'in', [fg_products]), ('type', 'in', ['product', 'consu'])]

    year_calculation_selection = fields.Selection([
        ('live', 'Live'),
        ('on_Progress', 'Deadline'),
        ('expired', 'Expired'),
        ('reschedule', 'Rescheduled'),
        ('none', 'Request')
    ], string='Year calculation', compute='year_calculation_selection_new')
    type = fields.Selection([
        ('1', 'Variable'),
        ('2', 'Attribute'),
    ], default="1", string='MSA Type', tracking=True)
    kappa = fields.Selection([
        ('1', '> 0.75 Agreement is Excellent'),
        ('2', '> 0.4 & < 0.75 Agreement is Good'),
        ('3', '< 0.4 Agreement is Poor'),
    ], string='Kappa Type', tracking=True)
    r_and_r = fields.Selection([
        ('1', 'Less than 10% - Gage system ok'),
        ('2', 'More 10% - 30% - Acceptable'),
        ('3', 'More than 30% - Unacceptable'),
    ], string='%R&R Type', tracking=True)
    ndc = fields.Selection([
        ('1', 'More than 5% - Gage system ok'),
        ('2', 'Less than 5% Not ok'),
    ], string='NDC Type', tracking=True)
    kappa_value = fields.Float(string='Kappa Value', tracking=True)
    r_value = fields.Float(string='%R&R Value', tracking=True)
    ndc_value = fields.Float(string='NDC Value', tracking=True)
    name = fields.Char()
    pdf_file = fields.Many2many('ir.attachment', string="Attachment File")
    part_no = fields.Many2one('product.template', string='Part No', domain=lambda self: self.get_finished_goods(),
                              tracking=True)
    part_char_name = fields.Char(string='Part Name', tracking=True, )
    description = fields.Char(string='Description', tracking=True, )
    range = fields.Char(string='Range/size', tracking=True, )
    part_drawing_date = fields.Date(string="Drawing Revision Date", tracking=True)
    part_drawing_no = fields.Char(string='Drawing Revision No', tracking=True)
    customer_name = fields.Many2one('res.partner', string='Customer Name', tracking=True, )
    start_date = fields.Date("From Date")
    end_date = fields.Date("Due Date", compute='end_date_changes')
    early_done = fields.Date("Early Done Date")

    priority_order = fields.Integer(string="Priority Order")
    re_inspection = fields.Date("ReInspection Date")
    re_inspection_boolean = fields.Boolean(string='ReInspection Boolean', compute='value_for_variable_and_attribute',
                                           )
    re_inspection_char = fields.Char(string='ReInspection Char', compute='value_for_variable_and_attribute_char')
    remarks = fields.Char(string='Remarks')
    msa_id = fields.Many2one('msa.data', string='MSA ID')
    related_record = fields.Integer("record", compute='related_search_count')
    resecheduled_boolean = fields.Boolean(string='resecheduled_boolean')
    approve = fields.Boolean(string='approve')

    def approver_btn(self):
        for i in self:
            i.approve = True

    def function_create_msa(self):
        layout_search = self.env['msa.data'].search([])
        for i in layout_search:
            i.priority_values()
            if i.year_calculation_selection == 'on_Progress':
                if i.resecheduled_boolean == False:
                    msa_plan = self.env['msa.data'].create({
                        'part_no': i.part_no.id,
                        'part_char_name': i.part_char_name,
                        'part_drawing_no': i.part_drawing_no,
                        'part_drawing_date': i.part_drawing_date,
                        'customer_name': i.customer_name.id,
                        'description': i.description,
                        'range': i.range,
                        'type': i.type,
                        'msa_id': i.id,
                    })
                    i.resecheduled_boolean = True

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

    def related_search_count(self):
        for rec in self:
            rec.related_record = self.env['msa.data'].sudo().search_count([('msa_id', '=', rec.id)])

    def view_old_records(self):
        return {
            'name': _('MSA Data'),
            'type': 'ir.actions.act_window',
            'res_model': 'msa.data',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('msa_id', '=', self.id)],
            'target': 'current'
        }

    def recreate_function_msa(self):
        for i in self:
            msa_plan = self.env['msa.data'].create({
                'part_no': i.part_no.id,
                'part_char_name': i.part_char_name,
                'part_drawing_no': i.part_drawing_no,
                'part_drawing_date': i.part_drawing_date,
                'description': i.description,
                'range': i.range,
                'customer_name': i.customer_name.id,
                'type': i.type,
                'msa_id': i.id,
            })
            i.re_inspection = fields.Date.today()

    def value_for_variable_and_attribute(self):
        for i in self:
            if i.type == '1':
                if i.r_and_r == "3" or i.ndc == "2":
                    i.re_inspection_boolean = True
                else:
                    i.re_inspection_boolean = False
            if i.type == '2':
                if i.kappa == "3":
                    i.re_inspection_boolean = True
                else:
                    i.re_inspection_boolean = False

    def value_for_variable_and_attribute_char(self):
        for i in self:
            if i.re_inspection_boolean == True:
                i.re_inspection_char = "There is a problem with the given value .. kindly resechedule it.."
        else:
            i.re_inspection_char = ""

    @api.onchange('kappa_value')
    def kappa_value_change(self):
        for i in self:
            if i.kappa_value:
                if i.kappa_value > 0.75:
                    i.kappa = '1'
                if 0.75 > i.kappa_value > 0.4:
                    i.kappa = '2'
                if i.kappa_value < 0.4:
                    i.kappa = '3'
            else:
                i.kappa = ''

    @api.onchange('r_value')
    def r_and_r_value_change(self):
        for i in self:
            if i.r_value:
                if i.r_value > 30:
                    i.r_and_r = '3'
                if 10 < i.r_value < 30:
                    i.r_and_r = '2'
                if i.r_value < 10:
                    i.r_and_r = '1'
            else:
                i.r_and_r = ''

    @api.onchange('ndc_value')
    def ndc_value_change(self):
        for i in self:
            if i.ndc_value:
                if i.ndc_value > 5:
                    i.ndc = '1'
                if i.ndc_value < 5:
                    i.ndc = '2'
            else:
                i.ndc = ''

    @api.depends('end_date', 'year_calculation_selection')
    @api.onchange('end_date', 'year_calculation_selection')
    def year_calculation_selection_new(self):
        today = fields.Date.today()
        for request in self:
            if request.end_date:
                if request.early_done:
                    if request.year_calculation_selection != 'expired':
                        if request.start_date <= request.early_done <= request.end_date:
                            request.year_calculation_selection = 'expired'
                else:
                    if request.re_inspection:
                        request.year_calculation_selection = 'reschedule'
                        request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)

                    elif request.start_date:
                        before_ten = request.end_date - timedelta(days=10)
                        if request.start_date <= today < before_ten:
                            if request.re_inspection_boolean == True:
                                request.year_calculation_selection = 'none'
                                request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)

                            else:
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

                    else:
                        request.year_calculation_selection = 'none'
                        request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)

            else:
                request.year_calculation_selection = 'none'
                request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)

    # @api.depends('year_calculation_selection')
    # @api.onchange('year_calculation_selection')
    # def priority_order_compute_(self):
    #     today = fields.Date.today()
    #     print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!11")
    #     for request in self:
    #         if request.end_date:
    #             if request.re_inspection:
    #                 if request.year_calculation_selection == 'reschedule':
    #                     request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)
    #
    #             elif request.start_date:
    #                 before_ten = request.end_date - timedelta(days=10)
    #                 if request.start_date <= today < before_ten:
    #                     if request.year_calculation_selection == 'live':
    #                         request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)
    #
    #                 elif before_ten <= today < request.end_date:
    #                     if request.year_calculation_selection == 'on_Progress':
    #                         request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)
    #
    #                 elif request.end_date <= today:
    #                     if request.year_calculation_selection == 'expired':
    #                         request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)
    #
    #                 else:
    #                     if request.year_calculation_selection == 'none':
    #                         request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)
    #
    #             else:
    #                 if request.year_calculation_selection == 'none':
    #                     request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)
    #
    #         else:
    #             if request.year_calculation_selection == 'none':
    #                 request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)

    @api.depends('start_date')
    def end_date_changes(self):
        for request in self:
            if request.start_date:
                request.end_date = request.start_date + relativedelta(years=1, days=-1)
                if request.msa_id:
                    request.msa_id.early_done = request.start_date
                if request.msa_id.msa_id:
                    request.msa_id.msa_id.early_done = request.start_date
            else:
                request.end_date = ''

    @api.onchange('part_no')
    def onchange_value(self):
        for i in self.part_no:
            self.part_char_name = i.name
            self.part_drawing_no = i.draw_rev_no
            self.part_drawing_date = i.draw_rev_date

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # if vals['r_value'] or vals['kappa_value'] or vals['ndc_value']  == '0.00':
            #     raise ValidationError(_('Kindly Fill The Value...'))
            if not vals.get('name') or vals['name'] == 'New':
                vals['name'] = self.sudo().env['ir.sequence'].next_by_code('msa.seq') or '/'

        res = super(MsaData, self).create(vals_list)
        return res
