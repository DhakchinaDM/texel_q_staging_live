{
    'name': 'Employee Common Time Off',
    'version': '17.0.1.0.4',
    'sequence': 1,
    'license': 'LGPL-3',
    'depends': ["base", "web",'hr'],
    'module_type': '',
    'data': [
        'views/xml_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'timeoff_employee/static/src/js/timeoff.js',
            'timeoff_employee/static/src/xml/timeoff.xml',
        ],
    },
    'application': True,
}

