# -*- coding: utf-8 -*-
{
    'name': 'Multiple Purchase Order With Single GRN',
    'category': 'Warehouses',
    'author': "Appscomp Widgets Pvt Ltd",
    'website': "http://www.appscomp.com",
    'version': '17.8',
    'license': 'LGPL-3',
    'summary': 'Record purchase orders by supplier, each with distinct order dates. Given that suppliers deliver GRNs '
               'in bulk, users manually input GRN entries. When entering a quantity of 1000, the system automatically'
               ' matches and displays the purchase orders that have been fulfilled and closed.',
    'sequence': 1,
    "data": [
        'security/ir.model.access.csv',
        'views/purchase_grn.xml',
    ],
    'depends': ['stock', 'purchase', 'mail'],
    'installable': True,
    'application': True,
}
