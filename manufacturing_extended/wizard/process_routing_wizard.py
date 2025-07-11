from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ProcessRoutingWizard(models.TransientModel):
    _name = 'process.routing.wizard'
    _description = 'Process Routing Wizard'

    product_id = fields.Many2many('process.routing', string='Process Routing')

    def print_pdf(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'product_id': self.product_id.ids,
            'form': {
                'product_id': self.product_id.ids,
            }
        }
        return self.env.ref('manufacturing_extended.report_process_routing_pdf').report_action(self, data=data)


class ProcessRoutingReport(models.AbstractModel):
    _name = 'report.manufacturing_extended.process_routing_template_pdf'
    _description = 'Process Routing Report'

    def _get_report_values(self, docids, data=None):
        process_routing = data['product_id']
        domain = []
        if process_routing:
            domain.append(('id', 'in', process_routing))
        pr = self.env['process.routing'].search(domain)
        data = [{
            'part_no': str(i.product_id.default_code) + ' Operations',
            'part_operations': [{
                'operation_code': j.operation_code,
                'operation_id': j.operation_id.name,
                'description': j.operation_description,
                'workcenters_text': j.workcenters_text,
                'partner_id': j.partner_id.name,
                'type': j.type,
                'piece_weight': j.piece_weight,
                'standard_qty': j.standard_qty,
                'container_type': j.container_type.name,
                'bom': j.bom_text,
                'location': j.location,
            } for j in i.order_lines]
        } for i in pr]

        return {
            'doc_ids': docids,
            'data': data,
            'doc_model': 'process.routing.wizard',
            'name': 'Process Routing Report',
        }
