from odoo import models, fields, api, _
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class CleanNess(models.Model):
    _name = 'clean.ness'
    _description = 'Clean Ness'
    _order = 'create_date desc'
    _inherit = ['mail.thread']

    @api.model
    def get_finished_goods(self):
        fg_products = self.env.ref('inventory_extended.category_finished_goods').id
        return [('categ_id', 'in', [fg_products]), ('type', 'in', ['product', 'consu'])]

    year_calculation_selection = fields.Selection([
        ('live', 'Live'),
        ('none', 'Request')
    ], default='none', string='Year calculation')
    filter_paper = fields.Selection([
        ('1', '5μ'),
        ('2', '10μ'),
        ('3', '15μ'),
        ('4', '20μ'),
        ('5', '25μ')
    ], string='Filter Paper', tracking=True)
    status = fields.Selection([
        ('accept', 'Accept'),
        ('reject', 'Reject'),
    ], string='Status', tracking=True, compute='action_accept')
    name = fields.Char()
    pdf_file = fields.Many2many('ir.attachment', string="Attachment File")
    code_no = fields.Char()
    part_no = fields.Many2one('product.template', string='Part No', domain=lambda self: self.get_finished_goods(),
                              tracking=True)
    part_char_name = fields.Char(string='Part Name', tracking=True, )
    part_drawing_date = fields.Date(string="Drawing Revision Date", tracking=True)
    part_drawing_no = fields.Char(string='Drawing Revision No', tracking=True)
    testing_result = fields.Integer(string='Testing Result', tracking=True)
    specification = fields.Integer(string='Specification', tracking=True)
    customer_name = fields.Many2one('res.partner', string='Customer Name', tracking=True, )
    start_date = fields.Date("Cleanness Date")
    re_testing = fields.Date("ReTesting Date")
    clean_id = fields.Many2one('clean.ness', "clean Id")
    re_testing_bool = fields.Boolean("boolean")
    resecheduled_boolean = fields.Boolean(string='resecheduled_boolean')
    remarks = fields.Char("Remarks")

    related_record = fields.Integer("record", compute='related_search_count')

    def related_search_count(self):
        for rec in self:
            rec.related_record = self.env['clean.ness'].sudo().search_count([('clean_id', '=', rec.id)])

    def view_old_records(self):
        return {
            'name': _('Cleanness Data'),
            'type': 'ir.actions.act_window',
            'res_model': 'clean.ness',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('clean_id', '=', self.id)],
            'target': 'current'
        }

    def state_testing(self):
        for i in self:
            i.year_calculation_selection = 'live'
            i.resecheduled_boolean = True

    # def function_create_clean(self):
    #     layout_search = self.env['clean.ness'].search([])
    #     for i in layout_search:
    #         if i.year_calculation_selection == 'on_Progress':
    #             if i.resecheduled_boolean == False:
    #                 clean_plan = self.env['clean.ness'].create({
    #                     'part_no': i.part_no.id,
    #                     'part_char_name': i.part_char_name,
    #                     'part_drawing_no': i.part_drawing_no,
    #                     'part_drawing_date': i.part_drawing_date,
    #                     'customer_name': i.customer_name.id,
    #                     'clean_id': i.id,
    #                 })
    #                 i.resecheduled_boolean = True

    def recreate_function_retesting(self):
        for i in self:
            clean_plan = self.env['clean.ness'].create({
                'part_no': i.part_no.id,
                'part_char_name': i.part_char_name,
                'part_drawing_no': i.part_drawing_no,
                'part_drawing_date': i.part_drawing_date,
                'customer_name': i.customer_name.id,
                'clean_id': i.id,
            })
            i.re_testing = fields.Date.today()
            i.re_testing_bool = True

    @api.onchange('testing_result')
    def action_accept(self):
        for rec in self:
            if rec.testing_result:
                if rec.specification < rec.testing_result:
                    rec.status = 'reject'
                else:
                    rec.status = 'accept'
            else:
                rec.status = 'accept'

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

    @api.onchange('part_no')
    def onchange_value(self):
        for i in self.part_no:
            self.part_char_name = i.name
            self.part_drawing_no = i.draw_rev_no
            self.part_drawing_date = i.draw_rev_date

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'New':
                vals['name'] = self.sudo().env['ir.sequence'].next_by_code('clean.seq') or '/'
        res = super(CleanNess, self).create(vals_list)
        return res
