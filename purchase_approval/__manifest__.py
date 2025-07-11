{
    'name': 'Purchase Approval',
    'version': '17.40',
    'summary': 'Purchase Approval',
    'description': 'Purchase Approval',
    'category': 'Inventory',
    'author': 'Appscomp Widgets Pvt Ltd.,',
    'website': 'appscomp.com',
    'license': 'LGPL-3',
    'depends': [
        'approval',
        'purchase',
        'product',
        'purchase_request',
        'apps_tender_management',
        'base',
    ],
    'assets': {
        'web.assets_backend': [
            'purchase_approval/static/src/**/*.xml',
        ],
    },
    'data': [
        'data/approve_mail_template.xml',
        'security/ir.model.access.csv',
        'security/user_group.xml',
        'views/purchase_order_inherit.xml',        
        'wizard/force_close.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False
}
