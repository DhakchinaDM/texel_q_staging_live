{
    'name': 'employee screeen',
    'version': '17.0.1.0.4',
    'sequence': 1,
    'license': 'LGPL-3',
    'depends': ["base", "web",'hr','hr_attendance'],
    'module_type': '',
    'data': [
        'views/xml_view.xml',
        'views/attendance.xml',
        'views/id_card.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'employee_face_tracking/static/src/js/employee.js',
            'employee_face_tracking/static/src/xml/employee.xml',
        ],
    },
    'application': True,
}

