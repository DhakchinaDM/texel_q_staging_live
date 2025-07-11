{
    'name': 'Purchase Request',
    'version': '17.11',
    'summary': 'Purchase Request',
    'description': 'Purchase Request from other Department to purchase',
    'category': 'Purchase',
    'author': 'Appscomp Widgets Pvt Ltd.,',
    'website': 'appscomp.com',
    'license': 'LGPL-3',
    'depends': ['purchase', 'mail', 'base', 'hr', 'stock', 'contacts', 'res_partner_extended'],
    'data': [
        'security/ir.model.access.csv',
        'data/approve_mail_template.xml',
        'data/purchase_request.xml',
        'views/purchase_request.xml',
        'views/purchase_order_view.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False
}
