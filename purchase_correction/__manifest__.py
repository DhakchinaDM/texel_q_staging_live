{
    'name': 'Purchase Correction',
    'version': '17.17',
    'summary': 'Purchase Correction',
    'description': 'Purchase Correction',
    'category': 'Inventory',
    'author': 'Appscomp Widgets Pvt Ltd.,',
    'website': 'appscomp.com',
    'license': 'LGPL-3',
    'depends': [
        'purchase_approval', 'purchase', 'apps_tender_management',
        'purchase',
        'base',
    ],
    'assets': {
        'web.assets_backend': [
        ],
    },
    'data': [
        'data/email_template.xml',
        'data/ontime_delivery.xml',
        'views/purchase_order.xml',
        'views/product_inherit.xml',
        'views/stock_picking_inherit.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False
}
