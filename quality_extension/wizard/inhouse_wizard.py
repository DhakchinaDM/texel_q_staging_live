from odoo import models, fields, api, _


class InHouseWizard(models.TransientModel):
    _name = 'in.house.wizard'
    _description = 'In House Wizard'

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    def print_pdf(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'form': {
                'start_date': self.start_date,
                'end_date': self.end_date,
            }
        }
        return self.env.ref('quality_extension.report_inhouse_nc').report_action(self, data=data)


class InHouseReport(models.AbstractModel):
    _name = 'report.quality_extension.in_house_template_pdf'
    _description = 'In House Report'

    def _get_report_values(self, docids, data=None):
        start_date = data['start_date']
        end_date = data['end_date']

        print('===start_date====', start_date)
        print('===end_date====', end_date)

        in_hnc = self.env['in.house.nc'].sudo().search([
            ('date', '>=', start_date),
            ('date', '<=', end_date)
        ])

        data_in_hnc = [{
            'date': j.date,
            'part_no': j.product_id.default_code,
            'part_name': j.product_id.name,
            'category': dict(j._fields['category'].selection).get(j.category),
            'partner_id': j.partner_id.name,
            'op_no': j.process_no.operation_no,
            'problem_id': j.problem_id.name,
            'actual': j.actual,
            'process_rejected_qty': j.process_rejected_qty,
            'for_rework_qty': j.for_rework_qty,
            'machine_no': j.machine_no.name,
            'stage': dict(j._fields['stage'].selection).get(j.stage),
            'four_m_cause': j.four_m_cause,
            'disposition_action': dict(j._fields['disposition_action'].selection).get(j.disposition_action),
        } for j in in_hnc]
        print("=====jj========", data_in_hnc)

        return {
            'doc_ids': docids,
            'data': data_in_hnc,
            'doc_model': 'in.house.wizard',
            'name': 'In House Non Conformance',
        }
