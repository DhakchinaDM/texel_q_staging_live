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


class LayoutRequest(models.Model):
    _name = 'layout.request'
    _description = 'Layout Request'
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
    name = fields.Char()
    layout_state = fields.Selection([
        ('inspector', 'Inspector'),
        ('approver', 'Approved'),
        ('re_inspect', 'Re-Inspection'),
        ('done', 'Done')
    ], string='State', default='inspector', store=True, tracking=True)
    code_no = fields.Char()
    part_no = fields.Many2one('product.template', string='Part No', domain=lambda self: self.get_finished_goods(),tracking=True)
    priority_order = fields.Integer(string="Priority Order")
    part_char_name = fields.Char(string='Part Name', tracking=True, )
    remarks = fields.Char(string='Re-Inspection Remarks', tracking=True)
    remarks_boolean = fields.Boolean("Remarks_boolean")
    part_drawing_date = fields.Date(string="Drawing Revision Date", tracking=True)
    part_drawing_no = fields.Char(string='Drawing Revision No', tracking=True)
    pdf_file = fields.Many2many('ir.attachment', string="Attachment File")
    customer_name = fields.Many2one('res.partner', string='Customer Name',tracking=True,)
    inspected_by = fields.Many2one('res.users', string='Inspected By')
    approved_by = fields.Many2one('res.users', string='Approved By')
    start_date = fields.Date("From Date")
    current_date = fields.Date("Current Date", compute='current_date_changes')
    end_date = fields.Date("Due Date", compute='end_date_changes')
    inspector = fields.Boolean("Inspector", compute='inspector_user')
    approver = fields.Boolean("Approver", compute='approver_user')
    inspection_remark = fields.Char("Inspection Remarks")
    layout_id = fields.Many2one('layout.request', string='layout_id', tracking=True)

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


    @api.depends('end_date')
    def year_calculation_selection_new(self):
        today = fields.Date.today()
        for request in self:
            if request.end_date:
                if request.layout_state == 'done':
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

                else:
                    request.year_calculation_selection = 'none'
                    request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)

            else:
                request.year_calculation_selection = 'none'
                request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)


    @api.depends('year_calculation_selection')
    def priority_order_compute_(self):
        today = fields.Date.today()
        for request in self:
            if request.end_date:
                if request.layout_state == 'done':
                    before_ten = request.end_date - timedelta(days=10)
                    if request.start_date <= today < before_ten:
                        if request.year_calculation_selection == 'live':
                            request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)


                    elif before_ten <= today < request.end_date:
                        if request.year_calculation_selection == 'on_Progress':
                            request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)


                    elif request.end_date <= today:
                        if request.year_calculation_selection == 'expired':
                            request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)


                    else:
                        if  request.year_calculation_selection == 'none':
                            request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)

                else:
                    if request.year_calculation_selection == 'none':
                        request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)

            else:
                if request.year_calculation_selection == 'none':
                    request.priority_order = PRIORITY_MAPPING.get(request.year_calculation_selection, 0)


    def current_date_changes(self):
        today = fields.Date.today()
        for i in self:
            i.current_date = today

    def inspector_btn(self):
        for i in self:
            i.layout_state = 'approver'

    def approver_btn(self):
        for i in self:
            i.layout_state = 'done'

    def re_inspection_function(self):
        view_id = self.env['layout.remarks']
        return {
            'type': 'ir.actions.act_window',
            'name': 'Re-Inspection Remarks',
            'res_model': 'layout.remarks',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': view_id.id,
            'context': {
                'default_remarks_id': self.id},
            'view_id': self.env.ref('quality_extension.layout_remarks_wizard', False).id,
            'target': 'new',
        }

    def inspector_user(self):
        for i in self:
            if i.inspected_by.id == self.env.user.id:
                i.inspector = True
            else:
                i.inspector = False

    def approver_user(self):
        for i in self:
            if i.approved_by.id == self.env.user.id:
                i.approver = True
            else:
                i.approver = False

    @api.onchange('part_no')
    def onchange_value(self):
        for i in self.part_no:
            self.part_char_name = i.name
            self.part_drawing_no = i.draw_rev_no
            self.part_drawing_date = i.draw_rev_date

    @api.depends('start_date')
    def end_date_changes(self):
        for request in self:
            if request.start_date:
                request.end_date = request.start_date + relativedelta(years=1, days=-1)
                # if request.line_id:
                #     request.line_id.early_done = request.start_date
                # if request.line_id.line_id:
                #     request.line_id.line_id.early_done = request.start_date
            else:
                request.end_date = ''

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'New':
                vals['name'] = self.sudo().env['ir.sequence'].next_by_code('layout.seq') or '/'
        res = super(LayoutRequest, self).create(vals_list)
        return res

    def default_get(self, fields_list):
        defaults = super(LayoutRequest, self).default_get(fields_list)
        user_id = self.env['ir.config_parameter'].sudo().get_param(
            'quality_extension.enable_Customer_inspect')
        user_id_2 = self.env['ir.config_parameter'].sudo().get_param(
            'quality_extension.enable_Customer_approve')
        defaults['inspected_by'] = int(user_id) if user_id else False.id
        defaults['approved_by'] = int(user_id_2) if user_id else False.id

        return defaults

    resecheduled_boolean = fields.Boolean(string='resecheduled_boolean')

    def function_create_layout(self):
        layout_search = self.env['layout.request'].search([])
        for i in layout_search:
            i.priority_values()
            if i.year_calculation_selection == 'on_Progress':
                if i.resecheduled_boolean == False:
                    layout_plan = self.env['layout.request'].create({
                        'part_no': i.part_no.id,
                        'part_char_name': i.part_char_name,
                        'part_drawing_no': i.part_drawing_no,
                        'part_drawing_date': i.part_drawing_date,
                        'customer_name': i.customer_name.id,
                        'layout_id': i.id,
                    })
                    i.resecheduled_boolean = True

    related_record = fields.Integer("record", compute='related_search_count')

    def related_search_count(self):
        for rec in self:
            rec.related_record = self.env['layout.request'].sudo().search_count([('layout_id', '=', rec.id)])

    def view_old_records(self):
            return {
                'name': _('Layout Data'),
                'type': 'ir.actions.act_window',
                'res_model': 'layout.request',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'domain': [('layout_id', '=', self.id)],
                'target': 'current'
            }


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _description = 'Res Config Settings'

    enable_Customer_inspect = fields.Many2one(
        'res.users',
        string="Inspecter By",
        help="User responsible for approving credit limits"
    )
    enable_Customer_approve = fields.Many2one(
        'res.users',
        string="Approver By",
        help="User responsible for approving credit limits"
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        user_id = IrConfigParam.get_param('quality_extension.enable_Customer_inspect', default=False)
        user_id_2 = IrConfigParam.get_param('quality_extension.enable_Customer_approve', default=False)
        res.update(
            enable_Customer_inspect=int(user_id) if user_id else False,
            enable_Customer_approve=int(user_id_2) if user_id else False,
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        user_id = self.enable_Customer_inspect.id if self.enable_Customer_inspect else False
        user_id_2 = self.enable_Customer_approve.id if self.enable_Customer_approve else False
        IrConfigParam.set_param('quality_extension.enable_Customer_inspect', user_id)
        IrConfigParam.set_param('quality_extension.enable_Customer_approve', user_id_2)
