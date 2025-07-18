{
    'name': 'Quality Extension',
    'version': '17.141',
    'summary': 'Quality Extension Module',
    'description': 'Quality Extension',
    'category': 'Quality',
    'author': 'Appscomp Widgets Pvt Ltd.,',
    'website': 'appscomp.com',
    'license': 'LGPL-3',
    'depends': ['base', 'stock', 'product', 'quality_control', 'maintenance', 'mrp', 'hr_payroll_extended','purchase','hr'],
    'data': [
        'data/data.xml',
        'data/quality_sampling_data.xml',
        'data/expiry_scheduled_action.xml',
        'data/calibration_scheduled_action.xml',
        'data/spc_expiry_scheduled_action.xml',
        'data/spc_plan_month_notification.xml',
        'data/layout_inspection_plan_year_scheduled_action.xml',
        'security/user_group.xml',
        'security/ir.model.access.csv',
        'views/problem_master_view.xml',
        'views/process_master_view.xml',
        'views/incoming_inspection_view.xml',
        'views/product_template_view.xml',
        'views/quality_parameter.xml',
        'views/stock_picking.xml',
        'views/quality_menu.xml',
        'views/layout_configuration_view.xml',
        'views/setting_approval_view.xml',
        'views/line_inspection_view.xml',
        'views/self_inspection_view.xml',
        'views/final_inspection_view.xml',
        'views/layout_inspection_view.xml',
        'views/layout_inspection_plan.xml',
        'views/quality_sampling_view.xml',
        'views/mmr_list_view.xml',
        'views/mmr_location_view.xml',
        'views/calibration_request_view.xml',
        'views/spc_plan_view.xml',
        'views/spc_plan_request.xml',
        'views/inhouse_nc_view.xml',
        'views/layout_request.xml',
        'views/cleanness.xml',
        'views/msa.xml',
        'views/purchase_view.xml',
        'views/res_config_settings.xml',
        'reports/calibration_list_report.xml',
        'reports/incoming_inspection_report.xml',
        'reports/setting_approval_report.xml',
        'reports/line_inspection_report.xml',
        'reports/self_inspection_report.xml',
        'reports/final_inspection_report.xml',
        'reports/layout_inspection_report.xml',
        'reports/layout_inspection_plan_report.xml',
        'reports/inhouse_report.xml',
        'wizard/conditional_approve_view.xml',
        'wizard/calibration_list_wizard_view.xml',
        'wizard/inhouse_nc_reporting_view.xml',
        'wizard/spc_remarks_view.xml',
        'wizard/layout_wizard.xml',
        'wizard/incoming_inspection_inherit.xml',
        'data/groups.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False
}
