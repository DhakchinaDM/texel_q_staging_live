{
    'name': 'Location based products Screen',
    'version': '17.0.1.0.2',
    'sequence': 1,
    'license': 'LGPL-3',
    'depends': ["base", "web",'stock'],
    'module_type': '',
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/report.xml',
        'views/xml_view.xml',
        # 'views/order_line.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 'overall_reports/static/css/reserve_summary_button.css',
            'location_based_inventory/static/src/js/product.js',
            'location_based_inventory/static/src/xml/product.xml',
            # 'overall_reports/static/src/css/services.css',
        ],
    },
    'application': True,
}

