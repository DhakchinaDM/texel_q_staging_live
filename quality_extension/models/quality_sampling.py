from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class QualitySampling(models.Model):
    _name = 'quality.sampling'
    _description = 'Quality Sampling'
    _rec_name = 'model_name'

    model_id = fields.Many2one('ir.model', string='Inspection Model', compute='_compute_inspection_model', store=True)
    model_name = fields.Char(related='model_id.name')
    model_exact = fields.Char(related='model_id.model')
    sampling_ids = fields.One2many('sampling.lines', 'quality_id')
    type = fields.Selection([
        ('raw', 'Raw'),
        ('parts', 'Parts'),
    ], string='Type')
    incoming_bool = fields.Boolean(compute='_compute_type')
    sampling_type = fields.Selection([
        ('raw', 'Incoming Inspection Raw'),
        ('parts', 'Incoming Inspection Parts'),
        ('final', 'Final Inspection'),
    ])

    @api.depends('sampling_type')
    def _compute_inspection_model(self):
        for rec in self:
            if rec.sampling_type == 'raw':
                rec.write({
                    'model_id': self.env.ref('quality_extension.model_incoming_inspection').id,
                    'type': 'raw',
                })
            elif rec.sampling_type == 'parts':
                rec.write({
                    'model_id': self.env.ref('quality_extension.model_incoming_inspection').id,
                    'type': 'parts',
                })
            elif rec.sampling_type == 'final':
                rec.write({
                    'model_id': self.env.ref('quality_extension.model_final_inspection').id,
                    'type': 'parts',
                })
            else:
                rec.write({
                    'model_id': False,
                    'type': False,
                })

    @api.constrains('sampling_type')
    def _check_name(self):
        for record in self:
            if record.model_id:
                domain = [('sampling_type', '=', record.sampling_type)]
                codes = self.search(domain)
                if len(codes) > 1:
                    for code in codes:
                        if code.id != record.id:
                            raise ValidationError(
                                _('Alert! The Model already exists.'))

    def _compute_type(self):
        for rec in self:
            rec.incoming_bool = False
            if rec.model_id.id == self.env.ref('quality_extension.model_incoming_inspection').id:
                rec.incoming_bool = True


class SamplingLines(models.Model):
    _name = 'sampling.lines'
    _description = 'Sampling Lines'

    quality_id = fields.Many2one('quality.sampling')
    min_lot_qty = fields.Integer(string='Minimum Qty')
    max_lot_qty = fields.Integer(string='Maximum Qty')
    sample_size = fields.Integer(string='Sample Size')
