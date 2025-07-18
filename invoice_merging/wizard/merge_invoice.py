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
from odoo import fields, models, _
from odoo.exceptions import AccessError
from collections import defaultdict



class MergeInvoice(models.TransientModel):
    """
    Main method to merge selected invoices
    - If user select merge to existing then the selected invoices will be
      merged to the selected record
    - If no invoice is selected, then a new record will be created with the
      existing picking lines
    """
    _name = "merge.invoice"
    _description = "Invoice Merge"

    invoice_ids = fields.Many2many('account.move', string="Selected Invoices",
                                   help="Selected invoices to merge")
    partner_id = fields.Many2one('res.partner', string="Supplier",
                                 help="The new invoice will be created"
                                      " for selected partner")

    target_invoice_id = fields.Many2one(
        'account.move', string="Merge to existing",
        help="Select a invoice if you want to merge other invoices to selected "
             "one, Otherwise leave it empty")
    merge_type = fields.Selection(
        [('cancel', 'Cancel Others'), ('keep', 'Keep Others')],
        string="Merge type", default="cancel",
        help="Select the merge type to decide what to do with other invoices")

    def action_merge_invoice(self):
        """Method for merge invoices"""
        # Checking for is there any exceptions
        if len(list(set(self.invoice_ids))) == 1:
            raise AccessError(
                _("Merging is not possible on single Invoice or Bill"))
        if any(state in ['posted', 'cancel'] for state in
               self.invoice_ids.mapped('state')):
            raise AccessError(_("Merging is only possible on draft state "
                                "Invoices or Bills"))
        if len(list(set(self.invoice_ids.mapped('move_type')))) > 1:
            raise AccessError(_("Merging is only possible for different type "
                                "moves, so please select the same type."))
        # If there is no exceptions continue with the merging
        invoices = self.invoice_ids
        invoice_lines = []
        pay_reference = []
        if self.target_invoice_id:
            target_invoice = self.target_invoice_id
            invoices -= self.target_invoice_id
            pay_reference.append(target_invoice.name if
                                 target_invoice.name != "/" else
                                 f"Draft {str(target_invoice.id)}")
        else:
            target_invoice = self.env['account.move'].with_context(
                check_move_validity=False).create(
                {'partner_id': self.partner_id.id})
        # for record in invoices:
        #     for line in record.line_ids:
        #         if line.display_type not in ["payment_term", "tax"]:
        #             invoice_lines += line.with_context(
        #                 check_move_validity=False).copy(
        #                 {'move_id': target_invoice.id})
        #     pay_reference.append(record.name if
        #                          record.name != "/" else
        #                          f"Draft {str(record.id)}")
        #     if self.merge_type == "cancel":
        #         record.button_cancel()
        # target_invoice.write(
        #     {'payment_reference': f"Merged ({(', '.join(pay_reference))})"})
        product_line_data = defaultdict(lambda: {'quantity': 0, 'price_unit': 0, 'subtotal': 0, 'tax_ids': set()})

        for record in invoices:
            for line in record.invoice_line_ids:
                if line.display_type not in ["payment_term", "tax"] and line.product_id:
                    key = line.product_id.id
                    product_line_data[key]['quantity'] += line.quantity
                    product_line_data[key]['price_unit'] = line.price_unit  # Assume same price
                    product_line_data[key]['subtotal'] += line.price_subtotal
                    product_line_data[key]['tax_ids'].update(line.tax_ids.ids)
            pay_reference.append(record.name if
                                 record.name != "/" else
                                 f"Draft {str(record.id)}")
            if self.merge_type == "cancel":
                record.button_cancel()
            target_invoice.write(
                {'payment_reference': f"Merged ({(', '.join(pay_reference))})"})

        # Create the new invoice lines in the target invoice
        for product_id, data in product_line_data.items():
            self.env['account.move.line'].with_context(check_move_validity=False).create({
                'move_id': target_invoice.id,
                'product_id': product_id,
                'quantity': data['quantity'],
                'price_unit': data['price_unit'],
                'tax_ids': [(6, 0, list(data['tax_ids']))],
                'name': self.env['product.product'].browse(product_id).name,
                'account_id': self.env['product.product'].browse(product_id)._get_product_accounts()['income'].id,
            })
