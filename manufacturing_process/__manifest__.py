{
    'name': 'Manufacturing Process',
    'version': '17.2',
    'summary': '',
    'description': """ For Managing Manufacturing Process """,
    'category': 'Manufacturing',
    'author': 'AppsComp Widgets Pvt Ltd',
    'website': 'https://www.appscomp.com',
    'depends': ['base', 'purchase', 'stock', 'inventory_extended', 'mrp_plm', 'mail',
                'web_editor', 'mrp'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/part_operation_view.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
