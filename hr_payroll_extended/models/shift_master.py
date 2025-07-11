from odoo import models, fields, api, _


class ShiftMaster(models.Model):
    _name = 'shift.master'
    _description = 'Shift Master'

    name = fields.Char(string='Shift Name')
    start_time = fields.Float(string="Start Time", help="Enter the time in HH:MM format.")
    end_time = fields.Float(string="End Time", help="Enter the time in HH:MM format.")

    @api.depends('name', 'start_time', 'end_time')
    def _compute_display_name(self):
        for i in self:
            i.display_name = f"{i.name} ({i.start_time:.2f} to {i.end_time:.2f})"

