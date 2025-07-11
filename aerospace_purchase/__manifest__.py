{
    'name': 'Aerospace Purchase model',
    'version': '17.5',
    'summary': 'Aerospace Purchase model',
    'description': 'Aerospace Purchase model',
    'category': 'Human Resources',
    'author': 'Appscomp Widgets Pve Ltd.,',
    'website': 'appscomp.com',
    'license': 'LGPL-3',
    'depends': [
        'mail',
        'base',
        'purchase',
    ],
    'data': [   
        'security/ir.model.access.csv',
        'views/aerospace_view.xml',
        'reports/aerospace_report.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
