from odoo import api, fields, models, _
from num2words import num2words
from collections import defaultdict
from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import clean_context, formatLang
from odoo.tools import frozendict, groupby, split_every

from collections import defaultdict
from markupsafe import Markup

import ast
import math
import re


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _amount_in_words(self, amount):
        return num2words(amount, lang='en').title()


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def over_all_tax_val(self):
        sale_order_line = self.env['purchase.order.line'].search([("order_id", "=", self.id)])
        ll = []
        bbbb = 1
        for j in sale_order_line:
            if j.taxes_id not in ll:
                ll.append(j.taxes_id)
        for n in ll:
            bb = n.name
            oo = bb.split(" ")
            gg = oo[1]
            if str(gg) == "GST":
                bbbb = 2
            if str(gg) == "IGST":
                bbbb = 3

        # print('&*************************************************9',gg,bb)
        return bbbb

    def over_all_tax(self):
        dict_o = {}
        contents = []
        final_tax = []
        for tax_id in self.order_line:
            tax = [tax for tax in tax_id.taxes_id]
            headers_group = [{'name': child.description, 'rowspan': 1} for t in tax if t.amount_type == 'group' for
                             child in t.children_tax_ids]
            headers_percent = [{'name': t.description, 'rowspan': 1} for t in tax if t.amount_type == 'percent']
            headers = headers_group + headers_percent
            headers.insert(0, {'name': 'Taxable Value', 'rowspan': 0})
            headers.append({'name': 'Total', 'rowspan': 0})
            dict_o['header'] = headers
            for t in tax:
                base_line = tax_id._convert_to_tax_base_line_dict()
                to_update_vals, tax_values_list = t._compute_taxes_for_single_line(base_line)
                for ll in tax_values_list:
                    final_tax.append(ll)
        grouped_taxes = defaultdict(lambda: {'amount': 0, 'base_amount': 0})
        for tax in final_tax:
            key = (tax['id'], tax['name'])  # Use ID and name as key to identify unique taxes
            tax_val = self.env['account.tax'].search([('id', '=', tax['id'])])
            parent_tax = self.env['account.tax'].search([('children_tax_ids', 'in', tax['id'])])
            if parent_tax:
                tax_val = parent_tax
            grouped_taxes[key]['name'] = tax_val.name  # Set the name to the first tax encountered
            grouped_taxes[key]['id'] = int(tax_val.amount)
            grouped_taxes[key]['amount'] += tax['amount']
            grouped_taxes[key]['base_amount'] += tax['base']
        grouped_taxes = dict(grouped_taxes)
        dict_o['content'] = grouped_taxes
        return dict_o


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _prepare_tax_totals(self, base_lines, currency, tax_lines=None, is_company_currency_requested=False):
        """ Compute the tax totals details for the business documents.
        :param base_lines:                      A list of python dictionaries created using the '_convert_to_tax_base_line_dict' method.
        :param currency:                        The currency set on the business document.
        :param tax_lines:                       Optional list of python dictionaries created using the '_convert_to_tax_line_dict'
                                                method. If specified, the taxes will be recomputed using them instead of
                                                recomputing the taxes on the provided base lines.
        :param is_company_currency_requested :  Optional boolean which indicates whether or not the company currency is
                                                requested from the function. This can typically be used when using an
                                                invoice in foreign currency and the company currency is required.

        :return: A dictionary in the following form:
            {
                'amount_total':                 The total amount to be displayed on the document, including every total
                                                types.
                'amount_untaxed':               The untaxed amount to be displayed on the document.
                'formatted_amount_total':       Same as amount_total, but as a string formatted accordingly with
                                                partner's locale.
                'formatted_amount_untaxed':     Same as amount_untaxed, but as a string formatted accordingly with
                                                partner's locale.
                'groups_by_subtotals':          A dictionary formed liked {'subtotal': groups_data}
                                                Where total_type is a subtotal name defined on a tax group, or the
                                                default one: 'Untaxed Amount'.
                                                And groups_data is a list of dict in the following form:
                    {
                        'tax_group_name':                           The name of the tax groups this total is made for.
                        'tax_group_amount':                         The total tax amount in this tax group.
                        'tax_group_base_amount':                    The base amount for this tax group.
                        'formatted_tax_group_amount':               Same as tax_group_amount, but as a string formatted accordingly
                                                                    with partner's locale.
                        'formatted_tax_group_base_amount':          Same as tax_group_base_amount, but as a string formatted
                                                                    accordingly with partner's locale.
                        'tax_group_id':                             The id of the tax group corresponding to this dict.
                        'tax_group_base_amount_company_currency':   OPTIONAL: the base amount of the tax group expressed in
                                                                    the company currency when the parameter
                                                                    is_company_currency_requested is True
                        'tax_group_amount_company_currency':        OPTIONAL: the tax amount of the tax group expressed in
                                                                    the company currency when the parameter
                                                                    is_company_currency_requested is True
                    }
                'subtotals':                    A list of dictionaries in the following form, one for each subtotal in
                                                'groups_by_subtotals' keys.
                    {
                        'name':                             The name of the subtotal
                        'amount':                           The total amount for this subtotal, summing all the tax groups
                                                            belonging to preceding subtotals and the base amount
                        'formatted_amount':                 Same as amount, but as a string formatted accordingly with
                                                            partner's locale.
                        'amount_company_currency':          OPTIONAL: The total amount in company currency when the
                                                            parameter is_company_currency_requested is True
                    }
                'subtotals_order':              A list of keys of `groups_by_subtotals` defining the order in which it needs
                                                to be displayed
            }
        """

        # ==== Compute the taxes ====

        to_process = []
        for base_line in base_lines:
            to_update_vals, tax_values_list = self._compute_taxes_for_single_line(base_line)
            to_process.append((base_line, to_update_vals, tax_values_list))

        def grouping_key_generator(base_line, tax_values):
            source_tax = tax_values['tax_repartition_line'].tax_id
            return {'tax_group': source_tax.tax_group_id}

        global_tax_details = self._aggregate_taxes(to_process, grouping_key_generator=grouping_key_generator)

        tax_group_vals_list = []
        for tax_detail in global_tax_details['tax_details'].values():
            tax_group_vals = {
                'tax_group_name': tax_detail['group_tax_details'],
                'tax_group': tax_detail['tax_group'],
                'base_amount': tax_detail['base_amount_currency'],
                'tax_amount': tax_detail['tax_amount_currency'],
                'hide_base_amount': all(
                    x['tax_repartition_line'].tax_id.amount_type == 'fixed' for x in tax_detail['group_tax_details']),
            }
            if is_company_currency_requested:
                tax_group_vals['base_amount_company_currency'] = tax_detail['base_amount']
                tax_group_vals['tax_amount_company_currency'] = tax_detail['tax_amount']

            # Handle a manual edition of tax lines.
            if tax_lines is not None:
                matched_tax_lines = [
                    x
                    for x in tax_lines
                    if x['tax_repartition_line'].tax_id.tax_group_id == tax_detail['tax_group']
                ]
                if matched_tax_lines:
                    tax_group_vals['tax_amount'] = sum(x['tax_amount'] for x in matched_tax_lines)

            tax_group_vals_list.append(tax_group_vals)

        tax_group_vals_list = sorted(tax_group_vals_list, key=lambda x: (x['tax_group'].sequence, x['tax_group'].id))

        # ==== Partition the tax group values by subtotals ====

        amount_untaxed = global_tax_details['base_amount_currency']
        amount_tax = 0.0

        amount_untaxed_company_currency = global_tax_details['base_amount']
        amount_tax_company_currency = 0.0

        subtotal_order = {}
        groups_by_subtotal = defaultdict(list)
        for tax_group_vals in tax_group_vals_list:
            tax_group = tax_group_vals['tax_group']
            tax_group_tax_name = tax_group_vals['tax_group_name'][0]['name']

            subtotal_title = tax_group.preceding_subtotal or _("Untaxed Amount")
            sequence = tax_group.sequence

            subtotal_order[subtotal_title] = min(subtotal_order.get(subtotal_title, float('inf')), sequence)
            groups_by_subtotal[subtotal_title].append({
                'group_key': tax_group.id,
                'tax_group_id': tax_group.id,
                'tax_group_name': tax_group.name,
                'tax_group_percentage': tax_group_tax_name,
                'tax_group_amount': tax_group_vals['tax_amount'],
                'tax_group_base_amount': tax_group_vals['base_amount'],
                'formatted_tax_group_amount': formatLang(self.env, tax_group_vals['tax_amount'], currency_obj=currency),
                'formatted_tax_group_base_amount': formatLang(self.env, tax_group_vals['base_amount'],
                                                              currency_obj=currency),
                'hide_base_amount': tax_group_vals['hide_base_amount'],
            })
            if is_company_currency_requested:
                groups_by_subtotal[subtotal_title][-1]['tax_group_amount_company_currency'] = tax_group_vals[
                    'tax_amount_company_currency']
                groups_by_subtotal[subtotal_title][-1]['tax_group_base_amount_company_currency'] = tax_group_vals[
                    'base_amount_company_currency']

        # ==== Build the final result ====

        subtotals = []
        for subtotal_title in sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]):
            amount_total = amount_untaxed + amount_tax
            subtotals.append({
                'name': subtotal_title,
                'amount': amount_total,
                'formatted_amount': formatLang(self.env, amount_total, currency_obj=currency),
            })
            if is_company_currency_requested:
                subtotals[-1]['amount_company_currency'] = amount_untaxed_company_currency + amount_tax_company_currency
                amount_tax_company_currency += sum(
                    x['tax_group_amount_company_currency'] for x in groups_by_subtotal[subtotal_title])

            amount_tax += sum(x['tax_group_amount'] for x in groups_by_subtotal[subtotal_title])

        amount_total = amount_untaxed + amount_tax
        amount_total_company_currency = amount_untaxed_company_currency + amount_tax_company_currency

        display_tax_base = (len(global_tax_details['tax_details']) == 1 and currency.compare_amounts(
            tax_group_vals_list[0]['base_amount'], amount_untaxed) != 0) \
                           or len(global_tax_details['tax_details']) > 1

        result = {
            'amount_untaxed': currency.round(amount_untaxed) if currency else amount_untaxed,
            'amount_total': currency.round(amount_total) if currency else amount_total,
            'formatted_amount_total': formatLang(self.env, amount_total, currency_obj=currency),
            'formatted_amount_untaxed': formatLang(self.env, amount_untaxed, currency_obj=currency),
            'groups_by_subtotal': groups_by_subtotal,
            'subtotals': subtotals,
            'subtotals_order': sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]),
            'display_tax_base': display_tax_base
        }
        if is_company_currency_requested:
            comp_currency = self.env.company.currency_id
            result['amount_total_company_currency'] = comp_currency.round(amount_total_company_currency)

        return result