# -*- coding: utf-8 -*-
{
    'name': "Maintenance Extended",
    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    'description': """
        Long description of module's purpose
    """,
    'author': "My Company",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '17.83',
    'depends': ['base', 'maintenance', 'mail', 'stock', 'account',
                'web_editor','purchase_request','mrp_maintenance' ],
    'data': [
        'security/user_group.xml',
        'data/ir_sequence.xml',
        'data/scheduled_action.xml',
        'data/maintenance_data.xml',
        'data/minimum_stock_alert_data.xml',
        'security/ir.model.access.csv',
        'views/subcategory.xml',
        'views/maintenance_request.xml',
        'views/equipment_view.xml',
        'views/equipment_category.xml',
        'views/service_view.xml',
        'views/service_request_view.xml',
        'views/company_properties.xml',
        'views/service_order_view.xml',
        'views/spare_make.xml',
        'views/check_point.xml',
        'views/preventive_maintenance_check.xml',
        'wizards/add_request_rfq.xml',
        'wizards/internal_service_wizard.xml',
        'views/list_of_critical_spares_view.xml',
        'views/corrective_maintenance.xml',
        'views/machine_history_view.xml',
        'views/purchase_view.xml',
    ],
    'demo': [
        'data/data.xml',
    ],
    'license': 'LGPL-3',
}
