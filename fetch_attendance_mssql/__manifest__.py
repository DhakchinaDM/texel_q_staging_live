{
    'name': 'Fetch Attendance MSSQL',
    'version': '17.5',
    'summary': 'Fetch Attendance Data from MS Sql server',
    'description': 'Fetch Attendance Data',
    'category': 'Human Resources',
    'author': 'AppsComp Widgets Pvt Ltd',
    'website': 'appscomp.com',
    'license': 'LGPL-3',
    'depends': ['base', 'hr', 'hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'data/fetch_attendance_data.xml',
        'views/res_config_settings.xml',
        'views/hr_attendance_view.xml',
        'wizard/fetch_attendance_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fetch_attendance_mssql/static/src/js/fetch_attendance.js',
            'fetch_attendance_mssql/static/src/xml/fetch_attendance.xml',
        ],
    },
    'demo': [],
    'installable': True,
    'auto_install': False
}
