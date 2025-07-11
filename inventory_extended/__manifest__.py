{
    'name': 'Inventory Extended',
    'version': '17.28',
    'summary': '',
    'sequence': 10,
    'description': """ Stock Extended""",
    'category': 'Stock',
    'author': 'AppsComp Widgets Pvt Ltd',
    'website': 'https://www.appscomp.com',
    'depends': ['stock', 'product', 'l10n_in', 'sale', 'mrp', 'purchase'],
    'data': [
        'data/product_category.xml',
        'security/ir.model.access.csv',
        'views/product_inherit.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
