# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Akhil Ashok(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import models, fields, api, _
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from odoo.exceptions import AccessError


class AccountMove(models.Model):
    """
    Inherit AccountMove class for add merge invoice action function,
    Method:
         action_merge_invoice(self):
            Create new wizard with selected records
    """
    _inherit = "account.move"

    def action_merge_invoice(self):
        """ Method to create invoice merge wizard excluding canceled invoices """
        valid_invoices = self.filtered(lambda inv: inv.state != 'cancel')

        if not valid_invoices:
            raise ValidationError(_("All selected invoices are canceled and cannot be merged."))

        merge_invoice = self.env['merge.invoice'].create({
            'invoice_ids': [fields.Command.set(valid_invoices.ids)],
        })
        return {
            'name': _('Merge Debit Note'),
            'type': 'ir.actions.act_window',
            'res_model': 'merge.invoice',
            'view_mode': 'form',
            'res_id': merge_invoice.id,
            'target': 'new'
        }

