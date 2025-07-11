from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
import io
import base64
from odoo.exceptions import AccessError, UserError, ValidationError


class PreventiveMaintenanceCheck(models.Model):
    _name = 'preventive.maintenance.check'
    _description = 'Preventive Maintenance Check'
    _inherit = ['mail.thread.cc', 'mail.thread.main.attachment', 'mail.activity.mixin']

    user_id = fields.Many2one('res.users', string='User Name', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    logged_user = fields.Many2one('res.users', string='Logged User', compute='get_logged_user')
    active = fields.Boolean(default=True)
    doc_num = fields.Char(string='Document Number', tracking=True)
    rev_num = fields.Char(string='Revision Number', tracking=True)
    rev_date = fields.Date(string='Revision Date', tracking=True )
    name = fields.Char(string='Name', default='New')
    machine_id = fields.Many2one('maintenance.equipment', string='Machine No')
    serial_no = fields.Char(string='Serial Number', related='machine_id.serial_no')
    machine_name = fields.Char(string='Machine Name', related='machine_id.name')
    state = fields.Selection([
        ('draft', 'Next Due'),
        ('start', 'Started'),
        ('done', 'Completed'),
        ('cancel', 'Cancelled'),
    ], string='State', default='draft')
    preventive_maintenance_type = fields.Selection([
        ('annually', 'Annually'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annually', 'Semi-Annually'),
    ], string="Type ", required=True)
    plan_date = fields.Date(string='Plan Date')
    plan_hours = fields.Float(string='Plan Hours')
    actual_date = fields.Date(string='Actual Date')
    next_date_due = fields.Date(string='Next Date Due')
    pmc_count = fields.Integer(string='PMC Count', compute='_compute_pmc_count')
    remarks = fields.Text(string='Remarks')
    request_id = fields.Many2one('maintenance.request', string='Request No')
    observation_detail_ids = fields.One2many('observation.details', 'pmc_id', string='Observation Details',
                                             compute='_compute_check_point', store=True)
    next_pmc_bool = fields.Boolean(string='Next PMC Bool', copy=False)
    next_pmc_ref_id = fields.Many2one('preventive.maintenance.check', string='Next PMC Ref', copy=False)
    mc_type_id = fields.Many2one('mc.type', string='MC Type', related='machine_id.machine_type_mc_id', store=True)

    predictive_maintenance_id = fields.Many2one('corrective.maintenance', string='Predictive Maintenance Id')

    def create_predictive_maintenance(self):
        for rec in self:
            predictive_maintenance = self.env['corrective.maintenance'].create({
                'machine_id': rec.machine_id.id,
                'maintenance_type': 'preventive',
                'indentification_time': fields.Datetime.now(),
                'preventive_maintenance_id': rec.id,
            })

            rec.predictive_maintenance_id = predictive_maintenance.id
            return {
                'name': _('Predictive Maintenance'),
                'type': 'ir.actions.act_window',
                'res_model': 'corrective.maintenance',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_id': self.id,
                'domain': [('preventive_maintenance_id', '=', rec.id)],
                'target': 'current'
            }

    def get_predictive_maintenance(self):
        return {
            'name': _('Predictive Maintenance'),
            'type': 'ir.actions.act_window',
            'res_model': 'corrective.maintenance',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': self.id,
            'domain': [('preventive_maintenance_id', '=', self.id)],
            'target': 'current'
        }


    @api.constrains('observation_detail_ids')
    def restrict_check_point(self):
        for record in self:
            check_point_list = []
            for line in record.observation_detail_ids:
                if line.check_point_id:
                    if line.check_point_id in check_point_list:
                        raise ValidationError(_('Alert! The Check Point already exists.'))
                    check_point_list.append(line.check_point_id)

    @api.depends("preventive_maintenance_type")
    def _compute_check_point(self):
        for check in self:
            if check.preventive_maintenance_type:
                # check.observation_detail_ids = [(5, 0, 0)]
                check.observation_detail_ids = [(2, obs_detail.id, 0) for obs_detail in check.observation_detail_ids]
                checklist = self.env['check.point'].sudo().search(
                    [('preventive_maintenance_type', '=', check.preventive_maintenance_type),('mc_type_id', '=', check.machine_id.machine_type_mc_id.id)])
                for list in checklist:
                    if list.mc_type_id == check.machine_id.machine_type_mc_id:
                        for filtred in list:
                            check.write({
                                'observation_detail_ids': [(0, 0, {
                                    'check_point_id': i.id,
                                }) for i in filtred]
                            })
            else:
                check.observation_detail_ids = False

    def action_confirm(self):
        if not self.plan_date:
            raise ValidationError(
                f"Alert, Mr. {self.env.user.name}.\nPlease enter the Plan Date.")
        if self.plan_hours <= 0.00:
            raise ValidationError(
                f"Alert, Mr. {self.env.user.name}.\nPlease enter the Plan Hours.")
        if not self.actual_date:
            raise ValidationError(
                f"Alert, Mr. {self.env.user.name}.\nPlease enter the Actual Date.")
        if not self.observation_detail_ids:
            raise ValidationError(
                f"Alert, Mr. {self.env.user.name}.\nPlease enter the Observation Details.")
        self.write({
            'state': 'start'
        })

    def action_completed(self):
        incomplete_checkpoints = []
        for rec in self.observation_detail_ids:
            if not rec.is_completed:
                incomplete_checkpoints.append(rec.check_point_id.name)
        if incomplete_checkpoints:
            val = ", ".join(incomplete_checkpoints)
            raise ValidationError(
                f"Alert, Mr. {self.env.user.name}.\nPlease complete the Following Observation Details.\n{val}")
        data = []
        for rec in self:
            val = (0, 0, {
                'machine_id': rec.machine_id.id,
                'type': 'preventive',
                'user_id': rec.user_id.id,
                'plan_date': rec.plan_date,
                'plan_hours': rec.plan_hours,
                'actual_date': rec.actual_date,
                'remarks': rec.remarks,
                'preventive_maintenance_type': rec.preventive_maintenance_type,
                'reference': 'preventive.maintenance.check,' + str(rec.id)
            })
            data.append(val)
            rec.machine_id.write({
                'machine_history_ids': data
            })

        self.write({
            'state': 'done'
        })

    def create_next_pmc(self):
        today_plus_two = date.today() + timedelta(days=10)
        records = self.env['preventive.maintenance.check'].search(
            [('state', '=', 'done'), ('next_pmc_bool', '=', False), ('next_date_due', '=', today_plus_two)])
        for record in records:
            next_pmc = self.env['preventive.maintenance.check'].create({
                'machine_id': record.machine_id.id, 'state': 'draft',
                'preventive_maintenance_type': record.preventive_maintenance_type, 'plan_date': record.next_date_due})
            record.write({'next_pmc_bool': True, 'next_pmc_ref_id': next_pmc.id})

    # def notify_not_started_pmc(self):
    #     today = fields.Date.today()
    #     pmc_ids = []
    #     records = self.env['preventive.maintenance.check'].search(
    #         [('state', '=', 'draft'), ('plan_date', '<=', today)])
    #     for record in records:
    #         pmc_ids.append(record.name)
    #     if pmc_ids:
    #         pmc = ', '.join(pmc_ids)
    #         body = f"""
    #             Dear Maintenance Team,<br/><br/>
    #             The following PMC Requests are not started yet:<br/><br/>
    #             {pmc}<br/><br/>
    #             Regards,<br/>
    #             Administrator<br/><br/>
    #             <p align="center">
    #             ----------------------------------This is a system-generated email----------------------------------------------</p>
    #         """
    #         mail_value = {
    #             'subject': 'The PMC Requests are not started yet',
    #             'body_html': body,
    #             'email_cc': "",
    #             'email_to': "",
    #             'email_from': "",
    #         }
    #         mail = self.env['mail.mail'].create(mail_value)
    #         mail.send()

    def _compute_pmc_count(self):
        for rec in self:
            rec.pmc_count = self.env['preventive.maintenance.check'].sudo().search_count(
                [('name', '=', rec.next_pmc_ref_id.name)])

    def action_pmc_count(self):
        return {
            'name': _('New PMC'),
            'type': 'ir.actions.act_window',
            'res_model': 'preventive.maintenance.check',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': self.id,
            'domain': [('name', '=', self.next_pmc_ref_id.name)],
            'target': 'current'
        }

    def action_cancel(self):
        self.write({
            'state': 'cancel'
        })

    def action_set_to_draft(self):
        self.write({
            'state': 'draft'
        })

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.sudo().env['ir.sequence'].next_by_code('preventive.maintenance.check') or '/'
        return super().create(vals_list)

    @api.onchange('actual_date', 'preventive_maintenance_type')
    def onchange_actual_date_or_preventive_maintenance_type(self):
        for record in self:
            if record.actual_date and record.preventive_maintenance_type:
                if record.preventive_maintenance_type == 'annually':
                    record.next_date_due = record.actual_date + relativedelta(years=1)
                elif record.preventive_maintenance_type == 'monthly':
                    record.next_date_due = record.actual_date + relativedelta(months=1)
                elif record.preventive_maintenance_type == 'quarterly':
                    record.next_date_due = record.actual_date + relativedelta(months=3)
                elif record.preventive_maintenance_type == 'semi_annually':
                    record.next_date_due = record.actual_date + relativedelta(months=6)
                else:
                    record.next_date_due = False

    def get_logged_user(self):
        self.logged_user = self.env.uid


# PMC HISTORY DELETED
class PmcLines(models.Model):
    _name = 'pmc.lines'
    _description = 'Pmc Lines'

    user_id = fields.Many2one('res.users', string='User Name', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    logged_user = fields.Many2one('res.users', string='Logged User', compute='get_logged_user')
    preventive_maintenance_type = fields.Selection([
        ('annually', 'Annually'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annually', 'Semi-Annually'),
    ], string="Type")
    plan_date = fields.Date(string='Plan Date')
    plan_hours = fields.Float(string='Plan Hours')
    actual_date = fields.Date(string='Actual Date')
    next_date_due = fields.Date(string='Next Date Due')
    mc_no = fields.Char(string='M/c No')
    remarks = fields.Text(string='Remarks')

    def get_logged_user(self):
        self.logged_user = self.env.uid


class CheckPoint(models.Model):
    _name = 'check.point'
    _description = 'Check Point'

    name = fields.Char(string='Name')
    method_of_check = fields.Text(string='Method of Check ')
    preventive_maintenance_type = fields.Selection([
        ('annually', 'Annually'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annually', 'Semi-Annually'),
    ])
    mc_type = fields.Char(string='MC Type ')
    mc_type_id = fields.Many2one('mc.type', string='MC Type')
    user_id = fields.Many2one('res.users', string='User Name', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    logged_user = fields.Many2one('res.users', string='Logged User', compute='get_logged_user')

    def get_logged_user(self):
        self.logged_user = self.env.uid

class McTypelist(models.Model):
    _name = 'mc.type'
    _description = 'MC Details'

    name = fields.Char(string='MC Type')


class ObservationDetails(models.Model):
    _name = 'observation.details'
    _description = 'Observation Details'

    user_id = fields.Many2one('res.users', string='User Name', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_symbol = fields.Char(
        string='Currency Symbol', default=lambda self: self.env.company.currency_id.symbol, readonly=True, )
    logged_user = fields.Many2one('res.users', string='Logged User', compute='get_logged_user')
    check_point_id = fields.Many2one('check.point', string='Check Point')
    method_of_check = fields.Text(string='Method of Check', related='check_point_id.method_of_check')
    mc_type = fields.Char(string='MC Type ', related='check_point_id.mc_type')
    observations = fields.Text(string='Observations')
    pmc_id = fields.Many2one('preventive.maintenance.check', string='PMC Id  ')
    is_completed = fields.Boolean(string='Is Completed')
    state = fields.Selection(related='pmc_id.state', store=True)

    def get_logged_user(self):
        self.logged_user = self.env.uid
